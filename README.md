# spacescans-pipeline

Config-driven environmental-exposure linkage for EHR patient cohorts. The pipeline builds
geoid-level weight/exposure tables (**C3**) from geospatial sources, then links them to
patient address episodes (**C4**) as time/area-weighted exposures — all driven by YAML
configs and a unified DuckDB engine.

- **Distribution name:** `spacescans-pipeline`
- **Import name:** `spacescans`
- Light base install (pandas + DuckDB); geospatial / R / HDF4 / NetCDF features are optional extras.

## Installation

```bash
# Base install — yearly_areal / static_areal / cbp_fallback / faqsd
pip install spacescans-pipeline

# Add geospatial pipelines (boundary_overlap_fast, grid_weights, proximity)
pip install 'spacescans-pipeline[geo]'

# Add R / HDF4 / NetCDF readers
pip install 'spacescans-pipeline[rda,hdf4,nc]'

# Everything
pip install 'spacescans-pipeline[all]'
```

### Optional extras

| Extra | Unlocks | Notes |
|---|---|---|
| (base) | `yearly_areal`, `static_areal`, `cbp_fallback`, `faqsd`, `precomputed_areal`, `precomputed_static` | pandas + duckdb only |
| `[geo]` | `boundary_overlap_fast`, `grid_weights`, `gridded`, `*_proximity` | geopandas / rasterio / shapely / exactextract |
| `[rda]` | any reader for `.Rda` files (BG_NDI / BG_WI / CBP / FARA / UCR) | pyreadr |
| `[hdf4]` | TEMIS reader | requires system HDF4 library |
| `[nc]` | ACAG multi-pollutant reader | xarray / netCDF4 |
| `[all]` | everything above | |

**Note on native libraries:** `[hdf4]` requires the system HDF4 library
(`apt install libhdf4-dev` / `brew install hdf4` / `conda install -c conda-forge hdf4`).
`[geo]` works on most platforms via wheels; conda/mamba recommended for production.

### Linkage patterns

The pipeline runs in two stages. **C3** builds geoid-level weight/exposure tables from raw geospatial inputs (needs the `[geo]` extra). **C4** links those tables to patient episodes (base install; a few readers also need `[rda]`/`[hdf4]`/`[nc]`).

#### C3 — weight / exposure building (`[geo]`)

| Pattern | What it does | Typical data |
|---|---|---|
| `boundary_overlap_fast` | Patient 270 m buffer × polygon area-overlap weights (per-tile bulk rasterize) | BG, County, Tract, ZCTA5 |
| `grid_weights` | Patient buffer × raster cell coverage weights | ACAG, Noise, PRISM, TEMIS, VNL, MOD13Q1 |
| `tiger_proximity` | Nearest road distance per (geoid, year) | TIGER roads |
| `nhd_proximity` | Nearest blue-space distance per geoid | NHD |

#### C4 — patient linkage (base install)

Pure table operations (DuckDB/pandas) that consume the C3 weight tables — no extra required. They differ along two axes: **how exposure varies over time** × **whether spatial aggregation is still needed**.

| Pattern | Time dimension | Spatial | What it does | Typical data |
|---|---|---|---|---|
| `yearly_areal` | Yearly (2013–2019) | Area-weighted (uses C3 boundary weights) | Patient buffer × boundary area weights + residence-days per geoid → yearly "time × area" weighted mean | BG_NDI, UCR, ZBP |
| `static_areal` | Time-invariant | Area-weighted | Exposure is a single static value; area-weighted by residence days only | BG_WI (walkability), Noise |
| `cbp_fallback` | Yearly | Area-weighted | Business specialization of `yearly_areal`: patients use ZBP (ZIP-level) first; those missing ZBP fall back to county CBP, then concatenated | County/ZCTA5 business patterns |
| `faqsd` (`faqsd_daily_areal`) | Daily | Area-weighted | Daily air quality (O3/PM2.5); patient episode × daily values with day-level overlap + area weighting | TRACT FAQSD |
| `precomputed_areal` | Yearly | Precomputed (no spatial aggregation) | Exposure is already a `geoid × year` table; time-weighted by residence days directly (no rasterization/overlap) | TIGER road distance |
| `precomputed_static` | Time-invariant | Precomputed | Exposure is already a `geoid`-level static table; weighted average by episode days | NHD blue-space distance |

> `*_areal` vs `precomputed_*`: `areal` re-aggregates using the C3 boundary weights; `precomputed_*` exposures are already computed at the geoid level (e.g. TIGER/NHD distances), skipping the spatial step.
> Some C4 patterns need extras beyond base: `gridded` (`[geo]`), `acag_multi` (`[nc]`+`[geo]`), `fara_tract` (`[rda]`).

## Quickstart

```bash
pip install 'spacescans-pipeline[geo]'
spacescans quickstart --output-dir ./demo-out
```

This runs an end-to-end pipeline on bundled sample data (~10 synthetic
patients × 3 Delaware counties) and writes a Parquet result to `./demo-out/`.

## Running on your own data

```bash
export SPACESCANS_DATA_DIR=/path/to/exposome-data
export SPACESCANS_OUTPUT_DIR=/path/to/results

# Edit ./configs/c3/county.yaml etc. (paths use ${SPACESCANS_DATA_DIR}/...)

# Run the pipelines in dependency order
spacescans run ./configs/c3/county.yaml
spacescans run ./configs/c3/zcta5.yaml
spacescans run ./configs/c4/zbp.yaml          # depends on C3 zcta5
spacescans run ./configs/c4/cbp_fallback.yaml # depends on C3 county + C4 zbp
```

## Package structure

```
src/spacescans/
├── cli/                 run / quickstart / init-config
├── config_resolution.py 3-tier path resolution (CLI > env > YAML) + ${VAR} expansion
├── pipeline/            config loader + pattern registry + runner
├── models/              pydantic config schema, protocols, operation specs
├── engine/              DuckDB aggregation engine
├── io/                  readers (parquet/csv/.Rda) + writers
├── geometry/            buffers, overlap, grid weights, proximity ([geo])
├── transforms/          filter / recode / derive / date_parse / spatial_fix
├── linkage/             linkage-pattern implementations
├── plugins/             dataset-specific readers (extras-gated)
└── resources/           bundled sample data + template configs
```

The package is self-contained: `import spacescans` pulls in only base dependencies;
optional readers/patterns raise a friendly `MissingExtraError` telling you which
`pip install 'spacescans-pipeline[...]'` to run.

## Development

```bash
pip install -e '.[all,dev]'
pytest                  # full suite (base + extras present in the env)
pytest -m "not extras"  # base-only tests
pytest -m geo           # geo-extra tests
```

## License

MIT — see [LICENSE](LICENSE).
