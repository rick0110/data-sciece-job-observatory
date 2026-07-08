"""Script to unify data from raw_data.csv and linkedin_data_raw.json.

This module loads both data sources, normalizes columns to a unified
schema based on the LinkedIn pipeline, and produces a concatenated
DataFrame ready to feed the dashboard and the vector search system.

Final unified columns:
- company: Company name
- role: Normalized role/job function
- seniority: Seniority level (junior, pleno, senior, etc.)
- region: State/region (UF abbreviation or REMOTE)
- work_model: Work modality (remote, hybrid, on-site)
- contract_type: Contract type (CLT, PJ, freelance, etc.)
- salary: Base salary
- total_monthly_compensation: Total monthly compensation
- total_annual_compensation: Total annual compensation
- experience_years: Years of experience required
- technologies: Mentioned technologies/tools
- benefits: Offered benefits
- education: Required education level
- languages: Required languages
- description: Job description (for embeddings)
- source: Data source (raw_data or linkedin)

Usage:
    python -m data_treatment.merge_data_sources
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import re
import unicodedata
from pathlib import Path

from data_treatment.linkedin_data_pipeline import (
    LinkedInDataPipeline,
    ROLE_REGEX,
    SENIORITY_REGEX,
    EXTRACTION_PATTERNS,
)

BENEFITS_PATTERN = EXTRACTION_PATTERNS["benefits"]["pattern"]


def get_project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / 'data').exists():
            return parent
    return Path.cwd()

PROJECT_ROOT = get_project_root()
DATA_DIR = PROJECT_ROOT / 'data'

RAW_DATA_COLUMN_MAPPING: Dict[str, str] = {
    "cargo": "role",
    "empresa": "company",
    "salario_base": "salary",
    "localizacao": "raw_location",
    "modalidade_trabalho": "work_model",
    "nivel": "seniority",
    "experiencia": "experience_years",
    "tipo_contrato": "contract_type",
    "remuneracao_total_anual": "total_annual_compensation",
    "remuneracao_inclui": "compensation_includes",
    "salario_base_detalhado": "salary_detailed",
    "bonus_anual": "annual_bonus",
    "relacao_empresa": "company_relation",
    "area_especializacao": "specialization_area",
    "beneficios": "benefits",
    "remuneracao_total_mensal": "total_monthly_compensation",
}

SENIORITY_MAPPING: Dict[str, str] = {
    "estágio": "estagio",
    "estagio": "estagio",
    "júnior": "junior",
    "junior": "junior",
    "pleno": "pleno",
    "sênior": "senior",
    "senior": "senior",
    "especialista": "senior",
    "líder": "lead",
    "lider": "lead",
    "líder / coordenador": "lead",
    "coordenador": "lead",
    "gerente": "manager",
    "diretor": "manager",
    "staff": "staff",
}

WORK_MODEL_MAPPING: Dict[str, str] = {
    "remoto": "remote",
    "remote": "remote",
    "híbrido": "hybrid",
    "hibrido": "hybrid",
    "hybrid": "hybrid",
    "presencial": "on-site",
    "on-site": "on-site",
    "on site": "on-site",
}

REGIONS_REGEX: Dict[str, str] = {
    "MG": r"\b(minas\s*gerais|mg)\b",
    "SP": r"\b(s[ãa]o\s*paulo|sp)\b",
    "RJ": r"\b(rio\s*de\s*janeiro|rio|rj)\b",
    "DF": r"\b(distrito\s*federal|df|brasilia|bras[íi]lia)\b",
    "RS": r"\b(rio\s*grande\s*do\s*sul|rs)\b",
    "PR": r"\b(paran[áa]|pr)\b",
    "SC": r"\b(santa\s*catarina|sc)\b",
    "BA": r"\b(bahia|ba)\b",
    "PE": r"\b(pernambuco|pe)\b",
    "CE": r"\b(cear[áa]|ce)\b",
    "GO": r"\b(goi[áa]s|go)\b",
    "ES": r"\b(esp[íi]rito\s*santo|es)\b",
    "AM": r"\b(amazona[as]|am)\b",
    "PA": r"\b(par[áa]|pa)\b",
    "MA": r"\b(maranh[ãa]o|ma)\b",
    "RN": r"\b(rio\s*grande\s*do\s*norte|rn)\b",
    "PB": r"\b(para[íi]ba|pb)\b",
    "PI": r"\b(piau[íi]|pi)\b",
    "AL": r"\b(alagoas|al)\b",
    "SE": r"\b(sergipe|se)\b",
    "MT": r"\b(mato\s*grosso|mt)\b",
    "MS": r"\b(mato\s*grossso\s*do\s*sul|ms)\b",
    "RO": r"\b(rond[ôo]nia|ro)\b",
    "AC": r"\b(acre|ac)\b",
    "AP": r"\b(amap[áa]|ap)\b",
    "RR": r"\b(roraima|rr)\b",
    "TO": r"\b(tocantins|to)\b",
    "BR": r"\b(brasil|brazil|br)\b",
    "REMOTE": r"\b(remote|remoto|home\s*office|homeoffice)\b"
}


def normalize_text(text: str) -> str:
    """Normalize text by removing accents and converting to lower case."""
    if pd.isna(text) or text is None:
        return ""
    text = str(text).lower().strip()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    return text


def extract_region_from_location(location: str) -> Optional[str]:
    """Extract a state abbreviation from a free-form location string.

    Returns the matched state code (e.g. 'SP', 'RJ') or None if not found.
    """
    if pd.isna(location) or not location:
        return None
    
    normalized = normalize_text(location)
    
    for state, pattern in REGIONS_REGEX.items():
        if re.search(pattern, normalized, re.IGNORECASE):
            return state
    
    return None


def normalize_seniority(seniority: str) -> str:
    """Normalize a seniority level to the unified standard."""
    if pd.isna(seniority) or not seniority:
        return "not_specified"

    normalized = normalize_text(seniority)
    mapped = SENIORITY_MAPPING.get(normalized, normalized)
    canonical = {"estagio", "junior", "pleno", "senior", "staff", "lead", "manager", "not_specified"}
    if mapped in canonical:
        return mapped
    # SENIORITY_MAPPING only covers the exact spellings seen in raw_data.csv;
    # fall back to the broader regex vocabulary for variants it misses
    # (e.g. "Estagiário" instead of "Estágio").
    return classify_from_text(seniority, SENIORITY_REGEX) or mapped


def normalize_role(role: str) -> Optional[str]:
    """Classify a free-form job title into the unified role taxonomy.

    Keeps `role` consistent across every source (raw_data.csv previously
    stored the literal Portuguese title, e.g. "Analista de Dados Sênior",
    while other sources already used canonical keys like "data_analyst"),
    so charts grouping by role don't fragment the same job into multiple
    labels.
    """
    if pd.isna(role) or not role:
        return None
    return classify_from_text(role, ROLE_REGEX) or normalize_text(role)


def normalize_work_model(work_model: str) -> str:
    """Normalize the work model value to the unified standard."""
    if pd.isna(work_model) or not work_model:
        return "not_specified"
    
    normalized = normalize_text(work_model)
    return WORK_MODEL_MAPPING.get(normalized, normalized)


def classify_from_text(text: str, patterns: Dict[str, str]) -> Optional[str]:
    """Classify a free-form text against a dict of {label: regex} patterns.

    Args:
        text: Raw text to classify (will be normalized internally).
        patterns: Mapping of label -> regex pattern.

    Returns:
        The first matching label, or None if nothing matches.
    """
    normalized = normalize_text(text)
    if not normalized:
        return None
    for label, pattern in patterns.items():
        if re.search(pattern, normalized, re.IGNORECASE):
            return label
    return None


def parse_brl_amount(text: str) -> Optional[float]:
    """Extract a Brazilian Real amount (or the average of a range) from text.

    Handles values like "De R$ 9.001,00 a R$ 10.000,00" or "Até R$ 2.000,00".
    Returns None if no currency-formatted amount is found (guards against
    scraped rows where an unrelated free-text field leaked into this column).
    """
    if pd.isna(text) or not text:
        return None
    matches = re.findall(r"R\$\s*([\d.]+(?:,\d{2})?)", str(text))
    if not matches:
        return None
    values = []
    for m in matches:
        cleaned = m.replace(".", "").replace(",", ".")
        try:
            values.append(float(cleaned))
        except ValueError:
            continue
    if not values:
        return None
    return sum(values) / len(values)


def first_line(text: str) -> Optional[str]:
    """Return the first non-empty line of a text field.

    Several manually-scraped sources duplicate the same value across lines
    (e.g. "Híbrido\\nHíbrido"); this keeps only the first occurrence.
    """
    if pd.isna(text) or not text:
        return None
    return str(text).split("\n")[0].strip() or None


def extract_benefits_from_text(text: str) -> Optional[str]:
    """Detect known benefit keywords in free-text job descriptions.

    Uses the same controlled regex vocabulary as the LinkedIn pipeline
    (`EXTRACTION_PATTERNS["benefits"]`) instead of naively grabbing every
    line under a "Benefícios:" heading, which tends to swallow unrelated
    paragraphs in messily-scraped sources (no blank-line separators).
    """
    if pd.isna(text) or not text:
        return None
    matches = re.findall(BENEFITS_PATTERN, normalize_text(text), re.IGNORECASE)
    if not matches:
        return None
    return ", ".join(dict.fromkeys(matches))


def load_and_process_raw_data(path: str) -> pd.DataFrame:
    """Load and process `raw_data.csv` into the unified schema.

    Args:
        path: Path to the raw_data.csv file.

    Returns:
        DataFrame with renamed and normalized columns.
    """
    print(f"Carregando raw_data de: {path}")
    
    df = pd.read_csv(path, decimal=',', thousands='.')
    
    print(f"  → {len(df)} registros carregados")
    print(f"  → Colunas originais: {df.columns.tolist()}")
    
    df = df.rename(columns=RAW_DATA_COLUMN_MAPPING)
    
    if "raw_location" in df.columns:
        df["region"] = df["raw_location"].apply(extract_region_from_location)
    
    if "seniority" in df.columns:
        df["seniority"] = df["seniority"].apply(normalize_seniority)
    
    if "work_model" in df.columns:
        df["work_model"] = df["work_model"].apply(normalize_work_model)
    
    description_parts = []
    for col in ["role", "specialization_area", "benefits", "company"]:
        if col in df.columns:
            description_parts.append(df[col].fillna("").astype(str))
    
    if description_parts:
        df["description"] = description_parts[0]
        for part in description_parts[1:]:
            df["description"] = df["description"] + " " + part
        df["description"] = df["description"].str.strip()

    if "role" in df.columns:
        # Classify into the same canonical role taxonomy used by every other
        # source, so e.g. "Analista de Dados Sênior" and a LinkedIn posting
        # for the same job both end up as "data_analyst" instead of
        # fragmenting the role-based charts into dozens of literal titles.
        df["role"] = df["role"].apply(normalize_role)

    df["source"] = "raw_data"
    
    for col in ["technologies", "education", "languages"]:
        if col not in df.columns:
            df[col] = "not_specified"
    
    print(f"  → Colunas após processamento: {df.columns.tolist()}")
    
    return df


def load_and_process_linkedin_data(path: str) -> pd.DataFrame:
    """Load and process LinkedIn data using the existing pipeline.

    Args:
        path: Path to the linkedin_data_raw.json file.

    Returns:
        Processed DataFrame using the unified column names.
    """
    print(f"Carregando dados do LinkedIn de: {path}")
    
    pipeline = LinkedInDataPipeline(path)
    
    pipeline.clean_job_raw_positions()
    
    pipeline.clean_regions()
    
    pipeline.extract_information_regex(
        cols=["work_model", "contract_type", "salary", "experience_years", 
              "technologies", "education", "languages", "benefits"],
        description_col_name="raw_html_description"
    )
    
    df = pipeline.df
    
    print(f"  → {len(df)} registros processados")
    
    df["description"] = df["raw_html_description"].fillna("")
    
    df["source"] = "linkedin"
    
    for col in ["total_monthly_compensation", "total_annual_compensation", 
                "salary_detailed", "annual_bonus", "compensation_includes",
                "company_relation", "specialization_area"]:
        if col not in df.columns:
            df[col] = None
    
    print(f"  → Colunas após processamento: {df.columns.tolist()}")

    return df


def load_and_process_catho_data(path: str) -> pd.DataFrame:
    """Load and process manually scraped Catho postings (`data_preprocess/catho.csv`).

    The raw file has inconsistent column alignment depending on the page
    layout Catho served at scrape time (e.g. `localizacao` sometimes holds a
    company name instead of a city). Values are therefore extracted with
    regex guards instead of trusted by column position, and rows are
    deduplicated by `url` since the scraper saved one row per rendered card.

    Args:
        path: Path to catho.csv.

    Returns:
        DataFrame in the unified schema.
    """
    print(f"Carregando dados da Catho de: {path}")
    df = pd.read_csv(path)
    df = df.drop_duplicates(subset="url").reset_index(drop=True)
    print(f"  → {len(df)} vagas únicas (por url)")

    search_text = (
        df["titulo"].fillna("") + " " + df["descricao_vaga"].fillna("")
    )

    out = pd.DataFrame()
    # `empresa` is unreliable in this source: the scraper's company-name
    # selector picked up unrelated UI text ("compartilhar", "Idioma:") for
    # almost every row, so we drop it rather than surface bad company data.
    out["company"] = None
    out["role"] = search_text.apply(lambda t: classify_from_text(t, ROLE_REGEX))
    out["seniority"] = search_text.apply(lambda t: classify_from_text(t, SENIORITY_REGEX))
    # Region is intentionally read only from `localizacao` (a dedicated,
    # structured field) and not from the free-text description: short state
    # codes like "PA" or "TO" collide with common Portuguese/English words
    # ("para", "to"), producing false positives when scanned over prose.
    out["region"] = df["localizacao"].apply(extract_region_from_location)
    out["work_model"] = search_text.apply(
        lambda t: classify_from_text(
            t,
            {
                "remote": r"\b(remoto|home\s*office|100%\s*remota?|remote\s*work)\b",
                "hybrid": r"\b(h[íi]brido)\b",
                "on-site": r"\b(presencial)\b",
            },
        )
    )
    out["contract_type"] = df["info_regime_de_contratacao"].apply(first_line)
    out["salary"] = df["salario"].apply(parse_brl_amount)
    out["benefits"] = df["info_benefícios"].fillna(
        df["descricao_vaga"].apply(extract_benefits_from_text)
    )
    out["description"] = df["descricao_vaga"].fillna(df["titulo"])
    out["source"] = "catho"

    for col in ["technologies", "education", "languages"]:
        out[col] = "not_specified"

    return out


def load_and_process_gupy_data(path: str, source_name: str = "gupy") -> pd.DataFrame:
    """Load and process manually collected Gupy-style postings.

    Covers files such as `data_preprocess/cientista_de_dados.csv`, which
    aggregate job board pages that duplicate each field across two lines
    (e.g. "Híbrido\\nHíbrido"); only the first line is kept.

    Args:
        path: Path to the CSV file.
        source_name: Value stored in the `source` column for provenance.

    Returns:
        DataFrame in the unified schema.
    """
    print(f"Carregando dados (Gupy) de: {path}")
    df = pd.read_csv(path)
    print(f"  → {len(df)} vagas carregadas")

    description_cols = [
        c
        for c in ["descricao_vaga", "responsabilidades", "requisitos", "informacoes_adicionais"]
        if c in df.columns
    ]
    description = df[description_cols].fillna("").agg(" ".join, axis=1) if description_cols else pd.Series([""] * len(df))
    search_text = df["titulo"].fillna("") + " " + description

    out = pd.DataFrame()
    out["company"] = None
    out["role"] = search_text.apply(lambda t: classify_from_text(t, ROLE_REGEX))
    out["seniority"] = search_text.apply(lambda t: classify_from_text(t, SENIORITY_REGEX))
    out["region"] = df["localizacao"].apply(lambda t: extract_region_from_location(first_line(t)))
    out["work_model"] = df["modelo_trabalho"].apply(first_line).apply(normalize_work_model)
    out["contract_type"] = df["tipo_vaga"].apply(first_line) if "tipo_vaga" in df.columns else None
    out["salary"] = None
    out["benefits"] = (
        df["informacoes_adicionais"].apply(extract_benefits_from_text)
        if "informacoes_adicionais" in df.columns
        else None
    )
    out["description"] = description.str.strip()
    out["source"] = source_name

    for col in ["technologies", "education", "languages"]:
        out[col] = "not_specified"

    return out


def load_and_process_glassdoor_data(path: str) -> pd.DataFrame:
    """Load and process aggregated Glassdoor salary benchmark data.

    Unlike the other sources, each row of `data_preprocess/glassdoor.csv` is
    not an individual job posting but a (company, role) salary benchmark
    card (min/max/average, mirroring Glassdoor's own "Salaries" pages). Rows
    are kept 1:1 (not expanded by `número de vagas`, which represents the
    sample size behind the estimate, not open positions) so they contribute
    real salary data points without distorting job-count statistics.

    Args:
        path: Path to glassdoor.csv.

    Returns:
        DataFrame in the unified schema.
    """
    print(f"Carregando dados do Glassdoor de: {path}")
    df = pd.read_csv(path)
    df = df.drop_duplicates().reset_index(drop=True)
    print(f"  → {len(df)} registros de referência salarial (após remover duplicatas exatas)")

    out = pd.DataFrame()
    out["company"] = df["Nome da empresa"]
    out["role"] = df["cargo"].apply(lambda t: classify_from_text(t, ROLE_REGEX) or "data_scientist")
    out["seniority"] = df["cargo"].apply(lambda t: classify_from_text(t, SENIORITY_REGEX) or "not_specified")
    out["region"] = None
    out["work_model"] = None
    out["contract_type"] = None
    salary = pd.to_numeric(df["salário médio"], errors="coerce")
    # A handful of rows (e.g. "Lead Data Scientist" at R$640.000) are
    # implausible as a *monthly* base salary in Brazil and are most likely
    # annual compensation or a currency mixup upstream. Treat them as
    # missing rather than let them distort the salary charts.
    IMPLAUSIBLE_MONTHLY_SALARY = 100_000
    out["salary"] = salary.where(salary <= IMPLAUSIBLE_MONTHLY_SALARY)
    out["benefits"] = None
    out["description"] = df["cargo"].fillna("") + " " + df["Nome da empresa"].fillna("")
    out["source"] = "glassdoor"

    for col in ["technologies", "education", "languages"]:
        out[col] = "not_specified"

    return out


def merge_datasets(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate any number of processed DataFrames using the unified columns.

    Args:
        dfs: Processed DataFrames, one per data source, already using
            (a subset of) the unified column names.

    Returns:
        Concatenated DataFrame with standardized columns.
    """
    print("Mesclando datasets...")

    final_columns = [
        "company",
        "role",
        "seniority",
        "region",
        "work_model",
        "contract_type",
        "salary",
        "total_monthly_compensation",
        "total_annual_compensation",
        "experience_years",
        "technologies",
        "benefits",
        "education",
        "languages",
        "description",
        "source",
    ]

    prepared = []
    for df in dfs:
        for col in final_columns:
            if col not in df.columns:
                df[col] = None
        prepared.append(df[final_columns].copy())

    df_merged = pd.concat(prepared, ignore_index=True)

    print(f"  → Total registries: {len(df_merged)}")
    for df in prepared:
        source_name = df["source"].iloc[0] if len(df) else "?"
        print(f"  → Registries of {source_name}: {len(df)}")

    return df_merged


def preprocess_for_dashboard(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Preprocess the merged DataFrame for dashboard consumption.

    Includes:
    - Data type conversions
    - Creation of binary columns for benefits
    - Value cleaning

    Args:
        df: Merged DataFrame

    Returns:
        Tuple (processed DataFrame, list of identified benefits)
    """
    print("Preprocessando para dashboard...")
    
    if "salary" in df.columns:
        df["salary"] = pd.to_numeric(df["salary"], errors="coerce")
    
    if "total_monthly_compensation" in df.columns:
        df["total_monthly_compensation"] = pd.to_numeric(
            df["total_monthly_compensation"], errors="coerce"
        )
    
    benefit_list = []
    if "benefits" in df.columns:
        all_benefits = df["benefits"].dropna().unique()
        for ben_str in all_benefits:
            if ben_str and ben_str != "not_specified":
                parts = re.split(r"[,|]", str(ben_str))
                benefit_list.extend([b.strip().lower() for b in parts if b.strip()])
        
        benefit_list = sorted(set(benefit_list))
        
        for benefit in benefit_list:
            df[f"benefit_{benefit}"] = df["benefits"].apply(
                lambda x: "yes" if pd.notna(x) and benefit in str(x).lower() else "no"
            )
    
    print(f"  → {len(benefit_list)} unique benefits identified")
    
    return df, benefit_list


def _try_load(label: str, loader) -> Optional[pd.DataFrame]:
    """Run a source loader, tolerating a missing/optional file.

    Data collection sources are independent: the LinkedIn scraper output and
    some manual CSVs may simply not exist yet on a fresh checkout (they are
    either gitignored generated artifacts or optional manual contributions).
    Rather than crashing the whole pipeline, we skip the source and let the
    rest of the merge proceed with whatever is available.
    """
    try:
        return loader()
    except FileNotFoundError:
        print(f"  ⚠ Fonte '{label}' não encontrada, pulando (isso é esperado se ela ainda não foi coletada).")
        return None
    except (ValueError, KeyError) as e:
        print(f"  ⚠ Fonte '{label}' inválida/corrompida, pulando: {e}")
        return None


def run_merge_pipeline(
    raw_data_path: str = "./data/raw_data.csv",
    linkedin_data_path: str = "./data/linkedin_data_raw.json",
    catho_path: str = "./data_preprocess/catho.csv",
    glassdoor_path: str = "./data_preprocess/glassdoor.csv",
    gupy_path: str = "./data_preprocess/cientista_de_dados.csv",
    output_path: str = "./data/vagas_unificadas.csv",
) -> Tuple[pd.DataFrame, List[str]]:
    """Run the full merge and preprocessing pipeline.

    Combines every available data source into the unified schema. Sources
    that are missing on disk (e.g. `linkedin_data_raw.json` before the first
    scrape has been run) are skipped with a warning instead of failing the
    whole pipeline.

    Args:
        raw_data_path: Path to raw_data.csv (manually compiled salário transparente data).
        linkedin_data_path: Path to linkedin_data_raw.json (output of the scraper).
        catho_path: Path to the manually scraped Catho postings.
        glassdoor_path: Path to the Glassdoor salary benchmark export.
        gupy_path: Path to the manually collected Gupy-style postings.
        output_path: Path where the unified CSV will be saved.

    Returns:
        Tuple (final DataFrame, list of benefits)
    """
    print("=" * 60)
    print("STARTING DATA MERGE PIPELINE")
    print("=" * 60)

    sources = [
        _try_load("raw_data", lambda: load_and_process_raw_data(raw_data_path)),
        _try_load("linkedin", lambda: load_and_process_linkedin_data(linkedin_data_path)),
        _try_load("catho", lambda: load_and_process_catho_data(catho_path)),
        _try_load("glassdoor", lambda: load_and_process_glassdoor_data(glassdoor_path)),
        _try_load("gupy/cientista_de_dados", lambda: load_and_process_gupy_data(gupy_path)),
    ]
    available = [df for df in sources if df is not None and len(df) > 0]

    if not available:
        raise RuntimeError(
            "Nenhuma fonte de dados disponível. Verifique se ao menos "
            "data/raw_data.csv ou data_preprocess/*.csv existem."
        )

    df_merged = merge_datasets(available)

    df_final, benefit_list = preprocess_for_dashboard(df_merged)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(output_path, index=False)
    print(f"\n✓ Unified dataset saved at: {output_path}")

    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Total records: {len(df_final)}")
    print(f"Columns: {df_final.columns.tolist()}")
    print(f"Unique benefits: {len(benefit_list)}")

    return df_final, benefit_list


if __name__ == "__main__":
    df, benefits = run_merge_pipeline(
        raw_data_path=str(DATA_DIR / "raw_data.csv"),
        linkedin_data_path=str(DATA_DIR / "linkedin_data_raw.json"),
        catho_path=str(PROJECT_ROOT / "data_preprocess" / "catho.csv"),
        glassdoor_path=str(PROJECT_ROOT / "data_preprocess" / "glassdoor.csv"),
        gupy_path=str(PROJECT_ROOT / "data_preprocess" / "cientista_de_dados.csv"),
        output_path=str(DATA_DIR / "vagas_unificadas.csv"),
    )

    print("\nSAMPLE OF DATA:")
    print(df.head())
