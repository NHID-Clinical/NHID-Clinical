#!/usr/bin/env python3
"""Generate all 7 NHID-Clinical archive SVG diagrams."""
import os

OUT = os.path.dirname(os.path.abspath(__file__))

# Brand palette
NAVY    = "#0F172A"
TEAL    = "#14B8A6"
CYAN    = "#67E8F9"
WHITE   = "#F8FAFC"
LGRAY   = "#94A3B8"
DGRAY   = "#334155"
ORANGE  = "#FB923C"
RED     = "#F87171"
GREEN   = "#4ADE80"
YELLOW  = "#FACC15"

FONT_SANS = "Raleway, Inter, 'Helvetica Neue', Arial, sans-serif"

# ─────────────────────────────────────────────────────────────────────────────
# Diagram 1: Five-Layer Trust Stack
# ─────────────────────────────────────────────────────────────────────────────

def d1_trust_stack():
    W, H = 760, 520
    layers = [
        (5, "OpenTelemetry Spans",      "SIEM / Enterprise Observability",                       DGRAY,  WHITE,  False),
        (4, "FHIR AuditEvent R4",       "Healthcare-Native Audit Trail · 7 Milestones per Call", DGRAY,  WHITE,  False),
        (3, "NHID-Auth v2",             "Ed25519 · NPI-Bound Delegation Chains · 3-Hop Max",     DGRAY,  WHITE,  False),
        (2, "NHID-Clinical v1.3",       "4 Controls · 5 CTS Tests · Deterministic Engine",       TEAL,   NAVY,   True),
        (1, "STIR/SHAKEN (RFC 8224)",   "Carrier Number Authentication · A/B/C Attestation",     DGRAY,  WHITE,  False),
        (0, "NPI Authorization Gap",    "The Problem — No Cross-Org AI Agent Identity Standard", "#1E293B", LGRAY, False),
    ]
    row_h = 68
    pad_x, top = 40, 52
    inner_w = W - pad_x * 2

    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    lines += [
        f'<rect width="{W}" height="{H}" fill="{NAVY}"/>',
        f'<text x="{W//2}" y="32" text-anchor="middle" font-family="{FONT_SANS}" '
        f'font-size="17" font-weight="700" fill="{WHITE}" letter-spacing="1">NHID-CLINICAL FIVE-LAYER TRUST STACK</text>',
    ]

    for i, (num, name, desc, bg, fg, highlight) in enumerate(layers):
        y = top + i * row_h
        stroke = TEAL if highlight else "none"
        sw = 2 if highlight else 0
        lines.append(
            f'<rect x="{pad_x}" y="{y}" width="{inner_w}" height="{row_h - 6}" '
            f'rx="6" fill="{bg}" stroke="{stroke}" stroke-width="{sw}"/>'
        )
        label_color = TEAL if highlight else CYAN
        # Layer badge
        lines.append(
            f'<rect x="{pad_x + 10}" y="{y + 12}" width="38" height="38" rx="4" fill="{TEAL if highlight else DGRAY + "cc"}"/>'
        )
        lines.append(
            f'<text x="{pad_x + 29}" y="{y + 36}" text-anchor="middle" font-family="{FONT_SANS}" '
            f'font-size="15" font-weight="800" fill="{NAVY if highlight else WHITE}">{num}</text>'
        )
        lines.append(
            f'<text x="{pad_x + 60}" y="{y + 26}" font-family="{FONT_SANS}" '
            f'font-size="14" font-weight="700" fill="{label_color}">{name}</text>'
        )
        lines.append(
            f'<text x="{pad_x + 60}" y="{y + 44}" font-family="{FONT_SANS}" '
            f'font-size="11.5" fill="{LGRAY}">{desc}</text>'
        )
        if highlight:
            lines.append(
                f'<text x="{W - pad_x - 12}" y="{y + 36}" text-anchor="end" font-family="{FONT_SANS}" '
                f'font-size="10" font-weight="700" fill="{TEAL}" letter-spacing="0.5">THIS REPOSITORY</text>'
            )

    lines.append('</svg>')
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Diagram 2: Impersonation Latency Anatomy
# ─────────────────────────────────────────────────────────────────────────────

