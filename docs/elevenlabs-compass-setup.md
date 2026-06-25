# Compass — Remaining ElevenLabs Setup

Operational checklist for making the Compass chat widget (the `<elevenlabs-convai>`
embed on every page, `site.js:276`) fully self-service, so site visitors can get
answers without emailing or calling anyone. This is a checklist, not new product
code — everything below is either a one-time push from this repo or a dashboard
setting in ElevenLabs.

## 1. Push the three pending fixes

`agents/compass_system_prompt.md`'s Sync history table (2026-06-21 through
2026-06-25) documents three fixes that exist in this repo but have never reached
the live agent, because no environment so far has had a working
`ELEVENLABS_API_KEY`:

| Bug (still live) | Fix (in this repo, unpushed) |
| :--- | :--- |
| Widget greets as "Compass (Nicole)" — a dashboard placeholder name | `name`/`first_message` push, fixed in `src/elevenlabs_client.py`'s `sync_prompt` |
| Widget opens a voice call ("Listening" / "End") instead of a chat box | `agents/compass.config.json` → `"text_only": true`, pushed by `push_voice_and_model` |
| Vague "consult documentation" answers with no real link, e.g. for Vapi integration | Concrete adapter endpoints + URLs added to the `WHAT TO DO` section of the prompt fence |

All three go live with one command once a real key is available:

```bash
export ELEVENLABS_API_KEY=your_key
python scripts/sync_agent_config.py --agent compass --pull   # one-time: pull voice_id/llm (currently null in compass.config.json)
python scripts/sync_agent_config.py --agent compass          # push prompt + name + first_message + text_only
```

**If you don't have a key handy and want the chat box working today**: open the
ElevenLabs dashboard → Compass agent → Advanced tab → enable "Text only" manually.
That fixes bug #2 immediately; bugs #1 and #3 still need the prompt push.

## 2. Confirm guardrails are still on

Per the Sync history's 2026-06-20 entry, content guardrails (all categories,
end-conversation) and the Spotlight prompt-injection guardrail were enabled at
agent creation. Re-check both are still on after any dashboard edits — the
"Text only" toggle and guardrail toggles live on the same Advanced tab and it's
easy to fat-finger one while changing the other.

## 3. Add a Knowledge Base so Compass answers from real content

Today, everything Compass knows is hardcoded into its system prompt fence
(`agents/compass_system_prompt.md`). That's fine for the handful of facts that
prompt already covers, but it means any question outside that fence gets a
deflection ("say so and give the GitHub repo URL") instead of a real answer. A
Knowledge Base closes that gap — ElevenLabs' Conversational AI agents support a
per-agent Knowledge Base (URL scrape, pasted text, or file upload — PDF/TXT/DOCX/
HTML/EPUB) plus an optional RAG (Retrieval-Augmented Generation) index for larger
content, configured under the agent's **Knowledge Base** tab in the dashboard
([docs](https://elevenlabs.io/docs/conversational-ai/customization/knowledge-base)).

### What to load in

URL-scrape documents, one per page, kept in sync with auto-sync enabled so edits
to the live site propagate without manual re-upload:

- `https://nhid-clinical.org/specification.html` — what the four controls are
- `https://nhid-clinical.org/technical-stack.html`
- `https://nhid-clinical.org/regulatory-alignment.html`
- `https://nhid-clinical.org/developers.html` — adapter endpoints, quickstart
- `https://nhid-clinical.org/interoperability.html`
- `https://nhid-clinical.org/evidence-pack.html`
- `https://nhid-clinical.org/shadow-evaluation-guide.html`
- `https://nhid-clinical.org/for-payers.html`
- `https://nhid-clinical.org/registry.html`
- `https://nhid-clinical.org/roadmap.html`
- `https://nhid-clinical.org/faq.html`
- `https://github.com/NHID-Clinical/NHID-Clinical/blob/main/README.md`

### Configuration once documents are added

1. In the agent's Knowledge Base tab, toggle **Use RAG** on — the combined size of
   the pages above exceeds what should be stuffed into every prompt turn, and RAG
   retrieves only the relevant chunks per question instead.
2. Leave each document's usage mode as **Auto** (retrieved only when relevant) —
   do not set any of them to **Prompt** mode (always included), which would
   re-create the same "everything in every turn" cost problem RAG is meant to avoid.
3. Under Advanced, the embedding model and max-chunks/max-vector-distance defaults
   are reasonable starting points; tune only if Compass starts citing irrelevant
   pages in answers.
4. Turn on **source attribution** (`conversation_config.source_attribution`) so
   Compass's answers reference which page they came from — useful for visitors
   who want to verify a claim themselves, and for noticing if it's pulling from a
   stale cached page.

### Keep the system prompt as the front line

The Knowledge Base is a supplement, not a replacement, for
`agents/compass_system_prompt.md`'s non-negotiable accuracy constraints (no NIST
endorsement claims, no claimed pilot partners, the locked "Impersonation Latency"
term, exact test counts). Those constraints stay in the prompt fence so they apply
to every answer regardless of what the retrieved chunks say — a stale or
oddly-worded sentence on a scraped page should never override them.

### Why this isn't already wired into `scripts/sync_agent_config.py`

Knowledge Base documents are a separate ElevenLabs resource from the agent
itself (`POST /v1/convai/knowledge-base/url`, `/text`, `/file`, each returning a
`document_id`), attached to an agent via its `conversation_config.agent.prompt
.knowledge_base` array. Setting this up once through the dashboard is faster and
lower-risk than writing and testing new sync-script code against an API this repo
has never had a live key to exercise — once the dashboard configuration is
confirmed working, pulling it into `agents/compass.config.json` (mirroring the
existing `voice_id`/`llm`/`text_only` pattern) is a reasonable follow-up so the
repo stays the source of truth, but isn't required for the chat widget to work.

## 4. Add the existing FAQ page to the Knowledge Base

`faq.html` already exists and is exactly the kind of dense, purpose-written page
the Knowledge Base benefits from most (versus relying entirely on scraped
marketing copy). Add `https://nhid-clinical.org/faq.html` to the URL list in
Section 3 — it was omitted above only because it hadn't been confirmed to exist
yet at the time of writing.
