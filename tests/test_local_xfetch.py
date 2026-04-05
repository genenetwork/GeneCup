"""Test local xsearch + xfetch against a local PubMed archive.

Requires EDIRECT_LOCAL_ARCHIVE to point to a PubMed archive directory
(e.g. /export3/PubMed/Source) and edirect tools on PATH.

Run with: EDIRECT_LOCAL_ARCHIVE=/export3/PubMed/Source python3 -m unittest tests.test_local_xfetch -v
"""

import os
import subprocess
import unittest

ARCHIVE = os.environ.get("EDIRECT_LOCAL_ARCHIVE", "/export3/PubMed/Source")

@unittest.skipUnless(os.path.isdir(ARCHIVE),
                     f"EDIRECT_LOCAL_ARCHIVE not found: {ARCHIVE}")
class TestLocalXfetch(unittest.TestCase):
    def test_xsearch_xfetch_penk_stress(self):
        """Local xsearch + xfetch for Penk + stress, expect PMIDs."""
        env = os.environ.copy()
        env["EDIRECT_LOCAL_ARCHIVE"] = ARCHIVE
        result = subprocess.run(
            ["sh", "-c",
             'xsearch -db pubmed -query "(stress) AND (Penk [tiab])" '
             '| xfetch -db pubmed'],
            capture_output=True, text=True, timeout=120, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout.strip()
        self.assertGreater(len(output), 0, "Expected non-empty XML output")
        self.assertIn("PubmedArticle", output,
                      "Expected PubmedArticle XML elements")
        # Count articles
        count = output.count("<PubmedArticle>")
        print(f"  Found {count} PubmedArticle records for Penk+stress (local)")
        self.assertGreater(count, 10, "Expected at least 10 PubmedArticles")

if __name__ == "__main__":
    unittest.main()
