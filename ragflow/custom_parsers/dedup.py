#
#  Deduplication Layer for RagFlow Custom Parsers
#  
#  Uses MinHash LSH for fuzzy matching to detect:
#  - Duplicate content across documents
#  - Similar concepts that should reference canonical entries
#  - Boilerplate text that appears in multiple sources
#
#  Requires: pip install datasketch redis
#

import hashlib
import json
import logging
import os
import pickle
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime

# Try to import datasketch, provide fallback
try:
    from datasketch import MinHash, MinHashLSH
    HAS_DATASKETCH = True
except ImportError:
    HAS_DATASKETCH = False
    logging.warning("datasketch not installed. Using simple hash-based dedup.")

# Try to import redis for persistent storage
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class DedupConfig:
    """Configuration for deduplication behavior."""
    
    # Similarity threshold (0.0 - 1.0)
    # Higher = stricter matching (fewer false positives)
    similarity_threshold: float = 0.85
    
    # Number of permutations for MinHash (higher = more accurate, slower)
    num_perm: int = 128
    
    # Minimum text length to consider for dedup
    min_text_length: int = 50
    
    # Redis connection (if available)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 1
    redis_password: Optional[str] = None
    
    # Local file-based fallback storage
    local_storage_path: str = "/tmp/ragflow_dedup_index.pkl"
    
    # Canonical concepts file
    canonical_concepts_path: Optional[str] = None


@dataclass
class DedupResult:
    """Result of a deduplication check."""
    is_duplicate: bool
    similarity_score: float = 0.0
    matched_id: Optional[str] = None
    matched_source: Optional[str] = None
    action: str = "ingest"  # "ingest", "skip", "reference"


# =============================================================================
# CONCEPT NORMALIZATION
# =============================================================================

# Financial/Trading domain canonical terms
CANONICAL_TERMS = {
    # Moving Averages
    r"simple\s+moving\s+average": "SMA",
    r"exponential\s+moving\s+average": "EMA",
    r"weighted\s+moving\s+average": "WMA",
    r"moving\s+average\s+convergence\s+divergence": "MACD",
    
    # Indicators
    r"relative\s+strength\s+index": "RSI",
    r"bollinger\s+bands?": "Bollinger Bands",
    r"fibonacci\s+retracement": "Fibonacci Retracement",
    r"average\s+true\s+range": "ATR",
    r"on[\-\s]?balance\s+volume": "OBV",
    
    # Financial Statements
    r"balance\s+sheet": "Balance Sheet",
    r"income\s+statement": "Income Statement",
    r"cash\s+flow\s+statement": "Cash Flow Statement",
    r"statement\s+of\s+stockholders[\'\s]?\s*equity": "Equity Statement",
    
    # Ratios
    r"price[\-\s]?to[\-\s]?earnings(\s+ratio)?": "P/E Ratio",
    r"price[\-\s]?to[\-\s]?book(\s+ratio)?": "P/B Ratio",
    r"debt[\-\s]?to[\-\s]?equity(\s+ratio)?": "D/E Ratio",
    r"return\s+on\s+equity": "ROE",
    r"return\s+on\s+assets?": "ROA",
    r"earnings\s+per\s+share": "EPS",
    
    # SEC Terms
    r"form\s+10[\-\s]?k": "Form 10-K",
    r"form\s+10[\-\s]?q": "Form 10-Q",
    r"form\s+8[\-\s]?k": "Form 8-K",
    r"management[\'\s]?s?\s+discussion\s+and\s+analysis": "MD&A",
}


def normalize_text(text: str) -> str:
    """
    Normalize text by replacing common terms with canonical versions.
    This helps with deduplication by making similar content match.
    """
    normalized = text.lower()
    
    for pattern, canonical in CANONICAL_TERMS.items():
        normalized = re.sub(pattern, canonical.lower(), normalized, flags=re.IGNORECASE)
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized


def extract_shingles(text: str, k: int = 3) -> Set[str]:
    """
    Extract k-shingles (word n-grams) from text.
    Used for MinHash computation.
    """
    words = text.split()
    if len(words) < k:
        return {text}
    
    shingles = set()
    for i in range(len(words) - k + 1):
        shingle = ' '.join(words[i:i+k])
        shingles.add(shingle)
    
    return shingles


