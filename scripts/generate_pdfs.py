"""Generate NHID-Clinical PDF documents using reportlab."""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Brand colors (must match nhid-clinical-ui.css :root) ─────────────────────
BLUE    = colors.HexColor("#0b6ebc")
TEAL    = colors.HexColor("#188eaa")
DARK    = colors.HexColor("#1a1d26")
SLATE   = colors.HexColor("#2e3347")
LGRAY   = colors.HexColor("#f5f6fa")
MGRAY   = colors.HexColor("#e8eaef")
DGRAY   = colors.HexColor("#6b7285")
RED     = colors.HexColor("#c0392b")
GREEN   = colors.HexColor("#27ae60")
AMBER   = colors.HexColor("#e67e22")
WHITE   = colors.white

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "specs")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
FONT_DIR = os.path.join(ASSETS_DIR, "fonts")
LOGO_PATH = os.path.join(ASSETS_DIR, "brand-icon.png")

# ── Brand font: Inter (matches --sans / --display in nhid-clinical-ui.css) ──
try:
    pdfmetrics.registerFont(TTFont("Inter", os.path.join(FONT_DIR, "Inter-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Inter-Bold", os.path.join(FONT_DIR, "Inter-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Inter-SemiBold", os.path.join(FONT_DIR, "Inter-SemiBold.ttf")))
    pdfmetrics.registerFont(TTFont("Inter-Italic", os.path.join(FONT_DIR, "Inter-Italic.ttf")))
    pdfmetrics.registerFontFamily(
        "Inter", normal="Inter", bold="Inter-Bold",
        italic="Inter-Italic", boldItalic="Inter-Bold"
    )
    FONT_REGULAR, FONT_BOLD, FONT_SEMIBOLD, FONT_ITALIC = (
        "Inter", "Inter-Bold", "Inter-SemiBold", "Inter-Italic"
    )
except Exception:
    # Fallback if assets/fonts/*.ttf are missing — Helvetica is metric-compatible
    # but will not visually match the website's Inter typeface.
    FONT_REGULAR, FONT_BOLD, FONT_SEMIBOLD, FONT_ITALIC = (
        FONT_REGULAR, FONT_BOLD, FONT_BOLD, FONT_ITALIC
    )

# ── Custom flowables ─────────────────────────────────────────────────────────

class ColorBlock(Flowable):
    """A filled rectangle with a title + body text. Height auto-grows to fit
    the wrapped body text so long copy is never silently clipped."""
    def __init__(self, title, body, bg, fg=WHITE, width=None, height=None):
        super().__init__()
        self.title = title
        self.body = body
        self.bg = bg
        self.fg = fg
        self._width = width or 6.5 * inch
        self._lines = self._wrap_lines()
        min_height = 32 + len(self._lines) * 13 + 10
        self._height = max(height or 0, min_height)

    def _wrap_lines(self):
        words = self.body.split()
        lines = []
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if pdfmetrics.stringWidth(test, FONT_REGULAR, 9) < self._width - 28:
                line = test
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
        return lines

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.roundRect(0, 0, self._width, self._height, 6, fill=1, stroke=0)
        c.setFillColor(self.fg)
        c.setFont(FONT_BOLD, 10)
        c.drawString(14, self._height - 18, self.title)
        c.setFont(FONT_REGULAR, 9)
        y = self._height - 32
        for l in self._lines:
            c.drawString(14, y, l)
            y -= 13

    def wrap(self, availWidth, availHeight):
        return self._width, self._height


class TitleBanner(Flowable):
    """Full-width title banner."""
    def __init__(self, title, subtitle, version, bg=DARK, width=6.5*inch):
        super().__init__()
        self.title = title
        self.subtitle = subtitle
        self.version = version
        self.bg = bg
        self._width = width
        self._height = 1.6 * inch

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.rect(0, 0, self._width, self._height, fill=1, stroke=0)
        # accent bar
        c.setFillColor(TEAL)
        c.rect(0, self._height - 5, self._width, 5, fill=1, stroke=0)
        # title
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 20)
        c.drawString(18, self._height - 40, self.title)
        # subtitle — shrink to fit so long subtitles never run into the logo
        logo_clearance = 52 if os.path.exists(LOGO_PATH) else 0
        avail = self._width - 36 - logo_clearance
        sub_size = 11
        while sub_size > 8 and pdfmetrics.stringWidth(self.subtitle, FONT_REGULAR, sub_size) > avail:
            sub_size -= 0.5
        c.setFont(FONT_REGULAR, sub_size)
        c.setFillColor(colors.HexColor("#b0bcd4"))
        c.drawString(18, self._height - 58, self.subtitle)
        # version + date badges
        c.setFillColor(TEAL)
        c.roundRect(18, 12, 70, 20, 4, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 9)
        c.drawCentredString(53, 18, self.version)
        c.setFillColor(colors.HexColor("#3a4060"))
        c.roundRect(96, 12, 110, 20, 4, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#b0bcd4"))
        c.setFont(FONT_REGULAR, 9)
        c.drawCentredString(151, 18, "June 2026 · CC BY 4.0")
        # logo mark, top-right
        if os.path.exists(LOGO_PATH):
            try:
                logo_h = 34
                logo_w = 34
                c.drawImage(LOGO_PATH, self._width - logo_w - 18, self._height - logo_h - 16,
                            width=logo_w, height=logo_h, mask="auto", preserveAspectRatio=True)
            except Exception:
                pass

    def wrap(self, availWidth, availHeight):
        return self._width, self._height


class ControlCard(Flowable):
    """Visual card for one NHID control."""
    def __init__(self, control_id, name, requirement, color, width=3.05*inch):
        super().__init__()
        self.control_id = control_id
        self.name = name
        self.requirement = requirement
        self.color = color
        self._width = width
        self._height = 1.45 * inch

    def draw(self):
        c = self.canv
        # background
        c.setFillColor(LGRAY)
        c.roundRect(0, 0, self._width, self._height, 6, fill=1, stroke=0)
        # color top bar
        c.setFillColor(self.color)
        c.roundRect(0, self._height - 28, self._width, 28, 6, fill=1, stroke=0)
        c.rect(0, self._height - 28, self._width, 14, fill=1, stroke=0)
        # control ID
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 13)
        c.drawString(10, self._height - 20, self.control_id)
        # name
        c.setFont(FONT_REGULAR, 8)
        c.setFillColor(DGRAY)
        c.drawString(10, self._height - 40, self.name)
        # requirement text - word wrap
        c.setFont(FONT_REGULAR, 8.5)
        c.setFillColor(DARK)
        words = self.requirement.split()
        lines = []
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if c.stringWidth(test, FONT_REGULAR, 8.5) < self._width - 20:
                line = test
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
        y = self._height - 56
        for l in lines:
            if y < 8:
                break
            c.drawString(10, y, l)
            y -= 13

    def wrap(self, availWidth, availHeight):
        return self._width, self._height


class TimelineBar(Flowable):
    """3-month timeline bar."""
    def __init__(self, width=6.5*inch):
        super().__init__()
        self._width = width
        self._height = 1.5 * inch

    def draw(self):
        c = self.canv
        phases = [
            ("Month 1", "Behavioral\nBaseline", BLUE),
            ("Month 2", "Gap\nAnalysis", TEAL),
            ("Month 3", "Written\nAssessment", GREEN),
        ]
        seg_w = self._width / 3
        for i, (label, desc, col) in enumerate(phases):
            x = i * seg_w
            c.setFillColor(col)
            c.rect(x, self._height - 52, seg_w - 4, 52, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont(FONT_BOLD, 10)
            c.drawCentredString(x + seg_w / 2 - 2, self._height - 18, label)
            c.setFont(FONT_REGULAR, 8.5)
            for j, line in enumerate(desc.split("\n")):
                c.drawCentredString(x + seg_w / 2 - 2, self._height - 32 - j * 13, line)
            # connector arrow
            if i < 2:
                ax = x + seg_w - 4
                ay = self._height - 26
                c.setFillColor(WHITE)
                c.setFont(FONT_BOLD, 14)
                c.drawString(ax - 2, ay, "▶")
        # bottom labels
        c.setFillColor(DGRAY)
        c.setFont(FONT_REGULAR, 8)
        labels = ["Log · Identify · Record", "Evaluate · Quantify", "Compile · Share"]
        for i, lbl in enumerate(labels):
            c.drawCentredString((i + 0.5) * seg_w, 8, lbl)

    def wrap(self, availWidth, availHeight):
        return self._width, self._height


class LayerStack(Flowable):
    """Five-layer trust stack visual."""
    def __init__(self, width=6.5*inch):
        super().__init__()
        self._width = width
        self._height = 2.4 * inch

    def draw(self):
        c = self.canv
        layers = [
            ("0", "NPI Gap",            "The problem — no cross-org NPI auth",                  colors.HexColor("#8e2020")),
            ("1", "STIR/SHAKEN",        "RFC 8224 — carrier number auth (A/B/C attestation)",   colors.HexColor("#9e5a00")),
            ("2", "NHID-Clinical v1.3", "Behavioral baseline — 4 controls, 5 CTS tests",        BLUE),
            ("3", "NHID-Auth v2",       "Cryptographic agent identity — Ed25519, NPI binding",   TEAL),
            ("4", "FHIR / OpenTelemetry","Healthcare-native audit + SIEM export",                GREEN),
        ]
        row_h = self._height / len(layers)
        for i, (num, name, desc, col) in enumerate(reversed(layers)):
            y = i * row_h
            c.setFillColor(col)
            c.rect(0, y, self._width, row_h - 2, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont(FONT_BOLD, 9)
            c.drawString(10, y + row_h - 16, f"Layer {num}  ·  {name}")
            c.setFont(FONT_REGULAR, 8)
            c.setFillColor(colors.HexColor("#e0e8f0"))
            c.drawString(10, y + 6, desc)

    def wrap(self, availWidth, availHeight):
        return self._width, self._height


class APITable(Flowable):
    """API endpoints visual table."""
    def __init__(self, width=6.5*inch):
        super().__init__()
        self._width = width
        self._height = 1.9 * inch

    def draw(self):
        c = self.canv
        rows = [
            ("POST", "/v1/demo/check",           "none",      "Raw NHID event → result"),
            ("POST", "/v1/adapters/vapi/check",  "none",      "Native VAPI payload → result"),
            ("POST", "/v1/adapters/twilio/check","none",      "Native Twilio payload → result"),
            ("POST", "/v1/conformance/check",    "x-api-key", "Production conformance check"),
            ("GET",  "/health",                  "none",      "Liveness probe"),
        ]
        row_h = (self._height - 28) / len(rows)
        # header
        c.setFillColor(DARK)
        c.rect(0, self._height - 28, self._width, 28, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 9)
        c.drawString(8, self._height - 17, "Method")
        c.drawString(62, self._height - 17, "Endpoint")
        c.drawString(290, self._height - 17, "Auth")
        c.drawString(370, self._height - 17, "Purpose")
        for i, (method, path, auth, purpose) in enumerate(rows):
            y = self._height - 28 - (i + 1) * row_h
            bg = LGRAY if i % 2 == 0 else WHITE
            c.setFillColor(bg)
            c.rect(0, y, self._width, row_h, fill=1, stroke=0)
            mcol = BLUE if method == "POST" else GREEN
            c.setFillColor(mcol)
            c.roundRect(5, y + 4, 42, row_h - 8, 3, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont(FONT_BOLD, 7.5)
            c.drawCentredString(26, y + 9, method)
            c.setFillColor(DARK)
            c.setFont(FONT_REGULAR, 8)
            c.drawString(54, y + 9, path)
            akol = RED if auth == "x-api-key" else DGRAY
            c.setFillColor(akol)
            c.setFont(FONT_BOLD if auth != "none" else FONT_REGULAR, 8)
            c.drawString(286, y + 9, auth)
            c.setFillColor(DGRAY)
            c.setFont(FONT_REGULAR, 8)
            c.drawString(366, y + 9, purpose)

    def wrap(self, availWidth, availHeight):
        return self._width, self._height


def _styles():
    s = getSampleStyleSheet()
    normal = s["Normal"]
    h1 = ParagraphStyle("H1", fontName=FONT_BOLD, fontSize=14, textColor=DARK, spaceAfter=6)
    h2 = ParagraphStyle("H2", fontName=FONT_BOLD, fontSize=11, textColor=BLUE, spaceAfter=4, spaceBefore=10)
    body = ParagraphStyle("Body", fontName=FONT_REGULAR, fontSize=9, textColor=SLATE, leading=14, spaceAfter=4)
    small = ParagraphStyle("Small", fontName=FONT_REGULAR, fontSize=8, textColor=DGRAY, leading=12)
    disc = ParagraphStyle("Disclaimer", fontName=FONT_ITALIC, fontSize=7.5,
                          textColor=DGRAY, leading=11, borderColor=AMBER, borderWidth=0.5,
                          borderPadding=6, backColor=colors.HexColor("#fffbf0"))
    return h1, h2, body, small, disc


def _footer_canvas(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DGRAY)
    canvas.setFont(FONT_REGULAR, 7.5)
    canvas.drawString(inch, 0.5 * inch,
        "NHID-Clinical  ·  nhid-clinical.org  ·  CC BY 4.0  ·  Brianna Baynard  ·  NIST-2025-0035-0026")
    canvas.drawRightString(7.5 * inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


# ── Document 1: Shadow Evaluation Guide ──────────────────────────────────────

def make_shadow_guide():
    path = os.path.join(OUT_DIR, "NHID-Clinical-Shadow-Evaluation-Guide.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    H1, H2, BODY, SMALL, DISC = _styles()
    story = []

    story.append(TitleBanner(
        "Shadow Evaluation Guide",
        "NHID-Clinical v1.3  ·  90-Day Behavioral Baseline for AI Voice Agents",
        "v1.3"
    ))
    story.append(Spacer(1, 0.18*inch))

    # Disclaimer
    story.append(Paragraph(
        "⚠  NHID-Clinical is an early-stage open proposal by Brianna Baynard. "
        "It is not an accredited standard or regulatory requirement. No payer has piloted "
        "or adopted it yet — you would be among the first.",
        DISC
    ))
    story.append(Spacer(1, 0.15*inch))

    # What this is — 4 colored info boxes
    story.append(Paragraph("What This Is", H1))
    info_cards = [
        ("No Cost",        BLUE,  "No vendor changes. No production risk. Observe-only alongside your current call flow."),
        ("Shadow Mode",    TEAL,  "Your existing call handling is unchanged. Measure how today's AI voice traffic behaves."),
        ("No Commitment",  GREEN, "No certification, no SLA. Share anonymized findings with the community if you choose."),
        ("Clear Goal",     SLATE, "Produce a written behavioral baseline showing AI agent disclosure, escalation, and logging."),
    ]
    for title, col, body_txt in info_cards:
        story.append(ColorBlock(title, body_txt, col, width=6.5*inch, height=0.85*inch))
        story.append(Spacer(1, 0.06*inch))

    story.append(Spacer(1, 0.12*inch))

    # 90-Day Timeline
    story.append(Paragraph("The 90-Day Structure", H1))
    story.append(TimelineBar())
    story.append(Spacer(1, 0.08*inch))

    phase_data = [
        ("Month 1 — Behavioral Baseline",
         "Log incoming calls. Identify AI voice callers. Record disclosure timing, "
         "escalation behavior, and audit trail presence for a sample of eligibility, "
         "claim status, and prior authorization calls."),
        ("Month 2 — Gap Analysis",
         "Evaluate identified AI calls against the v1.3 controls (IDG-01, PDX-01, DBC-01, "
         "EIT-01, plus the supplemental ATR-01 audit-trail control). Quantify what passes, "
         "what fails, what is ambiguous."),
        ("Month 3 — Written Assessment",
         "Compile findings into a short written assessment. Share anonymized results "
         "with the community to help inform the next version of the proposal."),
    ]
    for title, body_txt in phase_data:
        story.append(Paragraph(title, H2))
        story.append(Paragraph(body_txt, BODY))

    # The Four Controls
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("The Four Controls You Are Observing", H1))
    story.append(Spacer(1, 0.08*inch))

    controls = [
        ("IDG-01", "Identity Disclosure Gate",
         "AI agent must disclose it is automated before any PHI or data exchange.", BLUE),
        ("DBC-01", "Deceptive Behavior Check",
         "No synthetic voice artifacts designed to impersonate a human. No fake breathing.", SLATE),
        ("EIT-01", "Escalation & Intervention",
         "Immediate, clean escalation to a human on request — no delay, no re-prompt.", TEAL),
        ("ATR-01", "Audit Trail",
         "Basic log reconstructing when disclosure occurred and what data was exchanged.", GREEN),
    ]
    # Two-column card layout
    for i in range(0, len(controls), 2):
        row_cards = []
        for cid, name, req, col in controls[i:i+2]:
            row_cards.append(ControlCard(cid, name, req, col))
        if len(row_cards) == 2:
            t = Table([[row_cards[0], row_cards[1]]], colWidths=[3.2*inch, 3.2*inch])
            t.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 4)]))
            story.append(t)
        else:
            story.append(row_cards[0])
        story.append(Spacer(1, 0.1*inch))

    # What you need
    story.append(Paragraph("What You Need", H1))
    needs = [
        "Access to call logs or recordings for a sample of incoming administrative calls "
        "(eligibility, claim status, prior authorization)",
        "About 30 minutes of staff time for orientation",
        "Willingness to share anonymized findings if you choose to",
    ]
    for n in needs:
        story.append(Paragraph(f"•  {n}", BODY))

    # How to start
    story.append(Spacer(1, 0.1*inch))
    story.append(ColorBlock(
        "How to Start",
        "Email contact@nhid-clinical.org with subject line 'Shadow Evaluation'. "
        "Include your role and the workflows you want to observe.",
        BLUE, width=6.5*inch, height=0.8*inch
    ))

    doc.build(story, onFirstPage=_footer_canvas, onLaterPages=_footer_canvas)
    print(f"  ✓  {path}")
    return path


# ── Document 2: Core Specification ───────────────────────────────────────────

def make_core_spec():
    path = os.path.join(OUT_DIR, "NHID-Clinical-v1.3-Core-Specification.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    H1, H2, BODY, SMALL, DISC = _styles()
    story = []

    story.append(TitleBanner(
        "NHID-Clinical v1.3 Core Specification",
        "Behavioral Baseline for AI Voice Agents in B2B Healthcare Payer–Provider Calls",
        "v1.3"
    ))
    story.append(Spacer(1, 0.18*inch))

    story.append(Paragraph(
        "⚠  NHID-Clinical is an early-stage open proposal by Brianna Baynard. "
        "It is not an accredited standard or regulatory requirement.",
        DISC
    ))
    story.append(Spacer(1, 0.15*inch))

    # Overview
    story.append(Paragraph("Overview", H1))
    story.append(Paragraph(
        "NHID-Clinical v1.3 defines four deterministic behavioral controls for AI voice agents "
        "operating in B2B healthcare calls. The conformance test suite (CTS) produces identical "
        "pass/fail output for the same input — no ambiguity, no interpretation.",
        BODY
    ))
    story.append(Spacer(1, 0.08*inch))

    # Stats row
    stats = [
        ("4", "Controls"),
        ("18", "CTS Tests"),
        ("270", "Tests Passing"),
        ("6", "Adapters\n(VAPI, Twilio, +4)"),
    ]
    stat_cells = []
    for val, lbl in stats:
        stat_cells.append(Paragraph(
            f'<font size="22" color="#0b6ebc"><b>{val}</b></font><br/>'
            f'<font size="8" color="#6b7285">{lbl}</font>',
            ParagraphStyle("SC", alignment=TA_CENTER, leading=16)
        ))
    t = Table([stat_cells], colWidths=[1.6*inch]*4)
    t.setStyle(TableStyle([
        ("BOX",          (0,0), (-1,-1), 0.5, MGRAY),
        ("LINEAFTER",    (0,0), (2,0),   0.5, MGRAY),
        ("BACKGROUND",   (0,0), (-1,-1), LGRAY),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.15*inch))

    # The Four Controls
    story.append(Paragraph("The Four Controls", H1))
    story.append(Spacer(1, 0.08*inch))

    controls = [
        ("IDG-01", "Identity Disclosure Gate",
         "AI agent MUST identify itself as automated before any PHI exchange. "
         "Disclosure must occur in the first utterance.", BLUE),
        ("PDX-01", "PHI Data Exchange Gate",
         "No protected health information may be exchanged until identity is disclosed "
         "and consent is obtained.", RED),
        ("DBC-01", "Deceptive Behavior Check",
         "No synthetic voice artifacts designed to impersonate a human caller. "
         "No fake breathing, no human-only openers.", SLATE),
        ("EIT-01", "Escalation & Intervention",
         "Human escalation path must be available and communicated. Transfer must "
         "execute immediately on request — no delay, no re-prompt.", TEAL),
    ]
    for i in range(0, len(controls), 2):
        row_cards = []
        for cid, name, req, col in controls[i:i+2]:
            row_cards.append(ControlCard(cid, name, req, col))
        if len(row_cards) == 2:
            t2 = Table([[row_cards[0], row_cards[1]]], colWidths=[3.2*inch, 3.2*inch])
            t2.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),4)]))
            story.append(t2)
        else:
            story.append(row_cards[0])
        story.append(Spacer(1, 0.1*inch))

    # ATR-01 full width
    story.append(ColorBlock(
        "ATR-01  ·  Audit Trail",
        "Machine-readable audit log must be producible for every call. "
        "Log must include: call start time, disclosure timestamp, data exchange events, "
        "escalation events, and agent identity. Validates as a plain HL7 FHIR R4 AuditEvent "
        "(base spec v4.0.1) — no named Implementation Guide conformance (e.g. IHE BALP) is claimed.",
        GREEN, width=6.5*inch, height=0.9*inch
    ))
    story.append(Spacer(1, 0.15*inch))

    # CTS Tests
    story.append(Paragraph("Conformance Test Suite (CTS) — 18 Test Cases", H1))
    story.append(Paragraph(
        "tests/nhid_conformance_test_suite_v1.yaml defines 18 deterministic CTS cases across "
        "the four controls below; representative cases shown.",
        SMALL
    ))
    story.append(Spacer(1, 0.04*inch))
    cts_data = [
        ["Test ID", "What It Verifies", "Severity"],
        ["CTS-IDG-01", "Disclosure present before any data exchange", "critical"],
        ["CTS-PDX-01", "No PHI before disclosure + consent", "critical"],
        ["CTS-DBC-01", "No deceptive audio artifacts in transcript", "high"],
        ["CTS-EIT-01", "Escalation path declared and accessible", "high"],
        ["CTS-ATR-01", "Audit log fields present and well-formed", "medium"],
    ]
    t3 = Table(cts_data, colWidths=[1.5*inch, 3.5*inch, 1.3*inch])
    t3.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), DARK),
        ("TEXTCOLOR",    (0,0), (-1,0), WHITE),
        ("FONTNAME",     (0,0), (-1,0), FONT_BOLD),
        ("FONTSIZE",     (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[LGRAY, WHITE]),
        ("GRID",         (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(t3)
    story.append(Spacer(1, 0.15*inch))

    # Live API
    story.append(Paragraph("Live Conformance API", H1))
    story.append(Paragraph(
        "The reference implementation is hosted on AWS Lambda. No signup required for demo routes.",
        BODY
    ))
    story.append(APITable())
    story.append(Spacer(1, 0.1*inch))
    story.append(ColorBlock(
        "Base URL",
        "https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod",
        SLATE, width=6.5*inch, height=0.55*inch
    ))
    story.append(Spacer(1, 0.15*inch))

    # NHID-Auth v2
    story.append(Paragraph("NHID-Auth v2 — Cryptographic Agent Identity", H1))
    story.append(ColorBlock(
        "Released June 2026  ·  CC BY 4.0",
        "Ed25519 provider-signed agent passports with NPI binding. Scoped delegation chains "
        "(max 3 hops). Per-agent and per-delegation revocation. Call-SID nonce binding. "
        "Reference implementation: src/agent_identity.py (42 dedicated tests).",
        TEAL, width=6.5*inch, height=0.9*inch
    ))

    doc.build(story, onFirstPage=_footer_canvas, onLaterPages=_footer_canvas)
    print(f"  ✓  {path}")
    return path


# ── Document 3: Operational Blueprint ────────────────────────────────────────

def make_operational_blueprint():
    path = os.path.join(OUT_DIR, "NHID-Clinical-Operational-Blueprint-v1.3.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    H1, H2, BODY, SMALL, DISC = _styles()
    story = []

    story.append(TitleBanner(
        "Operational Blueprint",
        "NHID-Clinical v1.3  ·  From RFP Language to Audit-Ready Production",
        "v1.3"
    ))
    story.append(Spacer(1, 0.18*inch))

    story.append(Paragraph(
        "⚠  NHID-Clinical is an early-stage open proposal by Brianna Baynard. "
        "It is not an accredited standard or regulatory requirement.",
        DISC
    ))
    story.append(Spacer(1, 0.15*inch))

    # Trust Stack
    story.append(Paragraph("Five-Layer Trust Stack", H1))
    story.append(LayerStack())
    story.append(Spacer(1, 0.15*inch))

    # Implementation Phases
    story.append(Paragraph("Implementation Phases", H1))
    phases = [
        ("Phase 1  ·  Weeks 1–2",  BLUE,  "Add RFP Language",
         "Insert the standard NHID-Clinical conformance clause into your next voice AI vendor "
         "RFP or BAA amendment. One clause covers all four controls."),
        ("Phase 2  ·  Weeks 3–6",  TEAL,  "Vendor Sandbox Testing",
         "Ask your vendor to run: git clone + pip install -r requirements.txt + "
         "python -m pytest tests/ -v. Results in under 5 minutes. Request full terminal output."),
        ("Phase 3  ·  Weeks 7–10", GREEN, "Validate Logs Yourself",
         "Place vendor JSON traces in the traces/ folder. Run the test suite. "
         "Manually verify: disclosure before NPI, no deceptive artifacts, escalation fires in ≤2s."),
        ("Phase 4  ·  Weeks 11–12",SLATE, "Measure & Decide",
         "Compare verification latency (target <5s) and escalation volume (target >30% reduction). "
         "Use findings to update vendor contract requirements."),
    ]
    for title, col, subtitle, body_txt in phases:
        story.append(ColorBlock(
            f"{title}  —  {subtitle}",
            body_txt, col, width=6.5*inch, height=0.85*inch
        ))
        story.append(Spacer(1, 0.06*inch))

    story.append(Spacer(1, 0.1*inch))

    # RFP Clause
    story.append(Paragraph("Standard RFP / BAA Clause", H1))
    story.append(Spacer(1, 0.1*inch))
    clause_style = ParagraphStyle(
        "Clause", fontName="Courier", fontSize=8.5, leading=13,
        backColor=colors.HexColor("#f0f4ff"),
        borderColor=BLUE, borderWidth=0.75, borderPadding=10,
        textColor=DARK
    )
    story.append(Paragraph(
        '"The vendor\'s AI agent SHALL produce NHID-Clinical v1.3 JSON trace logs for all '
        'B2B administrative calls, including disclosure timestamps and opt-out handling. '
        'The payer may run the open-source conformance test suite against vendor output at any time."',
        clause_style
    ))
    story.append(Spacer(1, 0.15*inch))

    # Metrics
    story.append(Paragraph("Target Metrics", H1))
    metric_data = [
        ["Metric",                     "Today (typical)",           "Target with NHID-Clinical"],
        ["Verification latency",        "3–5 min or call terminated","< 5 seconds"],
        ["Audit effort per vendor",     "Manual call review (hours)","~2 minutes (run test suite)"],
        ["RFP disclosure language",     "Custom per vendor",         "One standard clause"],
        ["Escalation response time",    "Untracked",                 "≤ 2 seconds, logged"],
    ]
    t4 = Table(metric_data, colWidths=[2.0*inch, 2.1*inch, 2.2*inch])
    t4.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), FONT_BOLD),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGRAY, WHITE]),
        ("TEXTCOLOR",     (2,1), (2,-1), GREEN),
        ("FONTNAME",      (2,1), (2,-1), FONT_BOLD),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(t4)
    story.append(Spacer(1, 0.15*inch))

    # Regulatory Alignment
    story.append(Paragraph("Regulatory Alignment", H1))
    reg_data = [
        ["Regulatory Driver",    "Specific Requirement",                "NHID-Clinical Control"],
        ["CMS-0057-F",           "FHIR API, 72hr turnaround, 5yr log",  "FHIR AuditEvent + ATR-01"],
        ["MACPAC May 2026",      "AI transparency, human review",       "EIT-01 + ATR-01"],
        ["DOJ FCA 2026",         "Explainability + audit trail",        "LOG + CTS evidence"],
        ["State AI Laws",        "Inspectable, auditable decisions",    "IDG-01 + DBC-01"],
        ["NIST CAISI 2026",      "Cross-org agent identity",            "NHID-Auth v2"],
    ]
    t5 = Table(reg_data, colWidths=[1.7*inch, 2.5*inch, 2.1*inch])
    t5.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), FONT_BOLD),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGRAY, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(t5)

    doc.build(story, onFirstPage=_footer_canvas, onLaterPages=_footer_canvas)
    print(f"  ✓  {path}")
    return path


