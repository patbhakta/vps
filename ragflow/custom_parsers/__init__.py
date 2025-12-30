#
#  Custom Parsers for RagFlow
#  Mount this directory to /ragflow/rag/app/custom
#
#  Available modules:
#  - financial: SEC filings parser with section filtering
#  - dedup: Deduplication layer with MinHash LSH
#

from .financial import chunk as financial_chunk
from .dedup import (
    Deduplicator,
    DedupConfig,
    DedupResult,
    deduplicate_chunks,
    get_deduplicator,
    normalize_text,
    CANONICAL_TERMS,
)

__all__ = [
    "financial_chunk",
    "Deduplicator",
    "DedupConfig", 
    "DedupResult",
    "deduplicate_chunks",
    "get_deduplicator",
    "normalize_text",
    "CANONICAL_TERMS",
]
