<div align="center">

# Data Jobs Observatory

Explore Brazil's data job market with interactive dashboards and continuously published analyses about opportunities in Data Science and related roles.

</div>

## Overview

This project is a comprehensive, end-to-end observatory for the Brazilian data job market. It consists of three main components:

1. **Interactive Dashboard**: A Flask web application serving real-time interactive Plotly charts with light/dark theme support
2. **Semantic Search Engine**: AI-powered job search using multilingual sentence embeddings
3. **Analysis Publication Platform**: A system for publishing and sharing detailed market analyses with rich visualizations

The platform combines data engineering, machine learning, and web development to provide actionable insights into Brazil's data science job market.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Detailed Component Breakdown](#detailed-component-breakdown)
  - [1. Data Pipeline & Processing](#1-data-pipeline--processing)
  - [2. Web Application (Flask)](#2-web-application-flask)
  - [3. Semantic Search Engine](#3-semantic-search-engine)
  - [4. Dashboard System](#4-dashboard-system)
  - [5. Analysis Publishing Platform](#5-analysis-publishing-platform)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [Contributing Analyses](#contributing-analyses)
- [Project Structure](#project-structure)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│  (Flask + Jinja2 Templates + Bootstrap + Dark Mode Support)    │
└────────────┬────────────────────────────────────┬───────────────┘
             │                                    │
    ┌────────▼────────┐                  ┌───────▼────────┐
    │   Dashboard     │                  │   Analyses     │
    │   (Plotly.js)   │                  │  (HTML/CSS/JS) │
    └────────┬────────┘                  └───────┬────────┘
             │                                    │
    ┌────────▼────────────────────────────────────▼────────┐
    │              Flask Backend (app.py)                  │
    │  Routes | Templates | Static Assets | API Endpoints │
    └────────┬────────────────────────────────┬────────────┘
             │                                │
    ┌────────▼────────┐              ┌───────▼─────────┐
    │  Data Pipeline  │              │  Search Engine  │
    │  (dashboard_    │              │  (Sentence      │
    │   data.py)      │              │   Transformers) │
    └────────┬────────┘              └───────┬─────────┘
             │                                │
    ┌────────▼────────────────────────────────▼─────────┐
    │              Data Layer                           │
    │  raw_data.csv | vagas_processadas.csv            │
    │  embeddings.npy | dashboard_context.json         │
    └──────────────────────────────────────────────────┘
```

---

## Detailed Component Breakdown

### 1. Data Pipeline & Processing

#### **Engine: Pandas + NumPy**

The data pipeline transforms raw job postings into analysis-ready formats.

**Location**: `job_obs/service/dashboard_data.py` and `job_obs/service/sample_search.py`

**Process Flow**:

1. **Data Ingestion** (`pandas.read_csv`)
   - Reads `data/raw_data.csv` with Brazilian locale settings
   - Handles decimal separators (`,`) and thousands separators (`.`)
   - Preserves encoding (UTF-8) for Portuguese characters

2. **Data Cleaning & Normalization**
   - **Job Title Standardization**: Maps Portuguese job titles to canonical English roles
     - Example: "Cientista de Dados" → "Data Scientist"
     - Uses `change_cargo()` function with dictionary mapping
   - **Location Parsing**: Extracts state codes from free-text location strings
     - Accent-insensitive matching (São Paulo, Sao Paulo → SP)
     - Handles variations and abbreviations
   - **Benefits Expansion**: Converts comma-separated benefits into boolean columns
     - Input: "VR, VA, Plano de Saúde"
     - Output: `vr=1, va=1, plano_saude=1, vt=0, ...`

3. **Feature Engineering**
   - Calculates salary statistics by seniority level
   - Groups data by state, modality, and role
   - Generates aggregations for visualizations

4. **Output Generation**
   - Saves cleaned data to `data/vagas_processadas.csv`
   - Exports dashboard configuration to `job_obs/static/images/dashboard_context.json`

**Key Functions**:
```python
# Job title normalization
change_cargo(cargo: str) -> str

# State extraction
extract_state(location: str) -> str

# Benefits parsing
expand_benefits(benefits_str: str) -> dict
```

---

### 2. Web Application (Flask)

#### **Engine: Flask 3.1.2 + Jinja2**

The Flask application serves as the central web server and routing system.

**Location**: `job_obs/app.py`

**Routes**:

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Landing page with project overview |
| `/dashboard` | GET | Interactive dashboard with Plotly charts |
| `/api/search` | GET | Semantic search API endpoint |
| `/vaga/nova` | GET/POST | Form to submit new job postings |
| `/analisys_html` | GET | Gallery of published analyses |
| `/analisys_html/<filename>` | GET | Render specific analysis |
| `/analisys_secondary_files/<path>` | GET | Serve analysis assets (CSS/JS/images) |

**Template System**:
- **`base.html`**: Master template with navbar, footer, and dark mode toggle
- **`index.html`**: Landing page extending base template
- **`dashboard.html`**: Dashboard view with Plotly chart containers
- **`analisys-default.html`**: Renders Markdown-based analyses within site layout
- **`analisys-detailed.html`**: Gallery view for browsing published analyses

**Static Assets**:
- CSS: Custom stylesheets for dark mode, animations, form styling
- JavaScript: Dark mode persistence, search functionality, chart interactions
- Images: Logos, icons, and dashboard context JSON

---

### 3. Semantic Search Engine

#### **Engine: SentenceTransformers + Scikit-learn**

The search system uses deep learning to understand natural language queries.

**Model**: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- Multilingual support (Portuguese/English)
- 768-dimensional embeddings
- Trained on paraphrase detection tasks

**Location**: `job_obs/service/sample_search.py` (training) and `job_obs/app.py` (inference)

**How It Works**:

1. **Embedding Generation** (Offline)
   ```python
   # Compose semantic-rich text for each job
   text = f"{cargo} {nivel} {estado} {modalidade_trabalho}"
   
   # Encode to 768-dim vector
   embedding = model.encode([text])[0]
   
   # Save all embeddings
   np.save('embeddings.npy', embeddings)
   ```

2. **Query Processing** (Runtime)
   ```python
   # User query: "cientista de dados remoto senior SP"
   query_embedding = model.encode([user_query])
   
   # Calculate cosine similarity with all jobs
   scores = cosine_similarity(query_embedding, embeddings)[0]
   
   # Return top-k matches sorted by relevance
   top_indices = np.argsort(scores)[::-1][:k]
   ```

3. **API Response**
   - Returns JSON with job details and similarity scores
   - Supports pagination via `k` parameter (max 100)
   - Handles empty queries gracefully

**Performance**:
- Average query time: <100ms
- Supports concurrent requests
- Embeddings loaded once at startup

---

### 4. Dashboard System

#### **Engine: Plotly.js 2.27.0 + Bootstrap 5.3**

The dashboard provides interactive, publication-quality visualizations.

**Location**: `job_obs/service/dashboard_data.py` (generation) and `job_obs/templates/dashboard.html` (rendering)

**Visualization Types**:

1. **Salary Distributions**
   - Histograms with KDE curves
   - Box plots by seniority level
   - Violin plots showing full distribution shapes

2. **Geographic Analysis**
   - Choropleth map of Brazil (using GeoJSON boundaries)
   - State-level aggregations
   - Heatmap of state × seniority level

3. **Categorical Breakdowns**
   - Work modality (Remote/Hybrid/Onsite) pie charts
   - Benefits prevalence bar charts
   - Role distribution sunburst charts

4. **Comparative Analysis**
   - Base salary vs. total compensation scatter plots
   - Seniority progression line charts
   - Multi-series comparisons

**Dark Mode Support**:
- All charts have light/dark variants pre-generated
- Theme switching syncs across all Plotly instances
- CSS variables ensure consistent color schemes

**Chart Configuration Export**:
```python
# dashboard_data.py generates this structure
{
  "graficos": [
    {
      "data": [...],          # Plotly traces
      "layout": {...},        # Plotly layout config
      "config": {...},        # Plotly display config
      "id": "salary-hist"
    },
    ...
  ],
  "stats": {                  # Summary statistics
    "mean_salary": 12500.00,
    "median_salary": 11000.00,
    ...
  }
}
```

**Interactivity**:
- Hover tooltips with detailed information
- Click-to-filter on legend items
- Zoom, pan, and export controls
- Responsive layout for mobile devices

---

### 5. Analysis Publishing Platform

#### **Engine: Python-Frontmatter + Markdown + Custom HTML/CSS/JS**

The platform allows contributors to publish rich, interactive analyses.

**Location**: `analisys_html/` (HTML files) and `analisys_secondary_files/` (assets)

**How Analyses Work**:

1. **Frontmatter Metadata** (YAML)
   ```yaml
   ---
   title: São Paulo Salary Analysis
   author: Richard Viana
   date: 22/11/2025
   subject: São Paulo Job Market
   summary: Complete analysis with interactive charts
   image_capa: analysis-hero.jpeg
   ---
   ```

2. **HTML Structure**
   - Full HTML5 document with `<head>` and `<body>`
   - Bootstrap 5.3 grid system for responsive layout
   - Custom sections with semantic IDs for navigation

3. **CSS Styling**
   - CSS variables for light/dark theme switching
   - Custom components (cards, tables, hero sections)
   - Animation keyframes for scroll effects

4. **JavaScript Functionality**
   - Dark mode persistence with localStorage
   - Scroll progress indicator
   - Smooth scrolling navigation
   - Plotly chart theme synchronization

5. **Plotly Integration**
   - Charts defined with `Plotly.newPlot()`
   - Theme-aware color schemes
   - Interactive hover and click events

**Rendering Pipeline**:
```
.html file → frontmatter.load() → extract metadata + content
          ↓
    metadata used for gallery card
          ↓
    content rendered in template (analisys-default.html or standalone)
          ↓
    served at /analisys_html/<filename>
```

---

## Technology Stack

### Backend
- **Python 3.12**: Core language
- **Flask 3.1.2**: Web framework
- **Pandas 2.2+**: Data manipulation
- **NumPy**: Numerical computing
- **Scikit-learn**: Cosine similarity calculations
- **SentenceTransformers**: Embedding generation
- **PyTorch**: ML backend for transformers
- **Python-Frontmatter**: YAML metadata parsing
- **Markdown**: Content conversion

### Frontend
- **Bootstrap 5.3.3**: UI framework
- **Plotly.js 2.27.0**: Interactive charts
- **Bootstrap Icons 1.11.1**: Icon library
- **Vanilla JavaScript**: Custom interactions
- **CSS3**: Custom styling with variables

### Data Science
- **sentence-transformers/paraphrase-multilingual-mpnet-base-v2**: Embedding model
- **Hugging Face Transformers**: Model loading and inference

### Development
- **Git**: Version control
- **Python venv**: Virtual environment management

---

## Getting Started

### Prerequisites
- Python 3.12+
- 4GB+ RAM (for loading transformer models)
- Modern web browser

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/rick0110/job-observatory-data-sciece.git
   cd coletadados
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv job_obs_env
   source job_obs_env/bin/activate  # Linux/Mac
   # job_obs_env\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Generate processed data and embeddings**
   ```bash
   cd job_obs/service
   python sample_search.py
   # Output: ../../data/vagas_processadas.csv and ../../data/embeddings.npy
   ```

5. **Build dashboard context**
   ```bash
   python dashboard_data.py
   # Output: ../static/images/dashboard_context.json
   ```

6. **Run the application**
   ```bash
   cd ..
   python app.py
   # Server starts at http://0.0.0.0:5005
   ```

7. **Access the platform**
   - Landing page: http://localhost:5005/
   - Dashboard: http://localhost:5005/dashboard
   - Analyses: http://localhost:5005/analisys_html

---

## API Documentation

### GET /api/search

Semantic search endpoint for job postings.

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | Yes | - | Natural language query (Portuguese or English) |
| `k` | integer | No | 20 | Number of results to return (max: 100) |

**Example Request**:
```bash
curl "http://localhost:5005/api/search?q=cientista%20de%20dados%20remoto%20senior&k=5"
```

**Example Response**:
```json
{
  "results": [
    {
      "cargo": "Data Scientist",
      "nivel": "Sênior",
      "estado": "SP",
      "modalidade_trabalho": "Remoto",
      "salario_base": 15300.0,
      "remuneracao_total_mensal": 20746.0
    },
    {
      "cargo": "Data Scientist",
      "nivel": "Sênior",
      "estado": "RJ",
      "modalidade_trabalho": "Híbrido",
      "salario_base": 14500.0,
      "remuneracao_total_mensal": 19200.0
    }
  ]
}
```

**Error Response**:
```json
{
  "error": "Error message",
  "results": []
}
```

---

## Contributing Analyses

We welcome community contributions of job market analyses! Follow this comprehensive guide to publish your analysis on the platform.

### Overview of Analysis Structure

Each analysis consists of:
1. **Main HTML file** (`analisys_html/<your-analysis>.html`)
2. **Assets folder** (`analisys_secondary_files/<your-analysis>/`)
   - `css/` - Custom stylesheets
   - `js/` - JavaScript files
   - `images/` - Images and graphics

### Step-by-Step Contribution Guide

#### Step 1: Create Your Analysis HTML File

Create a file in `analisys_html/` with this structure:

**File**: `analisys_html/remote-work-analysis.html`

```html
---
title: Remote Work Trends in Data Science
author: Your Name
date: 23/11/2025
subject: Remote Work Analysis
summary: Analysis of remote work trends, salary differences, and geographic distribution in Brazilian data science market.
image_capa: remote-hero.jpg
---

<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Remote Work Trends - Data Jobs Observatory</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    
    <!-- Custom CSS - IMPORTANT: Use this exact path pattern -->
    <link rel="stylesheet" href="/analisys_secondary_files/remote-work-analysis/css/analysis-style.css">
    
    <!-- Plotly for interactive charts -->
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
</head>
<body>
    <!-- Scroll Progress Bar -->
    <div class="scroll-progress" aria-hidden="true">
        <div class="progress-bar"></div>
    </div>

    <!-- Navigation Bar -->
    <nav class="navbar navbar-expand-lg portal-navbar sticky-top shadow-sm">
        <div class="container">
            <a class="navbar-brand fw-semibold" href="#overview" data-scroll>
                Data Jobs Observatory
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" 
                    data-bs-target="#mainNavbar">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="mainNavbar">
                <ul class="navbar-nav ms-auto align-items-lg-center gap-lg-3">
                    <li class="nav-item">
                        <a class="nav-link" href="#overview" data-scroll>Overview</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#metrics" data-scroll>Metrics</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#charts" data-scroll>Charts</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#conclusions" data-scroll>Conclusions</a>
                    </li>
                </ul>
                <!-- Dark Mode Toggle -->
                <div class="d-flex align-items-center gap-3 mt-3 mt-lg-0">
                    <div class="form-check form-switch mb-0">
                        <input class="form-check-input" type="checkbox" id="darkModeSwitch">
                        <label class="form-check-label" for="darkModeSwitch">
                            <i class="bi bi-moon-stars"></i>
                        </label>
                    </div>
                    <a href="/analisys_html" class="btn btn-sm btn-outline-primary">
                        <i class="bi bi-arrow-left"></i> All Analyses
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero-section">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-lg-6">
                    <div class="badge bg-primary-soft text-primary mb-3">
                        Market Analysis
                    </div>
                    <h1 class="display-4 fw-bold mb-4">
                        Remote Work Trends in Data Science
                    </h1>
                    <p class="lead text-muted mb-4">
                        Analysis of remote work trends, salary differences, and 
                        geographic distribution in Brazilian data science market.
                    </p>
                    <div class="d-flex gap-3 align-items-center">
                        <div>
                            <small class="text-muted d-block">Author</small>
                            <strong>Your Name</strong>
                        </div>
                        <div class="vr"></div>
                        <div>
                            <small class="text-muted d-block">Date</small>
                            <strong>November 23, 2025</strong>
                        </div>
                    </div>
                </div>
                <div class="col-lg-6">
                    <!-- Hero image - stored in analisys_secondary_files/remote-work-analysis/images/ -->
                    <img src="/analisys_secondary_files/remote-work-analysis/images/remote-hero.jpg" 
                         alt="Remote Work Analysis" 
                         class="img-fluid rounded-4 shadow-lg">
                </div>
            </div>
        </div>
    </section>

    <!-- Main Content -->
    <main class="container my-5">
        <!-- Overview Section -->
        <section id="overview" class="mb-5">
            <h2 class="section-title">Executive Summary</h2>
            <div class="row g-4">
                <div class="col-md-4">
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="bi bi-laptop"></i>
                        </div>
                        <h3 class="stat-value">67%</h3>
                        <p class="stat-label">Remote Positions</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="bi bi-cash-stack"></i>
                        </div>
                        <h3 class="stat-value">R$ 15,200</h3>
                        <p class="stat-label">Avg Remote Salary</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="bi bi-graph-up"></i>
                        </div>
                        <h3 class="stat-value">+23%</h3>
                        <p class="stat-label">YoY Growth</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Charts Section -->
        <section id="charts" class="mb-5">
            <h2 class="section-title">Data Visualizations</h2>
            
            <!-- Chart 1: Remote vs Onsite Salary Distribution -->
            <div class="chart-container mb-4">
                <h3 class="chart-title">Salary Distribution by Work Modality</h3>
                <div id="grafico-salary-modality"></div>
            </div>

            <!-- Chart 2: Geographic Distribution -->
            <div class="chart-container mb-4">
                <h3 class="chart-title">Remote Jobs by State</h3>
                <div id="grafico-geographic"></div>
            </div>
        </section>

        <!-- Conclusions Section -->
        <section id="conclusions" class="mb-5">
            <h2 class="section-title">Key Findings</h2>
            <div class="card border-0 shadow-sm">
                <div class="card-body p-4">
                    <ul class="list-unstyled">
                        <li class="mb-3">
                            <i class="bi bi-check-circle-fill text-success me-2"></i>
                            Remote positions offer 12% higher average salaries
                        </li>
                        <li class="mb-3">
                            <i class="bi bi-check-circle-fill text-success me-2"></i>
                            São Paulo leads with 45% of remote opportunities
                        </li>
                        <li class="mb-3">
                            <i class="bi bi-check-circle-fill text-success me-2"></i>
                            Senior roles are 3x more likely to be remote
                        </li>
                    </ul>
                </div>
            </div>
        </section>
    </main>

    <!-- Footer -->
    <footer class="portal-footer">
        <div class="container text-center">
            <p class="mb-0">Data Jobs Observatory © 2025</p>
        </div>
    </footer>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- Custom JavaScript - IMPORTANT: Use this exact path pattern -->
    <script src="/analisys_secondary_files/remote-work-analysis/js/animations.js"></script>
    <script src="/analisys_secondary_files/remote-work-analysis/js/charts-config.js"></script>
</body>
</html>
```

**Key Points**:
- ✅ **Frontmatter at top**: YAML metadata between `---` markers
- ✅ **Full HTML document**: Complete `<html>`, `<head>`, and `<body>` tags
- ✅ **Path convention**: Assets use `/analisys_secondary_files/<analysis-name>/...`
- ✅ **Dark mode toggle**: Include the checkbox with `id="darkModeSwitch"`
- ✅ **Bootstrap 5.3**: Use for responsive grid and components
- ✅ **Plotly charts**: Use `<div>` containers with unique IDs

---

#### Step 2: Create CSS Stylesheet

Create your styles in `analisys_secondary_files/<your-analysis>/css/analysis-style.css`

**File**: `analisys_secondary_files/remote-work-analysis/css/analysis-style.css`

```css
/* ==============================================
   CSS Variables for Theme Support
   ============================================== */
:root {
    /* Light Mode Colors */
    --bg: #ffffff;
    --text: #212529;
    --muted: #6c757d;
    --card-bg: #ffffff;
    --border: rgba(0,0,0,.125);
    --accent: #0d6efd;
    --accent-soft: rgba(13, 110, 253, 0.1);
    --shadow: 0 4px 6px rgba(0,0,0,.1);
}

/* Dark Mode Colors */
.dark {
    --bg: #071023;
    --text: #e6eef8;
    --muted: #9fb0c8;
    --card-bg: #0f1724;
    --border: rgba(255,255,255,.06);
    --accent: #4098ff;
    --accent-soft: rgba(64, 152, 255, 0.16);
    --shadow: 0 4px 6px rgba(0,0,0,.3);
}

/* ==============================================
   Global Styles
   ============================================== */
html, body {
    background-color: var(--bg);
    color: var(--text);
    transition: background-color 0.3s ease, color 0.3s ease;
    scroll-behavior: smooth;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* ==============================================
   Scroll Progress Bar
   ============================================== */
.scroll-progress {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 4px;
    background: transparent;
    z-index: 9999;
}

.scroll-progress .progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), #6610f2);
    width: 0%;
    transition: width 0.1s ease;
}

/* ==============================================
   Navigation Bar
   ============================================== */
.portal-navbar {
    background-color: var(--card-bg);
    border-bottom: 1px solid var(--border);
    backdrop-filter: blur(10px);
}

.navbar-brand {
    color: var(--text) !important;
    font-size: 1.25rem;
}

.nav-link {
    color: var(--muted) !important;
    transition: color 0.2s;
}

.nav-link:hover {
    color: var(--accent) !important;
}

/* ==============================================
   Hero Section
   ============================================== */
.hero-section {
    padding: 5rem 0;
    background: linear-gradient(135deg, var(--accent-soft), transparent);
}

.bg-primary-soft {
    background-color: var(--accent-soft) !important;
}

.text-primary {
    color: var(--accent) !important;
}

/* ==============================================
   Stat Cards
   ============================================== */
.stat-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    transition: transform 0.3s, box-shadow 0.3s;
}

.stat-card:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow);
}

.stat-icon {
    width: 64px;
    height: 64px;
    margin: 0 auto 1rem;
    background: var(--accent-soft);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    color: var(--accent);
}

.stat-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.5rem;
}

.stat-label {
    color: var(--muted);
    font-size: 1rem;
    margin: 0;
}

/* ==============================================
   Section Titles
   ============================================== */
.section-title {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 2rem;
    color: var(--text);
    position: relative;
    padding-bottom: 0.5rem;
}

.section-title::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 60px;
    height: 4px;
    background: var(--accent);
    border-radius: 2px;
}

