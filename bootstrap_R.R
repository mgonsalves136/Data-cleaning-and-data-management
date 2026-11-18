# Locate a project library, or the isolated library used in this workspace.
candidate_libraries <- c(file.path(getwd(),'.Rlibrary'),file.path(getwd(),'../../work/R-library'))
candidate_libraries <- candidate_libraries[dir.exists(candidate_libraries)]
if(length(candidate_libraries)) .libPaths(c(normalizePath(candidate_libraries),.libPaths()))
