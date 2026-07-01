"""Test script for hybrid RAG retrieval system."""

import logging
from pathlib import Path

from src.rag import build_hybrid_retriever

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Load policy
POLICIES_DIR = Path(__file__).resolve().parent / "data" / "policies"
policy_text = (POLICIES_DIR / "NCD_150.3.txt").read_text(encoding="utf-8")

print("\n" + "=" * 80)
print("TESTING HYBRID RAG RETRIEVAL")
print("=" * 80)

# Build hybrid retriever
print("\nBuilding hybrid retriever...")
retriever = build_hybrid_retriever(
    policy_text,
    doc_id="NCD_150.3",
    chunk_size=512,
    overlap=128,
    cache_dir=Path("data/rag_cache"),
)

# Test queries
test_queries = [
    "frequency limit months coverage",
    "HCPCS procedure codes bone mass measurement",
    "eligible beneficiaries conditions",
    "23 months screening",
]

for query in test_queries:
    print("\n" + "-" * 80)
    print(f"Query: {query}")
    print("-" * 80)
    
    chunks, metrics = retriever.retrieve_with_context(
        query,
        top_k=3,
        retrieval_k=10,
    )
    
    print(f"\nMetrics:")
    print(f"  Chunks: {metrics['num_results']}")
    print(f"  Top score: {metrics['top_score']:.3f}")
    print(f"  Mean score: {metrics['mean_score']:.3f}")
    print(f"  Unique sections: {metrics['unique_sections']}")
    
    print(f"\nTop {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks, 1):
        print(f"\n{i}. Section: {chunk.section or 'Unknown'}")
        print(f"   Position: chars {chunk.start_char}-{chunk.end_char}")
        print(f"   Text: {chunk.text[:200]}...")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