/* ==============================================
   Chart Containers
   ============================================== */
.chart-container {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 2rem;
    box-shadow: var(--shadow);
}

.chart-title {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1.5rem;
    color: var(--text);
}

/* ==============================================
   Cards
   ============================================== */
.card {
    background: var(--card-bg);
    border-color: var(--border);
    transition: transform 0.3s, box-shadow 0.3s;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow);
}

/* ==============================================
   Footer
   ============================================== */
.portal-footer {
    background-color: var(--card-bg);
    border-top: 1px solid var(--border);
    padding: 2rem 0;
    margin-top: 4rem;
    color: var(--muted);
}

/* ==============================================
   Responsive Design
   ============================================== */
@media (max-width: 768px) {
    .hero-section {
        padding: 3rem 0;
    }
    
    .section-title {
        font-size: 1.5rem;
    }
    
    .stat-value {
        font-size: 2rem;
    }
}
```

**Key Points**:
- ✅ **CSS Variables**: Define colors for both light and dark modes
- ✅ **`.dark` class**: Applied to `<html>` element by JavaScript
- ✅ **Smooth transitions**: All color changes animate smoothly
- ✅ **Responsive**: Mobile-friendly breakpoints
- ✅ **Component styles**: Reusable classes for cards, charts, etc.

---

#### Step 3: Create JavaScript Files

**File 1**: `analisys_secondary_files/remote-work-analysis/js/animations.js`

```javascript
// ==============================================
// Dark Mode Toggle with Plotly Chart Sync
// ==============================================
(function () {
    const STORAGE_KEY = 'jobobs-dark-mode';
    const darkModeSwitch = document.getElementById('darkModeSwitch');
    const htmlElement = document.documentElement;

    // Apply dark mode class and sync all Plotly charts
    function applyDarkMode(isDark) {
        htmlElement.classList.toggle('dark', isDark);
        if (darkModeSwitch) {
            darkModeSwitch.checked = isDark;
        }
        syncPlotlyCharts(isDark);
    }

    // Sync all Plotly charts to current theme
    function syncPlotlyCharts(isDark) {
        // Call custom theme function if defined in charts-config.js
        if (typeof window.applyPlotlyTheme === 'function') {
            window.applyPlotlyTheme(isDark);
            return;
        }

        // Fallback: update all Plotly divs
        const plotlyDivs = document.querySelectorAll('[id^="grafico-"]');
        plotlyDivs.forEach(div => {
            if (div.data && div.layout && window.Plotly) {
                const bgColor = isDark ? '#071023' : '#ffffff';
                const textColor = isDark ? '#e6eef8' : '#212529';
                const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';

                window.Plotly.relayout(div, {
                    'paper_bgcolor': bgColor,
                    'plot_bgcolor': bgColor,
                    'font.color': textColor,
                    'xaxis.gridcolor': gridColor,
                    'yaxis.gridcolor': gridColor
                });
            }
        });
    }

    // Load saved preference or detect system preference
    try {
        const savedMode = localStorage.getItem(STORAGE_KEY);
        if (savedMode === '1' || savedMode === '0') {
            applyDarkMode(savedMode === '1');
        } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            applyDarkMode(true);
        } else {
            applyDarkMode(false);
        }
    } catch (error) {
        console.error('Error loading dark mode preference:', error);
        applyDarkMode(false);
    }

    // Toggle dark mode on checkbox change
    if (darkModeSwitch) {
        darkModeSwitch.addEventListener('change', function() {
            const isDark = this.checked;
            applyDarkMode(isDark);
            try {
                localStorage.setItem(STORAGE_KEY, isDark ? '1' : '0');
            } catch (error) {
                console.error('Error saving dark mode preference:', error);
            }
        });
    }
})();

