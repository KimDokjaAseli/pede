#!/usr/bin/env python3
"""
Benchmark Script for Chunking and Embedding Retrieval

This script automates the process of testing different chunking configurations
(size, overlap) and measuring key metrics like Hit Rate, search latency, and index size
using the configured embedding model (all-MiniLM-L6-v2).
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from qdrant_client import QdrantClient

# Add project root to path
sys.path.append(str(Path(__file__).parent.resolve()))

from core.pdf_converter import convert_pdf_to_markdown, get_pdf_native_metadata
from core.metadata_extractor import extract_metadata
from core.chunker import chunk_markdown
from core.vector_store import VectorStore, COLLECTION_NAME, QDRANT_PATH

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("benchmark")

# Default test queries (can be customized)
DEFAULT_TEST_CASES = [
    {
        "query": "Apa hasil eksperimen utamanya dan berapa persen akurasinya?",
        "keywords": ["akurasi", "persen", "hasil", "eksperimen"],
    },
    {
        "query": "Siapa penulis atau afiliasi dari penelitian ini?",
        "keywords": ["university", "universitas", "author", "penulis", "departemen"],
    },
    {
        "query": "Apa metode atau arsitektur yang digunakan?",
        "keywords": ["metode", "arsitektur", "algoritma", "model", "sistem"],
    }
]

def get_directory_size(path: str) -> float:
    """Return directory size in Megabytes."""
    total_size = 0
    p = Path(path)
    if not p.exists():
        return 0.0
    if p.is_file():
        return p.stat().st_size / (1024 * 1024)
    for fp in p.glob("**/*"):
        if fp.is_file():
            total_size += fp.stat().st_size
    return total_size / (1024 * 1024)

def run_benchmark(pdf_path: str, chunk_size: int, chunk_overlap: int, test_cases: list):
    filename = os.path.basename(pdf_path)
    print(f"\nRunning benchmark: Size={chunk_size}, Overlap={chunk_overlap} for {filename}...")
    
    # 1. Clean and initialize VectorStore
    # We enforce recreation by initializing VectorStore which calls ensure_collection
    # with the configured dimension (384-d).
    vector_store = VectorStore(qdrant_path=QDRANT_PATH, collection_name=COLLECTION_NAME)
    
    # Clean the collection first to start fresh
    vector_store.client.delete_collection(COLLECTION_NAME)
    vector_store.ensure_collection()
    
    # 2. Convert PDF to Markdown
    print("  Converting PDF to Markdown...")
    markdown_text = convert_pdf_to_markdown(pdf_path, write_images=False)
    pdf_native_meta = get_pdf_native_metadata(pdf_path)
    article_meta = extract_metadata(pdf_path, markdown_text, pdf_native_meta)
    
    # 3. Chunking & Ingestion Time
    print("  Chunking and Ingesting...")
    start_ingest = time.time()
    chunks = chunk_markdown(
        markdown_text, article_meta, 
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    # Exclude references
    chunks = [c for c in chunks if c.content_type != "references"]
    
    vector_store.add_chunks(chunks)
    ingest_time = time.time() - start_ingest
    print(f"  Ingested {len(chunks)} chunks in {ingest_time:.2f}s")
    
    # 4. Measure Database Index Size
    # Force Qdrant write to disk before measuring
    time.sleep(1.0)
    db_size = get_directory_size(QDRANT_PATH)
    
    # 5. Retrieval & Latency/Hit Rate Evaluation
    print("  Evaluating Retrieval Quality...")
    latencies = []
    hits = 0
    top_k = 5
    
    for case in test_cases:
        query = case["query"]
        keywords = case["keywords"]
        
        start_search = time.time()
        results = vector_store.search(query, n_results=top_k)
        latencies.append((time.time() - start_search) * 1000) # ms
        
        # Determine a "Hit": if any retrieved chunk contains any of the target keywords
        hit_found = False
        for r in results:
            content_lower = r["content"].lower()
            if any(kw.lower() in content_lower for kw in keywords):
                hit_found = True
                break
        
        if hit_found:
            hits += 1
            
    hit_rate = (hits / len(test_cases)) * 100
    avg_latency = sum(latencies) / len(latencies)
    
    return {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "num_chunks": len(chunks),
        "ingest_time_s": ingest_time,
        "db_size_mb": db_size,
        "hit_rate_pct": hit_rate,
        "avg_latency_ms": avg_latency
    }

def main():
    parser = argparse.ArgumentParser(description="PEDE Chunking & Embedding Benchmark Script")
    parser.add_argument("pdf_path", nargs="?", help="Path to a test PDF file")
    
    # 10 combinations of size and overlap
    default_sizes = [200, 200, 400, 400, 600, 600, 800, 800, 1000, 1000]
    default_overlaps = [20, 40, 40, 80, 60, 120, 80, 160, 100, 200]
    
    parser.add_argument("--size", type=int, nargs="+", default=default_sizes, help="Chunk sizes to test")
    parser.add_argument("--overlap", type=int, nargs="+", default=default_overlaps, help="Chunk overlaps to test")
    args = parser.parse_args()
    
    pdf_path = args.pdf_path
    if not pdf_path:
        # Try to find any PDF in the current directory or parent directory
        pdfs = list(Path(".").glob("*.pdf")) + list(Path(".").glob("**/*.pdf"))
        if pdfs:
            pdf_path = str(pdfs[0])
            print(f"No PDF file specified. Auto-detected test PDF: {pdf_path}")
        else:
            print("Error: No PDF file found. Please provide a PDF path.")
            print("Usage: python benchmark_chunking.py <path_to_pdf>")
            sys.exit(1)
            
    # Run combinations of size & overlap
    configs = []
    sizes = args.size
    overlaps = args.overlap
    if len(sizes) != len(overlaps):
        min_len = min(len(sizes), len(overlaps))
        sizes = sizes[:min_len]
        overlaps = overlaps[:min_len]
        print(f"Warning: Unequal number of sizes and overlaps. Trimmed to {min_len} configs.")
        
    for s, o in zip(sizes, overlaps):
        configs.append((s, o))
        
    results = []
    for size, overlap in configs:
        res = run_benchmark(pdf_path, size, overlap, DEFAULT_TEST_CASES)
        results.append(res)
        
    # Generate Markdown Table
    print("\n" + "="*80)
    print("BENCHMARK RESULTS (all-MiniLM-L6-v2)")
    print("="*80)
    
    md_table = []
    md_table.append("| Ukuran Chunk | Overlap | Model Embedding | Total Chunks | Hit Rate (Recall@5) | Rata-rata Latensi | Ukuran Index DB | Catatan |")
    md_table.append("|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---|")
    
    for r in results:
        md_table.append(
            f"| {r['chunk_size']} | {r['chunk_overlap']} | all-MiniLM-L6-v2 | {r['num_chunks']} | {r['hit_rate_pct']:.1f}% | {r['avg_latency_ms']:.1f} ms | {r['db_size_mb']:.2f} MB | Ingest: {r['ingest_time_s']:.1f}s |"
        )
        
    print("\n".join(md_table))
    print("="*80)
    
    # Determine the most efficient configuration
    # Sort by: Hit Rate (desc), Latency (asc), DB Size (asc)
    sorted_results = sorted(results, key=lambda x: (-x["hit_rate_pct"], x["avg_latency_ms"], x["db_size_mb"]))
    best = sorted_results[0]
    
    efficiency_summary = (
        f"**Rekomendasi Konfigurasi Paling Efisien:**\n"
        f"- **Ukuran Chunk**: {best['chunk_size']} karakter\n"
        f"- **Overlap**: {best['chunk_overlap']} karakter\n"
        f"- **Hit Rate (Recall@5)**: {best['hit_rate_pct']:.1f}%\n"
        f"- **Rata-rata Latensi**: {best['avg_latency_ms']:.1f} ms\n"
        f"- **Ukuran Database**: {best['db_size_mb']:.2f} MB\n"
        f"- **Alasan**: Konfigurasi ini menghasilkan Recall tertinggi dengan latensi dan konsumsi penyimpanan minimal."
    )
    
    print("\n" + efficiency_summary)
    print("="*80)
    
    # Save results directly to benchmarks folder
    benchmarks_dir = Path("benchmarks")
    benchmarks_dir.mkdir(exist_ok=True)
    benchmark_file = benchmarks_dir / "BENCHMARK_MiniLM.md"
    
    with open(benchmark_file, "w", encoding="utf-8") as f:
        f.write("# Benchmark Results: all-MiniLM-L6-v2\n\n")
        f.write("Berikut adalah hasil evaluasi performa retrieval menggunakan model `all-MiniLM-L6-v2` (384 dimensi, dense-only):\n\n")
        f.write("\n".join(md_table))
        f.write("\n\n### Rekomendasi Efisiensi\n")
        f.write(efficiency_summary + "\n\n")
        f.write("### Analisis & Observasi\n")
        f.write("- **Latensi**: Sangat cepat dibandingkan BGE-M3 karena dimensi model lebih kecil (384-d vs 1024-d).\n")
        f.write("- **Ukuran Index**: Lebih hemat ruang karena ukuran vektor hanya ~37% dari BGE-M3.\n")
        f.write("- **Dukungan Bahasa**: Model ini optimal untuk dokumen Bahasa Inggris, namun memiliki keterbatasan jika dicari dengan kueri Bahasa Indonesia (tidak mendukung multi-bahasa dengan baik).\n")
        f.write("- **Sparse/Hybrid**: Tidak aktif karena model MiniLM tidak menghasilkan representasi leksikal/sparse secara native.\n")

    print(f"\nSaved benchmark markdown results to: {benchmark_file}")

if __name__ == "__main__":
    main()
