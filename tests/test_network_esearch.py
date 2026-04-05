"""Test PubMed esearch via edirect -- requires internet access.

Run with: python -m unittest tests.test_network_esearch -v
"""

import subprocess
import unittest

class TestNetworkEsearch(unittest.TestCase):
    def test_esearch_penk_stress(self):
        """Search PubMed for Penk + stress, expect at least some PMIDs."""
        result = subprocess.run(
            ["sh", "-c",
             'esearch -db pubmed -query "(stress) AND (Penk [tiab])" '
             '| efetch -format uid'],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        pmids = result.stdout.strip().split("\n")
        pmids = [p for p in pmids if p.strip()]
        print(f"  Found {len(pmids)} PMIDs for Penk+stress")
        self.assertGreater(len(pmids), 0, "Expected at least 1 PMID")

if __name__ == "__main__":
    unittest.main()