// ==============================================
// Scroll Progress Bar
// ==============================================
(function () {
    const progressBar = document.querySelector('.scroll-progress .progress-bar');
    
    if (progressBar) {
        window.addEventListener('scroll', function() {
            const windowHeight = window.innerHeight;
            const documentHeight = document.documentElement.scrollHeight;
            const scrolled = window.scrollY;
            const progress = (scrolled / (documentHeight - windowHeight)) * 100;
            progressBar.style.width = Math.min(progress, 100) + '%';
        });
    }
})();

// ==============================================
// Smooth Scroll for Anchor Links
// ==============================================
(function () {
    document.querySelectorAll('a[data-scroll]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
})();

// ==============================================
// Fade-in Animation on Scroll
// ==============================================
(function () {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.chart-container, .stat-card, .card').forEach(el => {
        observer.observe(el);
    });
})();
```

**File 2**: `analisys_secondary_files/remote-work-analysis/js/charts-config.js`

```javascript
// ==============================================
// Plotly Chart Configurations
// ==============================================

// Wait for DOM and Plotly to load
document.addEventListener('DOMContentLoaded', function() {
    // Detect initial theme
    const isDark = document.documentElement.classList.contains('dark');
    
    // Chart 1: Salary Distribution by Modality
    createSalaryModalityChart(isDark);
    
    // Chart 2: Geographic Distribution
    createGeographicChart(isDark);
    
    // Make theme function globally available
    window.applyPlotlyTheme = function(isDark) {
        createSalaryModalityChart(isDark);
        createGeographicChart(isDark);
    };
});

