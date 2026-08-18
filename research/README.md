# Research intermediates

`probe-results.tsv` and `probe2.tsv` are the committed evidence: the HTTP status returned by
each endpoint to an unauthenticated client on 17 August 2026. `run-probe.sh` / `run2.sh`
regenerate them.

Two large intermediates are deliberately not committed, since both are re-downloadable:

| File | Size | Regenerate with |
|---|---|---|
| `gias.csv` | 64 MB | `curl -o research/gias.csv https://ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public/edubasealldata<YYYYMMDD>.csv` |
| `lad-raw.geojson` | 704 KB | ONS Open Geography, `LAD_MAY_2024_EW_BUC_RUC` FeatureServer, `f=geojson&outSR=4326` |

Derived outputs used by the prototype are committed under `app/data/`.
