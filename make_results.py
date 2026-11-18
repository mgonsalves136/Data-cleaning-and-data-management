"""Static previews from validated tables, not screenshots of a running Shiny app."""
import collections,csv,html,json,math,pathlib,re,sqlite3
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=pathlib.Path(__file__).resolve().parents[1]
FONT=pathlib.Path('C:/Windows/Fonts/arial.ttf')
if not FONT.exists():FONT=pathlib.Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
def font(size):return ImageFont.truetype(str(FONT),size) if FONT.exists() else ImageFont.load_default()
def canvas(title,subtitle,w=1600,h=1000):
 im=Image.new('RGB',(w,h),'#f7f9fc');d=ImageDraw.Draw(im);d.text((60,32),title,font=font(32),fill='#142e4c');d.text((60,82),subtitle,font=font(19),fill='#526475');return im,d
c=sqlite3.connect(ROOT/'database/group16.sqlite');c.row_factory=sqlite3.Row
summary=json.loads((ROOT/'results/validation.json').read_text())
for entry in summary['query_genes']:
 s=entry['gene'];rows=c.execute('SELECT * FROM analysis_view WHERE symbol=? AND p_value IS NOT NULL ORDER BY p_value,analysis_id LIMIT 25',(s,)).fetchall()
 im,d=canvas(s+' | phenotype association overview',f"Top {len(rows)} analyses by supplied p-value; {entry['analyses']} retained in total. Red: gene-wide BH q < 0.05.")
 left=710;right=1500;top=160;bottom=875;span=max(1,len(rows));maxscore=max([2]+[-math.log10(max(r['p_value'],1e-16)) for r in rows]);maxscore=math.ceil(maxscore)
 for tick in np.linspace(0,maxscore,5):
  x=left+(right-left)*tick/maxscore;d.line((x,top-10,x,bottom),fill='#dce3ec');d.text((x-15,bottom+15),f'{tick:.1f}',font=font(17),fill='#526475')
 threshold=left+(right-left)*(-math.log10(.05))/maxscore;d.line((threshold,top-10,threshold,bottom),fill='#b4a199',width=2)
 for i,r in enumerate(rows):
  y=top+(bottom-top)*(i+.5)/span;score=-math.log10(max(r['p_value'],1e-16));label=(r['parameter_name'] or r['parameter_id'] or 'Unresolved parameter')
  if len(label)>55:label=label[:52]+'...'
  d.text((60,y-10),label,font=font(17),fill='#263c55');d.text((560,y-9),r['analysis_id'],font=font(14),fill='#718094')
  x=left+(right-left)*score/maxscore;col='#ba3344' if r['q_gene_bh'] is not None and r['q_gene_bh']<.05 else '#527a9e';d.line((left,y,x,y),fill=col,width=3);d.ellipse((x-5,y-5,x+5,y+5),fill=col)
 d.text((left,930),'-log10(supplied p-value); zeros capped at 16 for display',font=font(19),fill='#263c55')
 d.text((60,970),'Static data preview generated in Python; export the live RShiny plot after running app.R.',font=font(15),fill='#526475')
 im.save(ROOT/f'figures/{s}_phenotypes.png')

# Match the Shiny default clustering policy: coverage-ranked genes, median scores,
# coverage filtering, high-variance parameters, median imputation and UPGMA.
data=collections.defaultdict(list)
for r in c.execute('SELECT symbol,parameter_id,p_value FROM analysis_view WHERE p_value IS NOT NULL AND parameter_id IS NOT NULL'):
 data[(r['symbol'],r['parameter_id'])].append(-math.log10(max(r['p_value'],1e-16)))
