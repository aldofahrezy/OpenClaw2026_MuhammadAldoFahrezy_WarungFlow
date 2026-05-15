# Demo Script — 2 Minutes (Video)

**Title (YouTube):** `OpenClaw2026_MuhammadAldoFahrezy_WarungFlow`  
**Access:** Unlisted  
**Live URL:** http://43.157.208.68:8501  
**Track:** Best Payment Use Case

---

## Before you record (5 min prep)

1. Open http://43.157.208.68:8501 in a clean browser window (incognito is fine).
2. Sidebar → **Reset riwayat demo** once, then wait for the first auto-run to finish (status **Selesai** on Beranda).
3. **Simulasi** → **Mode pembayaran** = **Mock (demo aman)** (fastest path; no DOKU keys needed on camera).
4. Close other tabs; zoom browser to **100–110%** so text is readable on video.
5. Optional second tab ready: `?doku_pay=` only if you have 15s spare at the end for DOKU mention.

**Do not** during recording: reset demo, switch payment mode mid-flow, or wait for cold-start without cutting.

---

## Shot list (exactly 2:00)

| Time | Screen | You say (English) | You do |
|------|--------|-------------------|--------|
| **0:00–0:12** | Title card or Beranda | "Indonesian warung take orders on WhatsApp and QRIS, but closing the books is still manual. Who paid? Who owes? What's today's profit?" | Static or slow scroll on reconciliation table showing UNPAID rows. |
| **0:12–0:22** | Beranda loading → done | "WarungFlow is an autonomous finance agent, not a chatbot. It loads sample data and runs the full analysis automatically." | Let auto-run finish; point at KPI cards + **Langkah yang disarankan**. |
| **0:22–0:35** | Rekonsiliasi | "It reconciles messy orders to payments, flags unpaid and partial, and shows Sisa Rp and Lebih Rp per order." | Click **Rekonsiliasi**; highlight 1 UNPAID + 1 PAID row. |
| **0:35–0:55** | Simulasi → WhatsApp | "Customers order via WhatsApp. The bot creates a structured order and payment link." | **Simulasi** → tab **Pesanan WhatsApp** → phone `+628123456789` → send: `nasi goreng 2 - Kevin` → show bot reply in **Aktivitas chat** + **Pesanan dari bot** = **Menunggu bayar**. |
| **0:55–1:10** | Pay (Mock) | "Payment is recorded and the agent re-runs." | Click **mock_pay** link in chat *or* scroll to **Bayar pesanan bot** → **Tandai sudah bayar** → wait for refresh → **Pesanan dari bot** = **Lunas**. |
| **1:10–1:28** | Jejak agen | "Judges can verify autonomy: twenty tools, state-driven loop, up to twenty-four steps per run." | **Jejak agen** → expand one **run_id** → scroll 6–8 steps: PARSE_ORDERS, RECONCILE_PAYMENTS, CALCULATE_CASHFLOW, EXPORT_REPORTS. |
| **1:28–1:42** | Simulasi payment mode | "For Best Payment Use Case we integrate DOKU Sandbox: hosted checkout plus Check Status sync." | **Simulasi** → show **Mode pembayaran: DOKU Sandbox** in dropdown (no need to complete checkout on camera). |
| **1:42–2:00** | Beranda or Laporan | "From messy notes to bankable reports, autonomously. WarungFlow — live at forty-three dot one five seven dot two zero eight dot six eight colon eight five zero one." | **Beranda** KPIs or **Laporan** chart + point at export / health score. End on tagline. |

---

## Narration script (read verbatim, ~115 words)

> Indonesian warung take orders on WhatsApp and QRIS, but closing the books is still manual. Who paid? Who still owes? What's today's profit?
>
> WarungFlow is an **autonomous finance agent**, not a chatbot. It loads Warung Bu Sari sample data and runs a full tool loop automatically.
>
> It reconciles orders to payments, flags unpaid and partial amounts, and shows **Sisa Rp** and **Lebih Rp**.
>
> Here a customer orders on WhatsApp. The bot creates the order. I mark payment via mock link — status becomes **Lunas**, and the dashboard updates.
>
> On **Jejak agen** you see the proof: **twenty tools**, **decide_next_action** loop, execution trace per run.
>
> For the payment track we support **DOKU Sandbox**: hosted checkout and Check Status sync.
>
> **From messy notes to bankable reports, autonomously.** Thank you.

---

## If something breaks on camera

| Problem | Quick fix |
|---------|-----------|
| Agent still running | Wait 3s or click **Paksa refresh analisis** on Simulasi |
| No bot reply | Check phone field filled; resend message |
| Order not PAID | Use **Tandai sudah bayar** on Simulasi (faster than link) |
| Empty Jejak agen | Go Beranda first, wait for run to complete, then Jejak agen |
| Page slow | Say "auto-run on first load" while status spinner shows |

---

## What to show judges (priority order)

1. **Autonomy** — Jejak agen with many tool steps (required by competition rules).
2. **Not a chatbot** — Say "finance agent" + show reconciliation, not only chat UI.
3. **Payment track** — Mock pay flow + mention DOKU Sandbox mode (even 5 seconds on dropdown).
4. **Reactive** — UNPAID → PAID change after payment (Kevin or new order).

---

## Optional 15s cut (if under time)

Skip DOKU dropdown (1:28–1:42) and go straight from Jejak agen to closing.

## Optional 15s add (if over time)

Show **Laporan** export button for 3 seconds instead of extra Beranda scroll.

---

## Recording checklist

- [ ] Mic test; reduce background noise
- [ ] 1920×1080 or 1280×720 screen capture
- [ ] Mouse cursor visible; move deliberately
- [ ] YouTube: **Unlisted**, title `OpenClaw2026_MuhammadAldoFahrezy_WarungFlow`
- [ ] Paste link in Devpost **Video demo** field

**Do not commit this file** if you are only using it locally for recording prep.
