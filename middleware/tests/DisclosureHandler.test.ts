import { ComplianceStateMachine } from '../src/state/ComplianceStateMachine';
import { DisclosureHandler } from '../src/media/DisclosureHandler';
import { CallerType, DisclosureStatus, NHIDMiddlewareConfig } from '../src/types';

const BASE_CONFIG: NHIDMiddlewareConfig = {
  nhid_uuid: 'NHID-TEST-0002',
  agent_name: 'TestAgent',
  entity_name: 'Acme Payer',
  verification_timeout_ms: 5_000,
  acknowledgement_timeout_ms: 10_000,
};

function makeHandlerPair(overrides: Partial<NHIDMiddlewareConfig> = {}) {
  jest.useFakeTimers();
  const sm = new ComplianceStateMachine({ ...BASE_CONFIG, ...overrides });
  sm.identifyCaller('peer-001', CallerType.AI_AGENT);
  const dh = new DisclosureHandler({ ...BASE_CONFIG, ...overrides }, sm);
  return { sm, dh };
}

describe('DisclosureHandler — disclosure string', () => {
  test('contains agent name', () => {
    const { dh } = makeHandlerPair();
    expect(dh.getDisclosureText()).toContain('TestAgent');
  });

  test('contains entity name', () => {
    const { dh } = makeHandlerPair();
    expect(dh.getDisclosureText()).toContain('Acme Payer');
  });

  test('contains nhid_uuid', () => {
    const { dh } = makeHandlerPair();
    expect(dh.getDisclosureText()).toContain('NHID-TEST-0002');
  });

  test('custom template is applied', () => {
    const { dh } = makeHandlerPair({
      disclosure_template: 'I am {agentName} from {entity} id={nhidUuid}.',
    });
    expect(dh.getDisclosureText()).toBe('I am TestAgent from Acme Payer id=NHID-TEST-0002.');
  });
});

describe('DisclosureHandler — playback lifecycle', () => {
  test('emits NHID_DISCLOSURE_START on beginDisclosure', () => {
    const { dh } = makeHandlerPair();
    const events: unknown[] = [];
    dh.on('NHID_DISCLOSURE_START', (e) => events.push(e));
    dh.beginDisclosure();
    expect(events).toHaveLength(1);
  });

  test('emits NHID_DISCLOSURE_COMPLETE after all chunks play', () => {
    const { dh } = makeHandlerPair();
    const completed: unknown[] = [];
    dh.on('NHID_DISCLOSURE_COMPLETE', (e) => completed.push(e));
    dh.beginDisclosure();
    jest.runAllTimers();
    expect(completed).toHaveLength(1);
  });

  test('marks disclosure COMPLETE in state machine after all chunks', () => {
    const { sm, dh } = makeHandlerPair();
    dh.beginDisclosure();
    jest.runAllTimers();
    expect(sm.getSession().disclosure_status).toBe(DisclosureStatus.COMPLETE);
  });

  test('emits at least one NHID_DISCLOSURE_CHUNK per chunk', () => {
    const { dh } = makeHandlerPair();
    const chunks: unknown[] = [];
    dh.on('NHID_DISCLOSURE_CHUNK', (c) => chunks.push(c));
    dh.beginDisclosure();
    jest.runAllTimers();
    expect(chunks.length).toBeGreaterThanOrEqual(1);
  });

  test('beginDisclosure is idempotent — second call is a no-op while playing', () => {
    const { dh } = makeHandlerPair();
    const events: unknown[] = [];
    dh.on('NHID_DISCLOSURE_START', (e) => events.push(e));
    dh.beginDisclosure();
    dh.beginDisclosure();
    expect(events).toHaveLength(1);
  });
});

describe('DisclosureHandler — interruption reset (NHID-Sec-1 §3.2)', () => {
  test('emits NHID_INTERRUPTION_WARN when remote media arrives during disclosure', () => {
    const { dh } = makeHandlerPair();
    const warnings: unknown[] = [];
    dh.on('NHID_INTERRUPTION_WARN', (e) => warnings.push(e));
    dh.beginDisclosure();
    dh.handleRemoteMediaDetected(100);
    expect(warnings).toHaveLength(1);
  });

  test('NHID_INTERRUPTION_WARN includes interrupted_at_ms', () => {
    const { dh } = makeHandlerPair();
    const warnings: Array<{ interrupted_at_ms: number }> = [];
    dh.on('NHID_INTERRUPTION_WARN', (e) => warnings.push(e));
    dh.beginDisclosure();
    dh.handleRemoteMediaDetected(250);
    expect(warnings[0].interrupted_at_ms).toBe(250);
  });

  test('resets playbackPosition to 0 after interruption', () => {
    const { dh } = makeHandlerPair();
    const chunks: Array<{ index: number }> = [];
    dh.on('NHID_DISCLOSURE_CHUNK', (c) => chunks.push(c));
    dh.beginDisclosure();
    // Advance past first chunk
    jest.advanceTimersByTime(400);
    // Interrupt — should restart
    dh.handleRemoteMediaDetected(400);
    // First chunk after restart should be index 0 again
    const postInterruptChunks = chunks.slice(chunks.findIndex((c) => c.index === 0) + 1);
    const firstAfterReset = postInterruptChunks.find((c) => c.index === 0);
    expect(firstAfterReset).toBeDefined();
  });

  test('second interruption increments interruption_count to 2', () => {
    const { sm, dh } = makeHandlerPair();
    dh.beginDisclosure();
    dh.handleRemoteMediaDetected(100);
    dh.handleRemoteMediaDetected(200);
    expect(sm.getSession().interruption_count).toBe(2);
  });

  test('increments interruption_count after interruption', () => {
    // handleRemoteMediaDetected marks INTERRUPTED then immediately restarts (→ IN_PROGRESS).
    // The durable observable is interruption_count.
    const { sm, dh } = makeHandlerPair();
    dh.beginDisclosure();
    dh.handleRemoteMediaDetected(100);
    expect(sm.getSession().interruption_count).toBe(1);
  });

  test('no-op if not currently playing', () => {
    const { dh } = makeHandlerPair();
    const warnings: unknown[] = [];
    dh.on('NHID_INTERRUPTION_WARN', (e) => warnings.push(e));
    // Never started
    dh.handleRemoteMediaDetected(100);
    expect(warnings).toHaveLength(0);
  });
});

describe('DisclosureHandler — stopPlayback', () => {
  test('stops playback without emitting COMPLETE', () => {
    const { dh } = makeHandlerPair();
    const completed: unknown[] = [];
    dh.on('NHID_DISCLOSURE_COMPLETE', (e) => completed.push(e));
    dh.beginDisclosure();
    dh.stopPlayback();
    jest.runAllTimers();
    expect(completed).toHaveLength(0);
  });
});