// ==============================================
// Chart 1: Salary Distribution by Work Modality
// ==============================================
function createSalaryModalityChart(isDark) {
    const bgColor = isDark ? '#071023' : '#ffffff';
    const textColor = isDark ? '#e6eef8' : '#212529';
    const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
    
    // Sample data - replace with your actual data
    const data = [
        {
            x: ['Junior', 'Mid', 'Senior', 'Lead'],
            y: [8500, 12000, 18500, 25000],
            name: 'Remote',
            type: 'bar',
            marker: { color: '#0d6efd' }
        },
        {
            x: ['Junior', 'Mid', 'Senior', 'Lead'],
            y: [7500, 10500, 16500, 22000],
            name: 'Onsite',
            type: 'bar',
            marker: { color: '#6610f2' }
        }
    ];
    
    const layout = {
        paper_bgcolor: bgColor,
        plot_bgcolor: bgColor,
        font: { color: textColor, family: 'Inter, sans-serif' },
        xaxis: {
            title: 'Seniority Level',
            gridcolor: gridColor
        },
        yaxis: {
            title: 'Average Salary (R$)',
            gridcolor: gridColor
        },
        barmode: 'group',
        margin: { t: 40, r: 40, b: 60, l: 80 },
        hovermode: 'closest'
    };
    
    const config = {
        responsive: true,
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
    };
    
    Plotly.newPlot('grafico-salary-modality', data, layout, config);
}