# ── Document 4: v2 Technical Playbook ────────────────────────────────────────

def make_technical_playbook():
    path = os.path.join(OUT_DIR, "NHID-Clinical-v2-Technical-Playbook.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    H1, H2, BODY, SMALL, DISC = _styles()
    story = []

    story.append(TitleBanner(
        "v2 Technical Playbook",
        "NHID-Clinical  ·  Tech Stack, Adoption Tiers & Governance Framework Reference",
        "v2.0"
    ))
    story.append(Spacer(1, 0.18*inch))

    story.append(Paragraph(
        "⚠  NHID-Clinical is an early-stage open proposal by Brianna Baynard. "
        "It is not an accredited standard or regulatory requirement. This playbook is a "
        "condensed technical reference distilled from the project's internal knowledge archive.",
        DISC
    ))
    story.append(Spacer(1, 0.15*inch))

    # Core Objectives
    story.append(Paragraph("Core Objectives", H1))
    for n in [
        "Establish a voluntary behavioral baseline — disclosure, data-gating, escalation, "
        "and audit — for AI voice agents in B2B healthcare payer–provider calls.",
        "Provide an open, testable reference: every claim is backed by runnable, deterministic code.",
        "Layer in cryptographic agent identity (NHID-Auth v2) as authorization matures beyond "
        "behavior alone — NPI-bound passports, scoped delegation, per-agent revocation.",
        "Make Call Authorization Score (CAS) a procurement-grade compliance signal payers and "
        "vendors can both verify independently.",
    ]:
        story.append(Paragraph(f"•  {n}", BODY))
    story.append(Spacer(1, 0.1*inch))

    # Five-Layer Trust Stack
    story.append(Paragraph("Five-Layer Trust Stack", H1))
    story.append(LayerStack())
    story.append(Spacer(1, 0.15*inch))

    # Tech Stack
    story.append(Paragraph("Tech Stack & Repository Layout", H1))
    stack_data = [
        ["Layer", "Component", "Purpose"],
        ["Policy engine",  "src/nhid_policy_engine_v1.py",   "Deterministic rule evaluation (670+ lines)"],
        ["Identity (v2)",  "src/agent_identity.py",          "Ed25519 delegation & agent passports"],
        ["Scoring",        "src/nhid_cas.py",                "Call Authorization Score engine"],
        ["Audit",          "src/fhir_audit_emitter.py",      "FHIR R4 AuditEvent generation"],
        ["Conformance",    "tests/nhid_conformance_test_suite_v1.yaml", "18 deterministic CTS cases"],
        ["Adapters",       "adapters/*.py",                  "VAPI, Twilio, Vonage, Retell, Amazon Connect, call-progress"],
        ["Compute",        "functions/handler.py",           "AWS Lambda entry point"],
        ["Deploy",         "template.yaml",                  "AWS SAM CloudFormation"],
    ]
    t6 = Table(stack_data, colWidths=[1.25*inch, 2.55*inch, 2.55*inch])
    t6.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), FONT_BOLD),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGRAY, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(t6)
    story.append(Spacer(1, 0.15*inch))

    # Adoption Ladder
    story.append(Paragraph("Integration Ladder — Tier 0 to Tier 2", H1))
    story.append(Paragraph(
        "Each tier is independently useful. Stop at any rung — v2's cryptographic layer is "
        "powerful but it is not the on-ramp.",
        BODY
    ))
    tier_data = [
        ["Tier", "Time", "What You Get", "What You Need"],
        ["0", "15 min", "Conformance verdict + CAS score per call", "A transcript and curl"],
        ["1", "~2 hr",  "Automated per-call checks in your pipeline", "An end-of-call webhook"],
        ["2", "~1 day", "Cryptographic agent identity (NPI-bound)",   "pip install cryptography"],
    ]
    t7 = Table(tier_data, colWidths=[0.55*inch, 0.85*inch, 2.85*inch, 2.1*inch])
    t7.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), FONT_BOLD),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGRAY, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(t7)
    story.append(Spacer(1, 0.15*inch))

    story.append(PageBreak())

    # Governance Framework — CAS
    story.append(Paragraph("Governance Framework — Call Authorization Score (CAS)", H1))
    story.append(Paragraph(
        "CAS provides a continuous compliance signal between 0.0 and 1.0 per call session: "
        "<b>CAS = F_IAF × F_NOCF × ECF</b> — Identity Assurance, Operational Conformance, and "
        "Evidence Completeness factors.",
        BODY
    ))
    cas_data = [
        ["CAS Score", "Tier", "Badge"],
        ["≥ 0.90", "Verified Trust", "L2"],
        ["≥ 0.75", "Conditional Trust", "L1"],
        ["≥ 0.50", "Review Required", "—"],
        ["≥ 0.20", "Denied / Degraded", "—"],
        ["< 0.20", "Hard Denial", "—"],
    ]
    t8 = Table(cas_data, colWidths=[1.5*inch, 2.5*inch, 1.0*inch])
    t8.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), FONT_BOLD),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGRAY, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(t8)
    story.append(Spacer(1, 0.12*inch))

    story.append(Paragraph("Policy Engine Action Priority", H2))
    pri_data = [
        ["Priority", "Action", "Trigger"],
        ["5", "DENY_DATA", "IDG-01 or PDX-01 critical violation"],
        ["4", "ESCALATE_HUMAN", "EIT-01: escalation requested, path available"],
        ["3", "DISCLOSE_IDENTITY", "IDG-01: no prior disclosure detected"],
        ["2", "LOG_ONLY", "DBC-01 text heuristic (non-blocking), ATR-01 minor gap"],
        ["1", "CONTINUE_AI", "All controls pass"],
    ]
    t9 = Table(pri_data, colWidths=[0.7*inch, 1.6*inch, 4.2*inch])
    t9.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), FONT_BOLD),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGRAY, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(t9)
    story.append(Spacer(1, 0.15*inch))

    # Live API quick reference
    story.append(Paragraph("Live API Quick Reference", H1))
    story.append(APITable())
    story.append(Spacer(1, 0.1*inch))
    story.append(ColorBlock(
        "Base URL",
        "https://dc2ipcqs7k.execute-api.us-east-2.amazonaws.com/prod",
        SLATE, width=6.5*inch, height=0.55*inch
    ))

    doc.build(story, onFirstPage=_footer_canvas, onLaterPages=_footer_canvas)
    print(f"  ✓  {path}")
    return path


