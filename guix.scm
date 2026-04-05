;;
;; GeneCup guix.scm - package definition
;;
;; Build with:
;;
;;   guix build -f guix.scm
;;
;; Development shell:
;;
;;   guix shell -L . -L ../guix-bioinformatics -C -N -F genecup-gemini coreutils -- genecup --port 4201
;;
;; Note: API key is read from ~/.config/gemini/credentials
;;

(define-module (guix)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (guix build-system pyproject)
  #:use-module (guix build-system gnu)
  #:use-module (guix build-system python)
  #:use-module (guix download)
  #:use-module (guix gexp)
  #:use-module (guix git-download)
  #:use-module (guix packages)
  #:use-module (guix utils)
  #:use-module (gnu packages admin)
  #:use-module (gnu packages base)
  #:use-module (gnu packages bash)
  #:use-module (gnu packages compression)
  #:use-module (gnu packages curl)
  #:use-module (gnu packages wget)
  #:use-module (gnu packages gawk)
  #:use-module (gnu packages golang)
  #:use-module (gnu packages golang-build)
  #:use-module (gnu packages golang-compression)
  #:use-module (gnu packages golang-xyz)
  #:use-module (gnu packages javascript)
  #:use-module (gnu packages python)
  #:use-module (gnu packages python-crypto)
  #:use-module (gnu packages python-science)
  #:use-module (gnu packages python-web)
  #:use-module (gnu packages python-xyz)
  #:use-module (gnu packages python-check)
  #:use-module (gnu packages python-build)
  #:use-module (gnu packages nss)
  #:use-module (gnu packages perl)
  #:use-module (gnu packages xml)
  #:use-module (gnu packages time)
  #:use-module (gnu packages tls)
  #:use-module (gn packages javascript)
  #:use-module (gn packages web))

(define %source-dir (dirname (current-filename)))

(define nltk-punkt-source
  (origin
    (method url-fetch)
    (uri "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/tokenizers/punkt_tab.zip")
    (sha256
     (base32 "01h11srafj57yvp74xkidikh6m7ch7qscz21lck7f9vlg4c68zz5"))))

(define-public nltk-punkt
  (package
    (name "nltk-punkt")
    (version "1.0")
    (source nltk-punkt-source)
    (build-system gnu-build-system)
    (arguments
     (list
      #:phases
      #~(modify-phases %standard-phases
          (delete 'configure)
          (delete 'build)
          (delete 'check)
          (replace 'unpack
            (lambda* (#:key source #:allow-other-keys)
              (invoke "unzip" source)))
          (replace 'install
            (lambda* (#:key outputs #:allow-other-keys)
              (let ((out (string-append (assoc-ref outputs "out")
                                        "/share/nltk_data/tokenizers/punkt_tab")))
                (mkdir-p out)
                (copy-recursively "punkt_tab" out)))))))
    (native-inputs (list unzip))
    (home-page "https://www.nltk.org/nltk_data/")
    (synopsis "NLTK Punkt_Tab sentence tokenizer models")
    (description "Pre-trained models for the Punkt sentence boundary
detection tokenizer (tab format), used by NLTK's sent_tokenize function.")
    (license license:asl2.0)))

(define minipubmed-source
  (origin
    (method url-fetch)
    (uri "https://git.genenetwork.org/genecup/plain/minipubmed.tgz")
    (sha256
     (base32 "116k7plhn7xkbv170035si7xhbfqb1ff15rxqwimjrwm8rb1bbcc"))))

(define-public minipubmed
  (package
    (name "minipubmed")
    (version "1.0")
    (source minipubmed-source)
    (build-system gnu-build-system)
    (arguments
     (list
      #:phases
      #~(modify-phases %standard-phases
          (delete 'configure)
          (delete 'build)
          (delete 'check)
          (replace 'unpack
            (lambda* (#:key source #:allow-other-keys)
              (invoke "tar" "xzf" source)))
          (replace 'install
            (lambda* (#:key inputs outputs #:allow-other-keys)
              (let ((out (string-append (assoc-ref outputs "out")
                                        "/share/minipubmed")))
                ;; Generate test.xml from pmid.list
                (with-directory-excursion "minipubmed"
                  ;; Generate test.xml by looking up PMIDs in the local archive
                  (system "for uid in $(cat pmid.list); do p=$(printf '%.2s/%.2s/%.2s' \"$uid\" \"${uid#??}\" \"${uid#????}\"); f=PubMed/Archive/${p}/${uid}.xml.gz; [ -f \"$f\" ] && zcat \"$f\"; done > test.xml"))
                (mkdir-p out)
                (copy-recursively "minipubmed" out)))))))
    (inputs (list edirect-25))
    (home-page "https://genecup.org")
    (synopsis "Mini PubMed archive for GeneCup testing")
    (description "A small collection of 2473 PubMed abstracts for testing
GeneCup with four gene symbols (gria1, crhr1, drd2, and penk).")
    (license license:expat)))

(define-public edirect-25
  (package
    (name "edirect-25")
    (version "25.2.20260328")
    (source (origin
              (method url-fetch)
              (uri (string-append "https://ftp.ncbi.nlm.nih.gov/entrez/entrezdirect"
                                  "/versions/" version
                                  "/edirect-" version ".tar.gz"))
              (sha256
               (base32 "04km4hrnmiganafwn5516hm8n0var9ilhbr068chy8v95xk131x6"))
              (modules '((guix build utils)))
              (snippet
               '(begin
                  (delete-file "Mozilla-CA.tar.gz")
                  (delete-file "cacert.pem")))
              (patches
               (list (local-file "contrib/patches/edirect-xml-bounds-check.patch")))))
    (build-system gnu-build-system)
    (arguments
     (list
      #:tests? #t
      #:phases
      #~(modify-phases %standard-phases
          (delete 'configure)
          (add-after 'unpack 'patch-path-reset
            (lambda _
              ;; These scripts reset PATH=/bin:/usr/bin which breaks Guix
              (substitute* '("xtract" "rchive" "transmute")
                (("PATH=/bin:/usr/bin")
                 "PATH=\"/bin:/usr/bin:$PATH\""))))
          (add-after 'unpack 'patch-go-version
            (lambda _
              ;; Relax Go version requirement to match available toolchain
              (substitute* '("cmd/go.mod" "eutils/go.mod")
                (("go 1\\.26\\.1") "go 1.26.0"))))
          (replace 'build
            (lambda* (#:key inputs #:allow-other-keys)
              (setenv "HOME" (getcwd))
              (setenv "GOTOOLCHAIN" "local")
              (setenv "GO111MODULE" "off")
              ;; Build GOPATH from Guix Go package inputs + local eutils
              (let ((gopath (string-append (getcwd) "/gopath")))
                (mkdir-p (string-append gopath "/src"))
                (symlink (string-append (getcwd) "/eutils")
                         (string-append gopath "/src/eutils"))
                (setenv "GOPATH"
                  (string-join
                    (cons gopath
                      (map cdr
                        (filter
                          (lambda (input)
                            (directory-exists?
                              (string-append (cdr input) "/src")))
                          inputs)))
                    ":")))
              (with-directory-excursion "cmd"
                (for-each
                  (lambda (prog)
                    (invoke "go" "build" "-v"
                            "-o" (string-append prog ".Linux")
                            (string-append prog ".go")))
                  '("xtract" "rchive" "transmute")))))
          (replace 'install
            (lambda* (#:key outputs #:allow-other-keys)
              (let ((bin (string-append (assoc-ref outputs "out") "/bin")))
                (mkdir-p bin)
                ;; Install Go binaries
                (for-each
                  (lambda (prog)
                    (install-file (string-append "cmd/" prog ".Linux") bin))
                  '("xtract" "rchive" "transmute"))
                ;; Install executable scripts
                (for-each
                  (lambda (f)
                    (when (and (not (file-is-directory? f))
                               (access? f X_OK)
                               (not (string-suffix? ".go" f))
                               (not (string-suffix? ".py" f))
                               (not (string-suffix? ".pm" f))
                               (not (string-suffix? ".pdf" f))
                               (not (string-suffix? ".pem" f))
                               (not (string-suffix? ".gz" f))
                               (not (member (basename f)
                                            '("LICENSE" "README"))))
                      (install-file f bin)))
                  (find-files "."
                    (lambda (f s)
                      (and (not (string-contains f "/cmd/"))
                           (not (string-contains f "/eutils/"))
                           (not (string-contains f "/gopath/"))))
                    #:directories? #f))
                ;; Install extern/ data (contains .ini config files)
                (copy-recursively "extern"
                                  (string-append bin "/extern")))))
          (add-after 'install 'wrap-programs
            (lambda* (#:key inputs outputs #:allow-other-keys)
              (let* ((out (assoc-ref outputs "out"))
                     (bin (string-append out "/bin"))
                     (coreutils (assoc-ref inputs "coreutils")))
                ;; Only wrap scripts directly in bin/, not in
                ;; subdirs (extern/ scripts are sourced, not executed).
                ;; Skip .sh (sourced) and .Linux (Go binaries).
                (for-each
                  (lambda (f)
                    (wrap-program f
                      `("PATH" ":" prefix
                        (,bin ,(string-append coreutils "/bin")))))
                  (filter
                    (lambda (f)
                      (and (string=? (dirname f) bin)
                           (not (string-suffix? ".sh" f))
                           (not (string-suffix? ".Linux" f))))
                    (find-files bin)))
                ;; wrap-program renames xtract -> .xtract-real, but the
                ;; script looks for $0.Linux, so create symlinks
                (for-each
                  (lambda (prog)
                    (symlink (string-append bin "/" prog ".Linux")
                             (string-append bin "/." prog "-real.Linux")))
                  '("xtract" "rchive" "transmute")))))
          (delete 'check)
          (add-after 'wrap-programs 'smoke-test
            (lambda* (#:key outputs #:allow-other-keys)
              (let ((bin (string-append (assoc-ref outputs "out") "/bin")))
                ;; Smoke test: xtract.Linux parses XML
                (invoke "sh" "-c"
                  (string-append
                    "echo '<test><a>hello</a><b>world</b></test>' | "
                    bin "/xtract.Linux -pattern test -element a b"
                    " | grep -q hello"))
                ;; Smoke test: rchive.Linux version
                (invoke (string-append bin "/rchive.Linux") "-version")
                ;; Smoke test: transmute.Linux version
                (invoke (string-append bin "/transmute.Linux")
                        "-version")))))))
    (native-inputs
     (list go-1.26
           go-github-com-fatih-color
           go-github-com-gedex-inflector
           go-github-com-goccy-go-yaml
           go-github-com-klauspost-compress
           go-github-com-klauspost-cpuid-v2
           go-github-com-klauspost-pgzip
           go-github-com-komkom-toml
           go-github-com-mattn-go-colorable
           go-github-com-mattn-go-isatty
           go-github-com-pbnjay-memory
           go-github-com-pkg-errors
           go-github-com-surgebase-porter2
           go-golang-org-x-sys
           go-golang-org-x-text))
    (propagated-inputs (list curl wget grep sed gawk coreutils findutils gzip unzip))
    (inputs (list bash-minimal coreutils perl perl-xml-simple python))
    (home-page "https://www.ncbi.nlm.nih.gov/books/NBK179288/")
    (synopsis "Tools for accessing the NCBI's set of databases")
    (description "Entrez Direct (EDirect) provides access to the NCBI's suite
of interconnected databases from a Unix terminal window.  Search terms are
entered as command-line arguments.  Individual operations are connected with
Unix pipes to construct multi-step queries.  Selected records can then be
retrieved in a variety of formats.")
    (license license:public-domain)))

(define-public python-google-genai
  (package
    (name "python-google-genai")
    (version "1.68.0")
    (source
     (origin
       (method url-fetch)
       (uri (pypi-uri "google_genai" version))
       (sha256
        (base32 "15na2kxak5farpm5az0dw7r3c3mf3nhy95rsk5r963v3pjwc0c5c"))))
    (build-system pyproject-build-system)
    (arguments
     (list
      #:tests? #f)) ; tests require network access and API keys
    (propagated-inputs
     (list python
           python-google-auth
           python-httpx
           python-pydantic
           python-requests
           python-tenacity
           python-websockets
           python-typing-extensions
           python-distro
           python-sniffio
           sed))
    (native-inputs
     (list python-setuptools
           python-wheel))
    (home-page "https://github.com/googleapis/python-genai")
    (synopsis "Google Generative AI Python SDK")
    (description "Client library for the Google Generative AI API, providing
access to Gemini models.")
    (license license:asl2.0)))

(define-public genecup-gemini
  (package
    (name "genecup-gemini")
    (version "1.9")
    (source (local-file %source-dir #:recursive? #t))
    (build-system python-build-system)
    (arguments
     (list
      #:tests? #f ; no test suite
      #:phases
      #~(modify-phases %standard-phases
          (delete 'configure)
          (delete 'build)
          (add-after 'unpack 'patch-sources
            (lambda* (#:key inputs outputs #:allow-other-keys)
              (let ((inetutils (assoc-ref inputs "inetutils")))
                (substitute* '("templates/cytoscape.html"
                                "templates/tableview.html"
                                "templates/tableview0.html"
                                "templates/userarchive.html")
                  (("https.*FileSaver.js.*\\\">") "/static/FileSaver.js\">")
                  (("https.*cytoscape-svg.js.*\\\">") "/static/cytoscape-svg.js\">")
                  (("https.*cytoscape.min.js.*\\\">") "/static/cytoscape.min.js\">"))
                (substitute* "templates/layout.html"
                  (("https.*bootstrap.min.css.*\\\">") "/static/bootstrap.min.css\">")
                  (("https.*4.*bootstrap.min.js.*\\\">") "/static/bootstrap.min.js\">")
                  (("https.*4.7.0/css/font-awesome.min.css") "/static/font-awesome.min.css")
                  (("https.*jquery-3.2.1.slim.min.js.*\\\">") "/static/jquery.slim.min.js\">")
                  (("https.*1.12.9/umd/popper.min.js.*\\\">") "/static/popper.min.js\">")))))
          (add-after 'unpack 'setup-minipubmed
            (lambda* (#:key inputs #:allow-other-keys)
              (delete-file "minipubmed.tgz")
              (let ((pubmed (string-append (assoc-ref inputs "minipubmed")
                                           "/share/minipubmed/PubMed")))
                ;; Patch default pubmed path to store location
                (substitute* "more_functions.py"
                  (("\\./minipubmed") pubmed)))))
          (replace 'install
            (lambda* (#:key outputs #:allow-other-keys)
              (let ((out (assoc-ref outputs "out")))
                (copy-recursively "." out))))
          (add-after 'install 'install-javascript
            (lambda* (#:key inputs outputs #:allow-other-keys)
              (let ((out       (assoc-ref outputs "out"))
                    (awesome   (assoc-ref inputs "font-awesome"))
                    (bootstrap (assoc-ref inputs "bootstrap"))
                    (cytoscape (assoc-ref inputs "cytoscape"))
                    (cytoscape-svg (assoc-ref inputs "cytoscape-svg"))
                    (jquery    (assoc-ref inputs "jquery"))
                    (js-filesaver (assoc-ref inputs "js-filesaver"))
                    (js-popper (assoc-ref inputs "js-popper")))
                (symlink (string-append awesome
                                        "/share/web/font-awesomecss/font-awesome.min.css")
                         (string-append out "/static/font-awesome.min.css"))
                (symlink (string-append bootstrap
                                        "/share/web/bootstrap/css/bootstrap.min.css")
                         (string-append out "/static/bootstrap.min.css"))
                (symlink (string-append bootstrap
                                        "/share/web/bootstrap/js/bootstrap.min.js")
                         (string-append out "/static/bootstrap.min.js"))
                (symlink (string-append cytoscape
                                        "/share/genenetwork2/javascript/cytoscape/cytoscape.min.js")
                         (string-append out "/static/cytoscape.min.js"))
                (symlink (string-append cytoscape-svg
                                        "/share/javascript/cytoscape-svg.js")
                         (string-append out "/static/cytoscape-svg.js"))
                (symlink (string-append jquery
                                        "/share/web/jquery/jquery.slim.min.js")
                         (string-append out "/static/jquery.slim.min.js"))
                (symlink (string-append js-filesaver
                                        "/share/javascript/FileSaver.js")
                         (string-append out "/static/FileSaver.js"))
                (symlink (string-append js-popper
                                        "/share/javascript/popper.min.js")
                         (string-append out "/static/popper.min.js")))))
          (add-after 'install 'create-bin-wrapper
            (lambda* (#:key inputs outputs #:allow-other-keys)
              (let ((out  (assoc-ref outputs "out"))
                    (path (getenv "GUIX_PYTHONPATH")))
                (mkdir-p (string-append out "/bin"))
                (call-with-output-file (string-append out "/bin/genecup")
                  (lambda (port)
                    (format port "#!~a~%cd ~a~%exec ~a/server.py \"$@\"~%"
                            (which "bash") out out)))
                (chmod (string-append out "/bin/genecup") #o755)
                (wrap-program (string-append out "/bin/genecup")
                  `("PATH" ":" prefix (,(dirname (which "esearch"))
                                        ,(dirname (which "dirname"))
                                        ,(dirname (which "grep"))
                                        ,(dirname (which "sed"))))
                  `("GUIX_PYTHONPATH" ":" prefix (,path))
                  `("NLTK_DATA" ":" prefix
                    (,(string-append (assoc-ref inputs "nltk-punkt")
                                     "/share/nltk_data"))))))))))
    (propagated-inputs
     (list
       python-bcrypt
       python-flask
       python-flask-sqlalchemy
       python-google-genai
       python-nltk
       python-pandas
       python-pytz
       python
       nss-certs
       openssl
       ))
    (inputs
     `(("edirect-25" ,edirect-25)
       ("inetutils" ,inetutils)
       ("gzip" ,gzip)
       ("minipubmed" ,minipubmed)
       ("tar" ,tar)
       ;; JavaScript assets symlinked into static/
       ("bootstrap" ,web-bootstrap)
       ("cytoscape" ,javascript-cytoscape-3.17)
       ("cytoscape-svg" ,js-cytoscape-svg-vendor-0.3.1)
       ("font-awesome" ,web-font-awesome)
       ("jquery" ,web-jquery)
       ("js-filesaver" ,js-filesaver-1.3.2)
       ("nltk-punkt" ,nltk-punkt)
       ("js-popper" ,js-popper-1.12.9)))
    (home-page "http://genecup.org")
    (synopsis "GeneCup: gene-addiction relationship search using PubMed")
    (description "GeneCup automatically extracts information from PubMed and
the NHGRI-EBI GWAS catalog on the relationship of any gene with a custom list
of keywords hierarchically organized into an ontology.")
    (license license:expat)))

genecup-gemini
