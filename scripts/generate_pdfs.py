"""Generate NHID-Clinical PDF documents using reportlab.

Dependencies (not in requirements.txt): pip install reportlab svglib
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image, PageBreak, Preformatted
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import Flowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics import renderPDF

try:
    from svglib.svglib import svg2rlg
except ImportError:
    svg2rlg = None

# ── Brand palette — aligned with the redesigned nhid-clinical website ────────
#   The website moved from a blue-heavy system to teal/cyan on deep navy.
#   Design intent: LIGHT document pages (readable, printable, procurement-safe)
#   with DEEP-NAVY cover/banner/dark panels. Teal is the primary accent; cyan
#   is used sparingly for lines/relationships (it is too light to sit behind
#   white text). This is deliberately NOT a neon or dark-mode document.
#
#   Accent / primary
TEAL_BRIGHT = colors.HexColor("#14B8A6")   # primary accent (site --teal-bright)
CYAN        = colors.HexColor("#67E8F9")   # bright accent — lines/relationships only
TEAL        = colors.HexColor("#14B8A6")   # alias: legacy usages → primary teal
TEAL_DEEP   = colors.HexColor("#0E7E72")   # darker teal for text/fills on white
#   Structure / dark surfaces
NAVY        = colors.HexColor("#0B1726")   # deep navy — covers, banners, headers
SURFACE     = colors.HexColor("#111827")   # dark surface — dark cards/panels
DARK        = colors.HexColor("#111827")   # alias: legacy dark table headers
CREAM       = colors.HexColor("#E8E0D0")   # warm text ON dark surfaces
MUTED       = colors.HexColor("#94A3B8")   # muted text ON dark surfaces
#   Document body (light pages)
INK         = colors.HexColor("#0B1726")   # headings on white
SLATE       = colors.HexColor("#334155")   # body text
DGRAY       = colors.HexColor("#64748B")   # captions / muted body
LGRAY       = colors.HexColor("#f1f5f9")   # zebra row background
MGRAY       = colors.HexColor("#e2e8f0")   # hairline borders
#   Semantic
GREEN       = colors.HexColor("#059669")   # success (fills/text on white)
SUCCESS     = colors.HexColor("#34D399")   # success (bright, on dark surfaces)
AMBER       = colors.HexColor("#F59E0B")   # warning
RED         = colors.HexColor("#EF4444")   # failure
WHITE       = colors.white
#   Legacy alias retained so existing call sites keep compiling; repointed to
#   the primary teal so every former "blue" accent now reads teal.
BLUE        = TEAL_BRIGHT

# ── Per-control accent system (distinct, brand-consistent, dark enough for
#    white text on the control-card header bars) ──────────────────────────────
C_IDG = colors.HexColor("#14B8A6")   # teal
C_PDX = colors.HexColor("#0E7E72")   # deep teal
C_DBC = colors.HexColor("#475569")   # slate
C_EIT = colors.HexColor("#0E7490")   # cyan-deep
C_ATR = colors.HexColor("#059669")   # emerald

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "specs")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
FONT_DIR = os.path.join(ASSETS_DIR, "fonts")
SVG_3D_DIR = os.path.join(ASSETS_DIR, "images", "3d-svg")
RENDER_DIR = os.path.join(ASSETS_DIR, "images", "3d-renders")
LOGO_PATH = os.path.join(ASSETS_DIR, "brand-icon.png")
LOGO_LIGHT_PATH = os.path.join(ASSETS_DIR, "logo-light.jpg")
VISUAL_CAPTION = (
    "Illustrative 3D visualization — conceptual render for clarity (nhid-clinical.org)"
)

# ── Typography — aligned with the website hierarchy ──────────────────────────
#   Display / headlines: Raleway   ·   Body: Inter   ·   Technical: JetBrains Mono
#   (IBM Plex Mono is also vendored — it is the site's actual mono face; switch
#    FONT_MONO to it if exact site parity is preferred over the brief's request.)
FONT_REGULAR, FONT_BOLD, FONT_SEMIBOLD, FONT_ITALIC = (
    "Helvetica", "Helvetica-Bold", "Helvetica-Bold", "Helvetica-Oblique"
)
FONT_DISPLAY = FONT_BOLD          # headline face (Raleway if available)
FONT_DISPLAY_XB = FONT_BOLD       # extra-bold display (covers)
FONT_MONO = "Courier"             # technical face (JetBrains Mono if available)


def _register_fonts():
    global FONT_REGULAR, FONT_BOLD, FONT_SEMIBOLD, FONT_ITALIC
    global FONT_DISPLAY, FONT_DISPLAY_XB, FONT_MONO

    def reg(name, filename):
        pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, filename)))

    # Body — Inter
    try:
        reg("Inter", "Inter-Regular.ttf")
        reg("Inter-Bold", "Inter-Bold.ttf")
        reg("Inter-SemiBold", "Inter-SemiBold.ttf")
        reg("Inter-Italic", "Inter-Italic.ttf")
        pdfmetrics.registerFontFamily(
            "Inter", normal="Inter", bold="Inter-Bold",
            italic="Inter-Italic", boldItalic="Inter-Bold"
        )
        FONT_REGULAR, FONT_BOLD, FONT_SEMIBOLD, FONT_ITALIC = (
            "Inter", "Inter-Bold", "Inter-SemiBold", "Inter-Italic"
        )
        FONT_DISPLAY = FONT_DISPLAY_XB = "Inter-Bold"   # fallback before Raleway loads
    except Exception:
        pass

    # Display — Raleway (headline character matching the site)
    try:
        reg("Raleway-SemiBold", "Raleway-SemiBold.ttf")
        reg("Raleway-Bold", "Raleway-Bold.ttf")
        reg("Raleway-ExtraBold", "Raleway-ExtraBold.ttf")
        FONT_DISPLAY = "Raleway-Bold"
        FONT_DISPLAY_XB = "Raleway-ExtraBold"
    except Exception:
        pass

    # Technical — JetBrains Mono (per brief); IBM Plex Mono also vendored
    try:
        reg("JetBrainsMono", "JetBrainsMono-Regular.ttf")
        reg("JetBrainsMono-Bold", "JetBrainsMono-Bold.ttf")
        FONT_MONO = "JetBrainsMono"
    except Exception:
        pass


_register_fonts()

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


class DisclaimerBanner(Flowable):
    """Prominent open-proposal disclaimer bar."""
    def __init__(self, body, width=6.5 * inch):
        super().__init__()
        self.body = body
        self._width = width
        self._lines = self._wrap(self.body, FONT_REGULAR, 8, self._width - 28)
        self._height = 38 + len(self._lines) * 11 + 8

    def _wrap(self, text, font, size, max_w):
        words = text.split()
        lines, line = [], ""
        for w in words:
            test = (line + " " + w).strip()
            if pdfmetrics.stringWidth(test, font, size) < max_w:
                line = test
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
        return lines

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor("#fff8e6"))
        c.setStrokeColor(AMBER)
        c.setLineWidth(1)
        c.roundRect(0, 0, self._width, self._height, 6, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#9e5a00"))
        c.setFont(FONT_BOLD, 8)
        c.drawString(14, self._height - 16, "OPEN PROPOSAL — NOT A STANDARD OR REGULATORY REQUIREMENT")
        c.setFillColor(SLATE)
        c.setFont(FONT_REGULAR, 8)
        y = self._height - 30
        for ln in self._lines:
            c.drawString(14, y, ln)
            y -= 11

    def wrap(self, availWidth, availHeight):
        return self._width, self._height


class ScaledSvgVisual(Flowable):
    """Premium-framed 3D SVG visual (vector embed, no raster backend required)."""
    def __init__(self, svg_path, width=6.5 * inch, padding=12, caption=None):
        super().__init__()
        self._width = width
        self.padding = padding
        self.caption = caption or VISUAL_CAPTION
        self.drawing = None
        self._draw_h = 0
        self._scale = 1
        if svg2rlg and os.path.exists(svg_path):
            try:
                self.drawing = svg2rlg(svg_path)
            except Exception:
                self.drawing = None
        if self.drawing and self.drawing.width > 0:
            inner_w = width - 2 * padding
            self._scale = inner_w / self.drawing.width
            self._draw_h = self.drawing.height * self._scale
        cap_h = 0.24 * inch
        self._height = self._draw_h + 2 * padding + cap_h + 6

    def draw(self):
        c = self.canv
        if not self.drawing:
            return
        cap_h = 0.24 * inch
        frame_h = self._height - cap_h
        c.setFillColor(colors.HexColor("#f8fbfd"))
        c.setStrokeColor(NAVY)
        c.setLineWidth(0.75)
        c.roundRect(0, cap_h, self._width, frame_h - cap_h, 8, fill=1, stroke=1)
        c.setFillColor(TEAL)
        c.rect(0, frame_h - 5, self._width, 5, fill=1, stroke=0)
        c.saveState()
        c.translate(self.padding, cap_h + self.padding)
        c.scale(self._scale, self._scale)
        renderPDF.draw(self.drawing, c, 0, 0)
        c.restoreState()
        c.setFont(FONT_ITALIC, 7)
        c.setFillColor(DGRAY)
        cap_lines = self._wrap_caption(self.caption)
        y = cap_h - 10
        for ln in cap_lines:
            c.drawCentredString(self._width / 2, y, ln)
            y -= 9

    def _wrap_caption(self, text):
        words = text.split()
        lines, line = [], ""
        for w in words:
            test = (line + " " + w).strip()
            if pdfmetrics.stringWidth(test, FONT_ITALIC, 7) < self._width - 16:
                line = test
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
        return lines[:2]

    def wrap(self, availWidth, availHeight):
        return self._width, self._height


class SectionRule(Flowable):
    """Teal accent rule under section headings."""
    def __init__(self, width=6.5 * inch):
        super().__init__()
        self._width = width
        self._height = 0.14 * inch

    def draw(self):
        c = self.canv
        c.setStrokeColor(TEAL)
        c.setLineWidth(2)
        c.line(0, 0.06 * inch, 1.4 * inch, 0.06 * inch)
        c.setStrokeColor(MGRAY)
        c.setLineWidth(0.5)
        c.line(1.45 * inch, 0.06 * inch, self._width, 0.06 * inch)

    def wrap(self, availWidth, availHeight):
        return self._width, self._height


class TitleBanner(Flowable):
    """Full-width title banner."""
    def __init__(self, title, subtitle, version, bg=NAVY, width=6.5*inch,
                 logo_path=None, logo_w=34, logo_h=34, height=1.6*inch):
        super().__init__()
        self.title = title
        self.subtitle = subtitle
        self.version = version
        self.bg = bg
        self._width = width
        self._height = height
        self.logo_path = logo_path or LOGO_PATH
        self.logo_w = logo_w
        self.logo_h = logo_h

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
        logo_clearance = (self.logo_w + 24) if os.path.exists(self.logo_path) else 0
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
        if os.path.exists(self.logo_path):
            try:
                c.drawImage(
                    self.logo_path,
                    self._width - self.logo_w - 18,
                    self._height - self.logo_h - 16,
                    width=self.logo_w,
                    height=self.logo_h,
                    mask="auto",
                    preserveAspectRatio=True,
                )
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
            ("Month 1", "Behavioral\nBaseline", TEAL_DEEP),
            ("Month 2", "Gap\nAnalysis", TEAL_BRIGHT),
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
            ("2", "NHID-Clinical v1.3", "Behavioral baseline — 5 controls, 18 CTS tests",       TEAL_DEEP),
            ("3", "NHID-Auth v2",       "Cryptographic agent identity — Ed25519, NPI binding",  TEAL_BRIGHT),
            ("4", "FHIR / OpenTelemetry","Healthcare-native audit + SIEM export",               colors.HexColor("#0E7490")),
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


def _wrap_text(text, font, size, max_w):
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if pdfmetrics.stringWidth(test, font, size) < max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


class CoverPage(Flowable):
    """Full-bleed navy cover shared by every document in the suite.

    Carries the complete family masthead: wordmark, audience badge, title,
    subtitle, version · date · CC BY 4.0 · NIST public-comment reference, and
    the open-proposal disclaimer. A soft teal/cyan halo (low-alpha concentric
    rings) echoes the website's glow without turning the page neon.
    """
    def __init__(self, title, subtitle, version, audience,
                 date="June 2026", logo_path=None):
        super().__init__()
        self.title = title
        self.subtitle = subtitle
        self.version = version
        self.audience = audience
        self.date = date
        self.logo_path = logo_path or LOGO_PATH
        self._width = 6.5 * inch
        self._height = 9.25 * inch   # fits the content frame; the navy is drawn full-bleed

    def wrap(self, availWidth, availHeight):
        return self._width, self._height

    def draw(self):
        c = self.canv
        W, H = c._pagesize
        ox, oy = -inch, -0.75 * inch           # page origin relative to flowable
        # ── full-bleed deep navy field ───────────────────────────────────────
        c.setFillColor(NAVY)
        c.rect(ox, oy, W, H, fill=1, stroke=0)
        # ── soft teal/cyan halo, top-right (simulated glow) ──────────────────
        cx, cy = ox + W - 1.1 * inch, oy + H - 1.1 * inch
        for r, col, a in [(3.2*inch, CYAN, 0.06), (2.3*inch, TEAL_BRIGHT, 0.08),
                          (1.5*inch, TEAL_BRIGHT, 0.10)]:
            c.setFillColor(col)
            c.setFillAlpha(a)
            c.circle(cx, cy, r, fill=1, stroke=0)
        c.setFillAlpha(1)
        # ── top accent bar (teal → cyan) ─────────────────────────────────────
        c.setFillColor(TEAL_BRIGHT)
        c.rect(ox, oy + H - 6, W * 0.62, 6, fill=1, stroke=0)
        c.setFillColor(CYAN)
        c.rect(ox + W * 0.62, oy + H - 6, W * 0.38, 6, fill=1, stroke=0)
        # ── wordmark ─────────────────────────────────────────────────────────
        left = ox + inch
        top = oy + H - 1.2 * inch
        if os.path.exists(self.logo_path):
            try:
                c.drawImage(self.logo_path, left, top - 6, width=30, height=30,
                            mask="auto", preserveAspectRatio=True)
            except Exception:
                pass
        c.setFillColor = c.setFillColor
        c.setFillColor(WHITE)
        c.setFont(FONT_DISPLAY, 17)
        c.drawString(left + 40, top + 2, "NHID-Clinical")
        # ── audience badge ───────────────────────────────────────────────────
        by = top - 0.75 * inch
        badge = self.audience.upper()
        bw = pdfmetrics.stringWidth(badge, FONT_SEMIBOLD, 8.5) + 20
        c.setFillColor(TEAL_BRIGHT)
        c.setFillAlpha(0.16)
        c.roundRect(left, by, bw, 20, 5, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFillColor(CYAN)
        c.setFont(FONT_SEMIBOLD, 8.5)
        c.drawString(left + 10, by + 6, badge)
        # ── title (Raleway extra-bold, wrapped) ──────────────────────────────
        ty = by - 0.55 * inch
        c.setFillColor(WHITE)
        title_lines = _wrap_text(self.title, FONT_DISPLAY_XB, 30, W - 2.2 * inch)
        for ln in title_lines:
            c.setFont(FONT_DISPLAY_XB, 30)
            c.drawString(left, ty, ln)
            ty -= 34
        # ── subtitle ─────────────────────────────────────────────────────────
        ty -= 6
        c.setFillColor(CREAM)
        for ln in _wrap_text(self.subtitle, FONT_REGULAR, 12, W - 2.4 * inch):
            c.setFont(FONT_REGULAR, 12)
            c.drawString(left, ty, ln)
            ty -= 17
        # ── meta line ────────────────────────────────────────────────────────
        ty -= 20
        c.setStrokeColor(TEAL_BRIGHT)
        c.setLineWidth(2)
        c.line(left, ty + 10, left + 1.2 * inch, ty + 10)
        ty -= 6
        c.setFillColor(MUTED)
        c.setFont(FONT_SEMIBOLD, 9.5)
        for ln in [
            f"Version {self.version}  ·  {self.date}  ·  CC BY 4.0",
            "Author: Brianna Baynard  ·  Independent, practitioner-led",
            "NIST Public Comment: NIST-2025-0035-0026",
        ]:
            c.drawString(left, ty, ln)
            ty -= 15
        # ── open-proposal disclaimer, anchored near the foot ─────────────────
        dy = oy + 1.0 * inch
        dw = W - 2 * inch
        c.setStrokeColor(AMBER)
        c.setLineWidth(1)
        c.setFillColor(colors.HexColor("#161f14"))
        disc_lines = _wrap_text(
            "NHID-Clinical is an early-stage open proposal by Brianna Baynard. It is a "
            "voluntary open proposal — not an accredited standard, not a certification "
            "program, and not a regulatory requirement. No HIPAA compliance, security "
            "guarantees, or liability protection are implied.",
            FONT_REGULAR, 8.5, dw - 24)
        box_h = 22 + len(disc_lines) * 12 + 8
        c.roundRect(left, dy, dw, box_h, 6, fill=1, stroke=1)
        c.setFillColor(AMBER)
        c.setFont(FONT_SEMIBOLD, 8)
        c.drawString(left + 12, dy + box_h - 15, "OPEN PROPOSAL — NOT A STANDARD OR REGULATORY REQUIREMENT")
        c.setFillColor(CREAM)
        c.setFont(FONT_REGULAR, 8.5)
        yy = dy + box_h - 29
        for ln in disc_lines:
            c.drawString(left + 12, yy, ln)
            yy -= 12


class ExecutiveSummary(Flowable):
    """Page-1 executive panel: What it is · Why it matters · Operational impact.

    A light bordered card with a teal spine — designed so a VP grasps the
    document in well under 90 seconds before any dense prose.
    """
    def __init__(self, rows, width=6.5 * inch):
        super().__init__()
        self.rows = rows          # list[(label, text)]
        self._width = width
        self._pad = 14
        self._label_w = 1.35 * inch
        self._text_w = width - self._pad * 2 - self._label_w - 10
        self._row_lines = [
            _wrap_text(t, FONT_REGULAR, 9, self._text_w) for _, t in rows
        ]
        h = 30  # header
        for lines in self._row_lines:
            h += max(len(lines) * 12, 14) + 8
        self._height = h + 8

    def wrap(self, availWidth, availHeight):
        return self._width, self._height

    def draw(self):
        c = self.canv
        H = self._height
        c.setFillColor(colors.HexColor("#f4faf9"))
        c.setStrokeColor(MGRAY)
        c.setLineWidth(0.75)
        c.roundRect(0, 0, self._width, H, 8, fill=1, stroke=1)
        c.setFillColor(TEAL_BRIGHT)
        c.roundRect(0, 0, 5, H, 2, fill=1, stroke=0)
        c.rect(3, 0, 2, H, fill=1, stroke=0)
        c.setFillColor(TEAL_DEEP)
        c.setFont(FONT_SEMIBOLD, 8.5)
        c.drawString(self._pad + 6, H - 18, "EXECUTIVE SUMMARY")
        y = H - 36
        for (label, _), lines in zip(self.rows, self._row_lines):
            c.setFillColor(INK)
            c.setFont(FONT_SEMIBOLD, 9)
            c.drawString(self._pad + 6, y, label)
            c.setFillColor(SLATE)
            c.setFont(FONT_REGULAR, 9)
            ty = y
            for ln in lines:
                c.drawString(self._pad + 6 + self._label_w, ty, ln)
                ty -= 12
            y -= max(len(lines) * 12, 14) + 8


def _key_metrics(width=6.5 * inch):
    """Canonical suite metric row: 5 Controls · 18 CTS Cases · 343 Tests · 6 Adapters."""
    return _stats_row([
        ("5", "Controls"),
        ("18", "CTS Cases"),
        ("343", "Tests"),
        ("6", "Adapters"),
    ])


def _cover(story, title, subtitle, version, audience, logo_path=None):
    """Append a full cover page + page break — the shared suite masthead."""
    story.append(CoverPage(title, subtitle, version, audience, logo_path=logo_path))
    story.append(PageBreak())


def _styles():
    s = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", fontName=FONT_DISPLAY, fontSize=15, textColor=INK, spaceAfter=4)
    h2 = ParagraphStyle("H2", fontName=FONT_DISPLAY, fontSize=11.5, textColor=TEAL_DEEP, spaceAfter=4, spaceBefore=10)
    body = ParagraphStyle("Body", fontName=FONT_REGULAR, fontSize=9, textColor=SLATE, leading=14, spaceAfter=4)
    small = ParagraphStyle("Small", fontName=FONT_REGULAR, fontSize=8, textColor=DGRAY, leading=12)
    disc = ParagraphStyle("Disclaimer", fontName=FONT_ITALIC, fontSize=7.5,
                          textColor=DGRAY, leading=11, borderColor=AMBER, borderWidth=0.5,
                          borderPadding=6, backColor=colors.HexColor("#fffbf0"))
    return h1, h2, body, small, disc


def _svg_path(filename):
    return os.path.join(SVG_3D_DIR, filename)


def _svg_visual(filename, width=6.5 * inch, caption=None):
    path = _svg_path(filename)
    if svg2rlg and os.path.exists(path):
        return ScaledSvgVisual(path, width=width, caption=caption)
    return Spacer(1, 0.05 * inch)


def _append_meta_block(story, lines):
    meta = ParagraphStyle(
        "Meta", fontName=FONT_REGULAR, fontSize=8.5, textColor=DGRAY, leading=12, spaceAfter=2
    )
    for line in lines:
        story.append(Paragraph(line, meta))
    story.append(Spacer(1, 0.08 * inch))


def _section(story, title, H1):
    story.append(Paragraph(title, H1))
    story.append(SectionRule())
    story.append(Spacer(1, 0.06 * inch))


def _premium_table(data, col_widths, highlight_col=None):
    t = Table(data, colWidths=col_widths)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fbfd"), WHITE]),
        ("GRID", (0, 0), (-1, -1), 0.25, MGRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if highlight_col is not None:
        style += [
            ("TEXTCOLOR", (highlight_col, 1), (highlight_col, -1), GREEN),
            ("FONTNAME", (highlight_col, 1), (highlight_col, -1), FONT_BOLD),
        ]
    t.setStyle(TableStyle(style))
    return t


def _stats_row(stats):
    stat_cells = []
    for val, lbl in stats:
        stat_cells.append(Paragraph(
            f'<font size="22" color="#14B8A6"><b>{val}</b></font><br/>'
            f'<font size="8" color="#64748B">{lbl}</font>',
            ParagraphStyle("SC", alignment=TA_CENTER, leading=16)
        ))
    t = Table([stat_cells], colWidths=[1.6 * inch] * len(stats))
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, TEAL),
        ("LINEAFTER", (0, 0), (-2, 0), 0.5, MGRAY),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fbfd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return t


def _open_proposal_disclaimer():
    return (
        "NHID-Clinical is an early-stage open proposal by Brianna Baynard. "
        "It is not an accredited standard, not a certification program, and not a regulatory requirement. "
        "No HIPAA compliance, security guarantees, or liability protection are implied."
    )


def _footer_canvas(canvas, doc):
    canvas.saveState()
    # thin teal rule above the footer for a consistent running-foot
    canvas.setStrokeColor(MGRAY)
    canvas.setLineWidth(0.5)
    canvas.line(inch, 0.62 * inch, 7.5 * inch, 0.62 * inch)
    canvas.setFillColor(DGRAY)
    canvas.setFont(FONT_REGULAR, 7.5)
    canvas.drawString(inch, 0.46 * inch,
        "NHID-Clinical  ·  nhid-clinical.org  ·  CC BY 4.0  ·  Brianna Baynard  ·  NIST-2025-0035-0026")
    canvas.drawRightString(7.5 * inch, 0.46 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _cover_footer(canvas, doc):
    """First page is a full-bleed cover — suppress the running footer there."""
    return


# ── Document 1: Shadow Evaluation Guide ──────────────────────────────────────

def make_shadow_guide():
    path = os.path.join(OUT_DIR, "NHID-Clinical-Shadow-Evaluation-Guide.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    H1, H2, BODY, SMALL, DISC = _styles()
    story = []

    _cover(
        story,
        "Shadow Evaluation Guide",
        "NHID-Clinical v1.3  ·  90-Day Behavioral Baseline for AI Voice Agents",
        "1.3",
        "Payer Operations",
    )

    # Program-specific disclaimer (in addition to the cover's open-proposal notice)
    story.append(Paragraph(
        "⚠  NHID-Clinical is an early-stage open proposal by Brianna Baynard. "
        "It is not an accredited standard or regulatory requirement. No payer has piloted "
        "or adopted it yet — you would be among the first.",
        DISC
    ))
    story.append(Spacer(1, 0.15*inch))

    # What this is — 4 colored info boxes
    _section(story, "What This Is", H1)
    info_cards = [
        ("No Cost",        TEAL_DEEP,   "No vendor changes. No production risk. Observe-only alongside your current call flow."),
        ("Shadow Mode",    TEAL_BRIGHT, "Your existing call handling is unchanged. Measure how today's AI voice traffic behaves."),
        ("No Commitment",  GREEN,       "No certification, no SLA. Share anonymized findings with the community if you choose."),
        ("Clear Goal",     SLATE,       "Produce a written behavioral baseline showing AI agent disclosure, escalation, and logging."),
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
         "AI agent must disclose it is automated before any PHI or data exchange.", C_IDG),
        ("DBC-01", "Deceptive Behavior Check",
         "No synthetic voice artifacts designed to impersonate a human. No fake breathing.", C_DBC),
        ("EIT-01", "Escalation Implementation Test",
         "Immediate, clean escalation to a human on request — no delay, no re-prompt.", C_EIT),
        ("ATR-01", "Audit Trail",
         "Basic log reconstructing when disclosure occurred and what data was exchanged.", C_ATR),
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

    doc.build(story, onFirstPage=_cover_footer, onLaterPages=_footer_canvas)
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
    spec_logo = LOGO_LIGHT_PATH if os.path.exists(LOGO_LIGHT_PATH) else LOGO_PATH

    _cover(
        story,
        "NHID-Clinical v1.3 Core Specification",
        "Behavioral Baseline for AI Voice Agents in B2B Healthcare Payer–Provider Calls",
        "1.3",
        "Technical Reference",
        logo_path=spec_logo,
    )
    story.append(_svg_visual(
        "nexus.svg",
        caption="Governance Trust Nexus — illustrative bridge between payer and provider voice workflows",
    ))
    story.append(Spacer(1, 0.1 * inch))

    _section(story, "Overview", H1)
    story.append(Paragraph(
        "NHID-Clinical v1.3 defines four deterministic behavioral controls for AI voice agents "
        "in B2B healthcare administrative calls. The conformance test suite (CTS) and pytest harness "
        "produce identical pass/fail output for the same input — no ambiguity, no interpretation.",
        BODY
    ))
    story.append(Paragraph(
        "NHID-Clinical standardizes <b>observable disclosure and trace behaviors</b> only. "
        "It does not verify caller identity or certify vendors.",
        SMALL
    ))
    story.append(Spacer(1, 0.08 * inch))
    story.append(_stats_row([
        ("5", "Controls"),
        ("18", "CTS Cases"),
        ("343", "Unit Tests"),
        ("6", "Adapters"),
    ]))
    story.append(Spacer(1, 0.12 * inch))

    _section(story, "The Four Controls", H1)
    story.append(Paragraph(
        "Each control maps to RFC 2119 keywords in the full specification. "
        "Illustrated cards below summarize the v1.3 behavioral gates.",
        SMALL
    ))
    story.append(Spacer(1, 0.06 * inch))

    controls = [
        ("IDG-01", "Identity Disclosure Gate",
         "Agent MUST identify itself as automated before any PHI exchange. "
         "Disclosure in the first substantive utterance.", C_IDG),
        ("PDX-01", "Pre-Data Exchange Gate",
         "No PHI (member ID, NPI, DOB, claim number) until IDG-01 disclosure is confirmed.", C_PDX),
        ("DBC-01", "Deceptive Behavior Check",
         "No claim of human identity; no deceptive artifacts designed to imply human presence.", C_DBC),
        ("EIT-01", "Escalation Implementation Test",
         "Human escalation path communicated; transfer executes immediately on request.", C_EIT),
    ]
    for i in range(0, len(controls), 2):
        row_cards = [ControlCard(*c) for c in controls[i:i + 2]]
        if len(row_cards) == 2:
            t2 = Table([[row_cards[0], row_cards[1]]], colWidths=[3.2 * inch, 3.2 * inch])
            t2.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t2)
        else:
            story.append(row_cards[0])
        story.append(Spacer(1, 0.08 * inch))

    story.append(ColorBlock(
        "ATR-01  ·  Audit Trail (supplemental)",
        "Machine-readable JSON event trace for every call: disclosure timestamps, state transitions, "
        "escalation events, and execution context. Maps to HL7 FHIR R4 AuditEvent (base v4.0.1) — "
        "no named Implementation Guide conformance (e.g. IHE BALP) is claimed.",
        GREEN, width=6.5 * inch, height=0.95 * inch
    ))
    story.append(Spacer(1, 0.12 * inch))

    _section(story, "Conformance Test Suite — 18 Cases", H1)
    story.append(Paragraph(
        "tests/nhid_conformance_test_suite_v1.yaml — representative cases shown; full suite in repository.",
        SMALL
    ))
    story.append(Spacer(1, 0.04 * inch))
    story.append(_premium_table([
        ["Test ID", "What It Verifies", "Severity"],
        ["CTS-IDG-01", "Disclosure present before any data exchange", "critical"],
        ["CTS-PDX-01", "No PHI before disclosure + consent", "critical"],
        ["CTS-DBC-01", "No deceptive audio artifacts in transcript", "critical"],
        ["CTS-EIT-01", "Escalation path declared and accessible", "critical"],
        ["CTS-ATR-01", "Audit log fields present and well-formed", "critical"],
    ], [1.5 * inch, 3.5 * inch, 1.3 * inch]))
    story.append(Spacer(1, 0.12 * inch))

    _section(story, "Live Conformance API", H1)
    story.append(Paragraph(
        "Reference implementation on AWS Lambda. Demo routes require no API key; production check uses x-api-key.",
        BODY
    ))
    story.append(APITable())
    story.append(Spacer(1, 0.08 * inch))
    story.append(ColorBlock(
        "Base URL",
        "https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod",
        SLATE, width=6.5 * inch, height=0.55 * inch
    ))
    story.append(Spacer(1, 0.12 * inch))

    _section(story, "NHID-Auth v2 — Cryptographic Agent Identity", H1)
    story.append(Paragraph(
        "Separate reference layer for when behavioral controls alone are insufficient. "
        "Public reference code — not deployed trust infrastructure.",
        SMALL
    ))
    story.append(Spacer(1, 0.06 * inch))
    story.append(ColorBlock(
        "Released June 2026  ·  CC BY 4.0",
        "Ed25519 provider-signed agent passports with NPI binding. Scoped delegation chains "
        "(max 3 hops). Per-agent and per-delegation revocation. Call-SID nonce binding. "
        "Reference: src/agent_identity.py (26 dedicated tests).",
        TEAL, width=6.5 * inch, height=0.9 * inch
    ))

    doc.build(story, onFirstPage=_cover_footer, onLaterPages=_footer_canvas)
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
    spec_logo = LOGO_LIGHT_PATH if os.path.exists(LOGO_LIGHT_PATH) else LOGO_PATH

    _cover(
        story,
        "Operational Blueprint",
        "NHID-Clinical v1.3  ·  From RFP Language to Audit-Ready Production",
        "1.3",
        "Payer & Procurement Reference",
        logo_path=spec_logo,
    )
    story.append(ExecutiveSummary([
        ("What it is",
         "A payer- and procurement-facing blueprint for turning NHID-Clinical's voluntary "
         "transparency controls into RFP language and audit-ready vendor accountability."),
        ("How a payer uses it",
         "Add one standard conformance clause to a voice-AI vendor RFP or BAA amendment, have the "
         "vendor run the open test suite, validate the JSON traces yourself, then measure and decide."),
        ("Operational impact",
         "Machine-auditable proof of how each voice agent handles identity disclosure — no custom "
         "contract language, no internal validation tooling, and no production risk."),
    ]))
    story.append(Spacer(1, 0.12 * inch))
    story.append(_key_metrics())
    story.append(Spacer(1, 0.14 * inch))
    story.append(_svg_visual(
        "trust-stack.svg",
        caption="Five-layer trust stack — network foundation through observability",
    ))
    story.append(Spacer(1, 0.1 * inch))

    _section(story, "The Impersonation Latency Problem", H1)
    story.append(Paragraph(
        "When an AI agent calls a payer prior-auth or benefits line, the receiving party often "
        "lacks reliable disclosure about whether the caller is human or automated — causing "
        "repeated clarifications, transfers, and manual fallback routing.",
        BODY
    ))
    story.append(Spacer(1, 0.08 * inch))
    story.append(_svg_visual(
        "latency-split.svg",
        caption="Impersonation latency — time operating without non-human identity disclosure",
    ))
    story.append(Spacer(1, 0.08 * inch))
    story.append(ColorBlock(
        "Impersonation Latency (canonical term)",
        "Duration an AI agent operates and exchanges PHI without disclosing its non-human identity. "
        "NHID-Clinical median observation: 3 turns before first disclosure attempt. "
        "This proposal reduces that latency through standardized, auditable behavioral gates.",
        SLATE, width=6.5 * inch, height=0.95 * inch
    ))
    story.append(Spacer(1, 0.12 * inch))

    _section(story, "Five-Layer Trust Stack", H1)
    story.append(Paragraph(
        "NHID-Clinical v1.3 occupies Layer 2 (behavioral baseline). "
        "Layers 3–4 add cryptographic identity and healthcare-native audit export.",
        BODY
    ))
    story.append(LayerStack())
    story.append(Spacer(1, 0.12 * inch))

    _section(story, "Implementation Phases", H1)
    story.append(Paragraph(
        "A 12-week path from RFP language to measurable vendor accountability — no production risk.",
        SMALL
    ))
    story.append(Spacer(1, 0.06 * inch))
    story.append(TimelineBar())
    story.append(Spacer(1, 0.1 * inch))
    phases = [
        ("Phase 1  ·  Weeks 1–2", BLUE, "Add RFP Language",
         "Insert the standard NHID-Clinical conformance clause into your next voice AI vendor "
         "RFP or BAA amendment. One clause covers all four controls."),
        ("Phase 2  ·  Weeks 3–6", TEAL, "Vendor Sandbox Testing",
         "Ask your vendor to run: git clone + pip install -r requirements.txt + "
         "python -m pytest tests/ -v. Results in under 5 minutes. Request full terminal output."),
        ("Phase 3  ·  Weeks 7–10", GREEN, "Validate Logs Yourself",
         "Place vendor JSON traces in traces/. Run the test suite. "
         "Verify: disclosure before NPI, no deceptive artifacts, escalation ≤2s."),
        ("Phase 4  ·  Weeks 11–12", SLATE, "Measure & Decide",
         "Compare verification latency (target &lt;5s) and escalation volume. "
         "Use findings to update vendor contract requirements."),
    ]
    for title, col, subtitle, body_txt in phases:
        story.append(ColorBlock(
            f"{title}  —  {subtitle}",
            body_txt, col, width=6.5 * inch, height=0.85 * inch
        ))
        story.append(Spacer(1, 0.05 * inch))

    story.append(PageBreak())

    _section(story, "Standard RFP / BAA Clause", H1)
    story.append(Paragraph(
        "Copy-ready language for procurement. Voluntary transparency preference — not a certification hurdle.",
        SMALL
    ))
    story.append(Spacer(1, 0.08 * inch))
    clause_style = ParagraphStyle(
        "Clause", fontName="Courier", fontSize=8.5, leading=13,
        backColor=colors.HexColor("#f0f4ff"),
        borderColor=BLUE, borderWidth=0.75, borderPadding=12,
        textColor=NAVY
    )
    story.append(Paragraph(
        '"The vendor\'s AI agent SHALL produce NHID-Clinical v1.3 JSON trace logs for all '
        'B2B administrative calls, including disclosure timestamps and opt-out handling. '
        'The payer may run the open-source conformance test suite against vendor output at any time."',
        clause_style
    ))
    story.append(Spacer(1, 0.12 * inch))

    _section(story, "Target Metrics", H1)
    story.append(_premium_table([
        ["Metric", "Today (typical)", "Target with NHID-Clinical"],
        ["Verification latency", "3–5 min or call terminated", "< 5 seconds"],
        ["Audit effort per vendor", "Manual call review (hours)", "~2 minutes (test suite)"],
        ["RFP disclosure language", "Custom per vendor", "One standard clause"],
        ["Escalation response time", "Untracked", "≤ 2 seconds, logged"],
    ], [2.0 * inch, 2.1 * inch, 2.2 * inch], highlight_col=2))
    story.append(Spacer(1, 0.12 * inch))

    _section(story, "Regulatory Alignment", H1)
    story.append(Paragraph(
        "Illustrative mapping — not a claim of regulatory compliance or certification.",
        SMALL
    ))
    story.append(Spacer(1, 0.04 * inch))
    story.append(_premium_table([
        ["Regulatory Driver", "Specific Requirement", "NHID-Clinical Control"],
        ["CMS-0057-F", "FHIR API, 72hr turnaround, 5yr log", "FHIR AuditEvent + ATR-01"],
        ["MACPAC May 2026", "AI transparency, human review", "EIT-01 + ATR-01"],
        ["DOJ FCA 2026", "Explainability + audit trail", "LOG + CTS evidence"],
        ["State AI Laws", "Inspectable, auditable decisions", "IDG-01 + DBC-01"],
        ["NIST AI RMF / CAISI", "Cross-org agent identity", "NHID-Auth v2"],
    ], [1.7 * inch, 2.5 * inch, 2.1 * inch]))

    doc.build(story, onFirstPage=_cover_footer, onLaterPages=_footer_canvas)
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

    _cover(
        story,
        "v2 Technical Playbook",
        "NHID-Clinical  ·  Tech Stack, Adoption Tiers & Governance Framework Reference",
        "2.0",
        "Engineering Reference",
    )

    story.append(Paragraph(
        "⚠  NHID-Clinical is an early-stage open proposal by Brianna Baynard. "
        "It is not an accredited standard or regulatory requirement. This playbook is a "
        "condensed technical reference distilled from the project's internal knowledge archive.",
        DISC
    ))
    story.append(Spacer(1, 0.15*inch))

    # Core Objectives
    _section(story, "Core Objectives", H1)
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
        "https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod",
        SLATE, width=6.5*inch, height=0.55*inch
    ))

    doc.build(story, onFirstPage=_cover_footer, onLaterPages=_footer_canvas)
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

    _cover(
        story,
        "Knowledge Archive",
        "NHID-Clinical  ·  Public Reference Edition — Vision, Governance & Regulatory Alignment",
        "1.3",
        "Policy & Governance Reference",
    )

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
         "AI agent must disclose it is automated before any PHI request or exchange.", C_IDG),
        ("PDX-01", "Pre-Data Exchange Gate",
         "No PHI may be exchanged until IDG-01 disclosure is confirmed.", C_PDX),
        ("DBC-01", "Deceptive Behavior Check",
         "No synthetic voice artifacts or text claims implying human presence.", C_DBC),
        ("EIT-01", "Escalation Implementation Test",
         "Human escalation path must be available and honored immediately on request.", C_EIT),
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
    story.append(Spacer(1, 0.14*inch))
    _mindmap = os.path.join(ASSETS_DIR, "diagrams", "framework-mindmap.svg")
    if svg2rlg and os.path.exists(_mindmap):
        story.append(ScaledSvgVisual(
            _mindmap, width=6.5 * inch,
            caption="Framework map — core model, five controls, and trust-stack relationships",
        ))
    story.append(Spacer(1, 0.12*inch))

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
        ["NIST AI RMF / CAISI", "Cross-org agent identity",      "NHID-Auth v2"],
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

    doc.build(story, onFirstPage=_cover_footer, onLaterPages=_footer_canvas)
    print(f"  ✓  {path}")
    return path


# ── Document 6: v1.3 Public Overview (operational brief) ─────────────────────

def make_v13_overview():
    """Public operational reference model — payer-facing brief aligned with
    docs/MASTER-KNOWLEDGE-ARCHIVE.md."""
    path = os.path.join(OUT_DIR, "NHID-Clinical-v1.3-Overview.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    H1, H2, BODY, SMALL, DISC = _styles()
    overview_logo = LOGO_LIGHT_PATH if os.path.exists(LOGO_LIGHT_PATH) else LOGO_PATH
    story = []

    _cover(
        story,
        "Public Operational Reference Model",
        "A Voluntary Open Proposal for Agent Identity in Payer–Provider Voice Calls",
        "1.3",
        "Executive / Payer Brief",
        logo_path=overview_logo,
    )

    # ── Page 1: executive summary → key metrics → latency visual → behaviors ──
    story.append(ExecutiveSummary([
        ("What it is",
         "A voluntary, open operational reference model for how AI voice agents disclose their "
         "non-human identity in B2B healthcare payer–provider calls."),
        ("Why it matters",
         "An AI agent can begin interacting and requesting sensitive information before the "
         "receiving party can verify it is a non-human system authorized to act for the claimed "
         "organization."),
        ("Operational impact",
         "Standardized, auditable disclosure gates reduce impersonation latency, repeat calls, and "
         "manual fallback routing — with no production risk to evaluate."),
    ]))
    story.append(Spacer(1, 0.12 * inch))
    story.append(_key_metrics())
    story.append(Spacer(1, 0.14 * inch))

    story.append(_svg_visual(
        "latency-split.svg",
        caption="Impersonation latency — time an AI agent operates without disclosing its non-human identity",
    ))
    story.append(Spacer(1, 0.14 * inch))

    _section(story, "Proposed Core Behaviors (v1.3)", H1)
    behaviors = [
        ("IDG-01 — Early disclosure",
         "The agent states its non-human identity at the beginning of the interaction, before "
         "any substantive workflow execution or PHI request."),
        ("PDX-01 — Pre-data exchange gate",
         "No protected health information (member ID, NPI, DOB, claim number, etc.) may be "
         "exchanged until IDG-01 disclosure is confirmed."),
        ("DBC-01 — No deception",
         "The agent never claims to be human and does not use deceptive artifacts designed to "
         "imply human presence."),
        ("EIT-01 — Human escalation",
         "A human escalation path is communicated and honored immediately when the receiving "
         "party requests a person."),
        ("ATR-01 — Audit trace (supplemental)",
         "Every call produces a machine-readable JSON event trace with disclosure timestamps, "
         "state transitions, and execution context — deterministic under identical input conditions."),
    ]
    for title, body_txt in behaviors:
        story.append(Paragraph(f"<b>{title}.</b> {body_txt}", BODY))

    story.append(PageBreak())

    # ── Detailed explanation (moved after the at-a-glance page 1) ─────────────
    _section(story, "Public Brief: The Impersonation Latency", H1)
    story.append(Paragraph(
        "NHID-Clinical targets one specific failure: an AI agent can begin interacting and "
        "requesting sensitive information before the receiving party can verify that the caller "
        "is a non-human system and that it is authorized to act for the claimed organization.",
        BODY
    ))
    story.append(Paragraph(
        "This uncertainty causes repeated clarifications, call transfers, manual fallback routing, "
        "and often 10+ repeat calls for a single routine task. In observed payer operations, "
        "agents frequently request member IDs, NPIs, or dates of birth within the first 15 seconds "
        "with no prior statement that the caller is automated. Current telephony and IAM layers "
        "authenticate numbers or accounts, but do not provide portable proof that a specific AI "
        "caller is authorized to represent a particular provider organization.",
        BODY
    ))
    story.append(ColorBlock(
        "Impersonation Latency",
        "The duration of time an AI agent operates and exchanges PHI without disclosing its "
        "non-human identity. NHID-Clinical median observation: 3 turns before first disclosure "
        "attempt. This term is permanent and must never be renamed.",
        SLATE, width=6.5 * inch, height=0.95 * inch
    ))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(
        "<b>Focus area:</b> This proposal provides a standardized, voluntary blueprint to establish "
        "clear expectations around identity disclosure at the initiation of machine-to-human "
        "B2B voice interactions in healthcare administrative workflows. It does not address model "
        "fairness, clinical safety, or output quality — those remain separate governance "
        "responsibilities.",
        BODY
    ))
    story.append(Paragraph(
        "<b>Evidence status:</b> the governance gap is well documented and prototype feasibility is "
        "demonstrated, but large-scale production evidence is still limited. The recommended next "
        "step for most organizations is a focused shadow pilot on their own call traffic "
        "(see docs/pilot-kit in the repository).",
        BODY
    ))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("An Important Distinction", H1))
    story.append(Paragraph(
        "NHID-Clinical does not verify caller identity or agent authenticity. It standardizes "
        "<b>observable disclosure and trace behaviors</b> only. These behaviors are documented with "
        "RFC 2119 keywords (MUST, SHOULD, MAY) in the full v1.3 specification, but they are not "
        "legally binding — purely a voluntary public operational reference model.",
        BODY
    ))
    story.append(Paragraph(
        "Cryptographic authorization (NHID-Auth v2 — Ed25519 agent passports, NPI-bound delegation) "
        "is documented as a separate reference layer for when behavioral controls alone are "
        "insufficient. It is public reference code, not a deployed trust infrastructure.",
        SMALL
    ))

    story.append(PageBreak())

    # ── Page 2: Resources + payer value ──────────────────────────────────────
    story.append(Paragraph("Available Resources & Tooling", H1))
    story.append(Paragraph(
        "The following resources are available on <b>nhid-clinical.org</b> and in the public "
        "GitHub repository to support evaluation and voluntary adoption:",
        BODY
    ))
    resources = [
        "A working JSON event schema for call traces (nhid_trace_schema_v1.json).",
        "A deterministic policy engine that produces stable trace output under identical input "
        "conditions (modulo timestamps and non-deterministic IDs).",
        "An 18-case conformance test suite (CTS) in machine-readable YAML plus a pytest failure "
        "injection harness (343 passing unit tests in the reference implementation).",
        "10 canonical trace files in traces/ demonstrating real-world scenarios (eligibility, "
        "prior auth, claims status, bot-to-bot, audit gaps, and more).",
        "Six vendor adapters (VAPI, Twilio, Vonage, Retell, Amazon Connect, call-progress) "
        "accepting native call payloads and returning pass/fail conformance results.",
        "A live public conformance API — demo routes require no API key.",
        "Governance Simulator, Shadow Evaluation Guide, and Evidence Pack for payer operations teams.",
    ]
    for item in resources:
        story.append(Paragraph(f"•  {item}", BODY))

    story.append(Spacer(1, 0.1 * inch))
    story.append(ColorBlock(
        "Note on Scope",
        "There are no certification claims, no HIPAA compliance claims, and no regulatory authority "
        "claims associated with this reference model. CAS (Call Authorization Score) is a "
        "measurement, not a certification seal.",
        AMBER, width=6.5 * inch, height=0.8 * inch
    ))
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("The Payer Value Proposition", H1))
    story.append(Paragraph(
        "A regional payer that encourages its provider-facing vendors to adopt NHID-Clinical gains "
        "machine-auditable proof of how each voice agent handles identity disclosure — without "
        "writing custom contract language or building internal validation tooling from scratch.",
        BODY
    ))
    value_props = [
        "<b>Reduces audit friction:</b> Trace logs can be reviewed by your compliance team or "
        "fed into anomaly detection baselines.",
        "<b>Enables vendor transparency:</b> Require NHID-Clinical conformance as a lightweight "
        "RFP clause, not a heavy, expensive certification.",
        "<b>Supports asset inventorying:</b> Operations and security teams can treat NHID-Clinical "
        "traces as an observable signal alongside API keys and service accounts.",
        "<b>Zero production pilots to date:</b> NHID-Clinical is seeking its first shadow "
        "evaluation partners — you would be among the first.",
    ]
    for item in value_props:
        story.append(Paragraph(f"•  {item}", BODY))

    story.append(PageBreak())

    # ── Page 3: Tactical guidance + disclaimers ────────────────────────────
    story.append(Paragraph("Tactical Guidance for Payers", H1))
    story.append(Paragraph(
        "To leverage this proposal, payers can take the following immediate steps:",
        BODY
    ))
    steps = [
        "Read this operational brief and the Shadow Evaluation Guide (90-day observe-only methodology).",
        "Ask your voice AI vendors (prior auth automation, benefits verification tools) whether "
        "they can produce NHID-Clinical-compatible traces in a sandbox.",
        "Run the conformance test suite against their output — the test harness is ready on the "
        "Developers page and in the public repository.",
        "Optionally add voluntary conformance to your vendor onboarding checklist — not as a "
        "pass/fail hurdle, but as a transparency preference.",
    ]
    for i, step in enumerate(steps, 1):
        story.append(Paragraph(f"{i}. {step}", BODY))

    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(
        "You do not need to become a certification body, and you do not need intensive legal "
        "sign-off. This is a practical coordination tool, not a compliance mandate.",
        BODY
    ))
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Governance & Disclaimers", H1))
    disclaimers = [
        "This is not an official standard (neither ANSI, ISO, nor HL7).",
        "It is not a certification — no one is certified, and no seal is offered.",
        "It is strictly voluntary — there is no legal obligation or regulatory authority.",
        "It does not provide inherent HIPAA compliance, security guarantees, or liability protection.",
        "FHIR R4 AuditEvent mapping validates against the base spec (v4.0.1) only — no named "
        "Implementation Guide conformance (e.g., IHE BALP) is claimed.",
    ]
    for item in disclaimers:
        story.append(Paragraph(f"•  {item}", BODY))

    story.append(Spacer(1, 0.12 * inch))
    story.append(ColorBlock(
        "Access & Feedback",
        "Full technical artifacts: nhid-clinical.org/developers  ·  "
        "Specification: nhid-clinical.org/specification.html  ·  "
        "GitHub: github.com/NHID-Clinical/NHID-Clinical  ·  "
        "Feedback: GitHub Issues or contact@nhid-clinical.org",
        BLUE, width=6.5 * inch, height=0.85 * inch
    ))

    doc.build(story, onFirstPage=_cover_footer, onLaterPages=_footer_canvas)
    print(f"  ✓  {path}")
    return path


# ── Document 7: Evidence Pack ────────────────────────────────────────────────

def make_evidence_pack():
    """Procurement/security-facing evidence summary — mirrors evidence-pack.html.
    Deterministic guarantees, real-corpus detection evidence, a sample failure
    trace, and the audit-readiness model. Content faithful to the website page."""
    path = os.path.join(OUT_DIR, "NHID-Clinical-Evidence-Pack.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    H1, H2, BODY, SMALL, DISC = _styles()
    story = []
    spec_logo = LOGO_LIGHT_PATH if os.path.exists(LOGO_LIGHT_PATH) else LOGO_PATH

    _cover(
        story,
        "Evidence Pack",
        "NHID-Clinical v1.3  ·  Deterministic Guarantees, Detection Evidence & Audit Model",
        "1.3",
        "Procurement & Security Reference",
        logo_path=spec_logo,
    )

    story.append(ExecutiveSummary([
        ("What it is",
         "A summary of the deterministic guarantees, real-corpus detection evidence, a sample "
         "failure trace, and the audit-readiness model behind the reference implementation."),
        ("Why it matters",
         "Teams evaluating adoption need to see what the system guarantees, how it behaves against "
         "real conversational phrasing, and what an auditor could reconstruct from the event store."),
        ("Operational impact",
         "Everything here is self-attested and open for community review. NHID-Clinical does not "
         "issue certifications, conduct audits, or validate vendor implementations."),
    ]))
    story.append(Spacer(1, 0.12 * inch))
    story.append(_key_metrics())
    story.append(Spacer(1, 0.14 * inch))

    _section(story, "1 · System Behavior Guarantees", H1)
    guarantees = [
        ("Deterministic output",
         "Identical input event + identical policy version produce identical trace output. "
         "The policy engine is a pure function with no side effects."),
        ("Replay guarantee",
         "Any stored trace can be replayed. Policy version is embedded in each event header; "
         "version mismatches are flagged."),
        ("Failure invariants",
         "The engine never raises an unhandled exception. Malformed input returns a deterministic "
         "error trace; the caller always gets a response."),
        ("Idempotency",
         "Submitting the same request_id twice produces the same result — no duplicate state "
         "transitions and no double-counted events."),
    ]
    for i in range(0, len(guarantees), 2):
        row = [ColorBlock(t, b, C_EIT if j == 0 else TEAL_DEEP, width=3.16 * inch, height=1.15 * inch)
               for j, (t, b) in enumerate(guarantees[i:i + 2])]
        tbl = Table([row], colWidths=[3.24 * inch, 3.24 * inch])
        tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                 ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        story.append(tbl)
        story.append(Spacer(1, 0.08 * inch))

    _section(story, "2 · Real-Corpus Detection Rates", H1)
    story.append(Paragraph(
        "The CTS YAML suite validates the policy engine against synthetic, hand-authored cases. "
        "To check behavior against real conversational phrasing, the engine was also run against "
        "the Fabricate Battle-Test Corpus — 550 real-world voice AI conversations (4,839 turns). "
        "Detection rate is the share of corpus turns where a control correctly fired. These are "
        "reported honestly, including where coverage is weak.",
        SMALL
    ))
    story.append(Spacer(1, 0.06 * inch))
    story.append(_premium_table([
        ["Control", "Detection Rate", "Notes"],
        ["IDG-01 (Identity Disclosure)", "100%", "Holds against real phrasing"],
        ["EIT-01 (Escalation Trigger)", "94.7%", "Holds against real phrasing"],
        ["PDX-01 (PHI Data Exchange)", "58.6%", "Partial — real-world phrasing diverges from synthetic cases"],
        ["DBC-01 (Deceptive Behavior Claim)", "2.5%", "Weak — heuristic phrase list does not yet cover most real phrasing"],
        ["ATR-01 (supplemental)", "0.0%", "Corpus/adapter structural limitation — not a representative test"],
    ], [2.1 * inch, 1.2 * inch, 3.2 * inch]))
    story.append(Spacer(1, 0.12 * inch))

    _section(story, "3 · Anonymized Failure Trace Example", H1)
    story.append(Paragraph(
        "The example below is synthetic — constructed from observed behavior patterns, with all "
        "identifying information removed. No real PHI, no real provider data.",
        SMALL
    ))
    story.append(Spacer(1, 0.05 * inch))
    code_style = ParagraphStyle(
        "Code", fontName=FONT_MONO, fontSize=7.6, leading=11.5,
        textColor=CREAM, backColor=NAVY, borderColor=TEAL_DEEP,
        borderWidth=0.75, borderPadding=10, spaceAfter=6
    )
    story.append(Preformatted(
        'correlation_id: "auth-2026-05-26-001"   ·   policy: nhid-clinical-v1.3\n\n'
        't=00:00.000  INGEST     POST /voice/process received\n'
        't=00:00.123  VALIDATE   SpeechResult normalized\n'
        't=00:00.131  STATE      Session reconstructed: turn_count=0, disclosure=null\n'
        't=00:00.140  POLICY     IDG-01: DISCLOSE_IDENTITY triggered (turn_count=0)\n'
        't=00:00.145  EXEC       TwiML disclosure message rendered\n'
        't=00:00.152  PERSIST    Event written — disclosure_timestamp set',
        code_style
    ))
    story.append(Spacer(1, 0.12 * inch))

    _section(story, "4 · Audit Readiness Model", H1)
    story.append(Paragraph(
        "An external auditor reconstructing a session from the event store can determine:",
        BODY
    ))
    for pt in [
        "When the call started and when the first disclosure statement was made.",
        "Whether disclosure preceded any PHI or credential exchange.",
        "Whether opt-out or escalation was requested and how it was handled.",
        "Which policy engine version processed each event.",
        "Whether any partial failures or boundary violations were recorded.",
    ]:
        story.append(Paragraph(f"•  {pt}", BODY))
    story.append(Spacer(1, 0.1 * inch))
    story.append(ColorBlock(
        "Scope of this evidence",
        "This describes the reference implementation's technical properties. NHID-Clinical does "
        "not issue certifications, conduct audits, or validate vendor implementations. Everything "
        "here is self-attested and open for community review.",
        SLATE, width=6.5 * inch, height=0.8 * inch
    ))

    doc.build(story, onFirstPage=_cover_footer, onLaterPages=_footer_canvas)
    print(f"  ✓  {path}")
    return path


if __name__ == "__main__":
    print("Generating PDFs...")
    make_shadow_guide()
    make_core_spec()
    make_operational_blueprint()
    make_technical_playbook()
    make_knowledge_archive()
    make_v13_overview()
    make_evidence_pack()
    print("Done.")
