#
#  Phase 2: Section Filter (~50 lines)
#  Skip boilerplate SEC sections before they reach the vector DB
#
#  Usage:
#    from custom_parsers.filter_sections import should_skip
#    
#    for chunk in chunks:
#        if should_skip(chunk["content"]):
#            continue
#        # ... process chunk
#

import re

# =============================================================================
# CONFIGURATION - Add/remove patterns as needed
# =============================================================================

SKIP_SECTIONS = [
    r"forward[\-\s]*looking\s+statements?",
    r"safe\s+harbor",
    r"risk\s+factors",
    r"legal\s+proceedings",
    r"certifications?",
    r"power\s+of\s+attorney",
    r"signatures?\s*$",
]

SKIP_PHRASES = [
    r"pursuant\s+to\s+section\s+\d+",
    r"incorporated\s+by\s+reference",
    r"securities\s+and\s+exchange\s+commission",
    r"this\s+form\s+10-?[kq]",
]

# =============================================================================
# FILTER FUNCTION
# =============================================================================

def should_skip(text: str) -> bool:
    """
    Returns True if text is boilerplate that should be skipped.
    
    Checks:
    1. Section headers (Risk Factors, Forward-Looking, etc.)
    2. Boilerplate phrases (2+ matches = skip)
    """
    if not text or len(text) < 20:
        return False
    
    text_lower = text.lower()
    
    # Check section patterns
    for pattern in SKIP_SECTIONS:
        if re.search(pattern, text_lower):
            return True
    
    # Check phrase density (2+ = boilerplate)
    matches = sum(1 for p in SKIP_PHRASES if re.search(p, text_lower))
    return matches >= 2


def filter_chunks(chunks: list, content_key: str = "content") -> list:
    """Filter a list of chunk dicts, removing boilerplate."""
    return [c for c in chunks if not should_skip(c.get(content_key, ""))]