# ── Document 5: Knowledge Archive (public-safe distillation) ────────────────

def make_knowledge_archive():
    path = os.path.join(OUT_DIR, "NHID-Clinical-Knowledge-Archive.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    H1, H2, BODY, SMALL, DISC = _styles()
    story = []

    story.append(TitleBanner(
        "Knowledge Archive",
        "NHID-Clinical  ·  Public Reference Edition — Vision, Governance & Regulatory Alignment",
        "v1.2"
    ))
    story.append(Spacer(1, 0.18*inch))

    story.append(Paragraph(
        "⚠  NHID-Clinical is an early-stage open proposal by Brianna Baynard. "
        "It is not an accredited standard or regulatory requirement. This is a public-safe "
        "distillation of the project's internal knowledge archive; internal-only sections "
        "(partnership discussions, decision logs, build tasking) are excluded.",
        DISC
    ))
    story.append(Spacer(1, 0.15*inch))

    # Executive Vision
    story.append(Paragraph("Executive Vision", H1))
    story.append(Paragraph(
        "NHID-Clinical was conceived from firsthand experience in payer operations. AI voice "
        "agents began appearing in B2B healthcare payer–provider calls — calls that exchange "
        "Protected Health Information (PHI) and require human escalation paths — without any "
        "consistent disclosure, identity, or audit standard.",
        BODY
    ))
    story.append(ColorBlock(
        "Impersonation Latency",
        "The duration of time an AI agent operates and exchanges PHI without disclosing its "
        "non-human identity. NHID-Clinical median observation: 3 turns before first disclosure "
        "attempt. This is the canonical failure mode the framework exists to prevent.",
        SLATE, width=6.5*inch, height=0.95*inch
    ))
    story.append(Spacer(1, 0.1*inch))

    gap_data = [
        ["Gap", "Description"],
        ["Identity Gap",       "No existing standard requires AI agents to identify themselves before PHI exchange"],
        ["NPI Authorization Gap", "No cross-org NPI delegation mechanism for AI agents calling on behalf of providers"],
        ["Audit Gap",          "Call-level AI decisions are not captured in healthcare-compatible audit formats"],
        ["Escalation Gap",     "AI agents routinely fail to communicate or honor human escalation requests"],
        ["Deception Gap",      "Some vendors use synthetic breathing/hesitation patterns implying human presence"],
    ]
    t10 = Table(gap_data, colWidths=[1.6*inch, 4.9*inch])
    t10.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), FONT_BOLD),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGRAY, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(t10)
    story.append(Spacer(1, 0.15*inch))

    # Core Framework
    story.append(Paragraph("Core Framework — The Four Controls + ATR-01", H1))
    controls = [
        ("IDG-01", "Identity Disclosure Gate",
         "AI agent must disclose it is automated before any PHI request or exchange.", BLUE),
        ("PDX-01", "Pre-Data Exchange Gate",
         "No PHI may be exchanged until IDG-01 disclosure is confirmed.", RED),
        ("DBC-01", "Deceptive Behavior Check",
         "No synthetic voice artifacts or text claims implying human presence.", SLATE),
        ("EIT-01", "Escalation Implementation Test",
         "Human escalation path must be available and honored immediately on request.", TEAL),
    ]
    for i in range(0, len(controls), 2):
        row_cards = []
        for cid, name, req, col in controls[i:i+2]:
            row_cards.append(ControlCard(cid, name, req, col))
        t11 = Table([[row_cards[0], row_cards[1]]], colWidths=[3.2*inch, 3.2*inch])
        t11.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),4)]))
        story.append(t11)
        story.append(Spacer(1, 0.1*inch))
    story.append(ColorBlock(
        "ATR-01  ·  Audit Trail Requirements",
        "Every NHID event must carry event_id, timestamp, session_id, actor_id, state_before/"
        "after, and execution_context. Validates as a plain HL7 FHIR R4 AuditEvent (base spec "
        "v4.0.1) — no named Implementation Guide conformance is claimed.",
        GREEN, width=6.5*inch, height=0.95*inch
    ))
    story.append(Spacer(1, 0.15*inch))

    story.append(PageBreak())

    # Governance
    story.append(Paragraph("Governance — Version Roadmap & CAS", H1))
    ver_data = [
        ["Version", "Description", "Status"],
        ["v1.0", "Original 4 controls (IDG-01, PDX-01, DBC-01, EIT-01)", "Superseded"],
        ["v1.3", "Current: ATR-01 added, CTS expanded to 18 tests, CAS scoring", "Current"],
        ["v2.0", "NHID-Auth cryptographic layer (Ed25519, delegation chains)", "Reference impl. live"],
        ["v2.1", "Planned: STIR/SHAKEN integration, attestation registry", "Future"],
    ]
    t12 = Table(ver_data, colWidths=[0.8*inch, 4.0*inch, 1.7*inch])
    t12.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), FONT_BOLD),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGRAY, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(t12)
    story.append(Spacer(1, 0.15*inch))

    # Identity & Trust
    story.append(Paragraph("Identity & Trust Infrastructure", H1))
    story.append(Paragraph(
        "NHID-Auth v2 is the cryptographic authorization layer: provider-signed, NPI-bound agent "
        "passports (Ed25519), scoped delegation chains (max 3 hops), per-agent and per-delegation "
        "revocation, and call-SID nonce binding. Reference implementation: "
        "<b>src/agent_identity.py</b>.",
        BODY
    ))
    story.append(Spacer(1, 0.1*inch))

    # Technical Architecture
    story.append(Paragraph("Technical Architecture — Live API", H1))
    story.append(APITable())
    story.append(Spacer(1, 0.15*inch))

    # Regulatory Alignment
    story.append(Paragraph("Regulatory Alignment", H1))
    reg_data = [
        ["Regulatory Driver", "Requirement", "NHID-Clinical Control"],
        ["CMS-0057-F",      "FHIR API, 72hr turnaround, 5yr log", "FHIR AuditEvent + ATR-01"],
        ["MACPAC May 2026", "AI transparency, human review",     "EIT-01 + ATR-01"],
        ["State AI Laws",   "Inspectable, auditable decisions",  "IDG-01 + DBC-01"],
        ["NIST CAISI 2026", "Cross-org agent identity",          "NHID-Auth v2"],
        ["HIPAA Security Rule", "PHI safeguards + audit controls", "PDX-01 + ATR-01"],
        ["TCPA",            "Automated caller disclosure",       "IDG-01"],
    ]
    t13 = Table(reg_data, colWidths=[1.7*inch, 2.7*inch, 2.1*inch])
    t13.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), FONT_BOLD),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGRAY, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(t13)
    story.append(Spacer(1, 0.15*inch))

    # NIST / CMS References
    story.append(Paragraph("NIST & CMS Reference Standards", H1))
    std_data = [
        ["Standard", "Reference", "Relevance"],
        ["STIR/SHAKEN",    "RFC 8224 (IETF)",        "Layer 1: carrier number authentication"],
        ["FHIR R4",        "HL7 FHIR v4.0.1",        "Layer 4: AuditEvent resource"],
        ["NIST AI RMF",    "NIST AI 100-1",           "AI risk management framework"],
        ["NIST SP 800-207","Zero Trust Architecture", "Cross-org authorization patterns"],
        ["CMS-0057-F",     "88 FR 80236",             "Interoperability, FHIR API, claims turnaround"],
        ["NPI Registry",   "NPPES (CMS)",             "10-digit provider identifier"],
    ]
    t14 = Table(std_data, colWidths=[1.5*inch, 1.9*inch, 3.1*inch])
    t14.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), FONT_BOLD),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LGRAY, WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.25, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(t14)
    story.append(Spacer(1, 0.15*inch))

    story.append(PageBreak())

    # FAQ
    story.append(Paragraph("FAQ & Plain Language Guide", H1))
    faq = [
        ("Is NHID-Clinical a certification or accreditation?",
         "No. It is a voluntary open proposal (CC BY 4.0). It provides conformance scores, "
         "not formal certifications, and has no legal force."),
        ("Does NHID-Clinical claim FHIR Implementation Guide conformance?",
         "No. NHID-Clinical validates audit events as plain HL7 FHIR R4 AuditEvent resources "
         "against the base spec (v4.0.1) only — it does not claim conformance to any named "
         "Implementation Guide such as IHE BALP."),
        ("We use a realistic AI voice. Does that automatically trigger DBC-01?",
         "No. DBC-01 evaluates explicit deceptive artifact flags and impersonation phrases — "
         "it does not analyze the audio stream directly. Voice realism alone is not a violation."),
        ("What does a payer need to start a shadow evaluation?",
         "Access to a sample of incoming administrative call logs, about 30 minutes of staff "
         "orientation time, and optional willingness to share anonymized findings."),
    ]
    for q, a in faq:
        story.append(Paragraph(q, H2))
        story.append(Paragraph(a, BODY))

    doc.build(story, onFirstPage=_footer_canvas, onLaterPages=_footer_canvas)
    print(f"  ✓  {path}")
    return path


if __name__ == "__main__":
    print("Generating PDFs...")
    make_shadow_guide()
    make_core_spec()
    make_operational_blueprint()
    make_technical_playbook()
    make_knowledge_archive()
    print("Done.")