# =============================================================================
# SIMPLE HASH-BASED DEDUPLICATION (Fallback)
# =============================================================================

class SimpleDeduplicator:
    """
    Simple hash-based deduplicator for when datasketch is not available.
    Uses content hash for exact matching and normalized hash for fuzzy.
    """
    
    def __init__(self, config: DedupConfig):
        self.config = config
        self.exact_hashes: Dict[str, str] = {}  # hash -> doc_id
        self.normalized_hashes: Dict[str, str] = {}  # normalized_hash -> doc_id
        self._load_index()
    
    def _compute_hash(self, text: str) -> str:
        """Compute SHA256 hash of text."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    
    def _load_index(self):
        """Load index from disk if available."""
        path = Path(self.config.local_storage_path)
        if path.exists():
            try:
                with open(path, 'rb') as f:
                    data = pickle.load(f)
                    self.exact_hashes = data.get('exact', {})
                    self.normalized_hashes = data.get('normalized', {})
                logging.info(f"Loaded dedup index: {len(self.exact_hashes)} entries")
            except Exception as e:
                logging.warning(f"Failed to load dedup index: {e}")
    
    def _save_index(self):
        """Save index to disk."""
        path = Path(self.config.local_storage_path)
        try:
            with open(path, 'wb') as f:
                pickle.dump({
                    'exact': self.exact_hashes,
                    'normalized': self.normalized_hashes,
                }, f)
        except Exception as e:
            logging.warning(f"Failed to save dedup index: {e}")
    
    def check(self, text: str, doc_id: str, source: str = "") -> DedupResult:
        """Check if text is a duplicate."""
        if len(text) < self.config.min_text_length:
            return DedupResult(is_duplicate=False, action="ingest")
        
        # Check exact match
        exact_hash = self._compute_hash(text)
        if exact_hash in self.exact_hashes:
            return DedupResult(
                is_duplicate=True,
                similarity_score=1.0,
                matched_id=self.exact_hashes[exact_hash],
                action="skip"
            )
        
        # Check normalized match
        normalized = normalize_text(text)
        norm_hash = self._compute_hash(normalized)
        if norm_hash in self.normalized_hashes:
            return DedupResult(
                is_duplicate=True,
                similarity_score=0.95,
                matched_id=self.normalized_hashes[norm_hash],
                action="reference"
            )
        
        return DedupResult(is_duplicate=False, action="ingest")
    
    def add(self, text: str, doc_id: str, source: str = ""):
        """Add text to the dedup index."""
        if len(text) < self.config.min_text_length:
            return
        
        exact_hash = self._compute_hash(text)
        self.exact_hashes[exact_hash] = doc_id
        
        normalized = normalize_text(text)
        norm_hash = self._compute_hash(normalized)
        self.normalized_hashes[norm_hash] = doc_id
        
        self._save_index()


# =============================================================================
# MINHASH LSH DEDUPLICATION (Production)
# =============================================================================

class MinHashDeduplicator:
    """
    Production-grade deduplicator using MinHash LSH.
    Supports fuzzy matching and can detect similar but not identical content.
    """
    
    def __init__(self, config: DedupConfig):
        if not HAS_DATASKETCH:
            raise ImportError("datasketch required for MinHashDeduplicator")
        
        self.config = config
        self.lsh = MinHashLSH(
            threshold=config.similarity_threshold,
            num_perm=config.num_perm
        )
        self.minhashes: Dict[str, MinHash] = {}
        self.metadata: Dict[str, Dict] = {}  # doc_id -> {source, timestamp, text_preview}
        
        self._load_index()
    
    def _compute_minhash(self, text: str) -> MinHash:
        """Compute MinHash for text."""
        normalized = normalize_text(text)
        shingles = extract_shingles(normalized)
        
        m = MinHash(num_perm=self.config.num_perm)
        for shingle in shingles:
            m.update(shingle.encode('utf-8'))
        
        return m
    
    def _load_index(self):
        """Load index from Redis or disk."""
        if HAS_REDIS and self.config.redis_host:
            try:
                r = redis.Redis(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    db=self.config.redis_db,
                    password=self.config.redis_password
                )
                data = r.get('ragflow:dedup:index')
                if data:
                    loaded = pickle.loads(data)
                    self.minhashes = loaded.get('minhashes', {})
                    self.metadata = loaded.get('metadata', {})
                    # Rebuild LSH from stored minhashes
                    for doc_id, mh in self.minhashes.items():
                        self.lsh.insert(doc_id, mh)
                    logging.info(f"Loaded dedup index from Redis: {len(self.minhashes)} entries")
                return
            except Exception as e:
                logging.warning(f"Redis unavailable, falling back to disk: {e}")
        
        # Fall back to disk
        path = Path(self.config.local_storage_path.replace('.pkl', '_minhash.pkl'))
        if path.exists():
            try:
                with open(path, 'rb') as f:
                    loaded = pickle.load(f)
                    self.minhashes = loaded.get('minhashes', {})
                    self.metadata = loaded.get('metadata', {})
                    for doc_id, mh in self.minhashes.items():
                        self.lsh.insert(doc_id, mh)
                    logging.info(f"Loaded dedup index from disk: {len(self.minhashes)} entries")
            except Exception as e:
                logging.warning(f"Failed to load dedup index: {e}")
    
    def _save_index(self):
        """Save index to Redis or disk."""
        data = {
            'minhashes': self.minhashes,
            'metadata': self.metadata,
        }
        
        if HAS_REDIS and self.config.redis_host:
            try:
                r = redis.Redis(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    db=self.config.redis_db,
                    password=self.config.redis_password
                )
                r.set('ragflow:dedup:index', pickle.dumps(data))
                return
            except Exception as e:
                logging.warning(f"Redis save failed, falling back to disk: {e}")
        
        # Fall back to disk
        path = Path(self.config.local_storage_path.replace('.pkl', '_minhash.pkl'))
        try:
            with open(path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            logging.warning(f"Failed to save dedup index: {e}")
    
    def check(self, text: str, doc_id: str, source: str = "") -> DedupResult:
        """
        Check if text is a duplicate or near-duplicate.
        Returns DedupResult with action recommendation.
        """
        if len(text) < self.config.min_text_length:
            return DedupResult(is_duplicate=False, action="ingest")
        
        minhash = self._compute_minhash(text)
        
        # Query LSH for similar documents
        matches = self.lsh.query(minhash)
        
        if not matches:
            return DedupResult(is_duplicate=False, action="ingest")
        
        # Find the best match
        best_match = None
        best_score = 0.0
        
        for match_id in matches:
            if match_id in self.minhashes:
                score = minhash.jaccard(self.minhashes[match_id])
                if score > best_score:
                    best_score = score
                    best_match = match_id
        
        if best_match and best_score >= self.config.similarity_threshold:
            meta = self.metadata.get(best_match, {})
            
            # Determine action based on similarity
            if best_score > 0.95:
                action = "skip"  # Near-exact duplicate
            else:
                action = "reference"  # Similar, but add with reference
            
            return DedupResult(
                is_duplicate=True,
                similarity_score=best_score,
                matched_id=best_match,
                matched_source=meta.get('source', ''),
                action=action
            )
        
        return DedupResult(is_duplicate=False, action="ingest")
    
    def add(self, text: str, doc_id: str, source: str = ""):
        """Add text to the dedup index."""
        if len(text) < self.config.min_text_length:
            return
        
        minhash = self._compute_minhash(text)
        
        # Store in LSH
        try:
            self.lsh.insert(doc_id, minhash)
        except ValueError:
            # Already exists, update
            pass
        
        self.minhashes[doc_id] = minhash
        self.metadata[doc_id] = {
            'source': source,
            'timestamp': datetime.now().isoformat(),
            'text_preview': text[:100],
        }
        
        self._save_index()
    
    def remove(self, doc_id: str):
        """Remove a document from the dedup index."""
        if doc_id in self.minhashes:
            try:
                self.lsh.remove(doc_id)
            except KeyError:
                pass
            del self.minhashes[doc_id]
            self.metadata.pop(doc_id, None)
            self._save_index()
    
    def get_stats(self) -> Dict:
        """Get statistics about the dedup index."""
        return {
            'total_entries': len(self.minhashes),
            'threshold': self.config.similarity_threshold,
            'storage': 'redis' if HAS_REDIS else 'disk',
        }


# =============================================================================
# UNIFIED DEDUPLICATOR INTERFACE
# =============================================================================

class Deduplicator:
    """
    Unified deduplication interface.
    Automatically selects the best available implementation.
    """
    
    def __init__(self, config: Optional[DedupConfig] = None):
        self.config = config or DedupConfig()
        
        if HAS_DATASKETCH:
            logging.info("Using MinHash LSH deduplicator")
            self._impl = MinHashDeduplicator(self.config)
        else:
            logging.info("Using simple hash deduplicator (install datasketch for better results)")
            self._impl = SimpleDeduplicator(self.config)
    
    def check(self, text: str, doc_id: str, source: str = "") -> DedupResult:
        """Check if text is a duplicate."""
        return self._impl.check(text, doc_id, source)
    
    def add(self, text: str, doc_id: str, source: str = ""):
        """Add text to the index."""
        self._impl.add(text, doc_id, source)
    
    def check_and_add(self, text: str, doc_id: str, source: str = "") -> DedupResult:
        """Check for duplicates and add if not a duplicate."""
        result = self.check(text, doc_id, source)
        if not result.is_duplicate:
            self.add(text, doc_id, source)
        return result
    
    def remove(self, doc_id: str):
        """Remove a document from the index."""
        if hasattr(self._impl, 'remove'):
            self._impl.remove(doc_id)
    
    def get_stats(self) -> Dict:
        """Get index statistics."""
        if hasattr(self._impl, 'get_stats'):
            return self._impl.get_stats()
        return {}


# =============================================================================
# INTEGRATION WITH RAGFLOW PARSER
# =============================================================================

# Global deduplicator instance (initialized on first use)
_global_dedup: Optional[Deduplicator] = None


def get_deduplicator(config: Optional[DedupConfig] = None) -> Deduplicator:
    """Get or create the global deduplicator instance."""
    global _global_dedup
    if _global_dedup is None:
        _global_dedup = Deduplicator(config)
    return _global_dedup


def deduplicate_chunks(chunks: List[Dict], source: str = "") -> List[Dict]:
    """
    Filter a list of chunks, removing duplicates.
    Adds 'dedup_action' and 'dedup_ref' to each chunk.
    """
    dedup = get_deduplicator()
    filtered = []
    
    for i, chunk in enumerate(chunks):
        text = chunk.get('content_with_weight', '') or chunk.get('content', '')
        doc_id = f"{source}_{i}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
        
        result = dedup.check_and_add(text, doc_id, source)
        
        chunk['dedup_action'] = result.action
        chunk['dedup_score'] = result.similarity_score
        
        if result.action == "skip":
            logging.debug(f"Skipping duplicate chunk (score={result.similarity_score:.2f})")
            continue
        elif result.action == "reference":
            chunk['dedup_ref'] = result.matched_id
            logging.debug(f"Adding chunk with reference to {result.matched_id}")
        
        filtered.append(chunk)
    
    logging.info(f"Deduplication: {len(chunks)} -> {len(filtered)} chunks ({len(chunks) - len(filtered)} duplicates removed)")
    return filtered


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Test the deduplicator
    config = DedupConfig(similarity_threshold=0.8)
    dedup = Deduplicator(config)
    
    # Test texts
    texts = [
        "The Simple Moving Average (SMA) is calculated by taking the average of prices over a period.",
        "A simple moving average is computed as the mean of closing prices across a time window.",
        "The RSI indicator measures overbought and oversold conditions.",
        "Completely different text about quarterly earnings report.",
    ]
    
    print("=== Deduplication Test ===\n")
    
    for i, text in enumerate(texts):
        result = dedup.check_and_add(text, f"doc_{i}", "test")
        print(f"Text {i+1}: {text[:50]}...")
        print(f"  -> Duplicate: {result.is_duplicate}")
        print(f"  -> Similarity: {result.similarity_score:.2f}")
        print(f"  -> Action: {result.action}")
        if result.matched_id:
            print(f"  -> Matched: {result.matched_id}")
        print()
    
    print(f"Stats: {dedup.get_stats()}")
