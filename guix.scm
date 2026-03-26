;;
;; GeneCup guix.scm - package definition
;;
;; Build with:
;;
;;   guix build -L ../guix-bioinformatics -L ../guix-past/modules \
;;     -L ../guix-rust-past-crates/modules -f guix.scm
;;
;; Development shell:
;;
;;   guix shell -L ../guix-bioinformatics -L ../guix-past/modules \
;;     -L ../guix-rust-past-crates/modules -D -f guix.scm
;;

(define-module (guix)
  #:use-module ((guix licenses) #:prefix license:)
  #:use-module (guix build-system pyproject)
  #:use-module (guix build-system python)
  #:use-module (guix download)
  #:use-module (guix gexp)
  #:use-module (guix git-download)
  #:use-module (guix packages)
  #:use-module (guix utils)
  #:use-module (gnu packages admin)
  #:use-module (gnu packages base)
  #:use-module (gnu packages bioinformatics)
  #:use-module (gnu packages compression)
  #:use-module (gnu packages javascript)
  #:use-module (gnu packages python)
  #:use-module (gnu packages python-crypto)
  #:use-module (gnu packages python-science)
  #:use-module (gnu packages python-web)
  #:use-module (gnu packages python-xyz)
  #:use-module (gnu packages python-check)
  #:use-module (gnu packages python-build)
  #:use-module (gnu packages time)
  #:use-module (gn packages javascript)
  #:use-module (gn packages web))

(define %source-dir (dirname (current-filename)))

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
     (list python-google-auth
           python-httpx
           python-pydantic
           python-requests
           python-tenacity
           python-websockets
           python-typing-extensions
           python-distro
           python-sniffio))
    (native-inputs
     (list python-setuptools
           python-wheel))
    (home-page "https://github.com/googleapis/python-genai")
    (synopsis "Google Generative AI Python SDK")
    (description "Client library for the Google Generative AI API, providing
access to Gemini models.")
    (license license:asl2.0)))

(define-public genecup
  (package
    (name "genecup")
    (version "0.0.1")
    (source (local-file %source-dir #:recursive? #t))
    (build-system python-build-system)
    (arguments
     (list
      #:tests? #f ; no test suite
      #:phases
      #~(modify-phases %standard-phases
          (delete 'configure)
          (delete 'build)
          (add-after 'unpack 'make-files-writable
            (lambda _
              (for-each make-file-writable (find-files "."))))
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
          (add-after 'unpack 'extract-pubmed-archive
            (lambda _
              (invoke "gzip" "-d" "minipubmed.tgz")
              (invoke "tar" "xvf" "minipubmed.tar")))
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
          (add-after 'install 'wrap-executable
            (lambda* (#:key inputs outputs #:allow-other-keys)
              (let ((out  (assoc-ref outputs "out"))
                    (path (getenv "GUIX_PYTHONPATH")))
                (wrap-program (string-append out "/server.py")
                  `("PATH" ":" prefix (,(dirname (which "edirect.pl"))
                                        ,(dirname (which "dirname"))
                                        ,(dirname (which "grep"))
                                        ,(dirname (which "sed"))))
                  `("GUIX_PYTHONPATH" ":" prefix (,path)))))))))
    (inputs
     `(("edirect" ,edirect)
       ("inetutils" ,inetutils)
       ("gzip" ,gzip)
       ("tar" ,tar)
       ("python-bcrypt" ,python-bcrypt)
       ("python-dotenv" ,python-dotenv)
       ("python-flask" ,python-flask)
       ("python-flask-sqlalchemy" ,python-flask-sqlalchemy)
       ("python-google-genai" ,python-google-genai)
       ("python-nltk" ,python-nltk)
       ("python-pandas" ,python-pandas)
       ("python-pytz" ,python-pytz)
       ;; JavaScript assets symlinked into static/
       ("bootstrap" ,web-bootstrap)
       ("cytoscape" ,javascript-cytoscape-3.17)
       ("cytoscape-svg" ,js-cytoscape-svg-vendor-0.3.1)
       ("font-awesome" ,web-font-awesome)
       ("jquery" ,web-jquery)
       ("js-filesaver" ,js-filesaver-1.3.2)
       ("js-popper" ,js-popper-1.12.9)))
    (home-page "http://genecup.org")
    (synopsis "GeneCup: gene-addiction relationship search using PubMed")
    (description "GeneCup automatically extracts information from PubMed and
the NHGRI-EBI GWAS catalog on the relationship of any gene with a custom list
of keywords hierarchically organized into an ontology.")
    (license license:expat)))

genecup
