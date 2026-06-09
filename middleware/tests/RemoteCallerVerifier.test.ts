import { sign as cryptoSign, generateKeyPairSync } from 'crypto';
import { CallerRegistry } from '../src/identity/CallerRegistry';
import { RemoteCallerVerifier } from '../src/identity/RemoteCallerVerifier';
import { CallerType } from '../src/types/index';

function makeAgentKeyPair(): { publicKeyB64: string; privateKey: import('crypto').KeyObject } {
  const { privateKey, publicKey } = generateKeyPairSync('ed25519');
  const publicKeyB64 = publicKey.export({ type: 'spki', format: 'der' }).toString('base64');
  return { publicKeyB64, privateKey };
}

function signChallenge(privateKey: import('crypto').KeyObject, challenge: string): string {
  return cryptoSign(null, Buffer.from(challenge, 'utf8'), privateKey).toString('base64');
}

function makeVerifier(records: Parameters<CallerRegistry['register']>[0][] = []) {
  const registry = new CallerRegistry();
  for (const r of records) registry.register(r);
  return new RemoteCallerVerifier(registry);
}

const CHALLENGE = 'nhid-test-challenge-2026';
const ORG = 'Acme Payer';

describe('RemoteCallerVerifier — AI_AGENT', () => {
  test('valid Ed25519 proof → verified: true', async () => {
    const { publicKeyB64, privateKey } = makeAgentKeyPair();
    const verifier = makeVerifier([
      { entity_id: 'agent-1', organization: ORG, caller_type: CallerType.AI_AGENT,
        public_key_b64: publicKeyB64, display_name: 'TestBot', registered_at: new Date() },
    ]);
    const proof = signChallenge(privateKey, CHALLENGE);
    const result = await verifier.verifyRemoteCaller('agent-1', ORG, { proof, challenge: CHALLENGE });
    expect(result.verified).toBe(true);
    expect(result.caller_type).toBe(CallerType.AI_AGENT);
    expect(result.requires_acknowledgement).toBe(false);
  });

  test('invalid signature → verified: false with reason', async () => {
    const { publicKeyB64 } = makeAgentKeyPair();
    const { privateKey: otherKey } = makeAgentKeyPair();
    const verifier = makeVerifier([
      { entity_id: 'agent-2', organization: ORG, caller_type: CallerType.AI_AGENT,
        public_key_b64: publicKeyB64, display_name: 'TestBot', registered_at: new Date() },
    ]);
    const wrongProof = signChallenge(otherKey, CHALLENGE);
    const result = await verifier.verifyRemoteCaller('agent-2', ORG, { proof: wrongProof, challenge: CHALLENGE });
    expect(result.verified).toBe(false);
    expect(result.failure_reason).toContain('Ed25519 signature verification failed');
  });

  test('missing proof → verified: false', async () => {
    const { publicKeyB64 } = makeAgentKeyPair();
    const verifier = makeVerifier([
      { entity_id: 'agent-3', organization: ORG, caller_type: CallerType.AI_AGENT,
        public_key_b64: publicKeyB64, display_name: 'TestBot', registered_at: new Date() },
    ]);
    const result = await verifier.verifyRemoteCaller('agent-3', ORG, { challenge: CHALLENGE });
    expect(result.verified).toBe(false);
    expect(result.failure_reason).toContain('proof and challenge required');
  });

  test('missing challenge → verified: false', async () => {
    const { publicKeyB64, privateKey } = makeAgentKeyPair();
    const verifier = makeVerifier([
      { entity_id: 'agent-4', organization: ORG, caller_type: CallerType.AI_AGENT,
        public_key_b64: publicKeyB64, display_name: 'TestBot', registered_at: new Date() },
    ]);
    const proof = signChallenge(privateKey, CHALLENGE);
    const result = await verifier.verifyRemoteCaller('agent-4', ORG, { proof });
    expect(result.verified).toBe(false);
    expect(result.failure_reason).toContain('proof and challenge required');
  });

  test('no public key registered → verified: false', async () => {
    const verifier = makeVerifier([
      { entity_id: 'agent-5', organization: ORG, caller_type: CallerType.AI_AGENT,
        display_name: 'TestBot', registered_at: new Date() },
    ]);
    const result = await verifier.verifyRemoteCaller('agent-5', ORG, { proof: 'x', challenge: CHALLENGE });
    expect(result.verified).toBe(false);
    expect(result.failure_reason).toContain('no registered public key');
  });
});

describe('RemoteCallerVerifier — unknown caller / org mismatch', () => {
  test('unknown callerId → verified: false, caller_id not found', async () => {
    const verifier = makeVerifier([]);
    const result = await verifier.verifyRemoteCaller('ghost-99', ORG, {});
    expect(result.verified).toBe(false);
    expect(result.failure_reason).toContain('caller_id not found');
  });

  test('organization mismatch → verified: false', async () => {
    const { publicKeyB64 } = makeAgentKeyPair();
    const verifier = makeVerifier([
      { entity_id: 'agent-6', organization: 'Real Payer Inc', caller_type: CallerType.AI_AGENT,
        public_key_b64: publicKeyB64, display_name: 'TestBot', registered_at: new Date() },
    ]);
    const result = await verifier.verifyRemoteCaller('agent-6', 'Impostor Payer', {});
    expect(result.verified).toBe(false);
    expect(result.failure_reason).toContain('organization mismatch');
  });
});

describe('RemoteCallerVerifier — HUMAN_OPERATOR', () => {
  const humanRecord = {
    entity_id: 'human-1', organization: ORG, caller_type: CallerType.HUMAN_OPERATOR,
    display_name: 'Jane Operator', registered_at: new Date(),
  };

  test('acknowledgement_received: true → verified: true', async () => {
    const verifier = makeVerifier([humanRecord]);
    const result = await verifier.verifyRemoteCaller('human-1', ORG, { acknowledgement_received: true });
    expect(result.verified).toBe(true);
    expect(result.requires_acknowledgement).toBe(true);
    expect(result.acknowledgement_received).toBe(true);
    expect(result.caller_type).toBe(CallerType.HUMAN_OPERATOR);
  });

  test('acknowledgement_received: false → verified: false', async () => {
    const verifier = makeVerifier([humanRecord]);
    const result = await verifier.verifyRemoteCaller('human-1', ORG, { acknowledgement_received: false });
    expect(result.verified).toBe(false);
    expect(result.requires_acknowledgement).toBe(true);
    expect(result.failure_reason).toContain('not acknowledged');
  });

  test('acknowledgement_received omitted → verified: false', async () => {
    const verifier = makeVerifier([humanRecord]);
    const result = await verifier.verifyRemoteCaller('human-1', ORG, {});
    expect(result.verified).toBe(false);
    expect(result.requires_acknowledgement).toBe(true);
  });
});
