"""Test hybrid search: local xfetch with NCBI efetch fallback.

Requires EDIRECT_LOCAL_ARCHIVE and internet access.

Run with: EDIRECT_LOCAL_ARCHIVE=/export3/PubMed/Source python3 -m unittest tests.test_network_hybrid -v
"""

import os
import sys
import time
import unittest

# Add project root to path so we can import more_functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from more_functions import esearch_pmids, hybrid_fetch_abstracts

ARCHIVE = os.environ.get("EDIRECT_LOCAL_ARCHIVE", "/export3/PubMed/Source")
QUERY = '"(stress) AND (Penk [tiab])"'

@unittest.skipUnless(os.path.isdir(ARCHIVE),
                     f"EDIRECT_LOCAL_ARCHIVE not found: {ARCHIVE}")
class TestNetworkHybrid(unittest.TestCase):
    def test_1_hybrid_matches_esearch(self):
        """Hybrid xfetch+efetch should return same PMIDs as pure esearch."""
        t0 = time.time()
        ncbi_pmids = esearch_pmids(QUERY)
        t_search = time.time() - t0
        self.assertGreater(len(ncbi_pmids), 0)
        print(f"  NCBI esearch: {len(ncbi_pmids)} PMIDs ({t_search:.2f}s)")

        t0 = time.time()
        abstracts = hybrid_fetch_abstracts(ncbi_pmids)
        t_fetch = time.time() - t0
        hybrid_pmids = set()
        for line in abstracts.strip().split("\n"):
            if line.strip():
                hybrid_pmids.add(line.split("\t")[0])
        print(f"  Hybrid total: {len(hybrid_pmids)} abstracts ({t_fetch:.2f}s)")

        # Some articles have no abstract (letters, editorials) so
        # hybrid may be slightly less than NCBI. Allow up to 5% gap.
        gap = len(ncbi_pmids) - len(hybrid_pmids)
        print(f"  Gap: {gap} PMIDs without abstracts")
        self.assertLessEqual(gap, max(1, len(ncbi_pmids) // 20),
                             f"Too many missing: hybrid {len(hybrid_pmids)} vs NCBI {len(ncbi_pmids)}")

    def test_2_cached_esearch(self):
        """Second esearch call should use cache and be fast."""
        # First call to populate cache (may already be cached from test_1)
        pmids1 = esearch_pmids(QUERY)

        t0 = time.time()
        pmids2 = esearch_pmids(QUERY)
        t_cached = time.time() - t0

        print(f"  Cached esearch: {len(pmids2)} PMIDs ({t_cached:.4f}s)")
        self.assertEqual(pmids1, pmids2, "Cached results differ from first call")
        self.assertLess(t_cached, 0.01, f"Cache lookup too slow: {t_cached:.4f}s")

if __name__ == "__main__":
    unittest.main()
