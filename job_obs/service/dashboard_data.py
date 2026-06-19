"""Module to generate data and visualizations for the dashboard.

This module uses the unified column naming defined in
`data_treatment/merge_data_sources.py`.

Main columns:
- company: Company name
- role: Normalized role/job function
- seniority: Seniority level (junior, pleno, senior, etc.)
- region: State/region (UF code or REMOTE)
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
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import requests
import json
import unicodedata
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio


# Mapeamento de senioridade para labels em português (display)
SENIORITY_DISPLAY_LABELS = {
    "estagio": "Estágio",
    "junior": "Júnior",
    "pleno": "Pleno",
    "senior": "Sênior",
    "staff": "Staff",
    "lead": "Líder / Coordenador",
    "manager": "Gerente",
    "not_specified": "Não informado",
}

# Mapeamento de modalidade de trabalho para labels em português (display)
WORK_MODEL_DISPLAY_LABELS = {
    "remote": "Remoto",
    "hybrid": "Híbrido",
    "on-site": "Presencial",
    "not_specified": "Não informado",
}


def get_project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / 'data').exists():
            return parent
    return Path.cwd()


PROJECT_ROOT = get_project_root()
DATA_DIR = PROJECT_ROOT / 'data'
STATIC_DIR = PROJECT_ROOT / 'job_obs' / 'static'


BRAZIL_STATE_NAMES = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}

def load_data(path: str = None) -> pd.DataFrame:
    """Load data from the unified CSV file."""
    df = pd.read_csv(path)
    return df


def process_benefits(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Extract benefits and create binary columns for each benefit.

    Args:
        df: DataFrame containing a 'benefits' column.

    Returns:
        Tuple (DataFrame with benefit columns added, list of benefits).
    """
    import re
    
    if "benefits" not in df.columns:
        return df, []
    
    all_benefits = df["benefits"].dropna().unique()
    benefit_list = []
    
    for ben_str in all_benefits:
        if ben_str and ben_str != "not_specified":
            parts = re.split(r"[,|]", str(ben_str))
            benefit_list.extend([b.strip().lower() for b in parts if b.strip()])
    
    benefit_list = sorted(set(benefit_list))
    
    for benefit in benefit_list:
        col_name = f"benefit_{benefit}"
        if col_name not in df.columns:
            df[col_name] = df["benefits"].apply(
                lambda x: "yes" if pd.notna(x) and benefit in str(x).lower() else "no"
            )
    
    return df, benefit_list


def normalizar(txt: str | None) -> str | None:
    """Normalize text by removing accents and converting to lower case."""
    if txt is None:
        return None
    txt = str(txt).strip()
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt.lower()


