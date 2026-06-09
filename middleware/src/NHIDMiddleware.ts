import { EventEmitter } from 'events';
import {
  NHIDMiddlewareConfig,
  CallerType,
  TerminationReason,
  MediaPacket,
  CallerRecord,
} from './types/index.js';
import { ComplianceStateMachine } from './state/ComplianceStateMachine.js';
import { DisclosureHandler } from './media/DisclosureHandler.js';
import { NoopMediaPipelineHandler } from './media/MediaPipelineHandler.js';
import { CallerRegistry } from './identity/CallerRegistry.js';
import { RemoteCallerVerifier } from './identity/RemoteCallerVerifier.js';
import { PHIGateway } from './telemetry/PHIGateway.js';
import { NHIDComplianceLogger } from './telemetry/NHIDComplianceLogger.js';

export { ComplianceStateMachine } from './state/ComplianceStateMachine.js';
export { DisclosureHandler } from './media/DisclosureHandler.js';
export { MediaPipelineHandler, NoopMediaPipelineHandler } from './media/MediaPipelineHandler.js';
export { CallerRegistry } from './identity/CallerRegistry.js';
export { RemoteCallerVerifier } from './identity/RemoteCallerVerifier.js';
export { PHIGateway } from './telemetry/PHIGateway.js';
export { NHIDComplianceLogger } from './telemetry/NHIDComplianceLogger.js';
export * from './types/index.js';
export * from './errors.js';

/**
 * NHIDMiddleware — top-level orchestrator
 *
 * Wires together the state machine, disclosure handler, media pipeline,
 * identity verifier, and compliance logger into a single call lifecycle.
 *
 * Usage:
 *
 *   const mw = new NHIDMiddleware({ nhid_uuid: 'NHID-…', agent_name: '…', … });
 *   mw.registry.register({ entity_id: 'peer-001', … });
 *
 *   // When the remote party connects:
 *   await mw.onCallConnected('peer-001', 'Acme Health');
 *
 *   // For AI agents — pass signed proof:
 *   await mw.onCallConnected('peer-001', 'Acme Health', { proof, challenge });
 *
 *   // For human operators — pass acknowledgement flag after disclosure:
 *   await mw.onCallConnected('peer-001', 'Acme Health', { acknowledgement_received: true });
 *
 *   // Forward downstream data (blocked pre-TRUSTED):
 *   mw.sendMedia(packet);
 *
 *   // Receive inbound media (interrupts disclosure if in-progress):
 *   mw.receiveMedia(packet);
 *
 *   // Clean shutdown:
 *   mw.terminate(TerminationReason.EXPLICIT);
 */
export class NHIDMiddleware extends EventEmitter {
  public readonly registry: CallerRegistry;
  public readonly stateMachine: ComplianceStateMachine;
  public readonly disclosureHandler: DisclosureHandler;
  public readonly mediaPipeline: NoopMediaPipelineHandler;

  private readonly verifier: RemoteCallerVerifier;
  private readonly phi: PHIGateway;
  private readonly logger: NHIDComplianceLogger;

  constructor(private readonly config: NHIDMiddlewareConfig) {
    super();

    this.registry = new CallerRegistry();
    this.phi = new PHIGateway();
    this.logger = new NHIDComplianceLogger(
      config.logger ? (line) => config.logger!.log(JSON.parse(line)) : undefined,
      this.phi,
    );

    this.stateMachine = new ComplianceStateMachine(config);
    this.disclosureHandler = new DisclosureHandler(config, this.stateMachine);
    this.mediaPipeline = new NoopMediaPipelineHandler(
      this.stateMachine,
      this.disclosureHandler,
      this.phi,
    );
    this.verifier = new RemoteCallerVerifier(this.registry);

    this.wireInternalEvents();
    this.logEvent('CALL_CONNECTED');
  }

