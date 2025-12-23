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

from data_treatment.likedin_data_pipeline import LinkedInDataPipeline


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
    return SENIORITY_MAPPING.get(normalized, normalized)


def normalize_work_model(work_model: str) -> str:
    """Normalize the work model value to the unified standard."""
    if pd.isna(work_model) or not work_model:
        return "not_specified"
    
    normalized = normalize_text(work_model)
    return WORK_MODEL_MAPPING.get(normalized, normalized)


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
    
    pipeline.clan_regions()
    
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


def merge_datasets(df_raw: pd.DataFrame, df_linkedin: pd.DataFrame) -> pd.DataFrame:
    """Concatenate the two DataFrames using the unified columns.

    Args:
        df_raw: Processed DataFrame from raw_data.csv
        df_linkedin: Processed DataFrame from LinkedIn data

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
    
    for col in final_columns:
        if col not in df_raw.columns:
            df_raw[col] = None
        if col not in df_linkedin.columns:
            df_linkedin[col] = None
    
    df_raw_final = df_raw[final_columns].copy()
    df_linkedin_final = df_linkedin[final_columns].copy()
    
    df_merged = pd.concat([df_raw_final, df_linkedin_final], ignore_index=True)
    
    print(f"  → Total registries: {len(df_merged)}")
    print(f"  → Registries of raw_data: {len(df_raw_final)}")
    print(f"  → Registries of LinkedIn: {len(df_linkedin_final)}")
    
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


def run_merge_pipeline(
    raw_data_path: str = "./data/raw_data.csv",
    linkedin_data_path: str = "./data/linkedin_data_raw.json",
    output_path: str = "./data/vagas_unificadas.csv",
) -> Tuple[pd.DataFrame, List[str]]:
    """Run the full merge and preprocessing pipeline.

    Args:
        raw_data_path: Path to raw_data.csv
        linkedin_data_path: Path to linkedin_data_raw.json
        output_path: Path where the unified CSV will be saved

    Returns:
        Tuple (final DataFrame, list of benefits)
    """
    print("=" * 60)
    print("STARTING DATA MERGE PIPELINE")
    print("=" * 60)
    
    df_raw = load_and_process_raw_data(raw_data_path)
    
    df_linkedin = load_and_process_linkedin_data(linkedin_data_path)
    
    df_merged = merge_datasets(df_raw, df_linkedin)
    
    df_final, benefit_list = preprocess_for_dashboard(df_merged)
    
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
    raw_path = DATA_DIR / "raw_data.csv"
    linkedin_path = DATA_DIR / "linkedin_data_raw.json"
    output_path = DATA_DIR / "vagas_unificadas.csv"

    df, benefits = run_merge_pipeline(
        raw_data_path=str(raw_path),
        linkedin_data_path=str(linkedin_path),
        output_path=str(output_path),
    )
    
    print("\nSAMPLE OF DATA:")
    print(df.head())
