export enum ComplianceState {
  UNVERIFIED = 'UNVERIFIED',
  IDENTIFIED = 'IDENTIFIED',
  TRUSTED = 'TRUSTED',
  TERMINATED = 'TERMINATED',
}

export enum DisclosureStatus {
  PENDING = 'PENDING',
  IN_PROGRESS = 'IN_PROGRESS',
  COMPLETE = 'COMPLETE',
  INTERRUPTED = 'INTERRUPTED',
}

export enum CallerType {
  AI_AGENT = 'AI_AGENT',
  HUMAN_OPERATOR = 'HUMAN_OPERATOR',
}

export enum TerminationReason {
  POLICY_VIOLATION = 'POLICY_VIOLATION',
  VERIFICATION_FAILURE = 'VERIFICATION_FAILURE',
  TIMEOUT = 'TIMEOUT',
  PHI_BEFORE_TRUST = 'PHI_BEFORE_TRUST',
  DECEPTIVE_BEHAVIOR = 'DECEPTIVE_BEHAVIOR',
  ESCALATION_DENIED = 'ESCALATION_DENIED',
  EXPLICIT = 'EXPLICIT',
}

export interface NHIDSession {
  session_uuid: string;
  nhid_uuid: string;
  remote_entity_id: string | null;
  current_state: ComplianceState;
  disclosure_status: DisclosureStatus;
  caller_type: CallerType | null;
  call_start_time: Date;
  state_entered_at: Date;
  disclosure_completed_at: Date | null;
  termination_reason: TerminationReason | null;
  interruption_count: number;
}

export interface CallerRecord {
  entity_id: string;
  organization: string;
  caller_type: CallerType;
  /** Ed25519 public key (base64) — required for AI_AGENT */
  public_key_b64?: string;
  display_name: string;
  registered_at: Date;
}

export interface VerificationResult {
  verified: boolean;
  caller_type: CallerType;
  entity_id: string;
  /** Set to true only after explicit human acknowledgement */
  requires_acknowledgement: boolean;
  acknowledgement_received: boolean;
  failure_reason?: string;
}

export interface ComplianceLogEntry {
  timestamp: string;
  session_uuid: string;
  nhid_uuid: string;
  remote_entity_id: string | null;
  current_state: ComplianceState;
  disclosure_status: DisclosureStatus;
  event: string;
  caller_type: CallerType | null;
  termination_reason: TerminationReason | null;
  interruption_count: number;
  duration_ms: number;
}

export interface MediaPacket {
  session_uuid: string;
  timestamp: number;
  payload: Buffer;
  direction: 'inbound' | 'outbound';
}

export interface DisclosureChunk {
  text: string;
  duration_ms: number;
  index: number;
  total: number;
}

export interface NHIDMiddlewareConfig {
  nhid_uuid: string;
  agent_name: string;
  entity_name: string;
  /** Milliseconds before UNVERIFIED times out → TERMINATED */
  verification_timeout_ms: number;
  /** Milliseconds to wait for acknowledgement after disclosure completes */
  acknowledgement_timeout_ms: number;
  /** Allow configuring disclosure string template */
  disclosure_template?: string;
  logger?: ComplianceLoggerInterface;
}

export interface ComplianceLoggerInterface {
  log(entry: ComplianceLogEntry): void;
}
