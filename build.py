"""Reproducible Group16 ingestion. Python 3.10+, numpy; no database server needed.
Usage: python scripts/build.py --input /path/to/Group16 [--out .]
Raw bytes are archived in SQLite/MySQL separately from curated analytical tables.
"""
import argparse, collections, csv, hashlib, io, json, math, pathlib, re, sqlite3, zipfile
import numpy as np

MISSING={'','na','n/a','null','nan','none'}
def text(v):
    if v is None:return None
    v=' '.join(v.strip().split())
    return None if v.lower() in MISSING else v
def sig(v): return re.sub('[^a-z0-9]','',(v or '').lower())
def bh(values):
    result=[None]*len(values); valid=sorted((p,i) for i,p in enumerate(values) if p is not None)
    running=1.; m=len(valid)
    for rank in range(m,0,-1):
        p,i=valid[rank-1]; running=min(running,p*m/rank);result[i]=running
    return result
def unique_lookup(values):
    d=collections.defaultdict(set)
    for v in values:
        if v:d[sig(v)].add(v)
    result={k:next(iter(v)) for k,v in d.items() if len(v)==1}
    # Exact values remain valid even if stripping meaningful punctuation would
    # collide with another valid allele or stable ID.
    for v in values:
        if v:result['='+v.casefold()]=v
    return result
def repair(v,lookup):
    v=text(v)
    return lookup.get('='+v.casefold(),lookup.get(sig(v))) if v else None

