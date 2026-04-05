# GeneCup Release Notes

## Version 1.9.1 (2026-04-05)

### UI/UX
- Added header/footer in GN color scheme with version info across all pages
- Added --port and --debug command line switches
- Show environment variables (EDIRECT_PUBMED_MASTER, GEMINI_API_KEY, NLTK_DATA, GENECUP_DATADIR) on startup
- Added intermediate "Calling Gemini API..." loading page that auto-refreshes when classification completes

### Gemini API integration
- Replaced TensorFlow stress classifier with Google Gemini API (gemini-2.5-pro for few-shot, gemini-3-flash-preview for batch)
- API key read from ~/.config/gemini/credentials (with 0400 permission check)
- Batch classification: all stress sentences classified in one API call with JSON response
- In-memory cache for Gemini results (keyed by SHA-256 of sentence batch)
- Retry logic (3 attempts with 2s/4s backoff)
- Gemini prompts and responses logged to console

### PubMed / edirect
- Packaged edirect 25.x for Guix (Go programs compiled from source, XML bounds-check patch)
- Replaced missing fetch-pubmed with xfetch -db pubmed (local archive lookup)
- Hybrid abstract fetching: tries local xfetch first, falls back to NCBI efetch for PMIDs missing from the local archive
- In-memory cache for esearch PMID results (keyed by SHA-256 of query string)
- EDIRECT_LOCAL_ARCHIVE env var configures local PubMed archive path

### Packaging (guix.scm)
- Added edirect-25, nltk-punkt, minipubmed, python-google-genai packages
- genecup-gemini package with genecup wrapper script, JavaScript assets, NLTK data
- GENECUP_DATADIR for sqlite DB location

### Testing
- Added Python unittest framework (tests/)
- test_hello.py: offline smoke test (runs in guix build)
- test_network_esearch.py: NCBI esearch for Penk+stress PMIDs
- test_local_xfetch.py: local xsearch+xfetch against PubMed archive
- test_network_hybrid.py: validates hybrid fetch matches NCBI; tests esearch cache

### Cleanup
- Moved dead code to old/server.py
- Removed unused TensorFlow/Keras dependencies
- Removed stress_prompt.txt dependency (batch classifier builds its own prompt)