def d2_impersonation_latency():
    W, H = 760, 400
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    lines.append(f'<rect width="{W}" height="{H}" fill="{NAVY}"/>')
    lines.append(
        f'<text x="{W//2}" y="32" text-anchor="middle" font-family="{FONT_SANS}" '
        f'font-size="17" font-weight="700" fill="{WHITE}" letter-spacing="1">IMPERSONATION LATENCY — ANATOMY OF A VIOLATION</text>'
    )

    turns = [
        (1, "AI Agent", 'PHI REQUEST: "Can I get the member ID and date of birth?"',
         RED,   "IDG-01 FAIL: No disclosure", "PDX-01 FAIL: PHI before disclosure"),
        (2, "Human",   '"Member ID 789-XX-4421 · DOB 1965-04-12"',
         ORANGE, "PHI exchanged",              "Both violations already fired"),
        (3, "AI Agent", '"By the way, I am an automated system…"',
         YELLOW, "Disclosure — too late",      ""),
    ]

    turn_w = 210
    gap = 24
    total = len(turns) * turn_w + (len(turns) - 1) * gap
    start_x = (W - total) // 2
    top = 62

    # IL bracket
    il_x1 = start_x
    il_x2 = start_x + 2 * turn_w + gap + 20
    il_y = top + 240
    lines.append(f'<line x1="{il_x1}" y1="{il_y}" x2="{il_x2}" y2="{il_y}" stroke="{RED}" stroke-width="2" stroke-dasharray="4,3"/>')
    lines.append(f'<line x1="{il_x1}" y1="{il_y - 6}" x2="{il_x1}" y2="{il_y + 6}" stroke="{RED}" stroke-width="2"/>')
    lines.append(f'<line x1="{il_x2}" y1="{il_y - 6}" x2="{il_x2}" y2="{il_y + 6}" stroke="{RED}" stroke-width="2"/>')
    lines.append(
        f'<text x="{(il_x1 + il_x2)//2}" y="{il_y + 22}" text-anchor="middle" '
        f'font-family="{FONT_SANS}" font-size="11" font-weight="700" fill="{RED}">IMPERSONATION LATENCY</text>'
    )
    lines.append(
        f'<text x="{(il_x1 + il_x2)//2}" y="{il_y + 36}" text-anchor="middle" '
        f'font-family="{FONT_SANS}" font-size="10" fill="{LGRAY}">2 turns of undisclosed AI operation</text>'
    )

    for i, (turn, speaker, text, color, note1, note2) in enumerate(turns):
        x = start_x + i * (turn_w + gap)
        # Turn card
        lines.append(f'<rect x="{x}" y="{top}" width="{turn_w}" height="200" rx="8" fill="{DGRAY}"/>')
        lines.append(f'<rect x="{x}" y="{top}" width="{turn_w}" height="36" rx="8" fill="{color}"/>')
        lines.append(f'<rect x="{x}" y="{top + 28}" width="{turn_w}" height="8" fill="{color}"/>')
        lines.append(
            f'<text x="{x + turn_w//2}" y="{top + 23}" text-anchor="middle" '
            f'font-family="{FONT_SANS}" font-size="12" font-weight="700" fill="{NAVY}">Turn {turn} · {speaker}</text>'
        )
        # Word wrap text into 2 lines
        words = text.split()
        line1, line2 = [], []
        cur = line1
        for w in words:
            if len(" ".join(cur + [w])) > 30 and cur is line1:
                cur = line2
            cur.append(w)
        t1 = " ".join(line1)
        t2 = " ".join(line2)
        lines.append(
            f'<text x="{x + 10}" y="{top + 62}" font-family="{FONT_SANS}" font-size="11" '
            f'fill="{WHITE}" xml:space="preserve">{t1}</text>'
        )
        if t2:
            lines.append(
                f'<text x="{x + 10}" y="{top + 76}" font-family="{FONT_SANS}" font-size="11" '
                f'fill="{WHITE}" xml:space="preserve">{t2}</text>'
            )
        lines.append(
            f'<text x="{x + 10}" y="{top + 108}" font-family="{FONT_SANS}" font-size="10.5" '
            f'font-weight="700" fill="{color}">{note1}</text>'
        )
        if note2:
            lines.append(
                f'<text x="{x + 10}" y="{top + 124}" font-family="{FONT_SANS}" font-size="10" '
                f'fill="{LGRAY}">{note2}</text>'
            )

        # Arrow between turns
        if i < len(turns) - 1:
            ax = x + turn_w + 4
            ay = top + 100
            lines.append(f'<line x1="{ax}" y1="{ay}" x2="{ax + gap - 8}" y2="{ay}" stroke="{LGRAY}" stroke-width="1.5"/>')
            lines.append(f'<polygon points="{ax+gap-8},{ay-4} {ax+gap-8},{ay+4} {ax+gap},{ay}" fill="{LGRAY}"/>')

    # CAS result box
    cx = W // 2
    lines.append(
        f'<text x="{cx}" y="{H - 38}" text-anchor="middle" font-family="{FONT_SANS}" '
        f'font-size="13" font-weight="700" fill="{RED}">Action: DENY_DATA  ·  CAS = 0.0  ·  Tier: Hard Denial</text>'
    )
    lines.append(
        f'<text x="{cx}" y="{H - 20}" text-anchor="middle" font-family="{FONT_SANS}" '
        f'font-size="11" fill="{LGRAY}">IDG-01 CRITICAL + PDX-01 CRITICAL  ·  F_IAF = 0.0  →  CAS collapses to 0.0</text>'
    )

    lines.append('</svg>')
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Diagram 3: CAS Tier Ladder
# ─────────────────────────────────────────────────────────────────────────────

