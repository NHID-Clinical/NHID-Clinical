import { createVerify } from 'crypto';
import { CallerRecord, CallerType, VerificationResult } from '../types/index.js';
import { CallerRegistry } from './CallerRegistry.js';

/**
 * Turing Boundary enforcement:
 *
 *   AI_AGENT:        Ed25519 public key verification against a signed challenge.
 *                    No human interaction path is exercised.
 *
 *   HUMAN_OPERATOR:  Record lookup + explicit `acknowledgement_received` flag.
 *                    The caller MUST set acknowledgement_received=true, which
 *                    represents the human operator's spoken/keyed acceptance of
 *                    the disclosure. Without it, IDENTIFIED→TRUSTED is blocked.
 */
export class RemoteCallerVerifier {
  constructor(private readonly registry: CallerRegistry) {}

  /**
   * Verifies a remote caller and returns a VerificationResult.
   *
   * For AI_AGENT: `proof` must be a base64-encoded Ed25519 signature over
   *               the UTF-8 encoding of `challenge`.
   *
   * For HUMAN_OPERATOR: `acknowledgement_received` must be true.
   */
  async verifyRemoteCaller(
    callerId: string,
    organization: string,
    options: {
      /** Ed25519 signature (base64) — required for AI_AGENT */
      proof?: string;
      /** Challenge string that was signed — required for AI_AGENT */
      challenge?: string;
      /** Must be true for HUMAN_OPERATOR to reach TRUSTED */
      acknowledgement_received?: boolean;
    } = {},
  ): Promise<VerificationResult> {
    const record = this.registry.lookup(callerId);

    if (!record) {
      return this.failResult(callerId, 'caller_id not found in registry');
    }

    if (record.organization !== organization) {
      return this.failResult(callerId, 'organization mismatch');
    }

    if (record.caller_type === CallerType.AI_AGENT) {
      return this.verifyAgent(record, options.proof, options.challenge);
    }

    return this.verifyHuman(record, options.acknowledgement_received ?? false);
  }

  // ── private ──────────────────────────────────────────────────────────────

  private verifyAgent(
    record: CallerRecord,
    proof: string | undefined,
    challenge: string | undefined,
  ): VerificationResult {
    if (!record.public_key_b64) {
      return this.failResult(record.entity_id, 'AI_AGENT has no registered public key');
    }

    if (!proof || !challenge) {
      return this.failResult(record.entity_id, 'proof and challenge required for AI_AGENT');
    }

    try {
      const verify = createVerify('ed25519');
      verify.update(Buffer.from(challenge, 'utf8'));
      const publicKeyDer = Buffer.from(record.public_key_b64, 'base64');
      const valid = verify.verify(
        { key: publicKeyDer, format: 'der', type: 'spki' },
        Buffer.from(proof, 'base64'),
      );

      if (!valid) {
        return this.failResult(record.entity_id, 'Ed25519 signature verification failed');
      }

      return {
        verified: true,
        caller_type: CallerType.AI_AGENT,
        entity_id: record.entity_id,
        requires_acknowledgement: false,
        acknowledgement_received: false,
      };
    } catch (err) {
      return this.failResult(
        record.entity_id,
        `Crypto error: ${err instanceof Error ? err.message : String(err)}`,
      );
    }
  }

  private verifyHuman(record: CallerRecord, acknowledgement_received: boolean): VerificationResult {
    return {
      verified: acknowledgement_received,
      caller_type: CallerType.HUMAN_OPERATOR,
      entity_id: record.entity_id,
      requires_acknowledgement: true,
      acknowledgement_received,
      failure_reason: acknowledgement_received
        ? undefined
        : 'Human operator has not acknowledged disclosure',
    };
  }

  private failResult(entity_id: string, reason: string): VerificationResult {
    return {
      verified: false,
      caller_type: CallerType.AI_AGENT,
      entity_id,
      requires_acknowledgement: false,
      acknowledgement_received: false,
      failure_reason: reason,
    };
  }
}