coverage=collections.Counter(s for s,p in data);gs=sorted(coverage,key=lambda s:(-coverage[s],s))[:60];pars=sorted({p for s,p in data if s in gs})
mat=np.array([[np.median(data[(s,p)]) if (s,p) in data else np.nan for p in pars] for s in gs])
keep=np.mean(np.isfinite(mat),axis=0)>=.2;mat=mat[:,keep];pars=np.array(pars)[keep]
variances=np.nanvar(mat,axis=0,ddof=1);keep=np.where(np.isfinite(variances)&(variances>0))[0];keep=sorted(keep,key=lambda j:(-variances[j],pars[j]))[:30];mat=mat[:,keep];pars=pars[keep]
keep=np.sum(np.isfinite(mat),axis=1)>=max(2,math.ceil(.5*mat.shape[1]));mat=mat[keep,:];gs=np.array(gs)[keep];imputed=float(np.isnan(mat).mean())
med=np.nanmedian(mat,axis=0);mat=np.where(np.isnan(mat),med,mat)
clusters={i:[i] for i in range(len(gs))};dist={(i,j):float(np.linalg.norm(mat[i]-mat[j])) for i in clusters for j in clusters if i<j};nextid=len(gs);cuts=None
while len(clusters)>1:
 if len(clusters)==4:cuts=[v[:] for v in clusters.values()]
 i,j=min(dist,key=lambda k:(dist[k],k));ni,nj=len(clusters[i]),len(clusters[j]);others=[k for k in clusters if k not in (i,j)]
 newdist={k:(ni*dist[tuple(sorted((i,k)))]+nj*dist[tuple(sorted((j,k)))])/(ni+nj) for k in others}
 merged=clusters.pop(i)+clusters.pop(j);dist={k:v for k,v in dist.items() if i not in k and j not in k}
 for k,v in newdist.items():dist[tuple(sorted((k,nextid)))]=v
 clusters[nextid]=merged;nextid+=1
