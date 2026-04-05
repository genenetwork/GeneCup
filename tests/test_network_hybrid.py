"""Test hybrid search: local xfetch with NCBI efetch fallback.

Requires EDIRECT_LOCAL_ARCHIVE and internet access.

Run with: EDIRECT_LOCAL_ARCHIVE=/export3/PubMed/Source python3 -m unittest tests.test_network_hybrid -v
"""

import os
import subprocess
import sys
import unittest

# Add project root to path so we can import more_functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from more_functions import hybrid_fetch_abstracts

ARCHIVE = os.environ.get("EDIRECT_LOCAL_ARCHIVE", "/export3/PubMed/Source")

@unittest.skipUnless(os.path.isdir(ARCHIVE),
                     f"EDIRECT_LOCAL_ARCHIVE not found: {ARCHIVE}")
class TestNetworkHybrid(unittest.TestCase):
    def test_hybrid_matches_esearch(self):
        """Hybrid xfetch+efetch should return same PMIDs as pure esearch."""
        env = os.environ.copy()
        env["EDIRECT_LOCAL_ARCHIVE"] = ARCHIVE
        query = "(stress) AND (Penk [tiab])"

        # Step 1: get PMIDs from NCBI
        r1 = subprocess.run(
            ["sh", "-c",
             f'esearch -db pubmed -query "{query}" | efetch -format uid'],
            capture_output=True, text=True, timeout=120, env=env)
        self.assertEqual(r1.returncode, 0, r1.stderr)
        ncbi_pmids = sorted(set(r1.stdout.strip().split("\n")))
        ncbi_pmids = [p for p in ncbi_pmids if p.strip()]
        print(f"  NCBI esearch: {len(ncbi_pmids)} PMIDs")

        # Step 2: hybrid fetch using the shared function
        abstracts = hybrid_fetch_abstracts(ncbi_pmids)
        hybrid_pmids = set()
        for line in abstracts.strip().split("\n"):
            if line.strip():
                hybrid_pmids.add(line.split("\t")[0])
        print(f"  Hybrid total: {len(hybrid_pmids)} abstracts")

        # Some articles have no abstract (letters, editorials) so
        # hybrid may be slightly less than NCBI. Allow up to 5% gap.
        gap = len(ncbi_pmids) - len(hybrid_pmids)
        print(f"  Gap: {gap} PMIDs without abstracts")
        self.assertLessEqual(gap, max(1, len(ncbi_pmids) // 20),
                             f"Too many missing: hybrid {len(hybrid_pmids)} vs NCBI {len(ncbi_pmids)}")

if __name__ == "__main__":
    unittest.main()
