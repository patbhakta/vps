#
#  Phase 3: Fuzzy Dedup with MinHash (~80 lines)
#  Catches near-duplicates like "SMA is calculated by..." vs "The SMA is computed by..."
#
#  Requires: pip install datasketch
#
#  Usage:
#    from custom_parsers.fuzzy_dedup import FuzzyDedup
#    
#    dedup = FuzzyDedup(threshold=0.8)
#    for chunk in chunks:
#        if dedup.is_similar(chunk["content"]):
#            continue
#        dedup.add(chunk["content"])
#        # ... process chunk
#

import json
from pathlib import Path

try:
    from datasketch import MinHash, MinHashLSH
    HAS_MINHASH = True
except ImportError:
    HAS_MINHASH = False
    print("Install datasketch for fuzzy matching: pip install datasketch")

# =============================================================================
# FUZZY DEDUP CLASS
# =============================================================================

class FuzzyDedup:
    """
    Fuzzy deduplication using MinHash LSH.
    
    Args:
        threshold: Similarity threshold (0.0-1.0). Higher = stricter matching.
                   0.8 means ~80% similar text is considered duplicate.
        num_perm: Number of permutations. Higher = more accurate, slower.
    """
    
    def __init__(self, threshold: float = 0.8, num_perm: int = 128):
        if not HAS_MINHASH:
            raise ImportError("pip install datasketch")
        
        self.threshold = threshold
        self.num_perm = num_perm
        self.lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
        self.counter = 0
    
    def _make_minhash(self, text: str) -> MinHash:
        """Create MinHash from text using 3-word shingles."""
        m = MinHash(num_perm=self.num_perm)
        words = text.lower().split()
        
        # Create 3-word shingles
        for i in range(max(1, len(words) - 2)):
            shingle = ' '.join(words[i:i+3])
            m.update(shingle.encode('utf-8'))
        
        return m
    
    def is_similar(self, text: str) -> bool:
        """Check if text is similar to something already seen."""
        if len(text) < 50:
            return False
        
        minhash = self._make_minhash(text)
        matches = self.lsh.query(minhash)
        return len(matches) > 0
    
    def add(self, text: str) -> str:
        """Add text to the index. Returns the assigned ID."""
        if len(text) < 50:
            return ""
        
        self.counter += 1
        doc_id = f"doc_{self.counter}"
        minhash = self._make_minhash(text)
        self.lsh.insert(doc_id, minhash)
        return doc_id
    
    def check_and_add(self, text: str) -> tuple:
        """
        Check if similar exists, add if not.
        Returns: (is_duplicate: bool, doc_id: str or None)
        """
        if self.is_similar(text):
            return True, None
        doc_id = self.add(text)
        return False, doc_id


# =============================================================================
# SIMPLE USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    dedup = FuzzyDedup(threshold=0.8)
    
    texts = [
        "The Simple Moving Average (SMA) is calculated by taking the average of prices.",
        "A simple moving average is computed by averaging the closing prices.",  # Similar!
        "The RSI indicator measures overbought and oversold conditions.",
        "Quarterly revenue increased 15% to reach $50 billion.",
    ]
    
    for text in texts:
        is_dup, doc_id = dedup.check_and_add(text)
        status = "SKIP (similar)" if is_dup else f"ADD ({doc_id})"
        print(f"{status}: {text[:50]}...")
