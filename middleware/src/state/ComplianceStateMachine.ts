import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import {
  ComplianceState,
  DisclosureStatus,
  CallerType,
  TerminationReason,
  NHIDSession,
  NHIDMiddlewareConfig,
} from '../types/index.js';
import { StateTransitionError, TrustGateError } from '../errors.js';

/**
 * Emitted events:
 *   state:change    ({ from, to, session })
 *   state:terminated({ reason, session })
 *   disclosure:required(session)
 */
export class ComplianceStateMachine extends EventEmitter {
  private session: NHIDSession;
  private timeoutHandle: NodeJS.Timeout | null = null;

  constructor(private readonly config: NHIDMiddlewareConfig) {
    super();
    this.session = {
      session_uuid: uuidv4(),
      nhid_uuid: config.nhid_uuid,
      remote_entity_id: null,
      current_state: ComplianceState.UNVERIFIED,
      disclosure_status: DisclosureStatus.PENDING,
      caller_type: null,
      call_start_time: new Date(),
      state_entered_at: new Date(),
      disclosure_completed_at: null,
      termination_reason: null,
      interruption_count: 0,
    };

    this.armVerificationTimeout();
  }

  getSession(): Readonly<NHIDSession> {
    return Object.freeze({ ...this.session });
  }

  /**
   * Transitions UNVERIFIED → IDENTIFIED once the remote caller's identity
   * has been asserted (not yet verified/trusted).
   */
  identifyCaller(entity_id: string, caller_type: CallerType): void {
    this.assertCanTransition(ComplianceState.IDENTIFIED);
    this.clearTimeout();
    this.transition(ComplianceState.IDENTIFIED, {
      remote_entity_id: entity_id,
      caller_type,
    });
    this.emit('disclosure:required', this.getSession());
  }

  /**
   * Transitions IDENTIFIED → TRUSTED once full verification has passed
   * and (for human callers) explicit acknowledgement has been received.
   */
  trustCaller(): void {
    this.assertCanTransition(ComplianceState.TRUSTED);

    if (this.session.disclosure_status !== DisclosureStatus.COMPLETE) {
      this.forceTerminate(TerminationReason.POLICY_VIOLATION);
      throw new StateTransitionError(
        this.session.current_state,
        ComplianceState.TRUSTED,
        'Disclosure must be COMPLETE before TRUSTED transition',
      );
    }

    this.transition(ComplianceState.TRUSTED, {});
  }

  /**
   * Hard-terminates the session from any state.
   * Once TERMINATED, no further transitions are allowed.
   */
  forceTerminate(reason: TerminationReason): void {
    if (this.session.current_state === ComplianceState.TERMINATED) return;
    this.clearTimeout();
    const from = this.session.current_state;
    this.session = {
      ...this.session,
      current_state: ComplianceState.TERMINATED,
      termination_reason: reason,
      state_entered_at: new Date(),
    };
    this.emit('state:change', { from, to: ComplianceState.TERMINATED, session: this.getSession() });
    this.emit('state:terminated', { reason, session: this.getSession() });
  }

  markDisclosureStarted(): void {
    if (this.session.current_state === ComplianceState.TERMINATED) return;
    this.session = { ...this.session, disclosure_status: DisclosureStatus.IN_PROGRESS };
  }

  markDisclosureInterrupted(): void {
    if (this.session.current_state === ComplianceState.TERMINATED) return;
    this.session = {
      ...this.session,
      disclosure_status: DisclosureStatus.INTERRUPTED,
      interruption_count: this.session.interruption_count + 1,
    };
  }

  markDisclosureComplete(): void {
    if (
      this.session.current_state !== ComplianceState.IDENTIFIED &&
      this.session.current_state !== ComplianceState.TRUSTED
    ) {
      return;
    }
    this.session = {
      ...this.session,
      disclosure_status: DisclosureStatus.COMPLETE,
      disclosure_completed_at: new Date(),
    };
  }

  /**
   * Throws TrustGateError if the session is not TRUSTED.
   * Call this before forwarding any downstream data containing PHI.
   */
  requireTrusted(action: string): void {
    if (this.session.current_state !== ComplianceState.TRUSTED) {
      const err = new TrustGateError(
        this.session.session_uuid,
        this.session.current_state,
        action,
      );
      this.forceTerminate(err.termination_reason);
      throw err;
    }
  }

  isTerminated(): boolean {
    return this.session.current_state === ComplianceState.TERMINATED;
  }

  // ── private ──────────────────────────────────────────────────────────────

  private assertCanTransition(target: ComplianceState): void {
    const s = this.session.current_state;

    if (s === ComplianceState.TERMINATED) {
      throw new StateTransitionError(s, target, 'Session is already TERMINATED');
    }

    const allowed: Record<ComplianceState, ComplianceState[]> = {
      [ComplianceState.UNVERIFIED]: [ComplianceState.IDENTIFIED],
      [ComplianceState.IDENTIFIED]: [ComplianceState.TRUSTED],
      [ComplianceState.TRUSTED]: [],
      [ComplianceState.TERMINATED]: [],
    };

    if (!allowed[s].includes(target)) {
      this.forceTerminate(TerminationReason.POLICY_VIOLATION);
      throw new StateTransitionError(s, target, 'Transition not permitted');
    }
  }

  private transition(to: ComplianceState, patch: Partial<NHIDSession>): void {
    const from = this.session.current_state;
    this.session = {
      ...this.session,
      ...patch,
      current_state: to,
      state_entered_at: new Date(),
    };
    this.emit('state:change', { from, to, session: this.getSession() });
  }

  private armVerificationTimeout(): void {
    this.timeoutHandle = setTimeout(() => {
      if (this.session.current_state === ComplianceState.UNVERIFIED) {
        this.forceTerminate(TerminationReason.TIMEOUT);
      }
    }, this.config.verification_timeout_ms);
  }

  private clearTimeout(): void {
    if (this.timeoutHandle !== null) {
      clearTimeout(this.timeoutHandle);
      this.timeoutHandle = null;
    }
  }
}
