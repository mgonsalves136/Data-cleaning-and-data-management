# No contributed packages required. Independent BH cross-check against stats.
a <- read.csv('data/analyses.csv',stringsAsFactors=FALSE,na.strings=c('','NA'))
stopifnot(nrow(a)==29254)
expected <- p.adjust(a$p_value,method='BH',n=sum(!is.na(a$p_value)))
stopifnot(isTRUE(all.equal(expected,a$q_global_bh,tolerance=1e-12,check.attributes=FALSE)))
for (s in unique(a$symbol)) {
  keep <- a$symbol==s
  expected <- p.adjust(a$p_value[keep],method='BH',n=sum(!is.na(a$p_value[keep])))
  stopifnot(isTRUE(all.equal(expected,a$q_gene_bh[keep],tolerance=1e-12,check.attributes=FALSE)))
}
invisible(parse(file='app.R'))
writeLines(c('R app.R syntax: PASS','Global BH versus stats::p.adjust: PASS',
  'Every gene BH versus stats::p.adjust: PASS','RShiny runtime: see shiny_csv_test.txt and shiny_mysql_test.log'),
  'results/base_R_verification.txt')
cat('Base R independent verification passed.\n')