def d3_cas_tier_ladder():
    W, H = 440, 520
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    lines.append(f'<rect width="{W}" height="{H}" fill="{NAVY}"/>')
    lines.append(
        f'<text x="{W//2}" y="30" text-anchor="middle" font-family="{FONT_SANS}" '
        f'font-size="15" font-weight="700" fill="{WHITE}" letter-spacing="1">CAS TIER LADDER</text>'
    )

    tiers = [
        (0.90, 1.00, "Verified Trust",   GREEN,   "L2",  True),
        (0.75, 0.90, "Conditional Trust", TEAL,    "L1",  True),
        (0.50, 0.75, "Review Required",   YELLOW,  "",    False),
        (0.20, 0.50, "Denied / Degraded", ORANGE,  "",    False),
        (0.00, 0.20, "Hard Denial",        RED,     "",    False),
    ]

    scale_x, scale_w = 56, 20
    bar_x = scale_x + scale_w + 16
    bar_w = W - bar_x - 40
    top_y, bot_y = 52, H - 36
    scale_h = bot_y - top_y

    # Axis
    lines.append(f'<line x1="{scale_x + scale_w}" y1="{top_y}" x2="{scale_x + scale_w}" y2="{bot_y}" stroke="{LGRAY}" stroke-width="1"/>')

    def cas_to_y(val):
        return bot_y - int(val * scale_h)

    # Ticks at 0, 0.20, 0.50, 0.75, 0.90, 1.0
    for tick in [0.0, 0.20, 0.50, 0.75, 0.90, 1.0]:
        ty = cas_to_y(tick)
        lines.append(f'<line x1="{scale_x + scale_w - 6}" y1="{ty}" x2="{scale_x + scale_w}" y2="{ty}" stroke="{LGRAY}" stroke-width="1"/>')
        lines.append(
            f'<text x="{scale_x + scale_w - 10}" y="{ty + 4}" text-anchor="end" '
            f'font-family="{FONT_SANS}" font-size="10.5" fill="{LGRAY}">{tick:.2f}</text>'
        )

    for (lo, hi, name, color, badge, has_badge) in tiers:
        y_hi = cas_to_y(hi)
        y_lo = cas_to_y(lo)
        bh = y_lo - y_hi - 3
        lines.append(f'<rect x="{bar_x}" y="{y_hi + 1}" width="{bar_w}" height="{bh}" rx="4" fill="{color}" opacity="0.85"/>')
        mid_y = (y_hi + y_lo) // 2
        lines.append(
            f'<text x="{bar_x + 12}" y="{mid_y + 5}" font-family="{FONT_SANS}" '
            f'font-size="13" font-weight="700" fill="{NAVY}">{name}</text>'
        )
        if has_badge:
            bx = bar_x + bar_w - 44
            by = mid_y - 13
            lines.append(f'<rect x="{bx}" y="{by}" width="36" height="26" rx="5" fill="{NAVY}" opacity="0.6"/>')
            lines.append(
                f'<text x="{bx + 18}" y="{by + 17}" text-anchor="middle" font-family="{FONT_SANS}" '
                f'font-size="11" font-weight="800" fill="{WHITE}">{badge}</text>'
            )

    lines.append(
        f'<text x="{W//2}" y="{H - 14}" text-anchor="middle" font-family="{FONT_SANS}" '
        f'font-size="10" fill="{LGRAY}">CAS = F_IAF × F_NOCF × ECF</text>'
    )
    lines.append('</svg>')
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Diagram 4: System Architecture
# ─────────────────────────────────────────────────────────────────────────────

