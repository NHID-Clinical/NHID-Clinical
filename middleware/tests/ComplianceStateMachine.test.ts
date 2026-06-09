import { ComplianceStateMachine } from '../src/state/ComplianceStateMachine';
import {
  ComplianceState,
  DisclosureStatus,
  CallerType,
  TerminationReason,
  NHIDMiddlewareConfig,
} from '../src/types';
import { StateTransitionError, TrustGateError } from '../src/errors';

const BASE_CONFIG: NHIDMiddlewareConfig = {
  nhid_uuid: 'NHID-TEST-0001',
  agent_name: 'TestAgent',
  entity_name: 'Acme Payer',
  verification_timeout_ms: 5_000,
  acknowledgement_timeout_ms: 10_000,
};

function makeSM(overrides: Partial<NHIDMiddlewareConfig> = {}): ComplianceStateMachine {
  return new ComplianceStateMachine({ ...BASE_CONFIG, ...overrides });
}

describe('ComplianceStateMachine — initial state', () => {
  test('starts in UNVERIFIED', () => {
    const sm = makeSM();
    expect(sm.getSession().current_state).toBe(ComplianceState.UNVERIFIED);
  });

  test('starts with PENDING disclosure', () => {
    const sm = makeSM();
    expect(sm.getSession().disclosure_status).toBe(DisclosureStatus.PENDING);
  });

  test('generates a session UUID', () => {
    const sm = makeSM();
    expect(sm.getSession().session_uuid).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });
});

describe('ComplianceStateMachine — UNVERIFIED → IDENTIFIED', () => {
  test('identifyCaller advances to IDENTIFIED', () => {
    const sm = makeSM();
    sm.identifyCaller('peer-001', CallerType.AI_AGENT);
    expect(sm.getSession().current_state).toBe(ComplianceState.IDENTIFIED);
  });

  test('sets remote_entity_id and caller_type', () => {
    const sm = makeSM();
    sm.identifyCaller('peer-001', CallerType.HUMAN_OPERATOR);
    const session = sm.getSession();
    expect(session.remote_entity_id).toBe('peer-001');
    expect(session.caller_type).toBe(CallerType.HUMAN_OPERATOR);
  });

  test('emits state:change event', () => {
    const sm = makeSM();
    const events: unknown[] = [];
    sm.on('state:change', (e) => events.push(e));
    sm.identifyCaller('peer-001', CallerType.AI_AGENT);
    expect(events).toHaveLength(1);
    expect((events[0] as any).from).toBe(ComplianceState.UNVERIFIED);
    expect((events[0] as any).to).toBe(ComplianceState.IDENTIFIED);
  });

  test('emits disclosure:required event', () => {
    const sm = makeSM();
    const events: unknown[] = [];
    sm.on('disclosure:required', (e) => events.push(e));
    sm.identifyCaller('peer-001', CallerType.AI_AGENT);
    expect(events).toHaveLength(1);
  });
});

describe('ComplianceStateMachine — IDENTIFIED → TRUSTED', () => {
  test('trustCaller advances to TRUSTED after disclosure completes', () => {
    const sm = makeSM();
    sm.identifyCaller('peer-001', CallerType.AI_AGENT);
    sm.markDisclosureStarted();
    sm.markDisclosureComplete();
    sm.trustCaller();
    expect(sm.getSession().current_state).toBe(ComplianceState.TRUSTED);
  });

  test('trustCaller fails if disclosure is not COMPLETE', () => {
    const sm = makeSM();
    sm.identifyCaller('peer-001', CallerType.AI_AGENT);
    sm.markDisclosureStarted();
    expect(() => sm.trustCaller()).toThrow(StateTransitionError);
  });

  test('after trustCaller failure, session is TERMINATED', () => {
    const sm = makeSM();
    sm.identifyCaller('peer-001', CallerType.AI_AGENT);
    try { sm.trustCaller(); } catch {}
    expect(sm.getSession().current_state).toBe(ComplianceState.TERMINATED);
  });
});