// ==============================================
// Chart 2: Geographic Distribution of Remote Jobs
// ==============================================
function createGeographicChart(isDark) {
    const bgColor = isDark ? '#071023' : '#ffffff';
    const textColor = isDark ? '#e6eef8' : '#212529';
    
    // Sample data - replace with your actual data
    const data = [{
        type: 'bar',
        x: ['SP', 'RJ', 'MG', 'RS', 'SC', 'PR', 'BA', 'PE'],
        y: [450, 280, 120, 95, 85, 70, 45, 35],
        marker: {
            color: '#0d6efd',
            line: { color: textColor, width: 1 }
        },
        text: ['450', '280', '120', '95', '85', '70', '45', '35'],
        textposition: 'outside'
    }];
    
    const layout = {
        paper_bgcolor: bgColor,
        plot_bgcolor: bgColor,
        font: { color: textColor, family: 'Inter, sans-serif' },
        xaxis: {
            title: 'State',
            gridcolor: 'transparent'
        },
        yaxis: {
            title: 'Number of Remote Positions',
            gridcolor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'
        },
        margin: { t: 40, r: 40, b: 60, l: 80 }
    };
    
    const config = {
        responsive: true,
        displayModeBar: true,
        displaylogo: false
    };
    
    Plotly.newPlot('grafico-geographic', data, layout, config);
}
```

**Key Points**:
- ✅ **Theme synchronization**: Charts update when dark mode toggles
- ✅ **Responsive**: Charts resize with window
- ✅ **Customizable**: Easy to add new charts
- ✅ **Data-driven**: Replace sample data with your analysis results

---

#### Step 4: Add Images

Place your images in `analisys_secondary_files/<your-analysis>/images/`

**Example**:
```
analisys_secondary_files/
  remote-work-analysis/
    images/
      remote-hero.jpg          # Hero section image (1200x600px recommended)
      chart-screenshot.png     # Supporting images
      methodology-diagram.svg  # Vector graphics for diagrams
