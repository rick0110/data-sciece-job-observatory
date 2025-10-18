<div align="center">

# Data Jobs Observatory

Explore Brazil's data job market with interactive dashboards and continuously published analyses about opportunities in Data Science and related roles.

</div>

## Overview

This project is a small, end‑to‑end observatory for the Brazilian data job market. It has two main areas:

- Dashboard: a Flask app serving interactive Plotly charts (with light/dark themes) summarizing salaries, benefits, location, and roles across seniority levels.
- Analyses: a section to continuously publish curated analyses about jobs, including locality, salary ranges, benefits, and required skills for different seniority levels.

The data pipeline ingests a raw CSV, cleans and enriches it (benefits, state extraction, normalization), generates a ready‑to‑render dashboard context (JSON), and powers an intelligent search over vacancies using sentence embeddings.

## Key features

- Interactive dashboard (Flask + Jinja + Plotly) with dark mode and responsive layout
- Data enrichment
  - Job title normalization (pt‑BR to canonical roles)
  - Benefits expansion into binary columns
  - State extraction from free‑text location (accent insensitivity)
- Visualizations: salary distributions, by level, box/violin, top states, heatmap (state × seniority), base vs total comp, work modality, benefits, choropleth map of Brazil
- Intelligent search (semantic)
  - Embeddings from `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
  - Cosine similarity to retrieve top matching vacancies
  - Search bar in the dashboard updating the table live

## Project structure

```
coletadados/
├── data/
│   ├── raw_data.csv                 # input data (pt‑BR)
│   ├── vagas_processadas.csv        # processed data (generated)
│   └── embeddings.npy               # sentence embeddings (generated)
├── job_obs/
│   ├── app.py                       # Flask app (routes: /, /dashboard, /api/search)
│   ├── service/
│   │   ├── dashboard_data.py        # data transformations and Plotly figures → dashboard_context.json
│   │   └── sample_search.py         # generate embeddings and processed CSV
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   └── dashboard.html
│   └── static/
│       ├── css/
│       │   ├── dark-mode.css
│       │   └── front-style.css
│       └── images/
│           └── dashboard_context.json  # generated chart configs
├── requirements.txt
├── RUNNING.md                       # quickstart with minimal steps
└── README.md                        # this file
```

## Getting started

1) Create and activate a virtualenv (recommended)

```bash
python -m venv .venv
source .venv/bin/activate
```

2) Install dependencies

```bash
pip install -r requirements.txt
```

3) Generate processed data and embeddings (one‑time or when data changes)

```bash
cd job_obs/service
python sample_search.py
# creates ../../data/embeddings.npy and ../../data/vagas_processadas.csv
```

4) Build the dashboard context JSON

```bash
python dashboard_data.py
# writes ../static/images/dashboard_context.json
```

5) Run the web app

```bash
cd ..
python app.py
# open http://0.0.0.0:5001/
```

## API

### GET /api/search

Semantic search over processed vacancies.

- Query params:
  - `q` (string, required): user query, e.g. "cientista remoto SP júnior"
  - `k` (int, optional, default 20, max 100): number of results
- Response (JSON):

```json
{
  "results": [
    {
      "cargo": "Data Scientist",
      "nivel": "Sênior",
      "estado": "SP",
      "modalidade_trabalho": "Remoto",
      "salario_base": 15300.0,
      "remuneracao_total_mensal": 20746.0,
      "score": 0.82
    }
  ]
}
```

## Data pipeline (high level)

1. Load `data/raw_data.csv` with locale‑aware numeric parsing (decimal=',' and thousands='.')
2. Transformations (`dashboard_data.py`)
   - Normalize job titles (`change_cargo`)
   - Expand `beneficios` into boolean columns
   - Extract state from `localizacao` (accent‑insensitive string matching)
   - Build Plotly figures, export as JSON (light/dark variants)
3. Save dashboard context to `job_obs/static/images/dashboard_context.json`
4. Build semantic search artifacts (`sample_search.py`)
   - Compose a canonical text per vacancy (cargo, nivel, estado, modalidade)
   - Encode with SentenceTransformers → `embeddings.npy`
   - Save processed CSV to `vagas_processadas.csv`

