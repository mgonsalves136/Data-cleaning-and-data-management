source('scripts/bootstrap_R.R')
for(name in c('report_bilingual','report_english','README')) {
  md <- paste(readLines(paste0(name,'.md'),encoding='UTF-8',warn=FALSE),collapse='\n')
  body <- commonmark::markdown_html(md)
  doc <- paste0('<!doctype html><html><meta charset="utf-8"><title>',name,'</title><style>body{max-width:1000px;margin:40px auto;padding:0 24px;font:17px/1.8 system-ui;color:#18344b}img{max-width:100%}pre{background:#f2f5f8;padding:18px;overflow:auto}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:8px}h1,h2{line-height:1.3}@media print{body{font-size:11pt}img{max-height:8in;object-fit:contain}h2{break-after:avoid}}</style>',body,'</html>')
  writeLines(enc2utf8(doc),paste0(name,'.html'),useBytes=TRUE)
}
