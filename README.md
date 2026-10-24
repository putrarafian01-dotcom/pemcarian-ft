# Cari Jawaban Soal (GitHub Pages)

Dasbor pencarian soal statis — tanpa server. Data dari `all_latihan.xlsx` sudah dipadatkan ke folder `data/` (±0,5 MB).

## Deploy ke GitHub Pages
1. Buat repo baru di GitHub, upload **seluruh isi folder ini** (index.html, folder data/, tools/, .nojekyll).
2. Repo → Settings → Pages → Source: *Deploy from a branch* → Branch `main` / folder `/ (root)` → Save.
3. Tunggu 1–2 menit, buka `https://USERNAME.github.io/NAMA-REPO/`.

## Update data Excel
```
python3 tools/build_data.py all_latihan.xlsx
```
Lalu upload ulang folder `data/` ke GitHub. (Hanya butuh Python 3.8+, tanpa library tambahan.)

## Aturan pencarian
- Isi kata sama persis (urutan pilihan boleh diacak) = **100%** → hanya jawaban itu yang tampil.
- Tidak ada 100% → tampil semua soal ≥ 70% mirip, urut dari yang paling mirip di atas (ubah `MIN_SCORE` di index.html).
- Pop-up hijau jika ada, merah jika tidak ada.
- Referensi AI (Gemini/Claude): tombol “Referensi AI” → isi API key (tersimpan di browser saja). Aktif otomatis kalau soal tidak ada di Excel.
