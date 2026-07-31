import { NHIDSession, ComplianceLogEntry, ComplianceLoggerInterface } from '../types/index.js';
import { PHIGateway } from './PHIGateway.js';

/**
 * Structured compliance logger conforming to the NHID audit log spec.
 *
 * All free-text fields are routed through PHIGateway.strip() before
 * being persisted, regardless of session state. The spec requires audit
 * entries to be PHI-free at rest.
 *
 * Log entries are written to `output` (default: stdout) in NDJSON format.
 */
export class NHIDComplianceLogger implements ComplianceLoggerInterface {
  private readonly callStart: Date;
  private readonly phi: PHIGateway;

  constructor(
    private readonly output: (line: string) => void = (l) => process.stdout.write(l + '\n'),
    phi?: PHIGateway,
  ) {
    this.callStart = new Date();
    this.phi = phi ?? new PHIGateway();
  }

  log(entry: ComplianceLogEntry): void {
    // Sanitize any free-text event field before persisting
    const sanitizedEvent = this.phi.strip(entry.event).sanitized;

    const safe: ComplianceLogEntry = { ...entry, event: sanitizedEvent };
    this.output(JSON.stringify(safe));
  }

  /**
   * Builds a ComplianceLogEntry from the current session and an event name.
   * Caller passes this to `log()`.
   */
  buildEntry(session: Readonly<NHIDSession>, event: string): ComplianceLogEntry {
    return {
      timestamp: new Date().toISOString(),
      session_uuid: session.session_uuid,
      nhid_uuid: session.nhid_uuid,
      remote_entity_id: session.remote_entity_id,
      current_state: session.current_state,
      disclosure_status: session.disclosure_status,
      event,
      caller_type: session.caller_type,
      termination_reason: session.termination_reason,
      interruption_count: session.interruption_count,
      duration_ms: Date.now() - this.callStart.getTime(),
    };
  }
}
