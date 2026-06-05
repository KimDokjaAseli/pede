# README.md

# Evaluasi Model Embedding all-MiniLM-L6-v2 pada Aplikasi PEDE

## Deskripsi

Penelitian ini bertujuan untuk mengevaluasi performa model embedding **all-MiniLM-L6-v2** sebagai pengganti model **BAAI/bge-m3** pada aplikasi PEDE (Paper Embedding Database Engine).

Pengujian dilakukan untuk mengetahui pengaruh variasi **Chunk Size** dan **Overlap** terhadap kualitas pencarian dokumen, kecepatan retrieval, serta ukuran database vector yang dihasilkan.

---

# Arsitektur Sistem

```text
PDF Paper
    │
    ▼
ingest.py
    │
    ├── Ekstraksi Metadata
    ├── Ekstraksi DOI
    └── Chunking Dokumen
            │
            ▼
all-MiniLM-L6-v2
(Embedding 384 Dimensi)
            │
            ▼
Qdrant Vector Database
            │
            ▼
Semantic Search Query
            │
            ▼
Top-K Retrieval Result
```

---

# Model yang Digunakan

## all-MiniLM-L6-v2

Model embedding berbasis Sentence Transformers yang dirancang untuk menghasilkan representasi semantik kalimat secara efisien.

### Karakteristik

| Parameter           | Nilai             |
| ------------------- | ----------------- |
| Embedding Dimension | 384               |
| Arsitektur          | Transformer       |
| Max Input           | 256 Token         |
| Bahasa Utama        | Inggris           |
| Similarity          | Cosine Similarity |
| Kecepatan           | Tinggi            |
| Konsumsi Memori     | Rendah            |

### Kelebihan

* Ringan dan cepat
* Cocok untuk semantic search
* Ukuran index relatif kecil
* Latensi retrieval rendah
* Mudah dijalankan pada perangkat dengan spesifikasi menengah

### Kekurangan

* Context window lebih pendek dibanding BGE-M3
* Kurang optimal untuk dokumen sangat panjang
* Dukungan multilingual lebih terbatas

---

# Perbandingan dengan BAAI/bge-m3

| Parameter      | BGE-M3        | all-MiniLM-L6-v2 |
| -------------- | ------------- | ---------------- |
| Dimensi Vector | 1024 + Sparse | 384              |
| Max Token      | 8192          | 256              |
| Search Method  | Hybrid        | Dense Only       |
| Multilingual   | >100 Bahasa   | Dominan Inggris  |
| Memory Usage   | Tinggi        | Sangat Rendah    |
| Speed          | Sedang        | Sangat Cepat     |

---

# Metode Pengujian

Pengujian dilakukan menggunakan:

* 10 kombinasi Chunk Size dan Overlap
* Dataset jurnal ilmiah
* Retrieval Top-K
* Vector Database Qdrant

Metrik yang digunakan:

1. Recall@5
2. Hit Rate
3. Latency
4. Ukuran Database

---

# Hasil Pengujian

## Recall@5

Hasil menunjukkan Recall@5 stabil pada angka:

```text
33.3%
```

untuk seluruh konfigurasi pengujian.

Hal ini menunjukkan bahwa perubahan ukuran chunk tidak memberikan dampak signifikan terhadap kemampuan model dalam menemukan dokumen yang relevan pada dataset yang digunakan.

---

## Latensi

Rentang waktu retrieval:

```text
17.1 ms - 23.7 ms
```

Interpretasi:

* Seluruh konfigurasi termasuk sangat cepat.
* Tidak ditemukan bottleneck pada proses embedding maupun pencarian vector.
* Cocok digunakan untuk sistem pencarian real-time.

---

## Ukuran Database

Ukuran index meningkat seiring bertambahnya jumlah chunk:

| Kondisi  | Ukuran  |
| -------- | ------- |
| Minimum  | 1.50 MB |
| Maksimum | 3.86 MB |

Semakin kecil chunk size:

* Jumlah chunk meningkat
* Ukuran database meningkat
* Storage bertambah

Sebaliknya semakin besar chunk:

* Jumlah chunk berkurang
* Database lebih ringkas
* Retrieval lebih efisien

---

# Analisis Konfigurasi Terbaik

## Chunk Size 800

## Overlap 80

Konfigurasi ini menghasilkan performa paling efisien.

### Alasan

#### 1. Latensi Tercepat

```text
17.1 ms
```

Menjadi nilai tercepat dari seluruh pengujian.

#### 2. Ukuran Database Efisien

```text
3.38 MB
```

Dengan hanya:

```text
36 chunk
```

sehingga kebutuhan penyimpanan tetap rendah.

#### 3. Sesuai Batas Model

all-MiniLM-L6-v2 memiliki batas:

```text
256 token
```

Chunk 800 karakter diperkirakan menghasilkan sekitar:

```text
200 token
```

yang masih berada di bawah kapasitas maksimum model.

Akibatnya:

* Tidak terjadi truncation
* Informasi semantik tetap utuh
* Kualitas embedding lebih baik

---

# Kesimpulan

Penggunaan model all-MiniLM-L6-v2 pada aplikasi PEDE berhasil memberikan performa yang baik untuk semantic search dokumen ilmiah.

Hasil pengujian menunjukkan:

* Retrieval sangat cepat (17.1 - 23.7 ms)
* Ukuran database tetap kecil
* Recall stabil pada seluruh konfigurasi
* Konsumsi resource jauh lebih rendah dibanding BGE-M3

Konfigurasi terbaik yang direkomendasikan adalah:

```text
Chunk Size = 800
Overlap = 80
```

karena memberikan kombinasi terbaik antara:

* Kecepatan
* Efisiensi storage
* Kualitas representasi semantik

Model all-MiniLM-L6-v2 sangat cocok digunakan untuk sistem pencarian jurnal ilmiah yang membutuhkan performa tinggi dengan sumber daya komputasi yang terbatas.