def transform_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Apply transformations to the unified data.

    This function is kept for compatibility and expects data already in the
    unified format produced by `merge_data_sources.py`.

    Args:
        df: DataFrame in the unified schema.

    Returns:
        Tuple (transformed DataFrame, list of benefits).
    """
    # Processar benefícios
    df, benefit_list = process_benefits(df)
    
    # Converter salary para numérico se necessário
    if "salary" in df.columns:
        df["salary"] = pd.to_numeric(df["salary"], errors="coerce")
    
    if "total_monthly_compensation" in df.columns:
        df["total_monthly_compensation"] = pd.to_numeric(
            df["total_monthly_compensation"], errors="coerce"
        )
    
    return df, benefit_list

def _normalize_text(text: str) -> str:
    return unicodedata.normalize("NFD", text.lower().strip())

def _get_brazil_geojson() -> Dict[str, Any]:
    """Download the GeoJSON describing Brazilian states."""
    url_geojson = (
        "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/"
        "brazil-states.geojson"
    )
    response = requests.get(url_geojson, timeout=10)
    response.raise_for_status()
    geojson = response.json()

    normalized_map = {
        _normalize_text(label).encode("ascii", "ignore").decode(): code
        for code, label in BRAZIL_STATE_NAMES.items()
    }
    for feature in geojson.get("features", []):
        name = feature.get("properties", {}).get("name", "")
        normalized_name = (
            _normalize_text(name)
            .encode("ascii", "ignore")
            .decode()
        )
        code = normalized_map.get(normalized_name)
        if code:
            feature.setdefault("properties", {})["sigla"] = code
    return geojson

def _figure_to_dict(fig: go.Figure) -> Dict[str, Any]:
    """Convert a Plotly figure into a plain dict ready to be serialized."""
    return json.loads(pio.to_json(fig, pretty=False))


def _add_data_count_annotation(fig: go.Figure, n_records: int, total_records: int) -> None:
    """Add an annotation showing the number of records used in the figure."""
    fig.add_annotation(
        text=f"Records used: {n_records:,} of {total_records:,} ({100*n_records/total_records:.1f}%)",
        xref="paper",
        yref="paper",
        x=1.0,
        y=-0.12,
        showarrow=False,
        font=dict(size=10, color="gray"),
        xanchor="right",
        yanchor="top",
    )


def build_salary_histogram(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    """Build a histogram of base salary distribution."""
    total_records = len(df)
    df_clean = df.dropna(subset=["salary"])
    n_records = len(df_clean)
    
    fig = px.histogram(
        df_clean,
        x="salary",
        nbins=30,
        color_discrete_sequence=["#1f77b4"],
    )
    fig.update_layout(
        title="Distribuição Geral de Salários Base",
        xaxis_title="Salário Base (R$)",
        yaxis_title="Quantidade de Vagas",
        bargap=0.05,
        template=template,
        margin=dict(b=80),
    )
    fig.update_traces(hovertemplate="Salário: R$ %{x:,.0f}<br>Vagas: %{y}<extra></extra>")
    _add_data_count_annotation(fig, n_records, total_records)
    return _figure_to_dict(fig)


def build_salary_by_level(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    """Build salary histograms grouped by seniority level."""
    total_records = len(df)
    df_level = df.dropna(subset=["salary", "seniority"]).copy()
    n_records = len(df_level)
    
    # Mapear para labels de display
    df_level["seniority_display"] = df_level["seniority"].map(
        lambda x: SENIORITY_DISPLAY_LABELS.get(x, x)
    )
    
    dark_colors = [
        "chartreuse",
        "darksalmon",
        "darkcyan",
        "darkkhaki",
        "cadetblue",
        "darkorchid",   
        "firebrick"     
    ]
    
    category_order = ["Estágio", "Júnior", "Pleno", "Sênior", "Staff", "Líder / Coordenador", "Gerente", "Não informado"]
    
    if template == 'plotly_white':
        fig = px.histogram(
            df_level,
            x="salary",
            color="seniority_display",
            nbins=25,
            barmode="relative",
            opacity=1,
            labels={"seniority_display": "Nível"},
            category_orders={"seniority_display": category_order},
            color_discrete_sequence=px.colors.qualitative.D3,
        )
        fig.update_layout(
            title="Distribuição de Salários por Nível de Senioridade",
            xaxis_title="Faixa salarial (R$)",
            yaxis_title="Quantidade de Vagas",
            template=template,
            legend_title="Nível",
            margin=dict(b=80),
        )
        fig.update_traces(hovertemplate="Nível: %{legendgroup}<br>Salário: R$ %{x:,.0f}<br>Vagas: %{y}<extra></extra>")
        _add_data_count_annotation(fig, n_records, total_records)
        return _figure_to_dict(fig)
    
    elif template == 'plotly_dark':
        fig = px.histogram(
            df_level,
            x="salary",
            color="seniority_display",
            nbins=25,
            barmode="relative",
            opacity=1,
            labels={"seniority_display": "Nível"},
            category_orders={"seniority_display": category_order},
            color_discrete_sequence=dark_colors,
        )
        fig.update_layout(
            title="Distribuição de Salários por Nível de Senioridade",
            xaxis_title="Faixa salarial (R$)",
            yaxis_title="Quantidade de Vagas",
            template=template,
            legend_title="Nível",
            margin=dict(b=80),
        )
        fig.update_traces(hovertemplate="Nível: %{legendgroup}<br>Salário: R$ %{x:,.0f}<br>Vagas: %{y}<extra></extra>")
        _add_data_count_annotation(fig, n_records, total_records)
        return _figure_to_dict(fig)


def build_boxplot_by_level(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    """Build a boxplot of salaries by seniority level."""
    total_records = len(df)
    df_box = df.dropna(subset=["salary", "seniority"]).copy()
    n_records = len(df_box)
    
    df_box["seniority_display"] = df_box["seniority"].map(
        lambda x: SENIORITY_DISPLAY_LABELS.get(x, x)
    )
    
    fig = px.box(
        df_box,
        x="seniority_display",
        y="salary",
        color="seniority_display",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_layout(
        title="Boxplot de Salário Base por Nível",
        xaxis_title="Nível",
        yaxis_title="Salário Base (R$)",
        template=template,
        showlegend=False,
        margin=dict(b=80),
    )
    _add_data_count_annotation(fig, n_records, total_records)
    return _figure_to_dict(fig)


def build_violin_by_level(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    """Build a violin plot of salaries by seniority level."""
    total_records = len(df)
    df_violin = df.dropna(subset=["salary", "seniority"]).copy()
    n_records = len(df_violin)
    
    df_violin["seniority_display"] = df_violin["seniority"].map(
        lambda x: SENIORITY_DISPLAY_LABELS.get(x, x)
    )
    
    fig = px.violin(
        df_violin,
        x="seniority_display",
        y="salary",
        color="seniority_display",
        box=True,
        points="outliers",
        color_discrete_sequence=px.colors.qualitative.Vivid,
    )
    fig.update_layout(
        title="Distribuição (Violin Plot) por Nível",
        xaxis_title="Nível",
        yaxis_title="Salário Base (R$)",
        template=template,
        showlegend=False,
        margin=dict(b=80),
    )
    _add_data_count_annotation(fig, n_records, total_records)
    return _figure_to_dict(fig)

def build_states_bar(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    """Build a bar chart of the top 10 states by job count."""
    total_records = len(df)
    df_clean = df.dropna(subset=["region"])
    n_records = len(df_clean)
    
    top_states = df_clean["region"].value_counts().head(10).sort_values(ascending=True)
    states_df = top_states.reset_index()
    states_df.columns = ["region", "quantidade"]
    
    # Mapear siglas para nomes completos
    states_df["estado_nome"] = states_df["region"].map(
        lambda x: BRAZIL_STATE_NAMES.get(x, x)
    )
    
    fig = px.bar(
        states_df,
        x="quantidade",
        y="estado_nome",
        orientation="h",
        color="quantidade",
        color_continuous_scale="Reds",
    )
    fig.update_layout(
        title="Top 10 Estados com Mais Vagas",
        xaxis_title="Quantidade de Vagas",
        yaxis_title="Estado",
        template=template,
        coloraxis_showscale=False,
        margin=dict(b=80),
    )
    fig.update_traces(hovertemplate="Estado: %{y}<br>Vagas: %{x}<extra></extra>")
    _add_data_count_annotation(fig, n_records, total_records)
    return _figure_to_dict(fig)

def build_heatmap_state_level(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    """Build a heatmap of mean salary by state and seniority level."""
    total_records = len(df)
    df_heat = df.dropna(subset=["region", "seniority", "salary"]).copy()
    n_records = len(df_heat)
    
    df_heat["seniority_display"] = df_heat["seniority"].map(
        lambda x: SENIORITY_DISPLAY_LABELS.get(x, x)
    )
    
    pivot = (
        df_heat.groupby(["region", "seniority_display"])["salary"]
        .mean()
        .unstack(fill_value=0)
    )
    
    relevant_states = df_heat["region"].value_counts()
    valid_states = relevant_states[relevant_states >= 5].index
    pivot = pivot.loc[pivot.index.isin(valid_states)]

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="Viridis",
            colorbar=dict(title="Salário Médio (R$)"),
            hovertemplate=(
                "Estado: %{y}<br>Nível: %{x}<br>Salário médio: R$ %{z:,.0f}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Heatmap - Salário Médio por Estado e Nível",
        xaxis_title="Nível",
        yaxis_title="Estado",
        template=template,
        margin=dict(b=80),
    )
    _add_data_count_annotation(fig, n_records, total_records)
    return _figure_to_dict(fig)

def build_salary_comparison(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    """Build a scatter plot of base salary vs total compensation."""
    total_records = len(df)
    
    if "total_monthly_compensation" not in df.columns:
        return _figure_to_dict(go.Figure())

    df_comp = df.dropna(subset=["salary", "total_monthly_compensation"]).copy()
    if df_comp.empty:
        return _figure_to_dict(go.Figure())

    n_records = len(df_comp)
    
    df_comp["seniority_display"] = df_comp["seniority"].map(
        lambda x: SENIORITY_DISPLAY_LABELS.get(x, x)
    )

    q99_base = df_comp["salary"].quantile(0.99)
    q99_total = df_comp["total_monthly_compensation"].quantile(0.99)
    df_filtered = df_comp[(df_comp["salary"] <= q99_base) & (df_comp["total_monthly_compensation"] <= q99_total)]
    n_filtered = len(df_filtered)

    fig = px.scatter(
        df_filtered,
        x="salary",
        y="total_monthly_compensation",
        color="seniority_display",
        labels={"seniority_display": "Nível"},
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig.add_trace(
        go.Scatter(
            x=[0, df_filtered["salary"].max()],
            y=[0, df_filtered["salary"].max()],
            mode="lines",
            line=dict(color="red", dash="dash"),
            name="Linha de igualdade",
        )
    )
    fig.update_layout(
        title="Salário Base vs Remuneração Total Mensal",
        xaxis_title="Salário Base (R$)",
        yaxis_title="Remuneração Total (R$)",
        template=template,
        margin=dict(b=80),
    )
    fig.update_traces(hovertemplate="Salário Base: R$ %{x:,.0f}<br>Remuneração Total: R$ %{y:,.0f}<extra></extra>")
    _add_data_count_annotation(fig, n_filtered, total_records)
    return _figure_to_dict(fig)

def build_work_modality(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    """Build a pie chart for work modality distribution."""
    total_records = len(df)
    # Para o gráfico de modalidade, usamos todos os registros
    # Valores NA são mapeados para "Não informado"
    df_work = df.copy()
    df_work["work_model_display"] = df_work["work_model"].map(
        lambda x: WORK_MODEL_DISPLAY_LABELS.get(x, x) if pd.notna(x) else "Não informado"
    )
    
    n_records = len(df_work)
    
    modalidades = df_work["work_model_display"].fillna("Não informado").value_counts()
    modalidade_df = modalidades.reset_index()
    modalidade_df.columns = ["modalidade", "quantidade"]
    
    fig = px.pie(
        modalidade_df,
        names="modalidade",
        values="quantidade",
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig.update_traces(textposition="inside", texttemplate="%{label}<br>%{percent:.1%}")
    fig.update_layout(
        title="Distribuição de Vagas por Modalidade de Trabalho",
        template=template,
        margin=dict(b=80),
    )
    _add_data_count_annotation(fig, n_records, total_records)
    return _figure_to_dict(fig)

def build_career_analysis(df: pd.DataFrame, template) -> Dict[str, Any]:
    """Build a chart of mean salary by top roles."""
    total_records = len(df)
    df_clean = df.dropna(subset=["role", "salary"])
    n_records = len(df_clean)
    
    top_roles = df_clean["role"].value_counts().head(6).index
    subset = (
        df_clean[df_clean["role"].isin(top_roles)]
        .groupby("role")["salary"]
        .mean()
        .sort_values(ascending=True)
    )
    career_df = subset.reset_index()
    career_df.columns = ["role", "salario_medio"]
    
    fig = px.bar(
        career_df,
        x="salario_medio",
        y="role",
        orientation="h",
        color="salario_medio",
        color_continuous_scale="Purples",
    )
    fig.update_layout(
        title="Salário Médio por Cargo (Top 6)",
        xaxis_title="Salário Base Médio (R$)",
        yaxis_title="Cargo",
        template=template,
        coloraxis_showscale=False,
        margin=dict(b=80),
    )
    fig.update_traces(hovertemplate="Cargo: %{y}<br>Salário Médio: R$ %{x:,.0f}<extra></extra>")
    _add_data_count_annotation(fig, n_records, total_records)
    return _figure_to_dict(fig)

def _top_benefits(df: pd.DataFrame, benefit_list: List[str]) -> Tuple[pd.Series, int]:
    """Calcula os benefícios mais frequentes.
    
    Returns:
        Tupla (Series com contagens, número de registros com benefícios)
    """
    # Colunas de benefícios têm prefixo 'benefit_'
    benefit_cols = [f"benefit_{b}" for b in benefit_list if f"benefit_{b}" in df.columns]
    if not benefit_cols:
        return pd.Series(dtype="int64"), 0
    
    # Contar registros que têm pelo menos um benefício
    has_benefit = df[benefit_cols].eq("yes").any(axis=1)
    n_with_benefits = has_benefit.sum()
    
    counts = df[benefit_cols].eq("yes").sum()
    # Remover prefixo para exibição
    counts.index = [col.replace("benefit_", "") for col in counts.index]
    counts = counts.sort_values(ascending=False).head(15)
    return counts, n_with_benefits

def build_benefits_analysis(df: pd.DataFrame, benefit_list: List[str], template='plotly_white') -> Dict[str, Any]:
    total_records = len(df)
    benefits, n_with_benefits = _top_benefits(df, benefit_list)
    
    if benefits.empty:
        return _figure_to_dict(go.Figure())

    benefits_sorted = benefits.sort_values()
    fig = px.bar(
        benefits_sorted,
        x=benefits_sorted.values,
        y=benefits_sorted.index,
        orientation="h",
        color=benefits_sorted.values,
        color_continuous_scale="Teal",
    )
    fig.update_layout(
        title="Top 15 Benefícios Oferecidos",
        xaxis_title="Quantidade de Vagas",
        yaxis_title="Benefício",
        template=template,
        coloraxis_showscale=False,
        margin=dict(b=80),
    )
    fig.update_traces(
        hovertemplate="Benefício: %{y}<br>Vagas: %{x}<extra></extra>"
    )
    _add_data_count_annotation(fig, n_with_benefits, total_records)
    return _figure_to_dict(fig)

def build_interactive_map(df: pd.DataFrame, template = 'plotly_white') -> Dict[str, Any]:
    """Build an interactive choropleth map of job counts by state."""
    total_records = len(df)
    df_clean = df.dropna(subset=["region"])
    n_records = len(df_clean)
    
    geojson = _get_brazil_geojson()
    grouped = df_clean.groupby("region", dropna=True).agg(
        num_vagas=("role", "count"),
        media_salario_base=("salary", "mean"),
        media_remuneracao_total=("total_monthly_compensation", "mean"),
        salario_min=("salary", "min"),
        salario_max=("salary", "max"),
    )
    grouped = grouped.reset_index()
    all_states = pd.DataFrame({"region": list(BRAZIL_STATE_NAMES.keys())})
    merged = all_states.merge(grouped, on="region", how="left")
    for column in ["num_vagas", "media_salario_base", "media_remuneracao_total", "salario_min", "salario_max"]:
        if column in merged.columns:
            merged[column] = merged[column].fillna(0)

    merged["estado_nome"] = merged["region"].map(BRAZIL_STATE_NAMES)

    customdata = merged[["estado_nome", "num_vagas", "media_salario_base", "media_remuneracao_total", "salario_min", "salario_max"]].values

    fig = go.Figure()

    # neon colorscale (de mais claro a mais intenso)
    neon_colorscale = [
        [0.0, "#e0f7ff"],
        [0.2, "#00e5ff"],
        [0.5, "#00b3ff"],
        [0.8, "#0066ff"],
        [1.0, "#6600ff"],
    ]

    mask_pos = merged["num_vagas"] > 0
    if mask_pos.any():
        fig.add_trace(
            go.Choropleth(
                geojson=geojson,
                locations=merged.loc[mask_pos, "region"],
                z=merged.loc[mask_pos, "num_vagas"],
                featureidkey="properties.sigla",
                colorscale=neon_colorscale,
                marker_line_color="#0ff",  # neon-like border
                marker_line_width=0.8,
                colorbar=dict(title="Número de vagas", outlinecolor="#00e5ff"),
                customdata=merged.loc[mask_pos, ["estado_nome", "num_vagas", "media_salario_base", "media_remuneracao_total", "salario_min", "salario_max"]].values,
                hovertemplate=(
                    "<b style='color:#00e5ff'>Estado:</b> %{customdata[0]}<br>"
                    "<b style='color:#00e5ff'>Vagas:</b> %{customdata[1]}<br>"
                    "<b style='color:#00e5ff'>Salário médio:</b> R$ %{customdata[2]:,.0f}<br>"
                    "<b style='color:#00e5ff'>Remuneração média:</b> R$ %{customdata[3]:,.0f}<extra></extra>"
                ),
                hoverlabel=dict(bgcolor="#001122", font_size=12, font_color="#00e5ff"),
            )
        )
    mask_zero = merged["num_vagas"] == 0
    if mask_zero.any():
        fig.add_trace(
            go.Choropleth(
                geojson=geojson,
                locations=merged.loc[mask_zero, "region"],
                z=[1] * merged.loc[mask_zero].shape[0],
                featureidkey="properties.sigla",
                colorscale=[[0, "#f0f0f0"], [1, "#f0f0f0"]],
                showscale=False,
                marker_line_color="#cccccc",
                marker_line_width=0.5,
                hovertemplate=(
                    "Estado: %{location}<br>Vagas: 0<extra></extra>"
                ),
                hoverlabel=dict(bgcolor="#111111", font_size=11, font_color="#444444"),
            )
        )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        title="Distribuição de Vagas por Estado",
        template=template,
        margin=dict(l=0, r=0, t=40, b=60),
        uirevision='fixed',
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    _add_data_count_annotation(fig, n_records, total_records)

    return _figure_to_dict(fig)

def build_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Build a statistical summary of the dataset."""
    total_registros = len(df)
    salarios = df["salary"].dropna()
    n_salarios = len(salarios)
    
    # Calcular remuneração total média se disponível
    media_remuneracao = 0.0
    n_remuneracoes = 0
    if "total_monthly_compensation" in df.columns:
        remuneracoes = df["total_monthly_compensation"].dropna()
        n_remuneracoes = len(remuneracoes)
        if not remuneracoes.empty:
            media_remuneracao = float(remuneracoes.mean())
    
    return {
        "total_registros": total_registros,
        "media_salario": float(salarios.mean()) if not salarios.empty else 0.0,
        "mediana_salario": float(salarios.median()) if not salarios.empty else 0.0,
        "registros_com_salario": n_salarios,
        "registros_com_remuneracao": n_remuneracoes,
    }


