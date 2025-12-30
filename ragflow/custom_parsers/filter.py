#
#  Simplified Financial Document Filter for RagFlow
#  ~100 lines instead of 900
#
#  Usage: Import and apply to any RagFlow parser output
#

import hashlib
import re
import json
from pathlib import Path
from typing import List, Dict, Set

# =============================================================================
# CONFIGURATION (edit these)
# =============================================================================

# Sections to skip (regex patterns)
SKIP_PATTERNS = [
    r"forward[\-\s]*looking",
    r"safe\s+harbor",
    r"risk\s+factors",
    r"legal\s+proceedings",
    r"certifications?",
    r"signatures?$",
    r"exhibits?\s+and\s+financial",
]

# Boilerplate phrases (if 2+ match, skip the chunk)
BOILERPLATE = [
    r"pursuant\s+to\s+section",
    r"incorporated\s+by\s+reference",
    r"securities\s+and\s+exchange\s+commission",
]

# Dedup index file (simple JSON)
DEDUP_INDEX = Path("/tmp/ragflow_dedup.json")

# =============================================================================
# CORE FUNCTIONS (~50 lines)
# =============================================================================

def should_skip(text: str) -> bool:
    """Check if text matches skip patterns or is boilerplate."""
    text_lower = text.lower()
    
    # Check section patterns
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    
    # Check boilerplate (need 2+ matches)
    matches = sum(1 for p in BOILERPLATE if re.search(p, text_lower))
    return matches >= 2


def get_hash(text: str) -> str:
    """Simple content hash."""
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def load_dedup_index() -> Set[str]:
    """Load existing hashes from disk."""
    if DEDUP_INDEX.exists():
        try:
            return set(json.loads(DEDUP_INDEX.read_text()))
        except:
            pass
    return set()


def save_dedup_index(hashes: Set[str]):
    """Save hashes to disk."""
    DEDUP_INDEX.write_text(json.dumps(list(hashes)))


def is_duplicate(text: str, seen: Set[str]) -> bool:
    """Check if text is a duplicate."""
    h = get_hash(text)
    if h in seen:
        return True
    seen.add(h)
    return False


# =============================================================================
# MAIN FILTER FUNCTION
# =============================================================================

def filter_chunks(chunks: List[Dict], source: str = "") -> List[Dict]:
    """
    Filter chunks by:
    1. Removing skipped sections (Risk Factors, etc.)
    2. Removing boilerplate text
    3. Removing duplicates
    
    Args:
        chunks: List of RagFlow chunk dicts (must have 'content_with_weight' or 'content')
        source: Optional source identifier for logging
    
    Returns:
        Filtered list of chunks
    """
    seen = load_dedup_index()
    filtered = []
    stats = {"skipped": 0, "boilerplate": 0, "duplicate": 0, "kept": 0}
    
    for chunk in chunks:
        text = chunk.get('content_with_weight', '') or chunk.get('content', '')
        
        if not text or len(text) < 50:
            continue
        
        if should_skip(text):
            stats["skipped"] += 1
            continue
        
        if is_duplicate(text, seen):
            stats["duplicate"] += 1
            continue
        
        stats["kept"] += 1
        filtered.append(chunk)
    
    save_dedup_index(seen)
    
    print(f"[filter] {source}: kept={stats['kept']}, skipped={stats['skipped']}, "
          f"boilerplate={stats['boilerplate']}, duplicate={stats['duplicate']}")
    
    return filtered


def clear_dedup_index():
    """Clear the dedup index (call when you want to re-ingest everything)."""
    if DEDUP_INDEX.exists():
        DEDUP_INDEX.unlink()
        print(f"Cleared dedup index: {DEDUP_INDEX}")


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Test with sample chunks
    test_chunks = [
        {"content": "The Simple Moving Average (SMA) is calculated by averaging prices."},
        {"content": "Forward-looking statements in this report are subject to risks."},
        {"content": "The simple moving average is computed by averaging prices."},  # Duplicate
        {"content": "Revenue increased 15% year over year to $50 billion."},
    ]
    
    result = filter_chunks(test_chunks, source="test")
    print(f"\nKept {len(result)} of {len(test_chunks)} chunks")
    for c in result:
        print(f"  - {c['content'][:60]}...")