describe('ComplianceStateMachine — requireTrusted gate', () => {
  test('passes when TRUSTED', () => {
    const sm = makeSM();
    sm.identifyCaller('peer-001', CallerType.AI_AGENT);
    sm.markDisclosureStarted();
    sm.markDisclosureComplete();
    sm.trustCaller();
    expect(() => sm.requireTrusted('sendPHI')).not.toThrow();
  });

  test('throws TrustGateError when UNVERIFIED', () => {
    const sm = makeSM();
    expect(() => sm.requireTrusted('sendPHI')).toThrow(TrustGateError);
  });

  test('throws TrustGateError when IDENTIFIED', () => {
    const sm = makeSM();
    sm.identifyCaller('peer-001', CallerType.AI_AGENT);
    expect(() => sm.requireTrusted('sendPHI')).toThrow(TrustGateError);
  });

  test('terminates session on TrustGateError', () => {
    const sm = makeSM();
    try { sm.requireTrusted('sendPHI'); } catch {}
    expect(sm.getSession().current_state).toBe(ComplianceState.TERMINATED);
  });
});

describe('ComplianceStateMachine — forceTerminate', () => {
  test('terminates from UNVERIFIED', () => {
    const sm = makeSM();
    sm.forceTerminate(TerminationReason.EXPLICIT);
    expect(sm.getSession().current_state).toBe(ComplianceState.TERMINATED);
    expect(sm.getSession().termination_reason).toBe(TerminationReason.EXPLICIT);
  });

  test('terminates from IDENTIFIED', () => {
    const sm = makeSM();
    sm.identifyCaller('peer-001', CallerType.AI_AGENT);
    sm.forceTerminate(TerminationReason.POLICY_VIOLATION);
    expect(sm.isTerminated()).toBe(true);
  });

  test('is idempotent — second call is a no-op', () => {
    const sm = makeSM();
    const events: unknown[] = [];
    sm.on('state:terminated', (e) => events.push(e));
    sm.forceTerminate(TerminationReason.EXPLICIT);
    sm.forceTerminate(TerminationReason.EXPLICIT);
    expect(events).toHaveLength(1);
  });

  test('emits state:terminated with reason', () => {
    const sm = makeSM();
    const events: unknown[] = [];
    sm.on('state:terminated', (e) => events.push(e));
    sm.forceTerminate(TerminationReason.TIMEOUT);
    expect((events[0] as any).reason).toBe(TerminationReason.TIMEOUT);
  });
});

describe('ComplianceStateMachine — illegal transitions', () => {
  test('UNVERIFIED → TRUSTED throws', () => {
    const sm = makeSM();
    expect(() => sm.trustCaller()).toThrow(StateTransitionError);
  });

  test('TERMINATED → IDENTIFIED throws', () => {
    const sm = makeSM();
    sm.forceTerminate(TerminationReason.EXPLICIT);
    expect(() => sm.identifyCaller('x', CallerType.AI_AGENT)).toThrow(StateTransitionError);
  });

  test('TRUSTED has no further transitions', () => {
    const sm = makeSM();
    sm.identifyCaller('peer-001', CallerType.AI_AGENT);
    sm.markDisclosureStarted();
    sm.markDisclosureComplete();
    sm.trustCaller();
    expect(() => sm.trustCaller()).toThrow(StateTransitionError);
  });
});

describe('ComplianceStateMachine — timeout', () => {
  jest.useFakeTimers();

  test('auto-terminates when UNVERIFIED timeout fires', () => {
    const sm = makeSM({ verification_timeout_ms: 1_000 });
    expect(sm.getSession().current_state).toBe(ComplianceState.UNVERIFIED);
    jest.advanceTimersByTime(1_001);
    expect(sm.getSession().current_state).toBe(ComplianceState.TERMINATED);
    expect(sm.getSession().termination_reason).toBe(TerminationReason.TIMEOUT);
  });

  test('clears timeout on identifyCaller', () => {
    const sm = makeSM({ verification_timeout_ms: 1_000 });
    sm.identifyCaller('peer-001', CallerType.AI_AGENT);
    jest.advanceTimersByTime(5_000);
    expect(sm.getSession().current_state).toBe(ComplianceState.IDENTIFIED);
  });
});
