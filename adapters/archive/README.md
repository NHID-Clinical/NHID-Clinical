# Archived adapters

These four adapters are no longer actively maintained. They are kept here rather than
deleted because they are working reference implementations, and someone integrating the
corresponding platform will want to start from them.

- `vonage_adapter.py`
- `retell_adapter.py`
- `amazon_connect_adapter.py`
- `elevenlabs_postcall_adapter.py`

## Why they were archived

Six maintained adapters against six vendor APIs is a permanent maintenance cost, paid on
every vendor change, for a framework with no production deployments. Each adapter is a
promise to track an interface this project does not control.

The two that remain active — `twilio_adapter.py` and `vapi_adapter.py` — cover the
largest telephony install base and one AI-voice-native platform respectively, which is
enough to demonstrate that the normalization boundary works without claiming coverage
nobody has asked for.

## What this does and does not mean

It does **not** mean these platforms are unsupported in principle. The governance engine
never sees vendor-specific shapes: an adapter's whole job is to produce the canonical
event the engine reads. Reviving one of these is a small, well-bounded piece of work.

It does mean nobody is testing them against the current vendor APIs, so treat them as a
starting point rather than a guarantee.

**Un-archiving one is a reasonable response to a real integration request.** It is not a
reasonable response to wanting a longer list on a website.
