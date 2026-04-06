#!/bin/env python3
from nltk.tokenize import sent_tokenize
import hashlib
import os
import re
import time

from addiction_keywords import *
from gene_synonyms import *
import ast

global pubmed_path

# In-memory caches
_esearch_cache = {}  # hash(query) -> list of PMIDs
_gemini_query_cache = {}  # hash(prompt) -> response text

def gemini_query(prompt, model='gemini-2.5-flash'):
    """Send a prompt to the Gemini API with caching and retry.

    Returns the response text, or raises on failure.
    """
    from google import genai

    cache_key = hashlib.sha256(prompt.encode()).hexdigest()
    if cache_key in _gemini_query_cache:
        print(f"  Gemini query cache hit")
        return _gemini_query_cache[cache_key]

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        cred_file = os.path.expanduser("~/.config/gemini/credentials")
        if os.path.isfile(cred_file):
            with open(cred_file) as f:
                api_key = f.read().strip()
    if not api_key:
        raise RuntimeError("No Gemini API key found")

    client = genai.Client(api_key=api_key)
    last_error = None
    for attempt in range(3):
        try:
            if attempt > 0:
                time.sleep(2 * attempt)
                print(f"  Gemini retry {attempt + 1}/3")
            print(f"  Gemini API call ({model}): {prompt[:80]}...")
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            result = response.text.strip()
            print(f"  Gemini response: {result[:200]}")
            _gemini_query_cache[cache_key] = result
            return result
        except Exception as e:
            last_error = e
            print(f"  Gemini attempt {attempt + 1}/3 failed: {e}")
    raise RuntimeError(f"Gemini API failed after 3 attempts: {last_error}")

def esearch_pmids(query):
    """Search PubMed for PMIDs matching query. Results are cached in memory.

    Returns a list of PMID strings, or [] if none found.
    """
    key = hashlib.sha256(query.encode()).hexdigest()
    if key in _esearch_cache:
        print(f"  esearch cache hit for: {query}")
        return _esearch_cache[key]
    pmid_cmd = "esearch -db pubmed -query " + query + " | efetch -format uid"
    print(f"  popen: {pmid_cmd}")
    pmids = os.popen(pmid_cmd).read().strip()
    pmid_list = [p for p in pmids.split("\n") if p.strip()] if pmids else []
    if pmid_list:
        _esearch_cache[key] = pmid_list
    return pmid_list

def undic(dic):
    all_s=''
    for s in dic:
        all_s += "|".join(str(e) for e in s)
        all_s +="|"
    all_s=all_s[:-1]
    return all_s

def findWholeWord(w):
    return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search


def hybrid_fetch_abstracts(pmid_list):
    """Fetch abstracts for a list of PMIDs: try local xfetch first,
    fall back to NCBI efetch for any missing.

    Returns tab-separated lines: PMID, ArticleTitle, AbstractText
    with hyphens replaced by spaces.
    """
    extract = "xtract -pattern PubmedArticle -element MedlineCitation/PMID,ArticleTitle,AbstractText"
    safe_pmids = "\n".join(p.replace("'", "") for p in pmid_list)
    # Try local xfetch
    abs_cmd = "echo '" + safe_pmids + "' | xfetch -db pubmed | " + extract + " | sed \"s/-/ /g\""
    print(f"  popen(local): {abs_cmd}")
    abstracts = os.popen(abs_cmd).read()
    # Check which PMIDs came back with abstracts
    found_pmids = set()
    for line in abstracts.strip().split("\n"):
        if line.strip():
            found_pmids.add(line.split("\t")[0])
    missing = [p for p in pmid_list if p not in found_pmids]
    if missing:
        print(f"  {len(missing)} PMIDs missing from local, falling back to NCBI efetch")
        fallback_cmd = "echo '" + "\n".join(missing) + "' | efetch -db pubmed -format xml | " + extract + " | sed \"s/-/ /g\""
        print(f"  popen(ncbi): {fallback_cmd}")
        extra = os.popen(fallback_cmd).read()
        abstracts += extra
    return abstracts

def getabstracts_batch(genes, query):
    """Fetch abstracts for multiple genes in a single PubMed query.

    Builds: (keywords) AND (gene1 [tiab] OR gene2 [tiab] OR ...)
    Returns tab-separated lines: PMID, ArticleTitle, AbstractText
    """
    genes_clause = " OR ".join(g + " [tiab]" for g in genes)
    full_query = "\"(" + query + ") AND (" + genes_clause + ")\""
    pmid_list = esearch_pmids(full_query)
    if not pmid_list:
        print(f"  no PMIDs found for {genes}")
        return ""
    print(f"  PMIDs ({len(pmid_list)}): {' '.join(pmid_list[:20])}{'...' if len(pmid_list) > 20 else ''}")
    abstracts = hybrid_fetch_abstracts(pmid_list)
    return abstracts