```

**Image Guidelines**:
- ✅ **Formats**: JPG (photos), PNG (screenshots), SVG (diagrams)
- ✅ **Optimization**: Compress images to <500KB each
- ✅ **Naming**: Use kebab-case (lowercase with hyphens)
- ✅ **Alt text**: Always provide descriptive alt attributes

---

#### Step 5: File Naming Conventions

| Component | Path Pattern | Example |
|-----------|--------------|---------|
| HTML File | `analisys_html/<name>.html` | `analisys_html/remote-work-analysis.html` |
| CSS Folder | `analisys_secondary_files/<name>/css/` | `analisys_secondary_files/remote-work-analysis/css/` |
| JS Folder | `analisys_secondary_files/<name>/js/` | `analisys_secondary_files/remote-work-analysis/js/` |
| Images Folder | `analisys_secondary_files/<name>/images/` | `analisys_secondary_files/remote-work-analysis/images/` |

**Naming Rules**:
- ✅ Use **kebab-case** (lowercase with hyphens)
- ✅ Keep names **descriptive but concise**
- ✅ **Match** the HTML filename with the assets folder name
- ✅ Avoid spaces, special characters, or uppercase letters

---

#### Step 6: Testing Your Analysis Locally

1. **Place files in correct locations**
   ```bash
   # Your analysis should create these files:
   analisys_html/remote-work-analysis.html
   analisys_secondary_files/remote-work-analysis/css/analysis-style.css
   analisys_secondary_files/remote-work-analysis/js/animations.js
   analisys_secondary_files/remote-work-analysis/js/charts-config.js
   analisys_secondary_files/remote-work-analysis/images/remote-hero.jpg
   ```

2. **Start the Flask server**
   ```bash
   cd job_obs
   python app.py
   ```

3. **Access your analysis**
   - Gallery: http://localhost:5005/analisys_html
   - Direct link: http://localhost:5005/analisys_html/remote-work-analysis.html

4. **Test checklist**
   - ✅ Analysis appears in gallery with metadata
   - ✅ All images load correctly
   - ✅ Dark mode toggle works
   - ✅ Charts render properly
   - ✅ Charts update when theme changes
   - ✅ Navigation links work
   - ✅ Responsive on mobile (test at 375px width)

---

#### Step 7: Submit Your Contribution

1. **Fork the repository**
   ```bash
   git clone https://github.com/rick0110/job-observatory-data-sciece.git
   cd coletadados
   git checkout -b analysis/remote-work
   ```

2. **Add your files**
   ```bash
   git add analisys_html/remote-work-analysis.html
   git add analisys_secondary_files/remote-work-analysis/
   ```

3. **Commit with descriptive message**
   ```bash
   git commit -m "Add remote work trends analysis

   - Analyzes salary differences between remote and onsite positions
   - Includes geographic distribution of remote opportunities
   - Interactive Plotly charts with dark mode support
   - Responsive design for mobile devices"
   ```

4. **Push and create Pull Request**
   ```bash
   git push origin analysis/remote-work
   ```

5. **Pull Request Checklist**
   - ✅ Descriptive title and summary
   - ✅ Screenshots of your analysis (light and dark modes)
   - ✅ Mention any data sources or methodologies
   - ✅ Confirm all files are in correct locations
   - ✅ Tested locally before submitting

---

### Analysis Best Practices

#### Content Guidelines
- **Data-driven**: Base conclusions on actual data analysis
- **Visualizations**: Include at least 3-5 interactive charts
- **Actionable insights**: Provide clear takeaways for job seekers/employers
- **Transparency**: Document your methodology and data sources
- **Accessibility**: Use semantic HTML and descriptive alt text

#### Code Quality
- **Validate HTML**: Use W3C validator
- **Optimize assets**: Compress images and minify CSS/JS
- **Cross-browser**: Test in Chrome, Firefox, Safari
- **Performance**: Keep page load under 3 seconds
- **Mobile-first**: Design for small screens, enhance for desktop

#### Design Principles
- **Consistency**: Follow the existing visual language
- **Readability**: Use sufficient contrast ratios (WCAG AA)
- **Whitespace**: Don't overcrowd content
- **Typography**: Stick to system font stack or web-safe fonts
- **Color**: Use CSS variables for theme consistency

---

## Project Structure

```
coletadados/
├── data/
│   ├── raw_data.csv                      # Input: Raw job postings (pt-BR)
│   ├── vagas_processadas.csv            # Generated: Processed job data
│   └── embeddings.npy                    # Generated: Sentence embeddings (768-dim vectors)
│
├── job_obs/                              # Main Flask application
│   ├── app.py                            # Flask routes and application logic
│   │
│   ├── service/
│   │   ├── dashboard_data.py             # Data transformations & Plotly figure generation
│   │   └── sample_search.py              # Embedding generation & CSV processing
│   │
│   ├── templates/                        # Jinja2 templates
│   │   ├── base.html                     # Master template (navbar, footer, dark mode)
│   │   ├── index.html                    # Landing page
│   │   ├── dashboard.html                # Dashboard with Plotly charts
│   │   ├── analisys-default.html         # Markdown-based analysis renderer
│   │   ├── analisys-detailed.html        # Analysis gallery view
│   │   └── new_vag.html                  # Job posting submission form
│   │
│   └── static/
│       ├── css/
│       │   ├── dark-mode.css             # Dark mode styles and theme switching
│       │   ├── front-style.css           # Landing page styles
│       │   ├── form-animation.css        # Form interaction animations
│       │   └── analysis-detailed.css     # Analysis gallery styles
│       │
│       ├── js/
│       │   ├── base-dark-mode.js         # Dark mode persistence logic
│       │   ├── dark-mode.js              # Theme toggle functionality
│       │   ├── form-animation.js         # Form validation and animations
│       │   ├── reduced-motion.js         # Accessibility: respect prefers-reduced-motion
│       │   └── search_sample_job.js      # Dashboard search functionality
│       │
│       └── images/
│           └── dashboard_context.json     # Generated: Plotly chart configurations
│
├── analisys_html/                        # Published analyses (HTML files)
│   ├── analise_teste.html                # Example: São Paulo salary analysis
│   └── [your-analysis].html              # Your contributed analyses
│
├── analisys_secondary_files/             # Analysis assets (CSS, JS, images)
│   └── [analysis-name]/
│       ├── css/
│       │   └── analysis-style.css        # Custom styles for the analysis
│       ├── js/
│       │   ├── animations.js             # Dark mode, scroll effects, interactions
│       │   └── charts-config.js          # Plotly chart definitions
│       └── images/
│           └── *.jpg, *.png, *.svg       # Images and graphics
│
├── job_obs_env/                          # Python virtual environment
│   ├── bin/                              # Executables (python, pip, flask)
│   ├── lib/python3.12/site-packages/     # Installed packages
│   └── pyvenv.cfg                        # Virtual environment configuration
│
├── requirements.txt                      # Python dependencies
├── GUIA_TEMPLATES_ANALISE.md            # Portuguese guide for analysis templates
├── RUNNING.md                            # Quick start guide
└── README.md                             # This comprehensive documentation
```

---

## Maintenance and Updates

### Updating Data
```bash
# 1. Replace raw_data.csv with new data
cp new_data.csv data/raw_data.csv

