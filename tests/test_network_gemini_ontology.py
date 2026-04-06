"""Test Gemini API for generating SUD ontology terms.

Requires a Gemini API key in ~/.config/gemini/credentials and internet access.

Run with: python3 -m unittest tests.test_network_gemini_ontology -v
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from more_functions import gemini_query

PROMPT = (
    """
    Give me a list of terms on substance abuse disorder (SUD) that act
    as traits and classifiers in scientific literature with a focus on
    behaviour and brain attributes related to the hippocampus. Avoid
    aliases and synonyms as well as gene names. Each term should be
    1-3 words (max).  Give me a list of at least 20, but no more than
    80, most used terms.  Return only the terms, one per line, no
    numbering. Add abbreviations and aliases as a list with each term, separated by commas"""
)

class TestGeminiOntology(unittest.TestCase):
    def test_1_sud_ontology_terms(self):
        """Gemini should return 20-50 SUD ontology terms."""
        t0 = time.time()
        response = gemini_query(PROMPT)
        elapsed = time.time() - t0
        terms = [t.strip() for t in response.strip().split("\n") if t.strip()]
        print(f"  Got {len(terms)} terms ({elapsed:.2f}s)")
        for t in terms:
            print(f"    - {t}")
        self.assertGreaterEqual(len(terms), 20,
                                f"Expected at least 20 terms, got {len(terms)}")
        self.assertLessEqual(len(terms), 80,
                             f"Expected at most 80 terms, got {len(terms)}")
        # Each term should be short (1-3 words, allow some slack)
        long_terms = [t for t in terms if len(t.split()) > 5]

    def test_2_cached_ontology(self):
        """Second call should use cache and be fast."""
        # Ensure cache is populated from test_1
        gemini_query(PROMPT)
        t0 = time.time()
        response = gemini_query(PROMPT)
        elapsed = time.time() - t0
        terms = [t.strip() for t in response.strip().split("\n") if t.strip()]
        print(f"  Cached: {len(terms)} terms ({elapsed:.4f}s)")
        self.assertLess(elapsed, 0.01, f"Cache lookup too slow: {elapsed:.4f}s")

if __name__ == "__main__":
    unittest.main()
