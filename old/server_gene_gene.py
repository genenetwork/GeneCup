# Dead code removed from server.py -- gene-gene search routes
# These routes were not referenced from any template.

@app.route("/startGeneGene")
def startGeneGene():
    session['forTopGene']=request.args.get('forTopGene')
    return render_template('progress.html', url_in="searchGeneGene", url_out="showGeneTopGene",version=version())


@app.route("/searchGeneGene")
def gene_gene():
    if 'path' not in session:
        if 'email' not in session :
             tf_path_gg=tempfile.gettempdir()
             rnd_gg = "tmp_gg" + ''.join(random.choice(string.ascii_letters) for x in range(6))
             session['path'] = tf_path_gg + "/" + rnd_gg
             os.makedirs(session['path'], exist_ok=True)
        else:
            if 'path_user' in session:
                session['path'] = session['path_user']
            else:
                 return "Error: User session path not found.", 500


    tmp_ggPMID=session['path']+"_ggPMID"
    gg_file=session['path']+"_ggSent"
    result_file=session['path']+"_ggResult"

    def findWholeWord(w):
        return re.compile(r'(?<!\w)({})(?!\w)'.format(w), flags=re.IGNORECASE).search

    def generate(query):
        from nltk.tokenize import sent_tokenize
        progress=1
        yield "data:"+str(progress)+"\n\n"
        safe_query = query.replace("\"", "\\\"")
        os.system(f"esearch -db pubmed -query \"{safe_query}\" | efetch -format uid |sort > \"{tmp_ggPMID}\"")

        top_gene_pmid_file = "topGene_uniq.pmid"
        if not os.path.exists(top_gene_pmid_file):
            print(f"Warning: {top_gene_pmid_file} not found. Gene-gene search might be affected.")
            open(top_gene_pmid_file, 'a').close()

        abstracts_cmd = f"comm -1 -2 \"{top_gene_pmid_file}\" \"{tmp_ggPMID}\" | fetch-pubmed -path \"{pubmed_path}\" | xtract -pattern PubmedArticle -element MedlineCitation/PMID,ArticleTitle,AbstractText | sed \"s/-/ /g\""
        try:
            abstracts_process = os.popen(abstracts_cmd)
            abstracts = abstracts_process.read()
            abstracts_process.close()
        except Exception as e_abs:
            print(f"Error getting abstracts for gene-gene search: {e_abs}")
            abstracts = ""

        if os.path.exists(tmp_ggPMID):
            os.system(f"rm \"{tmp_ggPMID}\"")

        progress=10
        yield "data:"+str(progress)+"\n\n"
        topGenes=dict()
        out_str=str()
        hitGenes=dict()

        top_gene_alias_file = "topGene_symb_alias.txt"
        if os.path.exists(top_gene_alias_file):
            with open(top_gene_alias_file, "r") as top_f:
                for line in top_f:
                    parts = line.strip().split("\t")
                    if len(parts) == 2:
                        symb, alias = parts
                        topGenes[symb]=alias.replace("; ","|")
        else:
            print(f"Warning: {top_gene_alias_file} not found. Top gene list will be empty.")

        allAbstracts= abstracts.split("\n")
        abstractCnt=len(allAbstracts) if abstracts else 0
        rowCnt=0

        for row in allAbstracts:
            if not row.strip(): continue
            rowCnt+=1
            if abstractCnt > 0 and rowCnt % 10 == 0 :
                progress=10+round(rowCnt/abstractCnt,2)*80
                yield "data:"+str(progress)+"\n\n"

            tiab_parts=row.split("\t", 1)
            if len(tiab_parts) < 2: continue
            pmid = tiab_parts[0]
            tiab_text_gg = tiab_parts[1]

            sentences_gg = sent_tokenize(tiab_text_gg)
            for sent_item in sentences_gg:
                if findWholeWord(query)(sent_item):
                    sent_item=re.sub(r'\b(%s)\b' % query, r'<strong>\1</strong>', sent_item, flags=re.I)
                    for symb_item in topGenes:
                        allNames=symb_item+"|"+topGenes[symb_item]
                        if findWholeWord(allNames)(sent_item) :
                            sent_item=sent_item.replace("<b>","").replace("</b>","")
                            sent_item=re.sub(r'\b(%s)\b' % allNames, r'<b>\1</b>', sent_item, flags=re.I)
                            out_str+=query+"\t"+"gene\t" + symb_item+"\t"+pmid+"\t"+sent_item+"\n"
                            if symb_item in hitGenes:
                                hitGenes[symb_item]+=1
                            else:
                                hitGenes[symb_item]=1
        progress=95
        yield "data:"+str(progress)+"\n\n"
        with open(gg_file, "w+") as gg:
            gg.write(out_str)

        results_html="<h4>"+query+" vs top addiction genes</h4> Click on the number of sentences will show those sentences. Click on the <span style=\"background-color:#FcF3cf\">top addiction genes</span> will show an archived search for that gene.<hr>"
        topGeneHits={}
        for key_gene in hitGenes.keys():
            url_gg=gg_file+"|"+query+"|"+key_gene
            sentword="sentence" if hitGenes[key_gene]==1 else "sentences"
            topGeneHits[ "<li> <a href=/sentences?edgeID=" + url_gg+ " target=_new>" + "Show " + str(hitGenes[key_gene]) + " " + sentword +" </a> about "+query+" and <a href=/showTopGene?topGene="+key_gene+" target=_gene><span style=\"background-color:#FcF3cf\">"+key_gene+"</span></a>" ]=hitGenes[key_gene]

        topSorted = sorted(topGeneHits.items(), key=lambda item: item[1], reverse=True)

        for k_html,v_count in topSorted:
            results_html+=k_html

        with open(result_file, "w+") as saveResult:
            saveResult.write(results_html)

        progress=100
        yield "data:"+str(progress)+"\n\n"

    query_gene_gene=session.get('forTopGene', '')
    if not query_gene_gene:
        return Response("Error: No gene query found for gene-gene search.", mimetype='text/event-stream')
    return Response(generate(query_gene_gene), mimetype='text/event-stream')


@app.route('/showGeneTopGene')
def showGeneTopGene ():
    results_content = "<p>No results found.</p>"
    result_file_path = session.get('path', '') + "_ggResult"
    if result_file_path and os.path.exists(result_file_path):
        with open(result_file_path, "r") as result_f:
            results_content=result_f.read()
    else:
        print(f"Warning: Result file {result_file_path} not found for showGeneTopGene.")
    return render_template('sentences.html', sentences=results_content+"<p><br>",no_footer=True,version=version())