def d4_system_arch():
    W, H = 760, 460
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    lines.append(f'<rect width="{W}" height="{H}" fill="{NAVY}"/>')
    lines.append(
        f'<text x="{W//2}" y="28" text-anchor="middle" font-family="{FONT_SANS}" '
        f'font-size="16" font-weight="700" fill="{WHITE}" letter-spacing="1">SYSTEM ARCHITECTURE</text>'
    )

    def box(x, y, w, h, label, sub="", color=DGRAY, fg=WHITE, accent=None):
        lines.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{color}"/>')
        if accent:
            lines.append(f'<rect x="{x}" y="{y}" width="{w}" height="4" rx="3" fill="{accent}"/>')
        cy = y + h // 2 + (0 if not sub else -7)
        lines.append(
            f'<text x="{x + w//2}" y="{cy}" text-anchor="middle" font-family="{FONT_SANS}" '
            f'font-size="12" font-weight="700" fill="{fg}">{label}</text>'
        )
        if sub:
            lines.append(
                f'<text x="{x + w//2}" y="{cy + 16}" text-anchor="middle" font-family="{FONT_SANS}" '
                f'font-size="10" fill="{LGRAY}">{sub}</text>'
            )

    def arrow(x1, y1, x2, y2):
        lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{TEAL}" stroke-width="1.5" marker-end="url(#arr)"/>')

    lines.append(
        '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
        f'<path d="M0,0 L0,6 L8,3 z" fill="{TEAL}"/></marker></defs>'
    )

    # Row 1: Platforms
    plats = ["VAPI", "Twilio", "Vonage", "Retell", "Amazon Connect"]
    pw, ph, pgap = 110, 42, 14
    total_p = len(plats) * pw + (len(plats) - 1) * pgap
    px0 = (W - total_p) // 2
    py = 50
    for i, p in enumerate(plats):
        x = px0 + i * (pw + pgap)
        box(x, py, pw, ph, p, color="#1E293B", accent=CYAN)

    # Row 2: Adapters
    aw, ah = 280, 46
    ax = (W - aw) // 2
    ay = 130
    box(ax, ay, aw, ah, "Vendor Adapters", "to_nhid_event(payload) → (session, event)", color=DGRAY, accent=TEAL)

    # Arrow from platforms to adapters
    arrow(W//2, py + ph, W//2, ay)

    # Row 3: Lambda
    lw, lh = 340, 46
    lx = (W - lw) // 2
    ly = 214
    box(lx, ly, lw, lh, "AWS Lambda Handler", "functions/handler.py · Python 3.13 · 256 MB · 30s", color=DGRAY, accent=TEAL)
    arrow(W//2, ay + ah, W//2, ly)

    # Row 4: Policy Engine
    pew, peh = 340, 46
    pex = (W - pew) // 2
    pey = 298
    box(pex, pey, pew, peh, "Policy Engine", "evaluate_all(session, event) → PolicyDecision", color="#0D3D56", fg=CYAN, accent=TEAL)
    arrow(W//2, ly + lh, W//2, pey)

    # Row 5: CAS + FHIR (side by side)
    cw, ch = 240, 52
    cgap = 40
    cx1 = (W - 2*cw - cgap) // 2
    cx2 = cx1 + cw + cgap
    cy5 = 382
    box(cx1, cy5, cw, ch, "CAS Engine", "nhid_cas.py · 0.0–1.0 score", color=DGRAY, accent=TEAL)
    box(cx2, cy5, cw, ch, "FHIR Audit Emitter", "fhir_audit_emitter.py · R4 Bundle", color=DGRAY, accent=CYAN)
    arrow(pex + pew//2 - cw//2 - 10, pey + peh, cx1 + cw//2, cy5)
    arrow(pex + pew//2 + cw//2 + 10, pey + peh, cx2 + cw//2, cy5)

    lines.append('</svg>')
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Diagram 5: API Request Flow
# ─────────────────────────────────────────────────────────────────────────────

def d5_api_flow():
    W, H = 480, 580
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    lines.append(f'<rect width="{W}" height="{H}" fill="{NAVY}"/>')
    lines.append(
        f'<text x="{W//2}" y="28" text-anchor="middle" font-family="{FONT_SANS}" '
        f'font-size="15" font-weight="700" fill="{WHITE}" letter-spacing="1">API REQUEST FLOW</text>'
    )

    steps = [
        (CYAN,  "Vendor Platform",      'POST /v1/adapters/{platform}/check'),
        (TEAL,  "Vendor Adapter",       'to_nhid_event(payload)'),
        (TEAL,  "Policy Engine",        'evaluate_all(session, event)'),
        (TEAL,  "CAS Engine",           '_policy_cas(decision, event)'),
        (GREEN, "JSON Response",        '{ conformant, action, violations[], cas }'),
    ]

    bw, bh, gap = 360, 58, 28
    bx = (W - bw) // 2
    top = 50

    lines.append(
        '<defs><marker id="a2" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
        f'<path d="M0,0 L0,6 L8,3 z" fill="{TEAL}"/></marker></defs>'
    )

    total_h = len(steps) * bh + (len(steps) - 1) * gap
    start_y = (H - total_h) // 2

    for i, (color, label, sub) in enumerate(steps):
        y = start_y + i * (bh + gap)
        lines.append(f'<rect x="{bx}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="{DGRAY}"/>')
        lines.append(f'<rect x="{bx}" y="{y}" width="6" height="{bh}" rx="3" fill="{color}"/>')
        lines.append(
            f'<text x="{bx + 22}" y="{y + 24}" font-family="{FONT_SANS}" '
            f'font-size="13" font-weight="700" fill="{color}">{label}</text>'
        )
        lines.append(
            f'<text x="{bx + 22}" y="{y + 42}" font-family="{FONT_SANS}" '
            f'font-size="10.5" fill="{LGRAY}">{sub}</text>'
        )
        if i < len(steps) - 1:
            ay1 = y + bh
            ay2 = y + bh + gap
            lines.append(
                f'<line x1="{W//2}" y1="{ay1}" x2="{W//2}" y2="{ay2 - 6}" '
                f'stroke="{TEAL}" stroke-width="1.5" marker-end="url(#a2)"/>'
            )

    lines.append('</svg>')
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Diagram 6: Delegation Chain
# ─────────────────────────────────────────────────────────────────────────────

def d6_delegation_chain():
    W, H = 760, 360
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    lines.append(f'<rect width="{W}" height="{H}" fill="{NAVY}"/>')
    lines.append(
        f'<text x="{W//2}" y="28" text-anchor="middle" font-family="{FONT_SANS}" '
        f'font-size="16" font-weight="700" fill="{WHITE}" letter-spacing="1">NHID-AUTH v2 — DELEGATION CHAIN</text>'
    )
    lines.append(
        '<defs><marker id="a3" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">'
        f'<path d="M0,0 L0,6 L9,3 z" fill="{TEAL}"/></marker></defs>'
    )

    nodes = [
        ("Provider Org",    "NPI: 1234567890", "claims_inquiry\neligibility_check", TEAL,  NAVY),
        ("AI Vendor",       "Hop 1",           "claims_inquiry\neligibility_check", DGRAY, WHITE),
        ("Sub-Vendor",      "Hop 2",           "claims_inquiry",                    DGRAY, WHITE),
        ("Agent Instance",  "Hop 3 (max)",     "claims_inquiry",                    DGRAY, WHITE),
    ]

    nw, nh = 148, 110
    gap_x = 56
    total = len(nodes) * nw + (len(nodes) - 1) * gap_x
    nx0 = (W - total) // 2
    ny = 70

    for i, (name, sub, scope, bg, fg) in enumerate(nodes):
        x = nx0 + i * (nw + gap_x)
        lines.append(f'<rect x="{x}" y="{ny}" width="{nw}" height="{nh}" rx="8" fill="{bg}"/>')
        if i == 0:
            lines.append(f'<rect x="{x}" y="{ny}" width="{nw}" height="4" rx="3" fill="{TEAL}"/>')
        lines.append(
            f'<text x="{x + nw//2}" y="{ny + 26}" text-anchor="middle" font-family="{FONT_SANS}" '
            f'font-size="13" font-weight="700" fill="{fg}">{name}</text>'
        )
        lines.append(
            f'<text x="{x + nw//2}" y="{ny + 43}" text-anchor="middle" font-family="{FONT_SANS}" '
            f'font-size="10" fill="{LGRAY}">{sub}</text>'
        )
        # Scope
        for j, sc in enumerate(scope.split("\n")):
            lines.append(
                f'<text x="{x + nw//2}" y="{ny + 64 + j*15}" text-anchor="middle" font-family="{FONT_SANS}" '
                f'font-size="10" fill="{CYAN}">{sc}</text>'
            )

        # Arrow to next
        if i < len(nodes) - 1:
            ax1 = x + nw
            ax2 = x + nw + gap_x - 8
            ay = ny + nh // 2
            lines.append(
                f'<line x1="{ax1}" y1="{ay}" x2="{ax2}" y2="{ay}" '
                f'stroke="{TEAL}" stroke-width="1.5" marker-end="url(#a3)"/>'
            )
            # Scope narrowing label
            mid_ax = (ax1 + ax2) // 2
            lines.append(
                f'<text x="{mid_ax}" y="{ay - 10}" text-anchor="middle" font-family="{FONT_SANS}" '
                f'font-size="9" fill="{LGRAY}">narrowing</text>'
            )

    # Constraints callout
    cy = ny + nh + 36
    lines.append(
        f'<text x="{W//2}" y="{cy}" text-anchor="middle" font-family="{FONT_SANS}" '
        f'font-size="11.5" fill="{TEAL}" font-weight="700">Ed25519 signatures at every hop  ·  Scope can only narrow  ·  Max 3 hops  ·  Call-SID nonce binding</text>'
    )
    lines.append(
        f'<text x="{W//2}" y="{cy + 20}" text-anchor="middle" font-family="{FONT_SANS}" '
        f'font-size="10.5" fill="{LGRAY}">Per-agent and per-delegation revocation  ·  NPI validation on provider node</text>'
    )

    lines.append('</svg>')
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Diagram 7: IL Formal Measurement Definition (§2.4.1)
# ─────────────────────────────────────────────────────────────────────────────

def d7_il_formula():
    W, H = 760, 540
    M = "font-family=\"'Courier New', Courier, monospace\""
    S = f'font-family="{FONT_SANS}"'
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    lines.append(f'<rect width="{W}" height="{H}" fill="{NAVY}"/>')

    # Title
    lines.append(
        f'<text x="{W//2}" y="30" text-anchor="middle" {S} font-size="15" font-weight="700" '
        f'fill="{WHITE}" letter-spacing="1">IMPERSONATION LATENCY — FORMAL MEASUREMENT (§2.4.1)</text>'
    )

    # ── Timeline row ──────────────────────────────────────────────────────────
    TY = 80   # y-center of timeline bar
    X0 = 60   # t(connect)
    XD = 460  # t(disclosure)
    XE = 680  # t(end)

    # Grey track
    lines.append(f'<line x1="{X0}" y1="{TY}" x2="{XE}" y2="{TY}" stroke="{DGRAY}" stroke-width="4"/>')
    # IL bracket — teal span
    lines.append(f'<line x1="{X0}" y1="{TY}" x2="{XD}" y2="{TY}" stroke="{TEAL}" stroke-width="6"/>')

    # Endpoint circles
    for x, col in [(X0, CYAN), (XD, TEAL), (XE, LGRAY)]:
        lines.append(f'<circle cx="{x}" cy="{TY}" r="7" fill="{col}"/>')

    # Labels below timeline
    for x, label, col in [
        (X0, "t(connect)", CYAN),
        (XD, "t(disclosure)", TEAL),
        (XE, "t(end)", LGRAY),
    ]:
        lines.append(f'<text x="{x}" y="{TY+22}" text-anchor="middle" {M} font-size="10" fill="{col}">{label}</text>')

    # IL bracket annotation above
    mid = (X0 + XD) // 2
    lines.append(f'<line x1="{X0}" y1="{TY-18}" x2="{XD}" y2="{TY-18}" stroke="{TEAL}" stroke-width="1.5" stroke-dasharray="4,3"/>')
    lines.append(f'<text x="{mid}" y="{TY-24}" text-anchor="middle" {S} font-size="11" font-weight="700" fill="{TEAL}">IL = t(disclosure) − t(connect)</text>')

    # Right-censored case note
    lines.append(
        f'<text x="{XE+8}" y="{TY+5}" {S} font-size="10" fill="{LGRAY}">no disclosure → IL ≥ call duration (right-censored)</text>'
    )

    # ── Turns row ─────────────────────────────────────────────────────────────
    turns = [("T1", 110), ("T2", 185), ("T3", 260), ("T4", 335), ("T5 disc.", 410)]
    TY2 = 155
    lines.append(f'<line x1="{X0}" y1="{TY2}" x2="{XE}" y2="{TY2}" stroke="{DGRAY}" stroke-width="2"/>')
    for i, (label, tx) in enumerate(turns):
        col = TEAL if "disc" in label else (RED if i < 2 else LGRAY)
        lines.append(f'<circle cx="{tx}" cy="{TY2}" r="5" fill="{col}"/>')
        lines.append(f'<text x="{tx}" y="{TY2+18}" text-anchor="middle" {S} font-size="9" fill="{col}">{label}</text>')
    # Turn-form bracket
    lines.append(f'<text x="{(110+410)//2}" y="{TY2-12}" text-anchor="middle" {S} font-size="11" font-weight="700" fill="{CYAN}">IL(turns) = 4  →  conformant target: IL(turns) = 0</text>')

    # ── Exposure weighting row ────────────────────────────────────────────────
    EY = 218
    lines.append(f'<rect x="40" y="{EY}" width="{W-80}" height="56" rx="5" fill="{DGRAY}"/>')
    lines.append(f'<text x="56" y="{EY+18}" {S} font-size="11" font-weight="700" fill="{YELLOW}">Exposure weighting</text>')
    lines.append(f'<text x="56" y="{EY+35}" {M} font-size="10" fill="{WHITE}">Pre-Disclosure PHI Exposure = count( phi_accessed.timestamp &lt; t(disclosure) )</text>')
    lines.append(f'<text x="56" y="{EY+50}" {S} font-size="10" fill="{LGRAY}">PDX-01 fires when count &gt; 0 — high IL + zero exposure (bad practice) is not a breach; low IL + nonzero exposure (critical)</text>')

    # ── Perceptual variant ────────────────────────────────────────────────────
    PY = 292
    lines.append(f'<rect x="40" y="{PY}" width="{W-80}" height="44" rx="5" fill="{DGRAY}"/>')
    lines.append(f'<text x="56" y="{PY+17}" {S} font-size="11" font-weight="700" fill="{LGRAY}">Perceptual variant (excluded from conformance)</text>')
    lines.append(f'<text x="56" y="{PY+34}" {M} font-size="10" fill="{LGRAY}">IL(detection) = t(human detection) − t(connect)  →  not machine-observable; survey research only</text>')

    # ── Determinism guarantee ─────────────────────────────────────────────────
    DY = 354
    lines.append(f'<rect x="40" y="{DY}" width="{W-80}" height="56" rx="5" fill="#1E3A5F" stroke="{TEAL}" stroke-width="1.5"/>')
    lines.append(f'<text x="56" y="{DY+18}" {S} font-size="11" font-weight="700" fill="{TEAL}">Determinism guarantee</text>')
    lines.append(f'<text x="56" y="{DY+35}" {S} font-size="10" fill="{WHITE}">Both anchors are required ATR-01 event fields (disclosure_timestamp, session start).</text>')
    lines.append(f'<text x="56" y="{DY+50}" {S} font-size="10" fill="{WHITE}">IL is computable from any conformant audit trail with no human judgment.</text>')

    # ── Footer ────────────────────────────────────────────────────────────────
    lines.append(
        f'<text x="{W//2}" y="{H-12}" text-anchor="middle" {S} font-size="9" fill="{LGRAY}">'
        f'§2.4.1 · IL = t(disclosure) − t(connect) · deterministic from ATR-01 fields · right-censored when no disclosure occurs</text>'
    )
    lines.append('</svg>')
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Write all files
# ─────────────────────────────────────────────────────────────────────────────

diagrams = [
    ("fig1-trust-stack",            d1_trust_stack()),
    ("fig2-impersonation-latency",  d2_impersonation_latency()),
    ("fig3-cas-tier-ladder",        d3_cas_tier_ladder()),
    ("fig4-system-architecture",    d4_system_arch()),
    ("fig5-api-request-flow",       d5_api_flow()),
    ("fig6-delegation-chain",       d6_delegation_chain()),
    ("fig7-il-formula",             d7_il_formula()),
]

for name, svg in diagrams:
    path = os.path.join(OUT, f"{name}.svg")
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote {path}")

print("All SVG diagrams generated.")
