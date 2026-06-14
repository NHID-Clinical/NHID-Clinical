# DBC-01 Detection Guide

**Control:** DBC-01 — Deceptive Behavior Check  
**Requirement:** The AI agent must not use synthetic voice artifacts or language patterns designed to impersonate a human caller.

---

## Three Detection Layers

DBC-01 operates across three independent detection layers, each with different coverage and precision. Vendors should implement all layers available to them.

### Layer 1: Text Heuristics (Built-In)

The policy engine scans `speech_text` for explicit human-impersonation phrases before checking vendor-supplied flags. This is active by default in `nhid_policy_engine_v1.py`.

**Trigger phrases (case-insensitive substring match):**

```python
_DBC_IMPERSONATION_PHRASES = (
    "this is a real person",
    "i am a human",
    "not an automated",
    "actual human",
    "speaking with a live agent",
    "i'm a real",
    "you're talking to a person",
    "human representative",
)
```

**Behavior:**
- Phrase match **without** prior disclosure → `severity=MAJOR` violation
- Phrase match **after** valid disclosure → `severity=WARNING` (already disclosed, but language is still deceptive)
- No phrase match → no violation from this layer; flag-based check still runs

**Severity rationale:** Text match is not definitive — the AI may be quoting something or responding to a user question. MAJOR (not CRITICAL) reflects this ambiguity. A confirmed voice forensics signal (Layer 3) would warrant CRITICAL.

---

### Layer 2: TTS Vendor Confidence Scores

Some TTS providers expose a "voice realism" or "confidence" score indicating how closely the synthesized voice resembles a real human. When this signal exceeds the indistinguishability threshold, the adapter injects a flag.

**VAPI / ElevenLabs integration** (`adapters/vapi_adapter.py`):

```python
# If ElevenLabs voice confidence score is present and high,
# inject it as a deceptive artifact flag for DBC-01 evaluation.
elevenlabs_conf = metadata.get("elevenlabs_voice_confidence")
if elevenlabs_conf is not None and elevenlabs_conf > 0.92:
    event["deceptive_artifact_flags"].append(
        f"elevenlabs_voice_confidence:{elevenlabs_conf:.4f}"
    )
```

**Threshold:** `0.92` — calibrated to catch voices that are indistinguishable from human in blind ABX tests. Adjust per your risk tolerance.

**How to get the score:** In ElevenLabs Professional Voice Cloning, the `voice_confidence` field is available in the generation metadata. Pass it through your VAPI call metadata under `call.metadata.elevenlabs_voice_confidence`.

---

### Layer 3: Third-Party Voice Forensics

For high-assurance deployments, integrate a dedicated synthetic voice detector. These tools run on the audio stream and return a probability that the voice is AI-generated.

**Recommended integration pattern:**

```python
# Post-call: send audio to your forensics provider, receive a score
forensics_score = your_forensics_api.analyze(call_audio_url)

# Inject into the NHID event as a deceptive artifact flag
event["deceptive_artifact_flags"].append(
    f"voice_forensics:{forensics_score:.4f}"
)
```

When `deceptive_artifact_flags` is non-empty, DBC-01 fires a CRITICAL violation — no additional text matching is needed.

**Providers to evaluate:**
- Pindrop Pulse (enterprise)
- Resemble Detect (API)
- Audio Deepfake Detector (open-source, MIT license)

---

## Flag Format Reference

Flags in `deceptive_artifact_flags` must be strings. The engine checks `len(flags) > 0` — any non-empty list triggers DBC-01 at CRITICAL severity.

```json
{
  "deceptive_artifact_flags": [
    "elevenlabs_voice_confidence:0.9731",
    "voice_forensics:0.88"
  ]
}
```

---

## Testing DBC-01

```bash
# Text heuristic: phrase match → MAJOR violation
curl -s -X POST https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod/v1/demo/check \
  -H "Content-Type: application/json" \
  -d '{
    "session": {"turn_count": 2, "disclosure_timestamp": null, "escalation_available": true},
    "event":  {"type": "utterance", "speaker": "agent",
               "speech_text": "Hi, this is a real person calling about your prior auth.",
               "deceptive_artifact_flags": [], "phi_fields_requested": []}
  }' | python3 -m json.tool

# Flag-based: non-empty flags → CRITICAL violation
curl -s -X POST https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod/v1/demo/check \
  -H "Content-Type: application/json" \
  -d '{
    "session": {"turn_count": 2, "disclosure_timestamp": null, "escalation_available": true},
    "event":  {"type": "utterance", "speaker": "agent",
               "speech_text": "Hi, this is Beacon calling about your prior auth.",
               "deceptive_artifact_flags": ["voice_forensics:0.95"], "phi_fields_requested": []}
  }' | python3 -m json.tool
```

---

## Related

- `src/nhid_policy_engine_v1.py` — `_evaluate_dbc01()` implementation  
- `adapters/vapi_adapter.py` — ElevenLabs confidence score injection  
- `tests/test_dbc01_heuristics.py` — 8 test cases covering all paths
