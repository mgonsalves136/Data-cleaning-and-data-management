# Run from the project root after install_R.R. This script has not been run
# in the authoring environment because R is unavailable there.
source('app.R')
stopifnot(nrow(a)>0,all(c('p_value','q_gene_bh','q_global_bh') %in% names(a)))
shiny::testServer(server, {
  session$setInputs(stage='All',group='All',measure='q_gene_bh',alpha=.05,
    onlysig=FALSE,maxgenes=60,maxparams=30,coverage=.2,genecoverage=.5,clusters=4)
  for (s in c('Zfp616','Gna11','Enho','Folh1','Clec3b')) {
    session$setInputs(gt=a$genotype_id[which(a$symbol==s)[1]])
    stopifnot(nrow(gd())>0,selectedgene()==s)
    stopifnot(inherits(gp(),'ggplot'))
  }
  session$setInputs(pid=na.omit(a$parameter_id)[1])
  stopifnot(nrow(pd())>0,inherits(pp(),'ggplot'))
  cl <- clusterdata()
  stopifnot(nrow(cl$mat)>=3,ncol(cl$mat)>=2,all(is.finite(cl$mat)),nrow(cl$groups)==nrow(cl$mat))
})
cat('RShiny smoke tests passed.\n')
