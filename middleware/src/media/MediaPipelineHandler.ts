import { EventEmitter } from 'events';
import { MediaPacket } from '../types/index.js';
import { ComplianceStateMachine } from '../state/ComplianceStateMachine.js';
import { DisclosureHandler } from './DisclosureHandler.js';
import { PHIGateway } from '../telemetry/PHIGateway.js';

/**
 * Abstract interface for WebRTC/SIP transport integration.
 * Implement this to connect NHIDMiddleware to a concrete media stack.
 *
 * Emitted events (forwarded from constituent handlers):
 *   All events from DisclosureHandler (NHID_DISCLOSURE_*, NHID_INTERRUPTION_WARN)
 *   media:inbound  (packet: MediaPacket) — after gate check passes
 *   media:blocked  (packet: MediaPacket, reason: string) — when blocked pre-TRUSTED
 */
export abstract class MediaPipelineHandler extends EventEmitter {
  protected readonly disclosureHandler: DisclosureHandler;

  constructor(
    protected readonly stateMachine: ComplianceStateMachine,
    protected readonly disclosureHandlerInstance: DisclosureHandler,
    protected readonly phiGateway: PHIGateway,
  ) {
    super();
    this.disclosureHandler = disclosureHandlerInstance;
    this.forwardDisclosureEvents();
  }

  /**
   * Send a media packet downstream.
   * Blocks with TrustGateError if session is not TRUSTED.
   */
  sendMedia(packet: MediaPacket): void {
    this.stateMachine.requireTrusted('sendMedia');
    this.transmit(packet);
  }

  /**
   * Receive an inbound packet from the remote party.
   * During disclosure (IN_PROGRESS), triggers interruption reset.
   * When data contains text, runs PHI check before emitting.
   */
  receiveMedia(packet: MediaPacket): void {
    const session = this.stateMachine.getSession();

    // Any inbound media during disclosure triggers the interruption reset loop
    if (
      session.disclosure_status === 'IN_PROGRESS' ||
      session.disclosure_status === 'INTERRUPTED'
    ) {
      this.disclosureHandlerInstance.handleRemoteMediaDetected(packet.timestamp);
      return;
    }

    this.emit('media:inbound', packet);
  }

  /** Override in concrete implementations to write to the actual transport. */
  protected abstract transmit(packet: MediaPacket): void;

  private forwardDisclosureEvents(): void {
    for (const event of [
      'NHID_DISCLOSURE_START',
      'NHID_DISCLOSURE_CHUNK',
      'NHID_DISCLOSURE_COMPLETE',
      'NHID_INTERRUPTION_WARN',
    ]) {
      this.disclosureHandlerInstance.on(event, (...args) => this.emit(event, ...args));
    }
  }
}

/**
 * No-op reference implementation for testing and simulation.
 * Logs transmitted packets instead of sending them over the wire.
 */
export class NoopMediaPipelineHandler extends MediaPipelineHandler {
  public readonly transmitted: MediaPacket[] = [];

  protected transmit(packet: MediaPacket): void {
    this.transmitted.push(packet);
  }
}