# 2. Regenerate processed data and embeddings
cd job_obs/service
python sample_search.py

# 3. Rebuild dashboard context
python dashboard_data.py

# 4. Restart Flask server
cd ..
python app.py
```

### Adding New Dependencies
```bash
# Install package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt
```

### Monitoring and Logs
Flask runs in debug mode by default. To run in production:
```python
# In app.py, change:
app.run(host='0.0.0.0', port=5005, debug=False)
```

---

## Troubleshooting

### Common Issues

**Issue**: Embeddings generation fails with CUDA error
```bash
# Solution: Force CPU-only inference
export CUDA_VISIBLE_DEVICES=""
python sample_search.py
```

**Issue**: Charts don't appear in dashboard
```bash
# Solution: Regenerate dashboard context
cd job_obs/service
python dashboard_data.py
```

**Issue**: Dark mode doesn't persist
```bash
# Solution: Check browser localStorage permissions
# Ensure site is not in incognito/private mode
```

**Issue**: Analysis assets return 404
```bash
# Solution: Verify file paths match exactly
# HTML: /analisys_secondary_files/<analysis-name>/css/style.css
# Actual: analisys_secondary_files/<analysis-name>/css/style.css
```

---

## License

This project is open source and available under the MIT License.

---

## Contact and Support

- **Repository**: [github.com/rick0110/job-observatory-data-sciece](https://github.com/rick0110/job-observatory-data-sciece)
- **Issues**: Submit bug reports and feature requests via GitHub Issues
- **Discussions**: Join conversations in GitHub Discussions

---

## Acknowledgments

- **Data Sources**: Brazilian job market data aggregated from multiple sources
- **ML Model**: Sentence-Transformers by UKPLab
- **Visualization**: Plotly.js for interactive charts
- **Framework**: Flask web framework and Bootstrap UI toolkit

---

**Built with ❤️ for the Brazilian Data Science community**

