source('scripts/bootstrap_R.R')
packages <- c('shiny','ggplot2','DBI','RMariaDB','commonmark')
missing <- setdiff(packages,rownames(installed.packages()))
if(length(missing)) {
  dir.create('.Rlibrary',showWarnings=FALSE)
  .libPaths(c(normalizePath('.Rlibrary'),.libPaths()))
  install.packages(missing,lib=normalizePath('.Rlibrary'),repos='https://cloud.r-project.org')
}
