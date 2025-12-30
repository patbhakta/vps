#
#  Minimal Chunk Deduplicator (~30 lines)
#
#  Usage:
#    from custom_parsers.dedup import is_seen, mark_seen
#    
#    for chunk in chunks:
#        if is_seen(chunk["content"]):
#            continue  # skip
#        mark_seen(chunk["content"])
#        # ... process chunk
#

import hashlib
import json
from pathlib import Path

INDEX_FILE = Path("/tmp/ragflow_seen.json")

def _hash(text: str) -> str:
    """Normalize and hash text."""
    clean = ' '.join(text.lower().split())  # normalize whitespace
    return hashlib.md5(clean.encode()).hexdigest()[:12]

def _load() -> set:
    if INDEX_FILE.exists():
        return set(json.loads(INDEX_FILE.read_text()))
    return set()

def _save(seen: set):
    INDEX_FILE.write_text(json.dumps(list(seen)))

def is_seen(text: str) -> bool:
    """Check if this text (or very similar) was already seen."""
    return _hash(text) in _load()

def mark_seen(text: str):
    """Mark text as seen for future checks."""
    seen = _load()
    seen.add(_hash(text))
    _save(seen)

def clear():
    """Clear all seen hashes (fresh start)."""
    if INDEX_FILE.exists():
        INDEX_FILE.unlink()