order=next(iter(clusters.values()));membership={idx:k+1 for k,cl in enumerate(cuts or [order]) for idx in cl}
with (ROOT/'results/gene_clusters.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.writer(f);w.writerow(['gene','cluster']);w.writerows((gs[i],membership[i]) for i in order)
height=max(950,500+len(gs)*32)
im,d=canvas('Gene clusters | phenotype score similarity',f'{len(gs)} genes x {len(pars)} parameters | {imputed:.1%} median-imputed cells | average-linkage Euclidean distance',1800,height)
x0=250;y0=170;cw=45;ch=32;maximum=max(1,float(mat.max()))
for ii,i in enumerate(order):
 y=y0+ii*ch;d.text((50,y),f'{membership[i]}  {gs[i]}',font=font(14),fill='#263c55')
 for j in range(len(pars)):
  t=mat[i,j]/maximum;col=tuple(int(a+(b-a)*t) for a,b in zip((241,246,251),(164,27,61)));d.rectangle((x0+j*cw,y,x0+(j+1)*cw-1,y+ch-1),fill=col)
for j,p in enumerate(pars):
 label=Image.new('RGB',(220,20),'#f7f9fc');ld=ImageDraw.Draw(label);ld.text((0,0),str(p),font=font(13),fill='#263c55');label=label.rotate(90,expand=True);im.paste(label,(x0+j*cw+10,y0+len(gs)*ch+12))
legend_y=height-120
for j in range(400):
 t=j/399;col=tuple(int(a+(b-a)*t) for a,b in zip((241,246,251),(164,27,61)));d.line((300+j,legend_y,300+j,legend_y+20),fill=col)
d.text((300,legend_y+25),'0',font=font(16),fill='#263c55');d.text((670,legend_y+25),f'{maximum:.1f}',font=font(16),fill='#263c55');d.text((740,legend_y),'Median capped -log10(p)',font=font(19),fill='#263c55')
d.text((50,height-45),'Scores lack effect direction; clusters depend on coverage and imputation. Static preview, not an RShiny screenshot.',font=font(17),fill='#526475')
im.save(ROOT/'figures/gene_clusters.png')
(ROOT/'results/clustering_summary.json').write_text(json.dumps({'genes':len(gs),'parameters':len(pars),'imputed_fraction':imputed,'clusters':dict(collections.Counter(membership.values()))},indent=2))

# Readable high-level schema diagram; the SQL is the full field-level schema.
im,d=canvas('Group16 | relational database schema','Arrows indicate foreign-key relationships. Full columns and constraints: database/schema.sql',1800,1100)
boxes={
 'Gene':(70,180,480,320,['gene (MGI ID + mouse symbol)','genotype (allele + strain)']),
 'Analysis':(690,180,1110,370,['analysis (p, BH q, life stage)','analysis_source','lacz_observation -> tissue']),
 'Parameters':(1300,180,1730,430,['parameter','parameter_reference (original IDs)','procedure_parameter -> procedure_info','parameter_group_member -> parameter_group']),
 'Disease':(70,540,570,800,['ortholog -> human_gene','human_gene_disease -> disease','disease_mouse_model (external genotype IDs)']),
 'GO':(690,560,1220,900,['protein -> protein_synonym','go_annotation -> go_term','go_qualifier / go_reference','go_with_from / go_taxon']),
 'Provenance':(1300,610,1730,820,['source_file (raw bytes + SHA-256)','issue (field-level audit)','raw incomplete rows preserved'])}
for name,(x1,y1,x2,y2,lines) in boxes.items():
 d.rounded_rectangle((x1,y1,x2,y2),radius=15,fill='white',outline='#9bafc5',width=2);d.text((x1+20,y1+15),name,font=font(25),fill='#142e4c')
 for j,line in enumerate(lines):d.text((x1+20,y1+58+j*36),line,font=font(17),fill='#526475')
def arrow(a,b):
 d.line((*a,*b),fill='#437aab',width=4);angle=math.atan2(b[1]-a[1],b[0]-a[0]);d.polygon([b,(b[0]-15*math.cos(angle-.5),b[1]-15*math.sin(angle-.5)),(b[0]-15*math.cos(angle+.5),b[1]-15*math.sin(angle+.5))],fill='#437aab')
arrow((690,245),(480,245));arrow((1110,275),(1300,275));arrow((320,540),(320,320));arrow((690,650),(480,320));arrow((1110,340),(1390,610));arrow((1120,560),(1400,610))
d.text((70,1015),'Raw and curated layers are separate. Independent many-to-many relations are aggregated before joining to avoid inflated analysis counts.',font=font(21),fill='#263c55');im.save(ROOT/'figures/database_schema.png')

report_table=''.join('<tr>'+''.join('<td>'+html.escape(str(e[k]))+'</td>' for k in ['gene','analyses','genotypes','valid_p','nominal_p_lt_005','gene_bh_lt_005','go_annotations','diseases'])+'</tr>' for e in summary['query_genes'])
live=(ROOT/'figures/shiny_exports/Gna11.png').exists()
gallery=''.join(f'<h2>{e["gene"]}</h2><img src="'+(f'figures/shiny_exports/{e["gene"]}.png' if live else f'figures/{e["gene"]}_phenotypes.png')+'">' for e in summary['query_genes'])
page='''<!doctype html><html lang="zh"><meta charset="utf-8"><title>Group16 results</title><style>body{max-width:1200px;margin:40px auto;padding:0 24px;font:17px/1.6 system-ui;color:#19334e;background:#f7f9fc}img{max-width:100%;border:1px solid #ccd5e0}table{border-collapse:collapse;background:white}td,th{padding:9px;border:1px solid #ccd5e0}a{color:#216b9d}.note{padding:20px;background:#fff1cd}</style><h1>Group16 数据与结果</h1><p class="note">此页面展示经过实际清洗计算的静态结果，不是已运行 RShiny 的截图。R 与 MySQL 运行仍需在安装相应环境后完成。当前成果尚未发布至 GitHub。</p><p><a href="report_bilingual.md">中英文对照报告（侧重 RShiny）</a> · <a href="README_中文.md">运行与验收说明</a> · <a href="results/validation.json">数据验证结果</a></p><table><tr><th>Gene</th><th>Analyses</th><th>Genotypes</th><th>Valid p</th><th>p&lt;.05</th><th>Gene BH&lt;.05</th><th>GO rows</th><th>Disease terms</th></tr>'''+report_table+'</table>'+gallery+'<h2>Gene clusters</h2><img src="figures/gene_clusters.png"><h2>Database schema</h2><img src="figures/database_schema.png"></html>'
if live:
 page=page.replace('此页面展示经过实际清洗计算的静态结果，不是已运行 RShiny 的截图。R 与 MySQL 运行仍需在安装相应环境后完成。当前成果尚未发布至 GitHub。','RShiny 已实际启动，并通过 CSV 与 MySQL 两种模式的测试；下方基因图与聚类图由实际 Shiny 服务端绘图逻辑导出。MySQL 导入、查询及服务器原生备份已完成。按要求暂不发布 GitHub。')
 page=page.replace('report_bilingual.md','report_bilingual.html').replace('README_中文.md','README.html').replace('figures/gene_clusters.png','figures/shiny_exports/gene_clusters.png')
 page=page.replace('<h2>Gene clusters</h2>','<h2>Phenotype → genotypes</h2><img src="figures/shiny_exports/phenotype_to_genotypes.png"><h2>Gene clusters</h2>')
(ROOT/'index.html').write_text(page,encoding='utf-8')
print('Figures and result gallery written.')
