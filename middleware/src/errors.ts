import { ComplianceState, TerminationReason } from './types/index.js';

export class StateTransitionError extends Error {
  constructor(
    public readonly from: ComplianceState,
    public readonly attempted: ComplianceState,
    public readonly reason: string,
  ) {
    super(`Illegal state transition ${from} → ${attempted}: ${reason}`);
    this.name = 'StateTransitionError';
  }
}

export class PHIViolationError extends Error {
  constructor(
    public readonly pattern_name: string,
    public readonly session_uuid: string,
    public readonly current_state: ComplianceState,
  ) {
    super(
      `PHI pattern "${pattern_name}" detected in session ${session_uuid} while state is ${current_state}`,
    );
    this.name = 'PHIViolationError';
  }
}

export class VerificationTimeoutError extends Error {
  constructor(
    public readonly session_uuid: string,
    public readonly timeout_ms: number,
  ) {
    super(`Verification timed out after ${timeout_ms}ms for session ${session_uuid}`);
    this.name = 'VerificationTimeoutError';
  }
}

export class TrustGateError extends Error {
  constructor(
    public readonly session_uuid: string,
    public readonly current_state: ComplianceState,
    public readonly attempted_action: string,
  ) {
    super(
      `Action "${attempted_action}" blocked: session ${session_uuid} is ${current_state}, requires TRUSTED`,
    );
    this.name = 'TrustGateError';
    this.termination_reason = TerminationReason.PHI_BEFORE_TRUST;
  }
  public readonly termination_reason: TerminationReason;
}

export class DisclosureInterruptionError extends Error {
  constructor(
    public readonly session_uuid: string,
    public readonly interrupted_at_ms: number,
  ) {
    super(
      `Disclosure interrupted at ${interrupted_at_ms}ms for session ${session_uuid} — resetting to start`,
    );
    this.name = 'DisclosureInterruptionError';
  }
}
