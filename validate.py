"""Meaningful ingestion checks: provenance, FK integrity, duplicate exclusion,
BH calculation, ambiguous allele signatures, GO truncation, and cross-view counts.
Run after build.py, from project root: python scripts/validate.py
"""
import hashlib,json,pathlib,sqlite3
from build import bh,unique_lookup,repair
root=pathlib.Path(__file__).resolve().parents[1]
c=sqlite3.connect(root/'database/group16.sqlite');checks={}
def check(name,value):
    checks[name]=bool(value)
    if not value:raise AssertionError(name)
check('BH_known_example',all(abs(a-b)<1e-12 for a,b in zip(bh([.01,.04,.03]),[.03,.04,.04])))
check('BH_missing_preserved',bh([None,.02])==[None,.02])
lookup=unique_lookup(['Gene<tm1.1>','Gene<tm11>'])
check('exact_allele_survives_signature_collision',repair('Gene<tm1.1>',lookup)=='Gene<tm1.1>')
check('ambiguous_repair_rejected',repair('Gene<tm!11>',lookup) is None)
check('foreign_keys',c.execute('PRAGMA foreign_key_check').fetchall()==[])
check('sqlite_integrity',c.execute('PRAGMA integrity_check').fetchone()[0]=='ok')
check('raw_bytes_hashes',all(hashlib.sha256(b).hexdigest()==h for h,b in c.execute('SELECT sha256,raw_bytes FROM source_file')))
check('all_29877_experimental_files_archived',c.execute("SELECT COUNT(*) FROM source_file WHERE path LIKE 'group16_data/%.csv'").fetchone()[0]==29877)
check('analysis_view_preserves_cardinality',c.execute('SELECT COUNT(*) FROM analysis').fetchone()==c.execute('SELECT COUNT(*) FROM analysis_view').fetchone())
check('p_values_in_bounds',c.execute('SELECT COUNT(*) FROM analysis WHERE p_value<0 OR p_value>1').fetchone()[0]==0)
check('q_values_in_bounds',c.execute('SELECT COUNT(*) FROM analysis WHERE q_gene_bh<0 OR q_gene_bh>1 OR q_global_bh<0 OR q_global_bh>1').fetchone()[0]==0)
check('conflicting_duplicates_excluded',c.execute("SELECT COUNT(*) FROM analysis WHERE analysis_id IN (SELECT original FROM issue WHERE action='conflicting_duplicate')").fetchone()[0]==0)
check('all_tissues_accounted_for',c.execute('SELECT COUNT(*) FROM lacz_observation').fetchone()[0]==11*c.execute('SELECT COUNT(*) FROM analysis').fetchone()[0])
check('valid_GO_rows_retained',c.execute('SELECT COUNT(*) FROM go_annotation').fetchone()[0]==71546)
check('two_incomplete_GO_rows_quarantined',c.execute("SELECT COUNT(*) FROM issue WHERE action='quarantine_go'").fetchone()[0]==2)
check('five_query_genes',len(json.loads((root/'data/query_genes.json').read_text()))==5)
check('all_query_genes_have_retained_analyses',all(c.execute('SELECT COUNT(*) FROM analysis_view WHERE symbol=?',(s,)).fetchone()[0]>0 for s in json.loads((root/'data/query_genes.json').read_text())))
check('at_least_six_nonempty_groups',c.execute('SELECT COUNT(DISTINCT group_id) FROM parameter_group_member').fetchone()[0]>=6)
(root/'results/test_results.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
