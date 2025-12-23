# Pipeline de Dados Unificados - Job Data Observatory

# Unified Data Pipeline — Job Data Observatory

## Overview (friendly)

This document explains the `data_treatment` utilities that take raw job
postings from various sources, standardize and enrich them, and produce the
single CSV used across the dashboard and search API.

The goal is to make the dataset easy to consume for visualization and simple
semantic search while keeping the extraction logic auditable and simple.

## What this folder contains

- `merge_data_sources.py` — main script to read raw inputs, normalize columns,
   extract common fields and write `data/vagas_unificadas.csv`.
- `likedin_data_pipeline.py` — helper pipeline that focuses on LinkedIn JSON
   input: normalization, regex extraction and optional LLM fallbacks.
- `generate_embeddings.py` — simple wrapper to produce sentence embeddings
   (NumPy `.npy`) used by the search API.

## High-level flow

1. Collect raw inputs (CSV + LinkedIn JSON)
2. Run the unification pipeline to produce a single, canonical CSV
3. Generate embeddings from the unified CSV
4. Build dashboard context and serve via Flask

## Running the pipeline (examples)

From the repository root:

```bash
# merge raw sources into one CSV
python -m data_treatment.merge_data_sources

# produce embeddings
python -m data_treatment.generate_embeddings
```

Programmatic usage (inside Python):

```python
from data_treatment.merge_data_sources import run_merge_pipeline
from data_treatment.generate_embeddings import generate_embeddings

# run the full merge pipeline and persist the CSV
df, benefits = run_merge_pipeline(
      raw_data_path='data/raw_data.csv',
      linkedin_data_path='data/linkedin_data_raw.json',
      output_path='data/vagas_unificadas.csv',
)

# generate embeddings for the unified CSV
embeddings = generate_embeddings(
      input_path='data/vagas_unificadas.csv',
      output_path='data/embeddings.npy',
      model_name='sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
      batch_size=32,
)
```

## How the unification works (details)

- Column mapping: legacy Portuguese columns (e.g. `cargo`, `empresa`,
   `salario_base`) are mapped to a canonical schema (`role`, `company`,
   `salary`) through an explicit mapping table in `merge_data_sources.py`.
- Normalization: text fields are normalized (lowercased, accents removed) so
   the same tokens match across sources.
- Region extraction: a dictionary of regexes maps free-text locations to
   Brazilian state codes (e.g. `SP`, `RJ`) and recognizes remote keywords.
- Seniority & work model: normalization tables convert localized terms to the
   small set of canonical values used by the dashboard and API.
- Description assembly: the script concatenates prioritized columns to
   generate a `description` column that will feed the embeddings pipeline.

## NLP extraction approach

`likedin_data_pipeline.py` uses a pragmatic, layered approach:

1. Regex-first extraction for fields like `work_model`, `contract_type`,
    `technologies` and `benefits` (fast, transparent, and predictable).
2. Optional LLM fallbacks (via `transformers.pipeline`) for ambiguous cases
    where deterministic rules are insufficient. LLM use is off by default in
    most batch flows because it requires model downloads and can be slow.

The repository includes extensive regex dictionaries for roles, seniority
and regions to cover Portuguese, English and common variants.

## Embeddings: how texts are composed

`generate_embeddings.py` builds a compact textual representation for each job
by joining the most important fields in order of priority:

- `role`, `seniority`, `region`, `work_model`
- `technologies`, `benefits` (if present and not `not_specified`)
- `description` (truncated)

This keeps embeddings focused on the attributes users typically search by.

## Common troubleshooting

- Missing files: the merge script expects `data/raw_data.csv` and
   `data/linkedin_data_raw.json` (or it will produce the unified CSV only for
   the sources that exist).
- LLM slowdown: if you enable LLM fallbacks, the first run may download
   model weights. Run on a machine with enough disk space and (preferably) a
   GPU if you want speed.
- Embedding memory: `embeddings.npy` can be large; for production consider an
   on-disk index (FAISS) instead of loading all vectors into RAM.

## Developer notes — adding a new role/regex

- To add or refine role detection, update `ROLE_REGEX` in
   `likedin_data_pipeline.py`. Regexes are keyed by the canonical role id.
- To map a new Portuguese column from `raw_data.csv`, add it to the
   `RAW_DATA_COLUMN_MAPPING` in `merge_data_sources.py`.
- Keep changes small and add tests or sample rows showing the expected
   transformation.

## Contact / Next steps

If you want, I can:

- add runnable unit tests for the mapping logic,
- provide a small FAISS-based index example for scalable search,
- or expand docs with a step-by-step debugging guide for the LinkedIn scraper.

Happy to extend any of these — tell me which one you prefer.