def getabstracts(gene,query):
    """
      1. esearch -db pubmed -query ... -- searches PubMed for the gene + keyword query, returns matching record IDs
      2. efetch -format uid -- fetches just the PMIDs (unique identifiers) from the search results
      3. xfetch -db pubmed -- looks up those PMIDs in the local PubMed mirror first;
         falls back to efetch (NCBI API) for any PMIDs missing abstracts locally
      4. xtract -pattern PubmedArticle -element MedlineCitation/PMID,ArticleTitle,AbstractText -- extracts PMID, title, and
         abstract text from the XML into tab-separated fields
      5. sed "s/-/ /g" -- replaces hyphens with spaces (so hyphenated gene names match keyword searches later)

  So: search PubMed remotely for matching articles, get their PMIDs, retrieve the full XML from the local mirror, then extract the PMID + title + abstract as tab-separated text. efetch -format uid returns only PMIDs. The esearch itself just creates a search handle on NCBI's servers, and efetch -format uid pulls back only the numeric PMIDs from that handle. No abstracts or XML are fetched from NCBI.
    """

    query="\"(" + query + ") AND (" + gene + " [tiab])\""
    # Step 1: fetch PMIDs from PubMed (cached)
    pmid_list = esearch_pmids(query)
    if not pmid_list:
        print(f"  no PMIDs found for {gene}")
        return ""
    print(f"  PMIDs ({len(pmid_list)}): {' '.join(pmid_list)}")
    # Step 2: fetch abstracts via hybrid local+NCBI
    abstracts = hybrid_fetch_abstracts(pmid_list)
    return(abstracts)

def getSentences(gene, sentences_ls):
    out=str()
    # Keep the sentence only if it contains the gene
    #print(sentences_ls)
    for sent in sentences_ls:
        #if gene.lower() in sent.lower():
        if re.search(r'\b'+gene.lower()+r'\b',sent.lower()):
            pmid = sent.split(' ')[0]
            sent = sent.split(' ',1)[1]
            sent=re.sub(r'\b(%s)\b' % gene, r'<strong>\1</strong>', sent, flags=re.I)
            out+=pmid+"\t"+sent+"\n"
    return(out)

def gene_category(gene, cat_d, cat, abstracts,addiction_flag,dictn):
    # e.g. BDNF, addiction_d, undic(addiction_d) "addiction"
    sents=getSentences(gene, abstracts)
    #print(sents)
    #print(abstracts)
    out=str()
    if (addiction_flag==1):
        for sent in sents.split("\n"):
            for key in cat_d:
                if key =='s':
                    key_ad = key+"*"
                else:
                    key_ad = key+"s*"
                key_ad = key_ad.replace("s|", "s*|")
                key_ad = key_ad.replace("|", "s*|")
                key_ad = key_ad.replace("s*s*", "s*")
                key_ad_ls = key_ad.split('|')
                for key_ad in key_ad_ls:
                    re_find = re.compile(r'\b{}\b'.format(key_ad), re.IGNORECASE)
                    if re_find.findall(sent):
                        sent=sent.replace("<b>","").replace("</b>","") # remove other highlights
                        sent=re.sub(r'\b(%s)\b' % key_ad, r'<b>\1</b>', sent, flags=re.I) # highlight keyword
                        out+=gene+"\t"+ cat + "\t"+key+"\t"+sent+"\n"
    else:
        for key_1 in dictn[cat_d].keys():
            for key_2 in dictn[cat_d][key_1]:
                if key_2[-1] =='s':
                    key_2 = key_2+"*"
                else:
                    key_2 = key_2+"s*"
                key_2 = key_2.replace("s|", "s*|")
                key_2 = key_2.replace("|", "s*|")
                key_2 = key_2.replace("s*s*", "s*")
                key_2_ls = key_2.split('|')
                for sent in sents.split("\n"):
                    for key_2 in key_2_ls:
                        re_find = re.compile(r'\b{}\b'.format(key_2), re.IGNORECASE)
                        if re_find.findall(sent):
                            sent=sent.replace("<b>","").replace("</b>","") # remove other highlights
                            sent=re.sub(r'\b(%s)\b' % key_2, r'<b>\1</b>', sent, flags=re.I) # highlight keyword
                            out+=gene+"\t"+ cat + "\t"+key_1+"\t"+sent+"\n"
    return(out)

def generate_nodes(nodes_d, nodetype,nodecolor):
    # Include all search terms even if there are no edges, just to show negative result
    json0 =str()
    for node in nodes_d:
        json0 += "{ data: { id: '" + node +  "', nodecolor: '" + nodecolor + "', nodetype: '"+nodetype + "', url:'/shownode?nodetype=" + nodetype + "&node="+node+"' } },\n"
    return(json0)

def generate_nodes_json(nodes_d, nodetype,nodecolor):
    # Include all search terms even if there are no edges, just to show negative result
    nodes_json0 =str()
    for node in nodes_d:
        nodes_json0 += "{ \"id\": \"" + node +  "\", \"nodecolor\": \"" + nodecolor + "\", \"nodetype\": \"" + nodetype + "\", \"url\":\"/shownode?nodetype=" + nodetype + "&node="+node+"\" },\n"
    return(nodes_json0)

