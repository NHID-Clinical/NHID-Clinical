import { ComplianceState } from '../types/index.js';
import { PHIViolationError } from '../errors.js';

interface PHIPattern {
  name: string;
  pattern: RegExp;
}

/**
 * Detects and strips PHI before any content reaches the compliance log.
 * If PHI is detected while the session is not TRUSTED, throws PHIViolationError.
 */
export class PHIGateway {
  private static readonly PATTERNS: PHIPattern[] = [
    { name: 'SSN', pattern: /\b\d{3}-\d{2}-\d{4}\b/g },
    { name: 'SSN_UNFORMATTED', pattern: /\b\d{9}\b/g },
    { name: 'NPI', pattern: /\bNPI[:\s]{0,2}\d{10}\b/gi },
    { name: 'MBI', pattern: /\b[1-9][AC-HJ-NP-RT-Y]\d[AC-HJ-NP-RT-Y][AC-HJ-NP-RT-Y\d]\d[AC-HJ-NP-RT-Y\d]{2}\d[AC-HJ-NP-RT-Y\d]{2}\d\b/gi },
    { name: 'ICD10', pattern: /\b[A-Z]\d{2}(?:\.\d{1,4})?\b/g },
    { name: 'DATE_OF_BIRTH', pattern: /\b(?:dob|date\s+of\s+birth)[:\s]*\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4}\b/gi },
    { name: 'DATE_MMDDYYYY', pattern: /\b\d{2}[\/-]\d{2}[\/-]\d{4}\b/g },
    { name: 'MEMBER_ID', pattern: /\bMember\s*(?:ID|#|No\.?)[:\s]*[A-Z0-9]{6,20}\b/gi },
    { name: 'CLAIM_NUMBER', pattern: /\bClaim[:\s#]*[A-Z0-9]{8,20}\b/gi },
    { name: 'PHONE_NUMBER', pattern: /\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b/g },
    { name: 'EMAIL', pattern: /\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b/g },
    { name: 'DEA_NUMBER', pattern: /\b[A-Z]{2}\d{7}\b/g },
  ];

  /**
   * Checks `text` for PHI patterns.
   *
   * If `current_state` is not TRUSTED, any match throws PHIViolationError.
   * If TRUSTED, silently strips matches and returns the sanitized string.
   */
  check(text: string, session_uuid: string, current_state: ComplianceState): string {
    for (const { name, pattern } of PHIGateway.PATTERNS) {
      // Reset lastIndex for global patterns before each test
      pattern.lastIndex = 0;
      if (pattern.test(text)) {
        pattern.lastIndex = 0;
        if (current_state !== ComplianceState.TRUSTED) {
          throw new PHIViolationError(name, session_uuid, current_state);
        }
        // In TRUSTED state: strip and continue scanning remaining patterns
        text = text.replace(pattern, `[REDACTED:${name}]`);
      }
    }
    return text;
  }

  /**
   * Non-throwing variant — always strips PHI and returns sanitized text
   * along with a list of detected pattern names.
   */
  strip(text: string): { sanitized: string; detected: string[] } {
    const detected: string[] = [];
    for (const { name, pattern } of PHIGateway.PATTERNS) {
      pattern.lastIndex = 0;
      if (pattern.test(text)) {
        pattern.lastIndex = 0;
        detected.push(name);
        text = text.replace(pattern, `[REDACTED:${name}]`);
      }
    }
    return { sanitized: text, detected };
  }

  hasPatterns(): PHIPattern[] {
    return PHIGateway.PATTERNS;
  }
}
