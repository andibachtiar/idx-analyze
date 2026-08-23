#!/usr/bin/env python3
"""Quick diagnostic script."""
import sys

sys.path.insert(0, '/var/www/idx-scraper/python')

# Test 1: Check search_documents import
print("Test 1: Import search_documents")
try:
    from ai.vector import search_documents
    print("  OK: search_documents imported successfully")
except Exception as e:
    print(f"  FAIL: {e}")

# Test 2: Check chunk_text overlap
print("\nTest 2: chunk_text overlap")
try:
    from ai.vector import DocumentProcessor
    text = "A B C D E F G H I J K L M N O P"
    chunks = DocumentProcessor.chunk_text(text, chunk_size=10, overlap=5)
    print(f"  Text length: {len(text)}")
    print(f"  Number of chunks: {len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"  Chunk {i}: start={c['start']}, end={c['end']}, content='{c['content']}'")

    if len(chunks) >= 2:
        overlap_ok = chunks[0]["end"] > chunks[1]["start"]
        print(f"  Overlap check: chunks[0]['end'] ({chunks[0]['end']}) > chunks[1]['start'] ({chunks[1]['start']}) = {overlap_ok}")
except Exception as e:
    print(f"  FAIL: {e}")

# Test 3: Check memory report saving
print("\nTest 3: Memory report saving")
try:
    import tempfile

    from ai.memory import ResearchMemory
    with tempfile.TemporaryDirectory() as tmpdir:
        memory = ResearchMemory(storage_path=tmpdir)
        fp1 = memory.save_report("BBCA", {"test": 1}, question="Q1")
        fp2 = memory.save_report("BBCA", {"test": 2}, question="Q2")
        print(f"  File 1: {fp1}")
        print(f"  File 2: {fp2}")
        reports = memory.get_reports_for_ticker("BBCA")
        print(f"  Reports found: {len(reports)}")
        for r in reports:
            print(f"    - {r.get('question')}")
except Exception as e:
    print(f"  FAIL: {e}")

print("\nDone!")
