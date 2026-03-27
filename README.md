# GeneCup: Mining gene relationships from PubMed using custom ontology

/Enhanced with AI LLM search!/

URL: [https://genecup.org](https://genecup.org)

GeneCup automatically extracts information from PubMed and NHGRI-EBI GWAS catalog on the relationship of any gene with a custom list of keywords hierarchically organized into an ontology. The users create an ontology by identifying categories of concepts and a list of keywords for each concept.

As an example, we created an ontology for drug addiction related concepts over 300 of these keywords are organized into six categories:

* names of abused drugs, e.g., opioids
* terms describing addiction, e.g., relapse
* key brain regions implicated in addiction, e.g., ventral striatum
* neurotrasmission, e.g., dopaminergic
* synaptic plasticity, e.g., long term potentiation
* intracellular signaling, e.g., phosphorylation

Live searches are conducted through PubMed to get relevant PMIDs, which are then used to retrieve the abstracts from a local archive. The relationships are presented as an interactive cytoscape graph. The nodes can be moved around to better reveal the connections. Clicking on the links will bring up the corresponding sentences in a new browser window. Stress related sentences for addiction keywords are further classified into either systemic or cellular stress using a convolutional neural network.

## Top addiction related genes for addiction ontology

0. extract gene symbol, alias and name from NCBI gene_info for taxid 9606.
1. search PubMed to get a count of these names/alias, with addiction keywords and drug name
2. sort the genes with top counts, retrieve the abstracts and extract sentences with the 1) symbols and alias and 2) one of the keywords. manually check if there are stop words need to be removed.
3. sort the genes based on the number of abstracts with useful sentences.
4. generate the final list, include symbol, alias, and name

## Install local mirror of PubMed

- Following the instruction provided by NCBI: https://www.nlm.nih.gov/dataguide/edirect/archive.html

## Mini PubMed for testing

For testing or code development, it is useful to have a small collection of PubMed abstracts in the same format as the local PubMed mirror. We provide 2473 abstracts that can be used to test four gene symbols (gria1, crhr1, drd2, and penk).

1. install [edirect](https://dataguide.nlm.nih.gov/edirect/install.html) (make sure you refresh your shell after install so the PATH is updated)
2. unpack the minipubmed.tgz file
3. test the installation by running:

```
cd minipubmed
cat pmid.list |fetch-pubmed  -path PubMed/Archive/ >test.xml
```

You should see 2473 abstracts in the test.xml file.

## NLTK tokens

You also need to fetch punkt.zip from https://www.nltk.org/nltk_data/

```sh
cd minipubmed
mkdir tokenizers
cd tokenizers
wget https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/tokenizers/punkt.zip
unzip punkt.zip
```

# Run the server

You can use the [guix.scm](./guix.scm) container to run genecup:

```sh
GeneCup$ guix shell -L . -C -N -F genecup-gemini coreutils edirect -- env EDIRECT_PUBMED_MASTER=./minipubmed NLTK_DATA=./minipubmed GEMINI_API_KEY="AIza****" ./server.py --port 4201
```

## Development

The source code and data are in a git repository: https://git.genenetwork.org/genecup/

## Support

E-mail [Pjotr Prins](https://thebird.nl) or [Hao Chen](https://www.uthsc.edu/neuroscience-institute/about/faculty/chen.php).

## License

GeneCup source code is published under the liberal free software MIT licence (aka expat license)

## Cite

[GeneCup: mining PubMed and GWAS catalog for gene-keyword relationships](https://academic.oup.com/g3journal/article/12/5/jkac059/6548160) by
Gunturkun MH, Flashner E, Wang T, Mulligan MK, Williams RW, Prins P, and Chen H.

G3 (Bethesda). 2022 May 6;12(5):jkac059. doi: 10.1093/g3journal/jkac059. PMID: 35285473; PMCID: PMC9073678.

```
@article{GeneCup,
  pmid         = {35285473},
  author       = {Gunturkun, M. H. and Flashner, E. and Wang, T. and Mulligan, M. K. and Williams, R. W. and Prins, P. and Chen, H.},
  title        = {{GeneCup: mining PubMed and GWAS catalog for gene-keyword relationships}},
  journal      = {G3 (Bethesda)},
  year         = {2022},
  doi          = {10.1093/g3journal/jkac059},
  url          = {http://www.ncbi.nlm.nih.gov/pubmed/35285473}
}
```