  /**
   * Primary entry point for an incoming call.
   * Looks up the caller, runs the appropriate verification path,
   * triggers disclosure, and advances state to TRUSTED on success.
   */
  async onCallConnected(
    callerId: string,
    organization: string,
    options: {
      proof?: string;
      challenge?: string;
      acknowledgement_received?: boolean;
    } = {},
  ): Promise<void> {
    const result = await this.verifier.verifyRemoteCaller(callerId, organization, options);

    if (!result.verified) {
      this.logEvent(`VERIFICATION_FAILED: ${result.failure_reason ?? 'unknown'}`);
      this.stateMachine.forceTerminate(TerminationReason.VERIFICATION_FAILURE);
      return;
    }

    // Advance to IDENTIFIED — triggers 'disclosure:required'
    this.stateMachine.identifyCaller(result.entity_id, result.caller_type);
    this.disclosureHandler.beginDisclosure();

    // Wait for disclosure to complete, then advance to TRUSTED
    await this.awaitDisclosure();

    if (this.stateMachine.isTerminated()) return;

    // Human operators require explicit post-disclosure acknowledgement
    if (result.requires_acknowledgement && !result.acknowledgement_received) {
      this.logEvent('HUMAN_ACK_MISSING');
      this.stateMachine.forceTerminate(TerminationReason.POLICY_VIOLATION);
      return;
    }

    this.stateMachine.trustCaller();
    this.logEvent('SESSION_TRUSTED');
  }

  sendMedia(packet: MediaPacket): void {
    this.mediaPipeline.sendMedia(packet);
  }

  receiveMedia(packet: MediaPacket): void {
    this.mediaPipeline.receiveMedia(packet);
  }

  terminate(reason: TerminationReason = TerminationReason.EXPLICIT): void {
    this.disclosureHandler.stopPlayback();
    this.stateMachine.forceTerminate(reason);
  }

  getSession() {
    return this.stateMachine.getSession();
  }

  // ── private ──────────────────────────────────────────────────────────────

  private awaitDisclosure(): Promise<void> {
    return new Promise((resolve) => {
      if (this.stateMachine.getSession().disclosure_status === 'COMPLETE') {
        resolve();
        return;
      }
      const onComplete = () => {
        this.disclosureHandler.off('NHID_DISCLOSURE_COMPLETE', onComplete);
        this.disclosureHandler.off('terminated', onTerminated);
        resolve();
      };
      const onTerminated = () => {
        this.disclosureHandler.off('NHID_DISCLOSURE_COMPLETE', onComplete);
        this.disclosureHandler.off('terminated', onTerminated);
        resolve();
      };
      this.disclosureHandler.once('NHID_DISCLOSURE_COMPLETE', onComplete);
      this.stateMachine.once('state:terminated', onTerminated);
    });
  }

  private wireInternalEvents(): void {
    this.stateMachine.on('state:change', (data) => {
      this.logEvent(`STATE_CHANGE:${data.from}→${data.to}`);
      this.emit('state:change', data);
    });

    this.stateMachine.on('state:terminated', (data) => {
      this.logEvent(`SESSION_TERMINATED:${data.reason}`);
      this.emit('state:terminated', data);
    });

    this.disclosureHandler.on('NHID_INTERRUPTION_WARN', (data) => {
      this.logEvent(`DISCLOSURE_INTERRUPTED:count=${data.interruption_count}`);
      this.emit('NHID_INTERRUPTION_WARN', data);
    });

    this.mediaPipeline.on('NHID_DISCLOSURE_CHUNK', (chunk) => {
      this.emit('NHID_DISCLOSURE_CHUNK', chunk);
    });

    this.mediaPipeline.on('NHID_DISCLOSURE_COMPLETE', (data) => {
      this.logEvent('DISCLOSURE_COMPLETE');
      this.emit('NHID_DISCLOSURE_COMPLETE', data);
    });
  }

  private logEvent(event: string): void {
    const entry = this.logger.buildEntry(this.stateMachine.getSession(), event);
    this.logger.log(entry);
  }
}

// Convenience factory for the most common single-call configuration
export function createNHIDMiddleware(
  nhid_uuid: string,
  agent_name: string,
  entity_name: string,
  overrides: Partial<NHIDMiddlewareConfig> = {},
): NHIDMiddleware {
  return new NHIDMiddleware({
    nhid_uuid,
    agent_name,
    entity_name,
    verification_timeout_ms: overrides.verification_timeout_ms ?? 10_000,
    acknowledgement_timeout_ms: overrides.acknowledgement_timeout_ms ?? 30_000,
    ...overrides,
  });
}
