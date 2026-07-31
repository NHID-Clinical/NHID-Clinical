import { EventEmitter } from 'events';
import { NHIDMiddlewareConfig, DisclosureChunk } from '../types/index.js';
import { ComplianceStateMachine } from '../state/ComplianceStateMachine.js';

/**
 * NHID-Sec-1 Disclosure Protocol
 *
 * Emitted events:
 *   NHID_DISCLOSURE_START      ({ session_uuid, chunk_count })
 *   NHID_DISCLOSURE_CHUNK      (chunk: DisclosureChunk)
 *   NHID_DISCLOSURE_COMPLETE   ({ session_uuid })
 *   NHID_INTERRUPTION_WARN     ({ session_uuid, interrupted_at_ms, interruption_count })
 */
export class DisclosureHandler extends EventEmitter {
  private readonly disclosureText: string;
  private readonly chunks: DisclosureChunk[];
  private playbackPosition: number = 0;
  private playbackTimer: NodeJS.Timeout | null = null;
  private isPlaying: boolean = false;

  /** Average spoken words per minute used to estimate chunk duration */
  private static readonly WPM = 150;
  /** Chunk size in words */
  private static readonly CHUNK_WORDS = 8;

  constructor(
    private readonly config: NHIDMiddlewareConfig,
    private readonly stateMachine: ComplianceStateMachine,
  ) {
    super();

    this.disclosureText = this.buildDisclosureString();
    this.chunks = this.tokenizeIntoChunks(this.disclosureText);
  }

  getDisclosureText(): string {
    return this.disclosureText;
  }

  /**
   * Begins (or resumes from the current playback position) disclosure playback.
   * Must be called after the state machine has emitted 'disclosure:required'.
   */
  beginDisclosure(): void {
    if (this.isPlaying || this.stateMachine.isTerminated()) return;

    this.stateMachine.markDisclosureStarted();
    this.emit('NHID_DISCLOSURE_START', {
      session_uuid: this.stateMachine.getSession().session_uuid,
      chunk_count: this.chunks.length,
    });

    this.playNextChunk();
  }

  /**
   * Called when inbound remote media is detected during disclosure.
   * Interrupts playback, resets to position 0, re-emits from the beginning.
   */
  handleRemoteMediaDetected(detected_at_ms: number): void {
    if (!this.isPlaying) return;

    this.stopPlayback();
    const session = this.stateMachine.getSession();
    this.stateMachine.markDisclosureInterrupted();

    this.emit('NHID_INTERRUPTION_WARN', {
      session_uuid: session.session_uuid,
      interrupted_at_ms: detected_at_ms,
      interruption_count: session.interruption_count + 1,
    });

    // Reset to beginning and restart — per NHID-Sec-1 §3.2
    this.playbackPosition = 0;
    this.beginDisclosure();
  }

  /** Stops any active playback timer without resetting position. */
  stopPlayback(): void {
    if (this.playbackTimer !== null) {
      clearTimeout(this.playbackTimer);
      this.playbackTimer = null;
    }
    this.isPlaying = false;
  }

  // ── private ──────────────────────────────────────────────────────────────

  private playNextChunk(): void {
    if (this.stateMachine.isTerminated()) {
      this.stopPlayback();
      return;
    }

    if (this.playbackPosition >= this.chunks.length) {
      this.isPlaying = false;
      this.stateMachine.markDisclosureComplete();
      this.emit('NHID_DISCLOSURE_COMPLETE', {
        session_uuid: this.stateMachine.getSession().session_uuid,
      });
      return;
    }

    this.isPlaying = true;
    const chunk = this.chunks[this.playbackPosition];
    this.emit('NHID_DISCLOSURE_CHUNK', chunk);
    this.playbackPosition += 1;

    this.playbackTimer = setTimeout(() => {
      this.playNextChunk();
    }, chunk.duration_ms);
  }

  private buildDisclosureString(): string {
    const template =
      this.config.disclosure_template ??
      'This is {agentName}, an automated healthcare assistant operating on behalf of {entity}. ' +
        'This session is monitored and recorded for compliance. ' +
        'My unique system identifier is {nhidUuid}.';

    return template
      .replace('{agentName}', this.config.agent_name)
      .replace('{entity}', this.config.entity_name)
      .replace('{nhidUuid}', this.config.nhid_uuid);
  }

  private tokenizeIntoChunks(text: string): DisclosureChunk[] {
    const words = text.split(/\s+/);
    const msPerWord = 60_000 / DisclosureHandler.WPM;
    const chunkSize = DisclosureHandler.CHUNK_WORDS;
    const result: DisclosureChunk[] = [];

    for (let i = 0; i < words.length; i += chunkSize) {
      const slice = words.slice(i, i + chunkSize);
      result.push({
        text: slice.join(' '),
        duration_ms: Math.round(slice.length * msPerWord),
        index: result.length,
        total: Math.ceil(words.length / chunkSize),
      });
    }

    return result;
  }
}
