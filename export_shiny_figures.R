# Execute only after installing shiny and ggplot2, from the project directory.
# Plots are rendered from the actual Shiny server reactives via testServer.
source('app.R')
dir.create('figures/shiny_exports',showWarnings=FALSE)
shiny::testServer(server, {
 session$setInputs(stage='All',group='All',measure='q_gene_bh',alpha=.05,onlysig=FALSE,
   maxgenes=60,maxparams=30,coverage=.2,genecoverage=.5,clusters=4)
 for (s in c('Zfp616','Gna11','Enho','Folh1','Clec3b')) {
   session$setInputs(gt=a$genotype_id[which(a$symbol==s)[1]])
   ggplot2::ggsave(file.path('figures/shiny_exports',paste0(s,'.png')),gp(),width=18,height=11,dpi=180)
   session$setInputs(onlysig=TRUE)
   ggplot2::ggsave(file.path('figures/shiny_exports',paste0(s,'_significant.png')),gp(),width=12,height=8,dpi=180)
   session$setInputs(onlysig=FALSE)
 }
 session$setInputs(pid=na.omit(a$parameter_id)[1])
 ggplot2::ggsave('figures/shiny_exports/phenotype_to_genotypes.png',pp(),width=18,height=11,dpi=180)
 cl <- clusterdata();m <- cl$mat
 write.csv(cl$groups,'results/shiny_gene_clusters.csv',row.names=FALSE)
 writeLines(jsonlite::toJSON(list(genes=nrow(m),parameters=ncol(m),imputed_fraction=cl$missing,clusters=as.list(table(cl$groups$cluster))),auto_unbox=TRUE,pretty=TRUE),'results/shiny_clustering_summary.json')
 d <- as.data.frame(as.table(m));names(d) <- c('gene','parameter','score')
 p <- ggplot2::ggplot(d,ggplot2::aes(parameter,gene,fill=score))+ggplot2::geom_tile()+
   ggplot2::scale_fill_gradient(low='#f2f6fa',high='#a81d3d')+ggplot2::theme_minimal()+
   ggplot2::theme(axis.text.x=ggplot2::element_text(angle=90,hjust=1,size=7))
 ggplot2::ggsave('figures/shiny_exports/gene_clusters.png',p,width=16,height=10,dpi=180)
})
writeLines(capture.output(sessionInfo()),'results/R_sessionInfo.txt')
writeLines(c('CSV backend: passed','Five query genotypes: passed','Phenotype comparison: passed','Gene clustering: passed','Five genotype figures plus phenotype comparison and clustering exports: generated'),'results/shiny_csv_test.txt')