SCHEMA='''
CREATE TABLE source_file(source_id INTEGER PRIMARY KEY, path VARCHAR(255) UNIQUE NOT NULL, sha256 VARCHAR(64) NOT NULL, raw_bytes BLOB NOT NULL);
CREATE TABLE issue(issue_id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES source_file(source_id), field VARCHAR(128), original TEXT, cleaned TEXT, action VARCHAR(128), detail TEXT);
CREATE TABLE gene(gene_id INTEGER PRIMARY KEY, mgi_id VARCHAR(32) UNIQUE, symbol VARCHAR(128) NOT NULL UNIQUE);
CREATE TABLE parameter(parameter_id VARCHAR(64) PRIMARY KEY, original_id INTEGER UNIQUE, name VARCHAR(255) NOT NULL, description TEXT);
CREATE TABLE parameter_reference(original_id INTEGER PRIMARY KEY, parameter_id VARCHAR(64) REFERENCES parameter(parameter_id), name VARCHAR(255), description TEXT);
CREATE TABLE procedure_info(procedure_id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL, description TEXT, UNIQUE(name));
CREATE TABLE procedure_parameter(procedure_id INTEGER REFERENCES procedure_info(procedure_id), parameter_id VARCHAR(64) REFERENCES parameter(parameter_id), original_id INTEGER REFERENCES parameter_reference(original_id), is_mandatory INTEGER, PRIMARY KEY(procedure_id,original_id));
CREATE TABLE parameter_group(group_id INTEGER PRIMARY KEY, name VARCHAR(128) UNIQUE NOT NULL, rule TEXT NOT NULL);
CREATE TABLE parameter_group_member(parameter_id VARCHAR(64) REFERENCES parameter(parameter_id), group_id INTEGER REFERENCES parameter_group(group_id), PRIMARY KEY(parameter_id,group_id));
CREATE TABLE genotype(genotype_id INTEGER PRIMARY KEY, gene_id INTEGER NOT NULL REFERENCES gene(gene_id), allele_symbol VARCHAR(255), strain_name VARCHAR(128), UNIQUE(gene_id,allele_symbol,strain_name));
CREATE TABLE analysis(analysis_id VARCHAR(32) PRIMARY KEY, genotype_id INTEGER NOT NULL REFERENCES genotype(genotype_id), parameter_id VARCHAR(64) REFERENCES parameter(parameter_id), life_stage VARCHAR(64), p_value DOUBLE CHECK(p_value IS NULL OR (p_value>=0 AND p_value<=1)), q_gene_bh DOUBLE, q_global_bh DOUBLE, source_id INTEGER REFERENCES source_file(source_id));
CREATE TABLE analysis_source(analysis_id VARCHAR(32) REFERENCES analysis(analysis_id), source_id INTEGER REFERENCES source_file(source_id), PRIMARY KEY(analysis_id,source_id));
CREATE TABLE tissue(tissue_id INTEGER PRIMARY KEY, name VARCHAR(64) UNIQUE);
CREATE TABLE lacz_observation(analysis_id VARCHAR(32) REFERENCES analysis(analysis_id), tissue_id INTEGER REFERENCES tissue(tissue_id), status VARCHAR(32), PRIMARY KEY(analysis_id,tissue_id));
CREATE TABLE human_gene(hgnc_id VARCHAR(32) PRIMARY KEY, symbol VARCHAR(128), name TEXT);
CREATE TABLE ortholog(mouse_gene_id INTEGER REFERENCES gene(gene_id), hgnc_id VARCHAR(32) REFERENCES human_gene(hgnc_id), PRIMARY KEY(mouse_gene_id,hgnc_id));
CREATE TABLE disease(do_id VARCHAR(32) PRIMARY KEY, name VARCHAR(255));
CREATE TABLE human_gene_disease(hgnc_id VARCHAR(32) REFERENCES human_gene(hgnc_id), do_id VARCHAR(32) REFERENCES disease(do_id), PRIMARY KEY(hgnc_id,do_id));
CREATE TABLE disease_mouse_model(hgnc_id VARCHAR(32), do_id VARCHAR(32), mgi_genotype_id VARCHAR(32), PRIMARY KEY(hgnc_id,do_id,mgi_genotype_id), FOREIGN KEY(hgnc_id,do_id) REFERENCES human_gene_disease(hgnc_id,do_id));
CREATE TABLE protein(protein_id INTEGER PRIMARY KEY, db_name VARCHAR(64), accession VARCHAR(64), gene_id INTEGER REFERENCES gene(gene_id), object_name TEXT, object_type VARCHAR(64), UNIQUE(db_name,accession));
CREATE TABLE protein_synonym(protein_id INTEGER REFERENCES protein(protein_id), synonym VARCHAR(255), PRIMARY KEY(protein_id,synonym));
CREATE TABLE go_term(go_id VARCHAR(32) PRIMARY KEY, aspect VARCHAR(1));
CREATE TABLE go_annotation(annotation_id INTEGER PRIMARY KEY, protein_id INTEGER REFERENCES protein(protein_id), go_id VARCHAR(32) REFERENCES go_term(go_id), evidence VARCHAR(8), annotation_date VARCHAR(10), assigned_by VARCHAR(128), annotation_extension TEXT, product_form_id VARCHAR(255), source_id INTEGER REFERENCES source_file(source_id), source_line INTEGER);
CREATE TABLE go_qualifier(annotation_id INTEGER REFERENCES go_annotation(annotation_id), value VARCHAR(128), PRIMARY KEY(annotation_id,value));
CREATE TABLE go_reference(annotation_id INTEGER REFERENCES go_annotation(annotation_id), value VARCHAR(255), PRIMARY KEY(annotation_id,value));
CREATE TABLE go_with_from(annotation_id INTEGER REFERENCES go_annotation(annotation_id), value VARCHAR(255), PRIMARY KEY(annotation_id,value));
CREATE TABLE go_taxon(annotation_id INTEGER REFERENCES go_annotation(annotation_id), value VARCHAR(64), PRIMARY KEY(annotation_id,value));
CREATE INDEX idx_analysis_genotype ON analysis(genotype_id);
CREATE INDEX idx_analysis_parameter ON analysis(parameter_id);
CREATE INDEX idx_go_protein ON go_annotation(protein_id);
CREATE INDEX idx_go_term ON go_annotation(go_id);
CREATE INDEX idx_genotype_gene ON genotype(gene_id);
'''

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',required=True);parser.add_argument('--out',default='.')
    args=parser.parse_args();src=pathlib.Path(args.input);out=pathlib.Path(args.out);out.mkdir(exist_ok=True,parents=True)
    for d in ['data','database','results','figures']: (out/d).mkdir(exist_ok=True)
    db=out/'database/group16.sqlite';db.unlink(missing_ok=True)
    con=sqlite3.connect(db);con.execute('PRAGMA foreign_keys=ON');con.executescript(SCHEMA)
    def insert(table,row,ignore=False):
        con.execute('INSERT '+('OR IGNORE ' if ignore else '')+'INTO '+table+' VALUES ('+','.join('?' for _ in row)+')',row)
    nsource=0; nissue=0
    def archive(path,b):
        nonlocal nsource
        nsource+=1;insert('source_file',(nsource,path,hashlib.sha256(b).hexdigest(),b));return nsource
    def issue(sid,field,old,new,action,detail=''):
        nonlocal nissue
        nissue+=1;insert('issue',(nissue,sid,field,old,new,action,detail))
    aux={};auxid={}
    for f in sorted(src.iterdir()):
        if f.suffix.lower() in {'.txt','.csv'}:
            b=f.read_bytes();aux[f.name]=b.decode('utf-8-sig');auxid[f.name]=archive(f.name,b)
    genes={}; by_mgi={}
    def gene(symbol,mgi=None):
        symbol=text(symbol)
        if mgi and mgi in by_mgi:return by_mgi[mgi]
        if symbol in genes:
            gid=genes[symbol]
            if mgi:
                con.execute('UPDATE gene SET mgi_id=COALESCE(mgi_id,?) WHERE gene_id=?',(mgi,gid));by_mgi[mgi]=gid
            return gid
        gid=len(genes)+1;genes[symbol]=gid
        if mgi:by_mgi[mgi]=gid
        insert('gene',(gid,mgi,symbol));return gid
    # Disease file is TSV with comments, not a CSV and not headered.
    disease_rows=[]
    for line_no,line in enumerate(aux['Disease_information.txt'].splitlines(),1):
        if not line or line.startswith('#'):continue
        r=line.split('\t')
        if len(r)!=8:
            issue(auxid['Disease_information.txt'],'line',line,None,'quarantine',f'line {line_no}: expected 8 fields');continue
        hs,hn,hid,dn,did,models,ms,mid=map(lambda x:x.strip(),r)
        gid=gene(ms,mid);insert('human_gene',(hid,hs,hn),True);insert('ortholog',(gid,hid),True)
        if did:
            insert('disease',(did,dn),True);insert('human_gene_disease',(hid,did),True)
            for model in set(models.split('|'))- {''}:insert('disease_mouse_model',(hid,did,model),True)
        disease_rows.append(r)
    params={}; orig={}
    for r in csv.DictReader(io.StringIO(aux['IMPC_parameter_description.txt']),skipinitialspace=True):
        pid=r['parameterId'].strip();oid=int(r['impcParameterOrigId']);name=r['name'].strip();desc=text(r['description'])
        orig[oid]=pid
        if pid not in params:
            params[pid]=name;insert('parameter',(pid,oid,name,desc))
        else:issue(auxid['IMPC_parameter_description.txt'],'parameterId',pid,pid,'repeated_stable_id','all original-ID variants retained in parameter_reference')
        insert('parameter_reference',(oid,pid,name,desc),True)
    proc={}
    for r in csv.DictReader(io.StringIO(aux['IMPC_procedure.txt']),skipinitialspace=True):
        name=r['name'].strip();desc=text(r['description']);oid=int(r['impcParameterOrigId'])
        if name not in proc:
            proc[name]=len(proc)+1;insert('procedure_info',(proc[name],name,desc))
        if oid not in orig:
            issue(auxid['IMPC_procedure.txt'],'impcParameterOrigId',str(oid),None,'unlinked_reference');continue
        insert('procedure_parameter',(proc[name],orig[oid],oid,int(r['isMandatory'].strip().upper()=='TRUE')),True)
    rules=[('weight',r'\bweight\b'),('images',r'\b(image|images|imaging|photograph|photographs)\b'),('brain',r'\b(brain|cerebr\w*|cerebell\w*|hippocamp\w*|cortex|cortical)\b'),('blood',r'\b(blood|hemat\w*|haemat\w*|hemoglobin|haemoglobin|erythrocyt\w*|leukocyt\w*|platelet\w*)\b'),('cardiovascular',r'\b(heart|cardiac|ecg|electrocardio\w*|ventric\w*|aortic|pulse)\b'),('eye_vision',r'\b(eye|vision|visual|retina\w*|cornea\w*|pupil\w*|ocular)\b'),('hearing',r'\b(hearing|auditory|acoustic|abr|ear)\b'),('grip_strength',r'\b(grip|strength)\b')]
    for i,(name,pattern) in enumerate(rules,1):
        insert('parameter_group',(i,name,pattern))
        for pid,pname in params.items():
            if re.search(pattern,pname,re.I):insert('parameter_group_member',(pid,i))
    # Preserve every source file; parse vertical key/value records with line-level recovery.
    records=[];field_names=['gene_accession_id','gene_symbol','allele_symbol','strain_name','parameter_stable_id','p_value','parameter_name','mouse_life_stage','analysis_id']
    tissues=['blood','brain','colon','eye','heart','kidney','liver','lung','skeletal_muscle','skin','vascular_system']
    keys=field_names+['lacz_'+t for t in tissues];key_lookup=unique_lookup(keys)
    with zipfile.ZipFile(src/'group16_data.zip') as z:
        paths=sorted(n for n in z.namelist() if n.endswith('.csv') and not n.startswith('__MACOSX'))
        for path in paths:
            b=z.read(path);sid=archive(path,b);raw=b.decode('utf-8-sig');r={};failed=False
            for ln,line in enumerate(raw.splitlines(),1):
                if not line.strip():continue
                try: pair=next(csv.reader([line]))
                except csv.Error:pair=[]
                if len(pair)!=2:
                    # Limited fallback for the observed broken separator; preserve audit trail.
                    m=re.fullmatch(r'"?(lacz_[a-z_]+)"?\t+"?(.*?)"?',line)
                    if m:pair=[m[1],m[2].strip('"')];issue(sid,'line',line,json.dumps(pair),'repair_separator')
                    else:
                        issue(sid,'line',line,None,'quarantine_field',f'line {ln}');continue
                k,v=pair;kclean=repair(k,key_lookup)
                if kclean is None and k in tissues:kclean='lacz_'+k
                if kclean is None:
                    issue(sid,'key',k,None,'quarantine_field');continue
                if kclean!=k:issue(sid,'key',k,kclean,'repair_key')
                if kclean in r:
                    issue(sid,kclean,r[kclean],v,'duplicate_key');failed=True
                r[kclean]=v
            records.append({'sid':sid,'path':path,'raw':r,'parse_conflict':failed})
    # Build reference maps only from valid IDs/symbols, using observed consensus plus disease reference.
    observed_params=collections.defaultdict(collections.Counter)
    for item in records:
        rr=item['raw'];pid=text(rr.get('parameter_stable_id'));pn=text(rr.get('parameter_name'))
        if pid and re.fullmatch(r'(?:IMPC|MGP|ESLIM)_[A-Z0-9]+_\d{3}_\d{3}',pid) and pn:observed_params[pid][pn]+=1
    for pid,counter in observed_params.items():
        if pid not in params:
            pname=counter.most_common(1)[0][0];params[pid]=pname
            insert('parameter',(pid,None,pname,None))
            issue(auxid['IMPC_parameter_description.txt'],'parameterId',pid,pid,'experimental_parameter_only','valid-format ID in experimental data; no supplied procedure reference')
            for i,(_,pattern) in enumerate(rules,1):
                if re.search(pattern,pname,re.I):insert('parameter_group_member',(pid,i),True)
    pidlookup=unique_lookup(params)
    names=collections.defaultdict(set)
    for pid,name in params.items():names[sig(name)].add(pid)
    # Resolve case variants globally before accession consensus; a one-off uppercase
    # variant must not make the common official symbol ambiguous.
    symbol_counts=collections.defaultdict(collections.Counter)
    for item in records:
        s=text(item['raw'].get('gene_symbol'))
        if s and re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*',s):symbol_counts[s.lower()][s]+=1
    official={s.lower():s for s in genes}
    official.update({k:v.most_common(1)[0][0] for k,v in symbol_counts.items() if k not in official})
    consensus=collections.defaultdict(collections.Counter)
    for item in records:
        r=item['raw'];mid=text(r.get('gene_accession_id'));s=text(r.get('gene_symbol'))
        if mid and re.fullmatch(r'MGI:\d+',mid) and s and s.lower() in official:consensus[mid][official[s.lower()]]+=1
    mid_to_symbol={mid:next(k for k,v in genes.items() if v==gid) for mid,gid in by_mgi.items()}
    for mid,c in consensus.items():
        ranked=c.most_common()
        if mid not in mid_to_symbol and (len(ranked)==1 or ranked[0][1]>ranked[1][1]):mid_to_symbol[mid]=ranked[0][0]
    symbol_lookup=unique_lookup(set(mid_to_symbol.values()));midlookup=unique_lookup(mid_to_symbol)
    symbol_to_mids=collections.defaultdict(set)
    for m,s in mid_to_symbol.items():symbol_to_mids[s].add(m)
    allele_refs=collections.defaultdict(collections.Counter)
    for item in records:
        r=item['raw'];s=repair(r.get('gene_symbol'),symbol_lookup);a=text(r.get('allele_symbol'))
        if s and a and re.fullmatch(re.escape(s)+r'<[A-Za-z0-9.()_-]+>',a) and a.count('(')==a.count(')'):allele_refs[s][a]+=1
    allele_lookup={}
    for s,counter in allele_refs.items():
        families=collections.defaultdict(list)
        for a,n in counter.items():families[sig(a)].append((n,a))
        representatives=[]
        for variants in families.values():
            variants.sort(reverse=True)
            if len(variants)>1 and variants[0][0]>=3 and variants[0][0]>=3*variants[1][0]:representatives.append(variants[0][1])
            else:representatives.extend(a for n,a in variants)
        allele_lookup[s]=unique_lookup(representatives)
    stages=['E12.5','E15.5','E18.5','E9.5','Early adult','Late adult','Middle aged adult'];stage_lookup=unique_lookup(stages)
    statuses=['No data','ambiguous','expression','imageOnly','no expression','tissue not available'];status_lookup=unique_lookup(statuses)
    strains=['B6Brd;B6Dnk;B6N-Tyr<c-Brd>','C57BL/6Brd-Tyr<c-Brd>','C57BL/6Dnk','C57BL/6JTyr;C57BL/6N','C57BL/6N','C57BL/6NCrl','C57BL/6NJ','C57BL/6NTac','C57BL/6NTacDen'];strain_lookup=unique_lookup(strains)
    genotypes={};analyses={};unresolved=collections.Counter()
    for i,t in enumerate(tissues,1):insert('tissue',(i,t))
    for item in records:
        r=item['raw'];sid=item['sid'];clean={}
        mid=repair(r.get('gene_accession_id'),midlookup);s=repair(r.get('gene_symbol'),symbol_lookup)
        if mid:
            expected=mid_to_symbol[mid]
            if s and s!=expected:
                issue(sid,'gene_symbol',s,expected,'accession_symbol_conflict');s=None
            else:s=expected
        elif s and len(symbol_to_mids[s])==1:mid=next(iter(symbol_to_mids[s]))
        pid=repair(r.get('parameter_stable_id'),pidlookup)
        if not pid and len(names[sig(r.get('parameter_name'))])==1:pid=next(iter(names[sig(r.get('parameter_name'))]))
        clean.update(gene_accession_id=mid,gene_symbol=s,parameter_stable_id=pid,parameter_name=params.get(pid))
        a=text(r.get('allele_symbol'));clean['allele_symbol']=repair(a,allele_lookup.get(s,{}))
        clean['strain_name']=repair(r.get('strain_name'),strain_lookup);clean['mouse_life_stage']=repair(r.get('mouse_life_stage'),stage_lookup)
        p=text(r.get('p_value'))
        try:p=float(p) if p is not None else None
        except ValueError:p=None
        if p is not None and (not math.isfinite(p) or not 0<=p<=1):p=None
        clean['p_value']=p
        aid=text(r.get('analysis_id'));fileaid=re.search(r'an\d{10}',pathlib.PurePosixPath(item['path']).name)
        if not aid or not re.fullmatch(r'an\d{10}',aid):aid=fileaid[0] if fileaid else None
        clean['analysis_id']=aid
        for t in tissues:clean['lacz_'+t]=repair(r.get('lacz_'+t),status_lookup)
        for k,v in clean.items():
            old=r.get(k);same=(old is not None and str(v)==old)
            if k=='p_value' and v is not None:
                try:same=float(old)==v
                except (ValueError,TypeError):same=False
            if not same:
                action='missing' if text(old) is None and v is None else ('unresolved' if v is None else 'canonicalize_or_recover')
                issue(sid,k,old,None if v is None else str(v),action)
                if v is None:unresolved[k]+=1
        if item['parse_conflict'] or not s or not aid or not clean['allele_symbol'] or not clean['strain_name']:
            issue(sid,'record',json.dumps(clean),None,'quarantine_analysis','unresolved gene, allele, strain, ID or duplicate field');continue
        if aid in analyses:
            old=analyses[aid]
            if old['clean']==clean:insert('analysis_source',(aid,sid));issue(sid,'analysis_id',aid,aid,'duplicate_analysis')
            else:issue(sid,'analysis_id',aid,None,'conflicting_duplicate','variant excluded; original preserved in source_file')
            continue
        gid=gene(s,mid);gt=(gid,clean['allele_symbol'],clean['strain_name'])
        if gt not in genotypes:
            genotypes[gt]=len(genotypes)+1;insert('genotype',(genotypes[gt],*gt))
        insert('analysis',(aid,genotypes[gt],pid,clean['mouse_life_stage'],p,None,None,sid));insert('analysis_source',(aid,sid))
        for i,t in enumerate(tissues,1):insert('lacz_observation',(aid,i,clean['lacz_'+t]))
        analyses[aid]={'clean':clean,'gene':s}
    # Detect conflicting duplicates and exclude ALL competing versions from analytical output.
    conflicts=[r[0] for r in con.execute("SELECT DISTINCT original FROM issue WHERE action='conflicting_duplicate'")]
    for aid in conflicts:
        con.execute('DELETE FROM lacz_observation WHERE analysis_id=?',(aid,));con.execute('DELETE FROM analysis_source WHERE analysis_id=?',(aid,));con.execute('DELETE FROM analysis WHERE analysis_id=?',(aid,));analyses.pop(aid,None)
    ids=list(analyses);globalq=bh([analyses[x]['clean']['p_value'] for x in ids]);pergene=collections.defaultdict(list)
    for aid in ids:pergene[analyses[aid]['gene']].append(aid)
    for s,aids in pergene.items():
        for aid,q in zip(aids,bh([analyses[x]['clean']['p_value'] for x in aids])):con.execute('UPDATE analysis SET q_gene_bh=? WHERE analysis_id=?',(q,aid))
    for aid,q in zip(ids,globalq):con.execute('UPDATE analysis SET q_global_bh=? WHERE analysis_id=?',(q,aid))
    proteins={};go_bad=0
    for ln,line in enumerate(aux['bespokeTask_GO.txt'].splitlines(),1):
        r=line.split('\t')
        if len(r)!=17 or not re.fullmatch(r'GO:\d{7}',r[4]) or r[8] not in {'F','P','C'} or 'taxon:10090' not in r[12].split('|') or not re.fullmatch(r'\d{8}',r[13]):
            issue(auxid['bespokeTask_GO.txt'],'line',line,None,'quarantine_go',f'line {ln}: incomplete/invalid GAF record');go_bad+=1;continue
        dbn,acc,s,qual,go,refs,ev,wf,aspect,oname,syn,otype,taxa,date,assigned,ext,form=r
        gid=gene(s);pk=(dbn,acc)
        if pk not in proteins:
            proteins[pk]=len(proteins)+1;insert('protein',(proteins[pk],dbn,acc,gid,oname,otype))
        else:
            prev=con.execute('SELECT gene_id,object_name,object_type FROM protein WHERE protein_id=?',(proteins[pk],)).fetchone()
            if prev!=(gid,oname,otype):issue(auxid['bespokeTask_GO.txt'],'protein',json.dumps(r),None,'protein_metadata_conflict',f'line {ln}')
        prot=proteins[pk]
        for sy in set(syn.split('|'))-{''}:insert('protein_synonym',(prot,sy),True)
        insert('go_term',(go,aspect),True)
        aid=ln;insert('go_annotation',(aid,prot,go,ev,date,assigned,text(ext),text(form),auxid['bespokeTask_GO.txt'],ln))
        for table,value in [('go_qualifier',qual),('go_reference',refs),('go_with_from',wf),('go_taxon',taxa)]:
            for v in set(value.split('|'))-{''}:insert(table,(aid,v))
    con.commit()
    # Views join independent one-to-many relations separately to prevent row multiplication.
    con.executescript('''CREATE VIEW analysis_view AS SELECT a.*,g.symbol,g.mgi_id,gt.allele_symbol,gt.strain_name,p.name AS parameter_name FROM analysis a JOIN genotype gt USING(genotype_id) JOIN gene g USING(gene_id) LEFT JOIN parameter p USING(parameter_id);
CREATE VIEW gene_go_view AS SELECT g.symbol,pr.db_name,pr.accession,ga.*,t.aspect,(SELECT GROUP_CONCAT(value) FROM go_qualifier q WHERE q.annotation_id=ga.annotation_id) AS qualifier FROM go_annotation ga JOIN protein pr USING(protein_id) JOIN gene g USING(gene_id) JOIN go_term t USING(go_id);
''')
    def export(query,path):
        c=con.execute(query)
        with path.open('w',encoding='utf-8',newline='') as f:
            w=csv.writer(f);w.writerow([d[0] for d in c.description]);w.writerows(c)
    export('SELECT * FROM analysis_view',out/'data/analyses.csv')
    for t in ['gene','parameter','parameter_reference','parameter_group','parameter_group_member','procedure_info','procedure_parameter']:
        export('SELECT * FROM '+t,out/f'data/{t}.csv')
    export('SELECT * FROM issue',out/'results/cleaning_audit.csv')
    export('SELECT * FROM gene_go_view',out/'data/go_annotations.csv')
    export('SELECT g.symbol,h.hgnc_id,h.symbol AS human_symbol,d.do_id,d.name AS disease_name FROM ortholog o JOIN gene g ON g.gene_id=o.mouse_gene_id JOIN human_gene h USING(hgnc_id) LEFT JOIN human_gene_disease hd USING(hgnc_id) LEFT JOIN disease d USING(do_id)',out/'data/disease_links.csv')
    querygenes=[x.strip() for x in aux['group16_query_genes.csv'].splitlines() if x.strip()]
    (out/'data/query_genes.json').write_text(json.dumps(querygenes),encoding='utf-8')
    export("SELECT * FROM analysis_view WHERE symbol IN ("+','.join("'"+s.replace("'","''")+"'" for s in querygenes)+') ORDER BY symbol,p_value',out/'results/query_gene_analyses.csv')
    counts={t:con.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    querysummary=[]
    for s in querygenes:
        vals=con.execute('SELECT COUNT(*),COUNT(DISTINCT genotype_id),COUNT(p_value),SUM(CASE WHEN p_value<0.05 THEN 1 ELSE 0 END),SUM(CASE WHEN q_gene_bh<0.05 THEN 1 ELSE 0 END),MIN(p_value) FROM analysis_view WHERE symbol=?',(s,)).fetchone()
        go_count=con.execute('SELECT COUNT(*) FROM gene_go_view WHERE symbol=?',(s,)).fetchone()[0]
        dc=con.execute('SELECT COUNT(DISTINCT d.do_id) FROM gene g JOIN ortholog o ON g.gene_id=o.mouse_gene_id JOIN human_gene_disease d USING(hgnc_id) WHERE g.symbol=?',(s,)).fetchone()[0]
        querysummary.append(dict(zip(['gene','analyses','genotypes','valid_p','nominal_p_lt_005','gene_bh_lt_005','min_p','go_annotations','diseases'],[s,*vals,go_count,dc])))
    summary={'input_csv_files':len(records),'tables':counts,'issue_actions':dict(con.execute('SELECT action,COUNT(*) FROM issue GROUP BY action')),'unresolved_fields':dict(unresolved),'conflicting_analysis_ids':conflicts,'query_genes':querysummary,'parameter_groups':dict(con.execute('SELECT g.name,COUNT(m.parameter_id) FROM parameter_group g LEFT JOIN parameter_group_member m USING(group_id) GROUP BY g.name')),'go_truncated_rows':go_bad,'foreign_key_errors':con.execute('PRAGMA foreign_key_check').fetchall(),'integrity':con.execute('PRAGMA integrity_check').fetchone()[0]}
    (out/'results/validation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    # MySQL 8 portable export. Hex literals preserve raw bytes and Unicode without escape modes.
    mysql_lines=[]
    for line in SCHEMA.replace(' BLOB',' LONGBLOB').replace(' TEXT',' LONGTEXT').splitlines():
        fks=[]
        def foreign(match):
            col,typ,required,target,ref=match.groups()
            fks.append(f'FOREIGN KEY ({col}) REFERENCES {target}({ref})')
            return col+' '+typ+required
        line=re.sub(r'(\w+) (INTEGER|VARCHAR\(\d+\))((?: NOT NULL)?) REFERENCES (\w+)\((\w+)\)',foreign,line)
        if fks:line=line[:-2]+', '+', '.join(fks)+');'
        mysql_lines.append(line)
    mysqlschema='\n'.join(mysql_lines)
    (out/'database/schema.sql').write_text(mysqlschema,encoding='utf-8')
    tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    def sqlval(v):
        if v is None:return 'NULL'
        if isinstance(v,bytes):return "X'"+v.hex()+"'"
        if isinstance(v,str):return "CONVERT(X'"+v.encode('utf-8').hex()+"' USING utf8mb4)"
        return repr(v)
    with (out/'database/group16_mysql.sql').open('w',encoding='utf-8') as f:
        f.write('-- Generated SQL export, NOT a server-produced mysqldump. Import into a NEW MySQL 8 database.\nCREATE DATABASE IF NOT EXISTS group16_impc CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;\nUSE group16_impc;\nSET FOREIGN_KEY_CHECKS=0;\nSET NAMES utf8mb4;\n'+mysqlschema+'\nSTART TRANSACTION;\n')
        for table in tables:
            cursor=con.execute('SELECT * FROM '+table)
            while True:
                batch=cursor.fetchmany(100)
                if not batch:break
                f.write('INSERT INTO '+table+' VALUES\n'+',\n'.join('('+','.join(sqlval(v) for v in row)+')' for row in batch)+';\n')
        for (vsql,) in con.execute("SELECT sql FROM sqlite_master WHERE type='view'"):f.write(vsql+';\n')
        f.write('COMMIT;\nSET FOREIGN_KEY_CHECKS=1;\n')
    con.close();print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
