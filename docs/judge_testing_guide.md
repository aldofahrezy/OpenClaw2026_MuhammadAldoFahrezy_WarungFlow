# Panduan uji untuk juri — WarungFlow

**Tim:** OpenClaw2026_MuhammadAldoFahrezy  
**Live demo:** http://43.157.208.68:8501  
**Repo:** https://github.com/aldofahrezy/Warung-Flow

Dokumen ini menjelaskan cara menguji **dua jalur pembayaran** (Mock dan DOKU Sandbox) tanpa perlu membaca seluruh codebase.

---

## Prasyarat (5 menit)

```bash
git clone https://github.com/aldofahrezy/Warung-Flow.git
cd Warung-Flow
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python smoke_test.py -v
streamlit run app.py
```

Buka http://localhost:8501 — data contoh **Warung Bu Sari** dimuat otomatis dan analisis agen pertama berjalan sendiri.

| Mode | Kredensial | Cocok untuk |
|------|------------|-------------|
| **Mock** | Tidak perlu API key | Semua juri; Streamlit Cloud |
| **DOKU Sandbox** | `DOKU_CLIENT_ID` + `DOKU_SECRET_KEY` di `.env` | Track Best Payment Use Case |

**Penting:** Mode pembayaran dipilih di **Simulasi → Mode pembayaran**, bukan lewat variabel `PAYMENT_MODE` di env.

---

## Navigasi dashboard

| Halaman | Isi utama |
|---------|-----------|
| **Beranda** | KPI, rekonsiliasi, **Langkah yang disarankan**, unduh laporan |
| **Simulasi** | Chat WhatsApp, pesanan bot, QRIS manual, pengeluaran, **mode pembayaran**, auto-refresh |
| **Katalog** | CRUD produk + impor CSV |
| **Jejak agen** | Trace eksekusi per `run_id` (bukti otonomi) |
| **Rekonsiliasi** | Tabel tagihan / terbayar / sisa-kelebihan |
| **Laporan** | Grafik, skor kesehatan, ekspor MD/CSV |

**Sidebar:** Reset riwayat demo (hapus chat + pesanan bot di `runtime/`), navigasi halaman.

---

## Alur A — Mock mode (tanpa DOKU)

**Tujuan:** Bukti rekonsiliasi + pembayaran bot tanpa kredensial pihak ketiga.

### A1. Rekonsiliasi reaktif (Kevin UNPAID → PAID)

1. Buka **Simulasi** → tab **Pembayaran QRIS**.
2. Pastikan **Mode pembayaran** = **Mock (demo aman)**.
3. Aktifkan **Perbarui analisis otomatis** (jika ada).
4. Di tab **Pesanan WhatsApp**, kirim pesanan baru atau gunakan data contoh di Beranda.
5. Tambah baris pembayaran: nama **Kevin**, jumlah sesuai pesanan Kevin, metode QRIS, catatan berisi `order_id` jika ada.
6. Tunggu auto-refresh atau klik **Paksa refresh analisis**.
7. **Beranda / Rekonsiliasi:** status Kevin berubah **Lunas**; KPI dan skor kesehatan ikut berubah.

### A2. Pesanan lewat bot WhatsApp + bayar via deep link

1. **Simulasi** → **Mode pembayaran** = Mock.
2. Tab **Pesanan WhatsApp** → isi nomor (+628…) dan pesan, mis. `nasi goreng 2 - Andi`.
3. Lihat balasan bot di **Aktivitas chat** dan tabel **Pesanan dari bot** (status **Menunggu bayar**).
4. Di pesan bot ada link `?mock_pay=ORD-BOT-xxxxx` — klik atau buka di tab baru.
5. Halaman konfirmasi mencatat pembayaran → kembali ke **Simulasi**; status **Lunas**.
6. Alternatif: di Simulasi, bagian **Bayar pesanan bot** → **Tandai sudah bayar**.

### A3. Bukti agen otonom

1. **Jejak agen** — minimal 8–15 langkah: `LOAD_ORDERS`, `PARSE_ORDERS`, `RECONCILE_PAYMENTS`, `CALCULATE_CASHFLOW`, dll.
2. **Laporan** — unduh `daily_report.md`, `reconciliation_result.csv`.

**Waktu uji:** ~8 menit.

---

## Alur B — DOKU Sandbox mode

**Tujuan:** Integrasi pembayaran nyata (sandbox) + sinkron status ke WarungFlow.

### Prasyarat DOKU

Di `.env` (jangan commit file ini):

```env
DOKU_CLIENT_ID=your_client_id
DOKU_SECRET_KEY=your_secret_key
PUBLIC_BASE_URL=http://localhost:8501   # atau URL VPS Anda
```

