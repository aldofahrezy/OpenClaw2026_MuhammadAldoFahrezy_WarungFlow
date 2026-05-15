# Kepatuhan Pedoman Teknis — OpenClaw Agenthon 2026

**Tim:** OpenClaw2026_MuhammadAldoFahrezy  
**Proyek:** OpenClaw2026_MuhammadAldoFahrezy_WarungFlow  
**Devpost:** https://openclawagenthon.devpost.com/

Dokumen ini memetakan setiap ketentuan resmi RISTEK × Build Club ke bukti di repositori WarungFlow.

---

## Ringkasan eksekutif

| Area | Status | Catatan |
|------|--------|---------|
| AI Agent (tool call + autonomous loop) | ✅ Memenuhi | 20 tool, loop hingga 24 langkah, trace di Jejak agen |
| Bukan chatbot/UI kosong | ✅ Memenuhi | Inti = rekonsiliasi & laporan otonom; WhatsApp hanya saluran input |
| README & reproducible | ✅ Memenuhi | `README.md` + `docs/judge_testing_guide.md` + `smoke_test.py` |
| Best Payment Use Case | ✅ Memenuhi | DOKU Sandbox Checkout + Check Status API |
| Penamaan tim / proyek / video / deck | ✅ Memenuhi | Format `OpenClaw2026_MuhammadAldoFahrezy_WarungFlow` |
| **Penamaan repo GitHub** | ⚠️ Perbaiki | Saat ini: `aldofahrezy/Warung-Flow` — panitia mensyaratkan `OpenClaw2026_NamaTim_NamaProject` |
| Riwayat commit dalam sprint | ✅ Memenuhi | Commit pertama: 15 Mei 2026 **10:49 WIB** (setelah 09:45 WIB) |
| Push GitHub terbaru | ⚠️ Perbaiki | 1 commit lokal belum ter-push (`735f49b`) |
| Submission Devpost (manual) | ⏳ Anda lengkapi | Video YouTube, field Devpost, label track |

---

## 1. Format & ketentuan kompetisi

| Ketentuan | Status | Bukti / tindakan |
|-----------|--------|------------------|
| Online, 1 submission per tim | ✅ | Satu repo, satu proyek WarungFlow |
| Maks. 4 orang per tim | ✅ | Tim individu: Muhammad Aldo Fahrezy |
| Build sprint 12 jam | ✅ | Commit 15 Mei 2026 10:49–21:55 WIB (lihat `git log`) |
| Repo dibuat setelah 09:45 WIB | ✅ | `git log --reverse` → `2956b79` pada `2026-05-15 10:49:54 +0700` |
| Tidak commit setelah deadline | ⏳ | **Stop push/commit setelah 15 Mei 2026 23:00 WIB** |

---

## 2. Ketentuan pengembangan AI Agent (wajib)

### 2.1 Tool Call Capability

| Requirement | Status | Bukti |
|-------------|--------|-------|
| Agen memanggil tool/fungsi eksternal | ✅ | `agents/tool_handlers.py` → `TOOL_REGISTRY` (20 handler) |
| Tool usage tercatat | ✅ | `state.execution_trace`, UI **Jejak agen** |

**Daftar tool (cuplikan):** `LOAD_ORDERS`, `PARSE_ORDERS`, `RECONCILE_PAYMENTS`, `DETECT_PAYMENT_ISSUES`, `RESOLVE_PAYMENT_REQUESTS`, `CHECK_PAYMENT_STATUS`, `CALCULATE_CASHFLOW`, `VALIDATE_OUTPUTS`, `EXPORT_REPORTS`, `DOKU_WEBHOOK_SIMULATOR`, dll.

### 2.2 Autonomous Loop

| Requirement | Status | Bukti |
|-------------|--------|-------|
| Loop otonom hingga tugas selesai | ✅ | `agents/orchestrator.py` → `decide_next_action()` + `run_agent_stream()` |
| Minimal 1 task tuntas tanpa intervensi manual | ✅ | Load → parse → rekonsiliasi → cashflow → laporan → validasi → ekspor |
| Batas langkah | ✅ | `MAX_STEPS = 24` |
| Auto-run di UI | ✅ | `session_runtime.py` → `schedule_initial_run`, `process_pending_agent_run` |

**Verifikasi juri (30 detik):**

```bash
python smoke_test.py -v
streamlit run app.py
# Buka Jejak agen → lihat ≥8 langkah per run_id
```

### 2.3 Bukan chatbot / UI kosong

| Requirement | Status | Penjelasan untuk juri |
|-------------|--------|------------------------|
| Bukan wrapper chatbot saja | ✅ | **Orchestrator keuangan** yang memutuskan tool berikutnya dari `AgentState` |
| Bukan UI tanpa backend AI | ✅ | Streamlit = visualisasi; logika di `agents/`, `tools/` |
| WhatsApp = saluran input, bukan produk utama | ✅ | Bot (`tools/bot_service.py`) menghasilkan pesanan → **`SYNC_BOT_EVENTS`** → agen merekonsiliasi |

**Narasi singkat:** WarungFlow adalah *autonomous finance operations agent* untuk UMKM, bukan chatbot customer service.

### 2.4 Kebebasan stack

| Ketentuan | Status |
|-----------|--------|
| Framework/model bebas | ✅ Python, Streamlit, optional Groq/Gemini |
| Open-source / template diperbolehkan | ✅ |
| Tidak wajib OpenClaw | ✅ Workspace docs kompatibel OpenClaw/QwenPaw |

---

## 3. Submission requirements (Devpost — 15 Mei 2026 23:00 WIB)

