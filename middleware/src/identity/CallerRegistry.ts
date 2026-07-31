import { CallerRecord, CallerType } from '../types/index.js';

/**
 * In-memory registry of known callers.
 * In production, back this with a persistent store (DynamoDB, PostgreSQL, etc.)
 * and refresh records on a TTL.
 */
export class CallerRegistry {
  private readonly records: Map<string, CallerRecord> = new Map();

  register(record: CallerRecord): void {
    this.records.set(record.entity_id, record);
  }

  lookup(entity_id: string): CallerRecord | undefined {
    return this.records.get(entity_id);
  }

  has(entity_id: string): boolean {
    return this.records.has(entity_id);
  }

  /** Returns all registered AI agent records. */
  listAgents(): CallerRecord[] {
    return [...this.records.values()].filter((r) => r.caller_type === CallerType.AI_AGENT);
  }

  size(): number {
    return this.records.size;
  }
}