def sample_table(df: pd.DataFrame, limit: int = 15) -> List[Dict[str, Any]]:
    """Return a sample of job postings formatted for the frontend table."""
    # Mapeamento de colunas unificadas para display
    column_mapping = {
        "role": "cargo",
        "seniority": "nivel",
        "region": "estado",
        "work_model": "modalidade_trabalho",
        "salary": "salario_base",
        "total_monthly_compensation": "remuneracao_total_mensal",
    }
    
    # Colunas a selecionar (no formato unificado)
    unified_cols = ["role", "seniority", "region", "work_model", "salary", "total_monthly_compensation"]
    subset_cols = [col for col in unified_cols if col in df.columns]
    
    sample = df[subset_cols].dropna(subset=["salary"]).head(limit).copy()
    
    # Mapear seniority e work_model para labels de display
    if "seniority" in sample.columns:
        sample["seniority"] = sample["seniority"].map(
            lambda x: SENIORITY_DISPLAY_LABELS.get(x, x)
        )
    
    if "work_model" in sample.columns:
        sample["work_model"] = sample["work_model"].map(
            lambda x: WORK_MODEL_DISPLAY_LABELS.get(x, x) if pd.notna(x) else "Não informado"
        )
    
    # Renomear para formato esperado pelo frontend
    sample = sample.rename(columns=column_mapping)
    
    records: List[Dict[str, Any]] = []
    for row in sample.to_dict(orient="records"):
        row["salario_base"] = float(row.get("salario_base", 0)) if row.get("salario_base") is not None else None
        if "remuneracao_total_mensal" in row:
            value = row.get("remuneracao_total_mensal")
            row["remuneracao_total_mensal"] = float(value) if value is not None else None
        records.append(row)
    return records


