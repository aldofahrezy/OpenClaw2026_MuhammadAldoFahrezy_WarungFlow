"""Generate OpenClaw2026_MuhammadAldoFahrezy_WarungFlow.pdf.

Five-slide pitch deck for OpenClaw Agenthon 2026 (Best Payment Use Case).
16:9 landscape. No em dashes. Each slide carries citation footnote.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


OUT = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "OpenClaw2026_MuhammadAldoFahrezy_WarungFlow.pdf"
)

W = 13.333 * 72  # ~960
H = 7.5 * 72  # 540
SIZE = (W, H)

INK = HexColor("#0f172a")
BG = HexColor("#f5f7f5")
TEAL = HexColor("#1a3a5c")
TEAL_DK = HexColor("#0f2a44")
GREEN = HexColor("#006b47")
GREEN_SOFT = HexColor("#e6efe9")
AMBER = HexColor("#ffd54f")
MUTED = HexColor("#475569")
CARD = HexColor("#ffffff")
LINE = HexColor("#cbd5e1")
DOKU = HexColor("#e63946")
WHITE = HexColor("#ffffff")
SUBTLE = HexColor("#cfd8dc")


def _register(name: str, candidates: list[str]) -> str:
    for path in candidates:
        if Path(path).is_file():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue
    return ""


REG = _register(
    "Body",
    [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ],
) or "Helvetica"
BOLD = _register(
    "BodyBold",
    [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ],
) or "Helvetica-Bold"
MONO = _register(
    "Mono",
    [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    ],
) or "Courier"


def page_frame(c: canvas.Canvas) -> None:
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(0, H - 12, W, 12, fill=1, stroke=0)


def page_footer(c: canvas.Canvas, n: int, citation: str) -> None:
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(36, 38, W - 36, 38)
    c.setFont(REG, 7.5)
    c.setFillColor(MUTED)
    c.drawString(36, 24, citation)
    c.setFont(BOLD, 8)
    c.setFillColor(TEAL)
    c.drawRightString(W - 36, 24, f"{n} / 5")


def heading(c: canvas.Canvas, eyebrow: str, title: str) -> None:
    c.setFont(BOLD, 9)
    c.setFillColor(GREEN)
    c.drawString(48, H - 54, eyebrow.upper())
    c.setFont(BOLD, 26)
    c.setFillColor(TEAL)
    c.drawString(48, H - 82, title)
    c.setStrokeColor(GREEN)
    c.setLineWidth(2.5)
    c.line(48, H - 92, 96, H - 92)


def wrap(text: str, font: str, size: float, max_w: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        candidate = (cur + " " + w).strip()
        if pdfmetrics.stringWidth(candidate, font, size) <= max_w:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def bullet(
    c: canvas.Canvas,
    x: float,
    y: float,
    head: str,
    body: str,
    max_w: float,
    head_size: float = 11,
    body_size: float = 10.5,
    line_h: float = 13.5,
    head_color=TEAL,
) -> float:
    c.setFillColor(GREEN)
    c.circle(x + 4, y + 3.5, 3, fill=1, stroke=0)
    c.setFont(BOLD, head_size)
    c.setFillColor(head_color)
    c.drawString(x + 14, y, head)
    head_w = pdfmetrics.stringWidth(head, BOLD, head_size)
    c.setFont(REG, body_size)
    c.setFillColor(INK)
    body_lines = wrap(body, REG, body_size, max_w - 14 - head_w - 6)
    if body_lines:
        c.drawString(x + 14 + head_w + 6, y, body_lines[0])
        cur_y = y
        for line in body_lines[1:]:
            cur_y -= line_h
            c.drawString(x + 14, cur_y, line)
        return cur_y - line_h - 4
    return y - line_h - 4


def slide_1(c: canvas.Canvas) -> None:
    """Title + Problem Statement."""
    page_frame(c)

    c.setFont(BOLD, 10)
    c.setFillColor(GREEN)
    c.drawString(48, H - 64, "OPENCLAW AGENTHON 2026  |  BEST PAYMENT USE CASE")

    c.setFont(BOLD, 58)
    c.setFillColor(TEAL)
    c.drawString(48, H - 128, "WarungFlow")

    c.setFont(REG, 16)
    c.setFillColor(MUTED)
    c.drawString(48, H - 154, "From messy notes to bankable reports, autonomously.")
    c.setStrokeColor(GREEN)
    c.setLineWidth(3)
    c.line(48, H - 168, 140, H - 168)

    c.setFont(REG, 10.5)
    c.setFillColor(INK)
    c.drawString(48, H - 190, "Project: OpenClaw2026_MuhammadAldoFahrezy_WarungFlow")
    c.drawString(48, H - 204, "Team: OpenClaw2026_MuhammadAldoFahrezy  |  Member: Muhammad Aldo Fahrezy")

    bx, by = 48, 56
    bw = (W - 96) * 0.60
    bh = H - 240 - by
    c.setFillColor(CARD)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.8)
    c.roundRect(bx, by, bw, bh, 14, fill=1, stroke=1)

    c.setFont(BOLD, 13)
    c.setFillColor(TEAL)
    c.drawString(bx + 22, by + bh - 28, "Problem statement")

    bullets = [
        ("UMKM catat pesanan via WhatsApp,", "terima QRIS dan transfer setiap hari."),
        ("Tutup buku manual,", "sulit jawab siapa sudah bayar dan berapa laba."),
        ("Volume QRIS naik 148% YoY,", "rekonsiliasi harian makin berat untuk warung kecil."),
        ("Pembukuan informal,", "menghambat akses kredit dan laporan bankable."),
    ]
    y = by + bh - 56
    for head, body in bullets:
        y = bullet(c, bx + 22, y, head, body, bw - 44)

    sx = bx + bw + 16
    sw = W - 48 - sx
    sh = bh
    c.setFillColor(TEAL)
    c.roundRect(sx, by, sw, sh, 14, fill=1, stroke=0)

    c.setFont(BOLD, 10)
    c.setFillColor(AMBER)
    c.drawString(sx + 20, by + sh - 26, "PERTANYAAN HARIAN UMKM")

    qs = [
        "Siapa sudah bayar hari ini?",
        "Siapa masih nunggak?",
        "Mana yang partial atau overpaid?",
        "Berapa laba bersih hari ini?",
        "Siap ajukan kredit ke bank?",
    ]
    qy = by + sh - 52
    for q in qs:
        c.setFillColor(AMBER)
        c.circle(sx + 24, qy + 3, 2.4, fill=1, stroke=0)
        c.setFont(REG, 10.5)
        c.setFillColor(WHITE)
        c.drawString(sx + 34, qy, q)
        qy -= 18

    c.setFillColor(GREEN)
    c.roundRect(sx + 20, by + 20, sw - 40, 46, 8, fill=1, stroke=0)
    c.setFont(BOLD, 9)
    c.setFillColor(WHITE)
    c.drawString(sx + 32, by + 46, "Dampak")
    c.setFont(REG, 9.5)
    c.drawString(sx + 32, by + 30, "Cashflow lambat. Piutang lolos.")

    page_footer(
        c,
        1,
        "Sumber: Kemenkop UKM (2025); Bank Indonesia (2025); Statista (2024); OECD SME Outlook; World Bank SME Indonesia.",
    )


def slide_2(c: canvas.Canvas) -> None:
    """Solution Overview."""
    page_frame(c)
    heading(c, "Solution Overview", "Autonomous finance operations agent, bukan chatbot.")

    lx, ly = 48, 60
    lw = (W - 96) * 0.60
    lh = H - 150 - ly
    c.setFillColor(CARD)
    c.setStrokeColor(LINE)
    c.roundRect(lx, ly, lw, lh, 14, fill=1, stroke=1)
    c.setFont(BOLD, 12)
    c.setFillColor(TEAL)
    c.drawString(lx + 22, ly + lh - 28, "Apa yang WarungFlow lakukan otomatis")

    bullets = [
        ("Parse pesanan WhatsApp", "jadi struktur item + harga katalog."),
        ("Rekonsiliasi otomatis", "fuzzy nama + prioritas order ID."),
        ("Deteksi status pembayaran", "PAID, UNPAID, PARTIAL, OVERPAID."),
        ("Skor kesehatan kas 0 sampai 100", "plus Langkah yang disarankan."),
        ("Payment track", "Mock + DOKU Sandbox checkout + sync status."),
        ("Ekspor laporan", "daily_report.md, reconciliation_result.csv."),
    ]
    y = ly + lh - 56
    for head, body in bullets:
        y = bullet(c, lx + 22, y, head, body, lw - 44, head_size=11, body_size=10.5)

    rx = lx + lw + 16
    rw = W - 48 - rx
    rh = lh
    c.setFillColor(TEAL)
    c.roundRect(rx, ly, rw, rh, 14, fill=1, stroke=0)

    c.setFont(BOLD, 11)
    c.setFillColor(AMBER)
    c.drawString(rx + 20, ly + rh - 26, "DEMO MERCHANT")
    c.setFont(BOLD, 15)
    c.setFillColor(WHITE)
    c.drawString(rx + 20, ly + rh - 48, "Warung Bu Sari, Jakarta")
    c.setFont(REG, 9.5)
    c.setFillColor(SUBTLE)
    c.drawString(rx + 20, ly + rh - 62, "30 pesanan/hari, QRIS, transfer, tunai, pay later.")

    stats = [
        ("20", "Tool registered di TOOL_REGISTRY"),
        ("24", "Max steps autonomous loop"),
        ("2", "Payment modes: Mock + DOKU"),
    ]
    sy = ly + rh - 96
    for big, label in stats:
        c.setFillColor(TEAL_DK)
        c.roundRect(rx + 20, sy - 46, rw - 40, 50, 8, fill=1, stroke=0)
        c.setFont(BOLD, 22)
        c.setFillColor(AMBER)
        c.drawString(rx + 32, sy - 30, big)
        c.setFont(REG, 9.5)
        c.setFillColor(WHITE)
        c.drawString(rx + 78, sy - 26, label)
        sy -= 60

    c.setFillColor(GREEN)
    c.roundRect(rx + 20, ly + 18, rw - 40, 36, 8, fill=1, stroke=0)
    c.setFont(BOLD, 10.5)
    c.setFillColor(WHITE)
    c.drawString(rx + 32, ly + 32, "Live: 43.157.208.68:8501")

    page_footer(
        c,
        2,
        "Sumber: Statista (2024) WhatsApp 92% pengguna internet; Bank Indonesia (2025) volume QRIS 15,5 miliar transaksi.",
    )


def slide_3(c: canvas.Canvas) -> None:
    """AI Agent Workflow / Architecture."""
    page_frame(c)
    heading(
        c,
        "Architecture",
        "State-driven autonomous loop, bukan wrapper chat LLM.",
    )

    py = H - 218
    bw, bh = 138, 70
    gap = 22
    nodes = [
        ("Inputs", "WhatsApp + QRIS\nExpenses + Catalogue", TEAL),
        ("Parse & Catalogue", "LOAD_ORDERS\nPARSE_ORDERS", TEAL),
        ("Reconcile", "RECONCILE_PAYMENTS\nDETECT_PAYMENT_ISSUES", GREEN),
        ("Payment Sync", "RESOLVE_PAYMENT_REQUESTS\nCHECK_PAYMENT_STATUS", DOKU),
        ("Report & Export", "VALIDATE_OUTPUTS\nEXPORT_REPORTS", TEAL),
    ]
    total = bw * len(nodes) + gap * (len(nodes) - 1)
    sx = (W - total) / 2
    for i, (title, sub, color) in enumerate(nodes):
        x = sx + i * (bw + gap)
        c.setFillColor(color)
        c.roundRect(x, py, bw, bh, 10, fill=1, stroke=0)
        c.setFont(BOLD, 11)
        c.setFillColor(WHITE)
        c.drawCentredString(x + bw / 2, py + bh - 20, title)
        c.setFont(MONO, 7.4)
        c.setFillColor(GREEN_SOFT)
        for j, line in enumerate(sub.split("\n")):
            c.drawCentredString(x + bw / 2, py + bh - 38 - j * 11, line)
        if i < len(nodes) - 1:
            ax = x + bw
            c.setStrokeColor(MUTED)
            c.setFillColor(MUTED)
            c.setLineWidth(1.4)
            c.line(ax + 2, py + bh / 2, ax + gap - 6, py + bh / 2)
            p = c.beginPath()
            p.moveTo(ax + gap - 6, py + bh / 2)
            p.lineTo(ax + gap - 12, py + bh / 2 + 4)
            p.lineTo(ax + gap - 12, py + bh / 2 - 4)
            p.close()
            c.drawPath(p, fill=1, stroke=0)

    c.setFont(BOLD, 9.5)
    c.setFillColor(GREEN)
    c.drawCentredString(
        W / 2,
        py - 18,
        "decide_next_action() loop  |  up to 24 steps  |  execution_trace + run_id pada Jejak agen",
    )

    cy = 64
    ch = py - cy - 36
    cw = (W - 96 - 32) / 3
    cards = [
        (
            "Tool Call",
            TEAL,
            [
                "20 handlers di TOOL_REGISTRY",
                "agents/tool_handlers.py",
                "Contoh: PARSE_ORDERS,",
                "RECONCILE_PAYMENTS,",
                "CHECK_PAYMENT_STATUS.",
            ],
        ),
        (
            "Autonomous Loop",
            GREEN,
            [
                "decide_next_action()",
                "run_agent_stream()",
                "agents/orchestrator.py",
                "MAX_STEPS = 24",
                "Auto rerun saat data berubah.",
            ],
        ),
        (
            "Payment Sync (DOKU)",
            DOKU,
            [
                "POST /checkout/v1/payment",
                "GET /orders/v1/status/{inv}",
                "HMAC-SHA256 signature",
                "tools/doku_sandbox_provider.py",
                "tools/doku_payment_sync.py",
            ],
        ),
    ]
    for i, (title, color, lines) in enumerate(cards):
        x = 48 + i * (cw + 16)
        c.setFillColor(CARD)
        c.setStrokeColor(LINE)
        c.roundRect(x, cy, cw, ch, 10, fill=1, stroke=1)
        c.setFillColor(color)
        c.rect(x, cy + ch - 5, cw, 5, fill=1, stroke=0)
        c.setFont(BOLD, 12)
        c.setFillColor(color)
        c.drawString(x + 14, cy + ch - 26, title)
        c.setFont(MONO, 8.8)
        c.setFillColor(INK)
        for j, line in enumerate(lines):
            c.drawString(x + 14, cy + ch - 44 - j * 12.5, line)

    page_footer(
        c,
        3,
        "Compliance: OpenClaw Agenthon 2026 Official Technical Guidelines (tool call + autonomous loop, task otonom tuntas).",
    )


def slide_4(c: canvas.Canvas) -> None:
    """Key Features & Tech Stack."""
    page_frame(c)
    heading(c, "Key Features & Tech Stack", "Fitur produk yang sudah jalan + stack teknologi.")

    lx, ly = 48, 60
    lw = (W - 96) * 0.58
    lh = H - 150 - ly
    c.setFillColor(CARD)
    c.setStrokeColor(LINE)
    c.roundRect(lx, ly, lw, lh, 14, fill=1, stroke=1)
    c.setFont(BOLD, 12)
    c.setFillColor(TEAL)
    c.drawString(lx + 22, ly + lh - 28, "Fitur produk")

    rows = [
        ("Rekonsiliasi QRIS", "Fuzzy nama + prioritas order ID di catatan bank."),
        ("Status pembayaran", "PAID, UNPAID, PARTIAL, OVERPAID + Sisa / Lebih Rp."),
        ("Mock + DOKU Sandbox", "mock_pay dan doku_pay simulator + Check Status."),
        ("Katalog produk", "CRUD + CSV, harga dipakai parser pesanan."),
        ("Skor kesehatan kas", "0 sampai 100 + Langkah yang disarankan."),
        ("Jejak agen", "Execution trace per run_id sebagai bukti otonomi."),
        ("Reproducible", "python smoke_test.py -v + judge_testing_guide.md."),
    ]
    y = ly + lh - 56
    for head, body in rows:
        y = bullet(c, lx + 22, y, head, body, lw - 44, head_size=10.5, body_size=10)

    rx = lx + lw + 16
    rw = W - 48 - rx
    rh = lh
    c.setFillColor(CARD)
    c.setStrokeColor(LINE)
    c.roundRect(rx, ly, rw, rh, 14, fill=1, stroke=1)
    c.setFont(BOLD, 12)
    c.setFillColor(TEAL)
    c.drawString(rx + 22, ly + rh - 28, "Tech stack")

    chips = [
        ("Python 3.11", TEAL),
        ("Streamlit", TEAL),
        ("pandas", TEAL),
        ("rapidfuzz", GREEN),
        ("Altair", TEAL),
        ("FastAPI", TEAL),
        ("uvicorn", TEAL),
        ("python-dotenv", MUTED),
        ("DOKU Checkout", DOKU),
        ("DOKU Check Status", DOKU),
        ("HMAC-SHA256", DOKU),
        ("JSONL event store", MUTED),
        ("Cursor IDE", GREEN),
        ("Groq / Gemini (opt)", MUTED),
    ]
    cx = rx + 20
    cy_chip = ly + rh - 56
    chip_h = 20
    max_x = rx + rw - 20
    for label, color in chips:
        w = pdfmetrics.stringWidth(label, BOLD, 9) + 18
        if cx + w > max_x:
            cx = rx + 20
            cy_chip -= 26
        c.setFillColor(color)
        c.roundRect(cx, cy_chip - 14, w, chip_h, 10, fill=1, stroke=0)
        c.setFont(BOLD, 9)
        c.setFillColor(WHITE)
        c.drawString(cx + 9, cy_chip - 8, label)
        cx += w + 8

    nx = rx + 20
    nw = rw - 40
    nh = 60
    ny = ly + 100
    c.setFillColor(GREEN_SOFT)
    c.roundRect(nx, ny, nw, nh, 10, fill=1, stroke=0)
    c.setFont(BOLD, 9.5)
    c.setFillColor(GREEN)
    c.drawString(nx + 14, ny + nh - 18, "DETERMINISTIC FINANCE LOGIC")
    c.setFont(REG, 9.5)
    c.setFillColor(INK)
    c.drawString(nx + 14, ny + nh - 32, "Tool deterministik menangani uang dan aritmetika.")
    c.drawString(nx + 14, ny + nh - 46, "LLM opsional hanya untuk nada pengingat WhatsApp.")

    c.setFillColor(GREEN)
    c.roundRect(rx + 20, ly + 22, rw - 40, 56, 10, fill=1, stroke=0)
    c.setFont(BOLD, 10)
    c.setFillColor(WHITE)
    c.drawString(rx + 32, ly + 56, "Live demo:  43.157.208.68:8501")
    c.setFont(MONO, 10)
    c.drawString(rx + 32, ly + 38, "python smoke_test.py -v")

    page_footer(
        c,
        4,
        "Sumber: rapidfuzz (Maxbachmann, 2024) fuzzy matching; Bank Indonesia (2026) 43 juta merchant QRIS aktif.",
    )


def slide_5(c: canvas.Canvas) -> None:
    """Future Development + Impact."""
    page_frame(c)
    heading(c, "Future & Impact", "Roadmap menuju produksi UMKM Indonesia.")

    lx, ly = 48, 60
    lw = (W - 96) * 0.50
    lh = H - 150 - ly
    c.setFillColor(CARD)
    c.setStrokeColor(LINE)
    c.roundRect(lx, ly, lw, lh, 14, fill=1, stroke=1)
    c.setFont(BOLD, 12)
    c.setFillColor(TEAL)
    c.drawString(lx + 22, ly + lh - 28, "Roadmap")

    roadmap = [
        ("Q1", "WhatsApp Business API live ingestion."),
        ("Q2", "DOKU production HTTP notification webhooks."),
        ("Q3", "POS integration dan rekonsiliasi multi channel."),
        ("Q4", "Financing readiness packet untuk bank dan fintech."),
    ]
    y = ly + lh - 60
    for tag, body in roadmap:
        c.setFillColor(GREEN)
        c.roundRect(lx + 22, y - 12, 34, 22, 11, fill=1, stroke=0)
        c.setFont(BOLD, 10)
        c.setFillColor(WHITE)
        c.drawCentredString(lx + 39, y - 5, tag)
        c.setFont(REG, 11)
        c.setFillColor(INK)
        c.drawString(lx + 66, y - 4, body)
        y -= 40

    rx = lx + lw + 16
    rw = W - 48 - rx
    rh = lh
    c.setFillColor(TEAL)
    c.roundRect(rx, ly, rw, rh, 14, fill=1, stroke=0)
    c.setFont(BOLD, 12)
    c.setFillColor(AMBER)
    c.drawString(rx + 22, ly + rh - 26, "Impact")

    impacts = [
        ("66 jt", "UMKM target pasar (Kemenkop UKM, 2025)"),
        ("Rp 1.420 T", "Volume QRIS 2025 (Bank Indonesia)"),
        ("61,9%", "Kontribusi UMKM ke PDB (Kemenkop UKM)"),
        ("97%", "Serapan tenaga kerja oleh UMKM"),
    ]
    grid_x = rx + 22
    cell_w = (rw - 60) / 2
    cell_h = 70
    top_y = ly + rh - 50
    for i, (big, label) in enumerate(impacts):
        row, col = divmod(i, 2)
        cx = grid_x + col * (cell_w + 16)
        cy = top_y - row * (cell_h + 14)
        c.setFillColor(TEAL_DK)
        c.roundRect(cx, cy - cell_h, cell_w, cell_h, 10, fill=1, stroke=0)
        c.setFont(BOLD, 22)
        c.setFillColor(AMBER)
        c.drawString(cx + 14, cy - 32, big)
        c.setFont(REG, 8.5)
        c.setFillColor(SUBTLE)
        for j, ln in enumerate(wrap(label, REG, 8.5, cell_w - 28)):
            c.drawString(cx + 14, cy - 48 - j * 11, ln)

    closing_h = 56
    closing_y = ly + 18
    c.setFillColor(GREEN)
    c.roundRect(rx + 22, closing_y, rw - 44, closing_h, 10, fill=1, stroke=0)
    c.setFont(BOLD, 11.5)
    c.setFillColor(WHITE)
    c.drawString(rx + 36, closing_y + 34, "From messy notes to bankable")
    c.drawString(rx + 36, closing_y + 18, "reports, autonomously.")

    page_footer(
        c,
        5,
        "Sumber: Kemenkop UKM (2025); Bank Indonesia (2025); Bappenas Striving to Thrive (2024/25); OECD; World Bank.",
    )


def build() -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=SIZE)
    c.setTitle("OpenClaw2026_MuhammadAldoFahrezy_WarungFlow")
    c.setAuthor("Muhammad Aldo Fahrezy")
    c.setSubject("OpenClaw Agenthon 2026 - Best Payment Use Case")
    c.setKeywords("WarungFlow, OpenClaw, UMKM, autonomous agent, DOKU, QRIS")
    for fn in (slide_1, slide_2, slide_3, slide_4, slide_5):
        fn(c)
        c.showPage()
    c.save()
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"wrote: {p}")