Restart Streamlit setelah mengubah `.env`.

### B1. Buat pesanan dengan checkout DOKU

1. **Simulasi** → **Mode pembayaran** = **DOKU Sandbox**.
2. Pastikan caption menampilkan `kredensial DOKU OK` (bukan "belum lengkap").
3. Tab **Pesanan WhatsApp** → kirim pesanan (mis. `nasi goreng 1 - Doku`).
4. Di chat, bot mengirim:
   - Link **simulator** WarungFlow: `/?doku_pay=ORD-BOT-xxxxx`
   - Link **checkout resmi** DOKU: `https://staging.doku.com/checkout-link-v2/...`
5. Tabel **Pesanan dari bot** → status **Menunggu bayar**.

### B2. Bayar di DOKU staging

1. Buka link checkout DOKU (staging).
2. Pilih metode (VA, Indomaret, dll.) dan selesaikan pembayaran sandbox sesuai instruksi DOKU.
3. **Penting:** Pembayaran di halaman DOKU **tidak otomatis** mengubah dashboard sampai WarungFlow memanggil API Check Status.

### B3. Sinkronkan status ke WarungFlow

Pilih salah satu:

| Cara | Langkah |
|------|---------|
| **Simulator (disarankan)** | Buka `/?doku_pay=ORD-BOT-xxxxx` → klik **↻ Cek status pembayaran DOKU** |
| **Kembali dari DOKU** | Jika `DOKU_SUCCESS_URL` mengarah ke `?doku_return=...`, status dicek otomatis saat landing |
| **Uji cepat tanpa DOKU** | Di simulator, **✓ Bayar berhasil (simulator)** |

Setelah `SUCCESS` dari API DOKU:

- **Pesanan dari bot** → **Lunas**
- Agen dapat auto-refresh (jika toggle aktif)
- Pelanggan menerima pesan WhatsApp konfirmasi (mock)

**Catatan DOKU:** API Check Status disarankan ≥60 detik setelah pembayaran selesai. Jika masih `PENDING`, tunggu sebentar lalu klik **Cek status** lagi.

### B4. QRIS manual + pesanan bot

1. Buat pesanan bot (DOKU mode).
2. Tab **Pembayaran QRIS** → tambah mutasi dengan nominal + nama yang cocok.
3. WarungFlow dapat mengaitkan pembayaran manual ke pesanan bot (`link_manual_payment_to_bot_order`).

**Waktu uji:** ~12 menit (termasuk checkout DOKU).

---

## Checklist cepat juri

- [ ] `python smoke_test.py -v` → OK
- [ ] Beranda menampilkan rekonsiliasi setelah load pertama
- [ ] **Jejak agen** ≥8 langkah per run
- [ ] Mock: `?mock_pay=` atau QRIS → status **Lunas**
- [ ] DOKU: checkout staging + **Cek status pembayaran DOKU** → **Lunas**
- [ ] **Katalog**: edit harga → pesanan baru memakai harga baru
- [ ] **Laporan**: file di `outputs/` terunduh

---

## Troubleshooting

| Gejala | Penyebab / solusi |
|--------|-------------------|
| Mode DOKU selalu kembali ke Mock | `DOKU_CLIENT_ID` / `DOKU_SECRET_KEY` kosong di `.env` |
| Sudah bayar di DOKU, dashboard masih menunggu | Buka `?doku_pay=...` → **Cek status pembayaran DOKU** |
| DOKU API `PENDING` | Pembayaran belum final di sandbox; tunggu ~1 menit |
| Link pembayaran `localhost` di VPS | Set `PUBLIC_BASE_URL` ke URL publik (mis. `http://43.157.208.68:8501`) |
| Data lama setelah refresh | **Reset riwayat demo** di sidebar, lalu uji ulang |
| Agen tidak jalan lagi | **Paksa refresh analisis** di Simulasi |

---

## File teknis (referensi)

| File | Peran |
|------|--------|
| `tools/payment_links.py` | Bangun link mock vs DOKU |
| `tools/doku_sandbox_provider.py` | Checkout API + Check Status GET |
| `tools/doku_payment_sync.py` | Poll DOKU → `simulate_mock_payment` |
| `dashboard_doku_checkout.py` | UI `?doku_pay=` / `?doku_return=` |
| `tools/bot_service.py` | Alur pesanan + pembayaran bot |
| `runtime/orders.jsonl` | Persistensi pesanan bot |

---

## Perintah opsional

```bash
# Bot API terpisah (opsional)
uvicorn bot_server:app --host 0.0.0.0 --port 8000

# Deploy VPS (systemd)
sudo systemctl restart warungflow
```

Lihat juga: `README.md`, `DEPLOY.md`, `docs/demo_script.md`.