| Item | Format wajib | Status | Lokasi / tindakan |
|------|--------------|--------|-------------------|
| Nama tim | `OpenClaw2026_NamaTim` | ✅ | `OpenClaw2026_MuhammadAldoFahrezy` |
| Project description | Naratif | ✅ | Salin dari `docs/devpost_submission.md` |
| GitHub public + README | Reproducible | ✅ | `README.md`, `docs/judge_testing_guide.md` |
| **Nama repo GitHub** | `OpenClaw2026_NamaTim_NamaProject` | ⚠️ | **Rename** `Warung-Flow` → `OpenClaw2026_MuhammadAldoFahrezy_WarungFlow` di GitHub Settings |
| Demo video YouTube | Unlisted, ≤2 menit | ⏳ | Judul: `OpenClaw2026_MuhammadAldoFahrezy_WarungFlow` — skrip: `docs/demo_script.md` |
| Pitch deck PDF | ≤5 slide | ✅ | `docs/OpenClaw2026_MuhammadAldoFahrezy_WarungFlow.pdf` |
| Live deployment (opsional) | URL | ✅ | http://43.157.208.68:8501 |
| AI tools/models used | Daftar | ⏳ | Cantumkan di Devpost: Cursor, Gemini/Groq (opsional), DOKU Sandbox API |
| Label **Best Payment Use Case** | Wajib untuk track DOKU | ⏳ | Centang saat submit Devpost |
| Akses tanpa permission | Public/unlisted | ⏳ | Pastikan repo public, video Unlisted bukan Private |

---

## 4. Demo video & pitch deck

| Ketentuan | Status |
|-----------|--------|
| Durasi ≤2 menit | ⏳ Saat rekam, ikuti `docs/demo_script.md` |
| Tunjukkan workflow agen | ✅ Rekam: auto-run + **Jejak agen** + perubahan rekonsiliasi |
| Audio & layar jelas | ⏳ Saat produksi video |
| Pitch deck PDF max 5 slide | ✅ File ada; isi: Problem, Solution, Architecture, Features, Future |
| Penamaan deck | ✅ `OpenClaw2026_MuhammadAldoFahrezy_WarungFlow.pdf` |

---

## 5. Kriteria penilaian — mapping fitur

| Kriteria (bobot) | Cara WarungFlow menjawab |
|------------------|---------------------------|
| **Use case & impact (10%)** | Rekonsiliasi WhatsApp + QRIS untuk warung; Sisa/Lebih bayar; reminders BI |
| **Creativity (30%)** | Agent keuangan + katalog + bot + mock/DOKU payment |
| **Autonomy & agent (30%)** | `decide_next_action`, 20 tools, trace, reactive refresh, edge case partial/overpaid |
| **Technical execution (20%)** | `smoke_test.py`, parsers deterministik, DOKU HMAC signature, clean modules |
| **Deployability (10%)** | VPS live, DEPLOY.md, judge guide Mock + DOKU, `.env.example` |

### Best Payment Use Case (DOKU)

| Aspek | Status | Bukti |
|-------|--------|-------|
| Integrasi pembayaran nyata (sandbox) | ✅ | `tools/doku_sandbox_provider.py` — Checkout API |
| Status transaksi | ✅ | `tools/doku_payment_sync.py` — Check Status GET |
| Alur uji juri | ✅ | `docs/judge_testing_guide.md` — Alur B |
| UI simulator | ✅ | `?doku_pay=`, `dashboard_doku_checkout.py` |

---

## 6. Keamanan & etika

| Ketentuan | Status |
|-----------|--------|
| `.env` tidak di-commit | ✅ `.gitignore` memuat `.env` |
| Kredensial di dokumentasi | ✅ Hanya placeholder di `.env.example` |
| Tidak plagiarisme / sabotase | ✅ Proyek original tim |

---

## 7. Action items sebelum deadline

### Wajib (risiko diskualifikasi / penilaian)

1. **Rename repository GitHub** ke `OpenClaw2026_MuhammadAldoFahrezy_WarungFlow` (Settings → Repository name), lalu update URL di Devpost.
2. **Push commit terakhir:** `git push origin main` (commit `735f49b` masih lokal).
3. **Submit Devpost** lengkap + centang **Best Payment Use Case**.
4. **Upload video YouTube** (Unlisted), judul sesuai format.
5. **Stop semua commit** setelah 23:00 WIB 15 Mei 2026.

### Disarankan (nilai juri)

6. Di video: tunjukkan **Jejak agen** (bukan hanya chat WhatsApp).
7. Di Devpost description: tekankan **autonomous loop** + **20 tools**, bukan “chatbot warung”.
8. Tes live URL + `python smoke_test.py -v` sekali sebelum submit.

---

## 8. Bukti cepat untuk juri (copy-paste)

**Autonomous loop:**

```
agents/orchestrator.py     → decide_next_action(), run_agent_stream(), MAX_STEPS=24
agents/tool_handlers.py    → TOOL_REGISTRY (20 tools)
session_runtime.py         → auto-run on data change
```

**Bukan chatbot:**

```
tools/reconciliation.py    → fuzzy match + order_id priority
tools/cashflow.py          → P&L, health score
agents/orchestrator.py     → planner, bukan LLM chat loop
```

**Payment track:**

```
tools/doku_sandbox_provider.py  → DOKU Checkout + Check Status
tools/doku_payment_sync.py      → sync pembayaran → status PAID
```

---

*Terakhir diperbarui: 15 Mei 2026 — sesuai pedoman resmi RISTEK × Build Club OpenClaw Agenthon 2026.*
