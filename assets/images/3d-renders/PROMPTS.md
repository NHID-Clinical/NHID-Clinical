# 3D Render Drop-In Slots — Generation Prompts

This directory holds the optional high-resolution raster renders for the premium
visual layer. The site works fully WITHOUT them: every `<picture>` slot falls back
to the self-contained SVG in `assets/images/3d-svg/`. When a WebP listed below is
added here, the corresponding page upgrades automatically — no code changes.

Workflow: generate at max quality (8K if available) → downscale/optimize to WebP
(~1600–2200px wide, <400 KB; Squoosh or ImageOptim) → save with the EXACT filename.
Keep a PNG fallback only if a target browser matters to you (the `<picture>` tags
already reference `.webp` first and the SVG as final fallback).

House rules for every render: deep navy `#0F172A` base, teal `#14B8A6` energy
accents, slate/metallic silver materials, subtle gold inlays; no humans, no text
baked into the image; authoritative, grounded, premium — never salesy. Captions and
alt text on the site always say "Illustrative 3D visualization … conceptual render
for clarity."

## Slot 1 — `nexus-trust-bridge.webp` (index.html hero · wide 16:6-ish)

> Hyper-realistic insanely detailed 3D CGI cinematic render of an epic professional
> "Governance Trust Nexus" architectural structure in a stylized digital healthcare
> realm. A monumental modern-fortified archive or verification bridge spanning a
> subtle digital chasm between payer and provider domains. Intricate layered
> shields, ornate yet technical gates, and glowing teal energy pathways representing
> identity disclosure and verification protocols. Deep navy stone and metallic
> silver materials with subtle gold inlays. Volumetric god rays, dramatic cinematic
> lighting, high dynamic range, intricate PBR textures, depth of field, 8K
> resolution. Enterprise premium aesthetic like high-end Unreal Engine 5
> architectural visualization, wide landscape composition for website hero, no
> humans, no text, symbolic and authoritative.

## Slot 2 — `trust-stack-ziggurat.webp` (index.html stack section · portrait/square)

> Insanely detailed hyper-realistic 3D CGI cross-section render of a five-layer
> monumental trust architecture ziggurat for healthcare AI voice governance. Bottom
> foundational layer with intricate network protocol engravings. Successive layers:
> behavioral disclosure gates, cryptographic authorization chains and NPI bindings,
> comprehensive audit ledger textures, top observability spires. Each layer uniquely
> textured with deep navy stone, teal energy veins, silver/gold accents. Subtle
> control identifiers engraved. Dramatic side volumetric lighting, high resolution
> PBR, cinematic quality, angled view for clarity, premium enterprise visualization,
> no text overlays, authoritative mood.

## Slot 3 — `impersonation-vs-verified.webp` (latency section · wide split scene)

> Hyper-detailed cinematic 3D CGI split-scene render contrasting two halves of a
> digital healthcare realm. LEFT: a shadowed, red-tinged corridor where an unmarked
> caller orb passes a shattered gate straight into an exposed records vault — cold,
> hazardous, unverified. RIGHT: the same corridor rebuilt in deep navy and teal —
> an identity-disclosure gate, a verification checkpoint ring, and a sealed vault
> with a human-escalation stair, teal energy pulse traveling the verified path.
> Deep navy stone, metallic silver, teal light, subtle gold; volumetric lighting,
> PBR, 8K, no humans depicted literally (symbolic orbs/gates only), no text.

## Slot 4 — `idg01-gate.webp` (specification/controls · square)

> Insanely detailed 3D CGI render of a single monumental "Identity Disclosure Gate"
> — a secure glowing teal portal set in a deep navy stone frame with engraved
> circuit-like filigree and a silver keystone, faint gold inlay seams, closed until
> disclosure. Cinematic rim lighting, volumetric haze, PBR textures, 8K, symbolic,
> no text.

## Slot 5 — `verified-call-flow.webp` (simulator/technical-stack · wide isometric)

> Hyper-detailed isometric 3D CGI visualization of a verified AI call flow across a
> floating circuit-board landscape: caller node → disclosure gate → verification
> ring → PHI vault → human-escalation platform → audit ledger obelisk, connected by
> glowing teal conduits with directional pulses. Deep navy base, silver machinery,
> teal energy, subtle gold; clean readable composition, cinematic lighting, PBR,
> 8K, no text.

## Slot 6 set — per-control artifacts (optional gallery)

Same style as Slot 4, one per control. Filenames: `pdx01-checkpoint.webp`
(verification checkpoint ring before a sealed data conduit), `dbc01-mirror.webp`
(a truth-mirror device that reveals a machine silhouette behind a human-seeming
waveform), `eit01-stair.webp` (an always-lit escalation stair rising from the call
floor to a human platform), `atr01-ledger.webp` (an immutable audit obelisk with
engraved event rows and teal seal-stamps).