def generate_edges(data, filename):
    pmid_list=[]
    json0=str()
    edgeCnts={}

    for line in  data.split("\n"):
        if len(line.strip())!=0:
            (source, cat, target, pmid, sent) = line.split("\t")
            edgeID=filename+"|"+source+"|"+target
            if (edgeID in edgeCnts) and (pmid+target not in pmid_list):
                edgeCnts[edgeID]+=1
                pmid_list.append(pmid+target)
            elif (edgeID not in edgeCnts) and (pmid+target not in pmid_list):
                edgeCnts[edgeID]=1
                pmid_list.append(pmid+target)

    for edgeID in edgeCnts:
        (filename, source,target)=edgeID.split("|")
        json0+="{ data: { id: '" + edgeID + "', source: '" + source + "', target: '" + target + "', sentCnt: " + str(edgeCnts[edgeID]) + ",  url:'/sentences?edgeID=" + edgeID + "' } },\n"
    return(json0)

def generate_edges_json(data, filename):
    pmid_list=[]
    edges_json0=str()
    edgeCnts={}

    for line in  data.split("\n"):
        if len(line.strip())!=0:
            (source, cat, target, pmid, sent) = line.split("\t")
            edgeID=filename+"|"+source+"|"+target
            if (edgeID in edgeCnts) and (pmid+target not in pmid_list):
                edgeCnts[edgeID]+=1
                pmid_list.append(pmid+target)
            elif (edgeID not in edgeCnts) and (pmid+target not in pmid_list):
                edgeCnts[edgeID]=1
                pmid_list.append(pmid+target)
    for edgeID in edgeCnts:
        (filename, source,target)=edgeID.split("|")
        edges_json0+="{ \"id\": \"" + edgeID + "\", \"source\": \"" + source + "\", \"target\": \"" + target + "\", \"sentCnt\": \"" + str(edgeCnts[edgeID]) + "\",  \"url\":\"/sentences?edgeID=" + edgeID + "\" },\n"
    return(edges_json0)

def searchArchived(sets, query, filetype,sents, path_user):
    # NOTE: dataFile, filetype, and initial nodes assignment are unused
    if sets=='topGene':
        dataFile="topGene_addiction_sentences.tab"
        nodes= "{ data: { id: '" + query +  "', nodecolor: '" + "#2471A3" + "', fontweight:700, url:'/progress?query="+query+"' } },\n"
    elif sets=='GWAS':
        dataFile="gwas_addiction.tab"
        nodes=str()
    pmid_list=[]
    catCnt={}
    sn_file = ''

    for sn in sents:
        (symb, cat0, cat1, pmid, sent)=sn.split("\t")
        if (symb.upper() == query.upper()) :
            if (cat1 in catCnt.keys()) and (pmid+cat1 not in pmid_list):
                pmid_list.append(pmid+cat1)
                catCnt[cat1]+=1
            elif (cat1 not in catCnt.keys()):
                catCnt[cat1]=1
                pmid_list.append(pmid+cat1)
        sn_file += sn + '\n'

    nodes= "{ data: { id: '" + query +  "', nodecolor: '" + "#2471A3" + "', fontweight:700, url:'/progress?query="+query+"' } },\n"
    edges=str()
    gwas_json=str()
    nodecolor={}
    nodecolor["GWAS"]="hsl(0, 0%, 70%)"

    for key in catCnt.keys():
        if sets=='GWAS':
            nc=nodecolor["GWAS"]
            nodes += "{ data: { id: '" + key +  "', nodecolor: '" + nc + "', url:'https://www.ebi.ac.uk/gwas/search?query="+key.replace("_GWAS","")+"' } },\n"
        edgeID=path_user+'gwas_results.tab'+"|"+query+"|"+key
        edges+="{ data: { id: '" + edgeID+ "', source: '" + query + "', target: '" + key + "', sentCnt: " + str(catCnt[key]) + ",  url:'/sentences?edgeID=" + edgeID + "' } },\n"
        gwas_json+="{ \"id\": \"" + edgeID + "\", \"source\": \"" + query + "\", \"target\": \"" + key + "\", \"sentCnt\": \"" + str(catCnt[key]) + "\",  \"url\":\"/sentences?edgeID=" + edgeID + "\" },\n"
    return(nodes+edges,gwas_json,sn_file)

pubmed_path=os.environ.get("EDIRECT_LOCAL_ARCHIVE", "./minipubmed")
print(f"  pubmed_path={pubmed_path}")

if not os.path.isdir(pubmed_path):
    print(f"ERROR: EDIRECT_LOCAL_ARCHIVE directory not found: {pubmed_path} - note this is a recent env variable that replaces the others (ignore the minipub reference)")
    raise SystemExit(1)
testdir = os.path.join(pubmed_path, "pubmed", "Archive", "00")
if not os.path.isdir(testdir):
    print(f"ERROR: PubMed/Archive not found in {testdir} (EDIRECT_LOCAL_ARCHIVE={pubmed_path})")
    raise SystemExit(1)
    raise SystemExit(1)
