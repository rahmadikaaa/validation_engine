

## Laporan Strategis: Modernisasi Workflow Audit Harga Surveyor (SHBJ 2026)

### 1. Executive Summary

Saat ini, pemrosesan data Standar Harga Barang Jasa (SHBJ) DKI Jakarta 2026 yang berjumlah **13.548 baris** dilakukan secara manual dan linear. Metode konvensional ini memiliki risiko inefisiensi yang sangat tinggi serta rentan terhadap *human error* pada tahap ekstraksi data realita pasar. Transformasi menuju sistem berbasis AI dan *Knowledge Graph* (Grapify) diusulkan untuk mengonversi data statis menjadi aset informasi yang dinamis, terintegrasi, dan *scalable*.

### 2. Analisis Workflow Manual (Current State)

Proses yang berjalan saat ini bersifat repetitif dan memakan waktu (*time-consuming*) dengan tahapan sebagai berikut:

* 
**Penyediaan Data Standar:** Mengacu pada tabel Excel SHBJ 2026 yang berisi spesifikasi teknis dan harga satuan standar.


* 
**Pencarian & Ekstraksi:** Melakukan survei lapangan (*online* via INAPROC atau *offline*) dan mengetik ulang data barang/harga ke tabel survei secara manual.


* 
**Kalkulasi Deviasi:** Menghitung selisih harga pasar terhadap standar secara manual (ditemukan deviasi signifikan antara -10% hingga +31%).


* 
**Dokumentasi:** Mengunggah bukti ke Google Docs dan menyalin tautannya satu per satu ke kolom laporan.



### 3. Arsitektur Solusi: The Grapify Engine

Sistem ini menggunakan **Grapify** sebagai "Otak Tengah" yang menghubungkan seluruh pengetahuan agar AI tetap berada di koridor data yang benar (*grounding*).

#### A. Struktur Knowledge Graph (Lapis Knowledge)

Data ribuan baris dipecah menjadi jaringan keterhubungan:

* 
**Nodes (Titik):** Merepresentasikan entitas unik seperti "Nama Barang", "Vendor", dan "Harga Standar".


* 
**Edges (Hubungan):** Menghubungkan logika antar data, misalnya: Barang (A) **memiliki** Harga Standar (B) dan **ditemukan** pada Vendor (C).



#### B. Alur Kerja Otomatis (Efficiency Flow)

1. 
**Input:** Pengguna hanya perlu mengunggah *screenshot* hasil survei (misal: data INAPROC) ke aplikasi di Cloud Run.


2. 
**Processing:** Gemini di AI Studio melakukan OCR instan untuk ekstraksi nama barang dan harga tanpa input manual.


3. 
**Validation:** Sistem memvalidasi harga tersebut terhadap "peta logika" di Grapify untuk mencari plafon harga standar secara otomatis.


4. 
**Guardrails:** Jika deviasi harga > 10%, sistem otomatis memberikan tanda **RED FLAG**.


5. 
**Output:** Laporan PDF hasil perbandingan dan ringkasan bukti survei di-generate secara instan.



### 4. Nilai Strategis & Keunggulan

* 
**Anti-Halusinasi:** AI hanya mengambil referensi dari sumber data SHBJ eksklusif, bukan dari data umum internet.


* 
**Akses Data Instan:** Pencarian tidak lagi bersifat linear (baris demi baris), melainkan langsung "melompat" ke titik data yang relevan melalui *edge* di Grapify.


* 
**Scalability:** Penambahan data survei baru hanya memerlukan pembuatan hubungan (*edge*) baru tanpa merusak struktur database yang ada.



---

**Strategic Impact:**
Implementasi ini merupakan prototipe **Audit Harga Otomatis** yang sangat relevan bagi instansi besar. Fokus pada kategori Suku Cadang (Ban) dalam demo #JuaraVibeCoding akan menunjukkan kematangan arsitektur yang lo bangun, sekaligus membuktikan bahwa lo adalah kandidat yang "satu frekuensi" dengan kebutuhan efisiensi di AGIT.

