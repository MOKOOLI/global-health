# Minimal R client (UNTESTED: no R interpreter was available when this was written).
# Needs: install.packages(c("httr2", "jsonlite"))
atlas_base <- function() Sys.getenv("GHATLAS_URL", "http://localhost:8000")

atlas_get <- function(path, ...) {
  req <- httr2::request(paste0(atlas_base(), path))
  req <- httr2::req_url_query(req, ...)
  key <- Sys.getenv("GHATLAS_KEY", "")
  if (nzchar(key)) req <- httr2::req_headers(req, `X-API-Key` = key)
  httr2::resp_body_string(httr2::req_perform(req))
}

atlas_ask <- function(q) jsonlite::fromJSON(atlas_get("/api/ask", q = q))

atlas_indicator <- function(code) {
  txt <- sub("^﻿", "", atlas_get(paste0("/api/export/indicator/", code, ".csv")))
  utils::read.csv(text = txt, stringsAsFactors = FALSE)
}