def load_dashboard_context(df: pd.DataFrame, benefit_list: List[str]) -> Dict[str, Any]:
    """Load the full dashboard context.

    Args:
        df: Unified DataFrame with job data
        benefit_list: List of identified benefits for analysis

    Returns:
        Dictionary containing visualizations, summary and a sample of jobs
    """
    visualizations = [
        #{
        #    "id": "chart-salary-histogram",
        #    "title": "Distribuição Geral de Salários",
        #    "description": "Entenda como os salários base estão distribuídos na amostra coletada.",
        #    "figure_light": build_salary_histogram(df, template='plotly_white'),
        #    "figure_dark": build_salary_histogram(df, template='plotly_dark'),
        #},
        {
            "id": "chart-salary-level",
            "title": "Salários por Nível",
            "description": "Compare a distribuição salarial por nível de senioridade.",
            "figure_light": build_salary_by_level(df, template='plotly_white'),
            "figure_dark": build_salary_by_level(df, template='plotly_dark'),
        },
        {
            "id": "chart-boxplot-level",
            "title": "Boxplot por Nível",
            "description": "Visualize mediana, quartis e outliers por nível de carreira.",
            "figure_light": build_boxplot_by_level(df, template='plotly_white'),
            "figure_dark": build_boxplot_by_level(df, template='plotly_dark'),
        },
        #{
        #    "id": "chart-violin-level",
        #    "title": "Densidade Salarial por Nível",
        #    "description": "Distribuição completa dos salários base por nível, com outliers destacados.",
        #    "figure_light": build_violin_by_level(df, template='plotly_white'),
        #    "figure_dark": build_violin_by_level(df, template='plotly_dark'),
        #},
        {
            "id": "chart-states",
            "title": "Estados com Mais Vagas",
            "description": "Os 10 estados que concentram mais oportunidades na base.",
            "figure_light": build_states_bar(df, template='plotly_white'),
            "figure_dark": build_states_bar(df, template='plotly_dark'),
        },
        {
            "id": "chart-heatmap",
            "title": "Heatmap Estado x Nível",
            "description": "Salário médio por estado e nível de senioridade.",
            "figure_light": build_heatmap_state_level(df, template='plotly_white'),
            "figure_dark": build_heatmap_state_level(df, template='plotly_dark'),
        },
        #{
        #    "id": "chart-salary-comparison",
        #    "title": "Salário Base vs Remuneração Total",
        #    "description": "Entenda o quanto a remuneração total se distancia do salário base.",
        #    "figure_light": build_salary_comparison(df, template='plotly_white'),
        #    "figure_dark": build_salary_comparison(df, template='plotly_dark'),
        #},
        {
            "id": "chart-work-modality",
            "title": "Modalidade de Trabalho",
            "description": "Distribuição de modalidades como presencial, híbrido ou remoto.",
            "figure_light": build_work_modality(df, template='plotly_white'),
            "figure_dark": build_work_modality(df, template='plotly_dark'),
        },
        {
            "id": "chart-career",
            "title": "Salário Médio por Cargo",
            "description": "Top 6 cargos mais frequentes e seus salários médios.",
            "figure_light": build_career_analysis(df, template='plotly_white'),
            "figure_dark": build_career_analysis(df, template='plotly_dark'),
        },
        {
            "id": "chart-benefits",
            "title": "Benefícios Oferecidos",
            "description": "Os benefícios mais recorrentes nas vagas analisadas.",
            "figure_light": build_benefits_analysis(df, benefit_list, template='plotly_white'),
            "figure_dark": build_benefits_analysis(df, benefit_list, template='plotly_dark'),
        },
        {
            "id": "chart-map",
            "title": "Mapa Interativo de Vagas",
            "description": "Explore a distribuição de vagas e salários médios por estado.",
            "figure_light": build_interactive_map(df, template='plotly_white'),
            "figure_dark": build_interactive_map(df, template='plotly_dark'),
        },
    ]

    context = {
        "visualizations": visualizations,
        "summary": build_summary(df),
        "sample_jobs": sample_table(df),
    }
    return context


def main():
    """Função principal para gerar o contexto do dashboard."""
    # Executar pipeline de merge (usa caminhos baseados no project root)
    from data_treatment.merge_data_sources import run_merge_pipeline

    # Executar pipeline de merge
    df, benefits = run_merge_pipeline(
        raw_data_path=str(DATA_DIR / "raw_data.csv"),
        linkedin_data_path=str(DATA_DIR / "linkedin_data_raw.json"),
        output_path=str(DATA_DIR / "vagas_unificadas.csv"),
    )

    # Aplicar transformações adicionais
    df, benefit_list = transform_data(df)

    # Gerar contexto do dashboard
    context = load_dashboard_context(df, benefit_list=benefit_list)

    output_path = STATIC_DIR / "images" / "dashboard_context.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(context, f)
    
    print(f"Contexto do dashboard salvo em: {output_path}")


if __name__ == "__main__":
    main()

