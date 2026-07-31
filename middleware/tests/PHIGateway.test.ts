import { PHIGateway } from '../src/telemetry/PHIGateway';
import { ComplianceState } from '../src/types';
import { PHIViolationError } from '../src/errors';

const gateway = new PHIGateway();
const SESSION = 'test-session-uuid';

describe('PHIGateway.check — throws when pre-TRUSTED', () => {
  test.each([ComplianceState.UNVERIFIED, ComplianceState.IDENTIFIED])(
    'state %s: throws PHIViolationError on SSN',
    (state) => {
      expect(() => gateway.check('SSN is 123-45-6789', SESSION, state)).toThrow(PHIViolationError);
    },
  );

  test('throws on NPI in UNVERIFIED state', () => {
    expect(() =>
      gateway.check('Caller NPI: 1234567890', SESSION, ComplianceState.UNVERIFIED),
    ).toThrow(PHIViolationError);
  });

  test('throws on ICD-10 code pre-TRUSTED', () => {
    expect(() =>
      gateway.check('Diagnosis: A01.0', SESSION, ComplianceState.UNVERIFIED),
    ).toThrow(PHIViolationError);
  });

  test('PHIViolationError contains session_uuid', () => {
    try {
      gateway.check('SSN: 123-45-6789', SESSION, ComplianceState.UNVERIFIED);
    } catch (e) {
      expect((e as PHIViolationError).session_uuid).toBe(SESSION);
    }
  });
});

describe('PHIGateway.check — strips when TRUSTED', () => {
  test('strips SSN', () => {
    const result = gateway.check(
      'SSN is 123-45-6789 ok',
      SESSION,
      ComplianceState.TRUSTED,
    );
    expect(result).not.toContain('123-45-6789');
    expect(result).toContain('[REDACTED:SSN]');
  });

  test('strips email address', () => {
    const result = gateway.check(
      'Email: patient@example.com',
      SESSION,
      ComplianceState.TRUSTED,
    );
    expect(result).not.toContain('patient@example.com');
    expect(result).toContain('[REDACTED:EMAIL]');
  });

  test('strips phone number', () => {
    const result = gateway.check(
      'Call me at 555-867-5309',
      SESSION,
      ComplianceState.TRUSTED,
    );
    expect(result).not.toContain('555-867-5309');
  });

  test('passes clean text through unchanged', () => {
    const clean = 'Hello, please verify your provider.';
    const result = gateway.check(clean, SESSION, ComplianceState.TRUSTED);
    expect(result).toBe(clean);
  });
});

describe('PHIGateway.strip — non-throwing variant', () => {
  test('returns detected pattern names', () => {
    const { detected } = gateway.strip('SSN 123-45-6789 email: foo@bar.com');
    expect(detected).toContain('SSN');
    expect(detected).toContain('EMAIL');
  });

  test('sanitized text has no raw SSN', () => {
    const { sanitized } = gateway.strip('SSN 123-45-6789');
    expect(sanitized).not.toContain('123-45-6789');
  });

  test('empty detected for clean text', () => {
    const { detected, sanitized } = gateway.strip('Hello world');
    expect(detected).toHaveLength(0);
    expect(sanitized).toBe('Hello world');
  });

  test('multiple patterns detected in one call', () => {
    const text = 'SSN: 123-45-6789, email: test@example.com, NPI: 1234567890';
    const { detected } = gateway.strip(text);
    expect(detected.length).toBeGreaterThanOrEqual(2);
  });
});

describe('PHIGateway — pattern coverage', () => {
  test('detects MBI-format string', () => {
    // Constructed to match pattern: [1-9][AC-HJ-NP-RT-Y]\d[AC-HJ-NP-RT-Y][AC-HJ-NP-RT-Y\d]\d[AC-HJ-NP-RT-Y\d]{2}\d[AC-HJ-NP-RT-Y\d]{2}\d
    const { detected } = gateway.strip('MBI: 1A1AA1AA1AA1');
    expect(detected).toContain('MBI');
  });

  test('detects date of birth pattern', () => {
    const { detected } = gateway.strip('DOB: 01/15/1980');
    expect(detected).toContain('DATE_OF_BIRTH');
  });

  test('detects member ID pattern', () => {
    const { detected } = gateway.strip('Member ID: MBR1234567');
    expect(detected).toContain('MEMBER_ID');
  });

  test('detects claim number', () => {
    const { detected } = gateway.strip('Claim: CLM20261234567');
    expect(detected).toContain('CLAIM_NUMBER');
  });
});
