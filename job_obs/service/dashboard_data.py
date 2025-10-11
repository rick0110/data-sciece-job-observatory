from __future__ import annotations
import pandas as pd
import numpy as np
import requests
import json
import unicodedata
import os
from pathlib import Path
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import requests

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
    df = pd.read_csv(path)
    return df

def change_cargo(x):
    """Normalize job titles to English equivalents"""
    cargo_mapping = {
        'cientista de dados': 'Data Scientist',
        'engenheiro de dados': 'Data Engineer',
        'analista de dados': 'Data Analyst',
        'analista de dados pleno': 'Data Analyst',
        'analista de dados sênior': 'Data Analyst',
        'analista de dados pleno e bi': 'Data Analyst',
        'analista de dados e analytics': 'Data Analyst',
        'analista de dados sr.': 'Data Analyst',
        'analista de dados operacionais': 'Data Analyst',
        'analista de dados industriais': 'Data Analyst',
        'analista de dados sr': 'Data Analyst',
        'engenheiro de machine learning': 'Machine Learning Engineer',
        'engenheiro de software': 'Software Engineer',
        'engenheiro de dados 2': 'Data Engineer',
        'engenheiro de dados ii': 'Data Engineer',
        'engenheiro de dados sênior': 'Data Engineer',
        'cientista de dados lider': 'Data Scientist',
        'cientista de dados sênior': 'Data Scientist',
        'analista cientista de dados': 'Data Scientist',
        'engenheiro de dados júnior': 'Data Engineer',
        'engenheiro de dados pleno': 'Data Engineer',
        'data scientist 2': 'Data Scientist',
        'data scientist i': 'Data Scientist',
        'data scientist jr': 'Data Scientist',
        'engenheiro de dados specialist': 'Data Engineer',
        'data analist finance': 'Data Analyst',
        'analista de dados e sistemas pl': 'Data Analyst and pl Systems',
        'analista de dados industriais 2': 'Data Analyst and Industrial',
        'analista de dados imobiliários i': 'Data Analyst',
        'analista de dados e produtos': 'Analyst and Products',
        'analista de dados e bi': 'Data Analyst',
        'analista de dados senior': 'Data Analyst',
        'analista de dados iii': 'Data Analyst',
        'associate data analyst': 'Data Analyst',
        'data analyst finance': 'Data Analyst'
    }
    return cargo_mapping.get(x.lower(), x)

def process_benefits(df):
    """Extract and create binary columns for benefits"""
    beneficios = df['beneficios'].dropna().unique()
    list_beneficios = []
    for ben in beneficios:
        list_beneficios.extend([b.strip() for b in ben.split('|')])
    list_beneficios = sorted(set(list_beneficios))

    for ben in list_beneficios:
        df[ben] = df['beneficios'].apply(
            lambda x: 'sim' if pd.notna(x) and ben in [b.strip() for b in x.split('|')] else 'nao'
        )
    return df, list_beneficios

def normalizar(txt):
    if txt is None:
        return None
    txt = str(txt).strip()
    txt = ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')
    return txt.lower()

def extract_state(df):
    """Extract state information from location column"""
    ESTADO_NOME_P_SIGLA = {
        'acre': 'AC', 'alagoas': 'AL', 'amapa': 'AP', 'amazonas': 'AM', 'bahia': 'BA', 'ceara': 'CE',
        'distrito federal': 'DF', 'espirito santo': 'ES', 'goias': 'GO', 'maranhao': 'MA', 'mato grosso': 'MT',
        'mato grosso do sul': 'MS', 'minas gerais': 'MG', 'para': 'PA', 'paraiba': 'PB', 'parana': 'PR',
        'pernambuco': 'PE', 'piaui': 'PI', 'rio de janeiro': 'RJ', 'rio grande do norte': 'RN',
        'rio grande do sul': 'RS', 'rondonia': 'RO', 'roraima': 'RR', 'santa catarina': 'SC', 'sao paulo': 'SP',
        'sergipe': 'SE', 'tocantins': 'TO'
    }
    
    def extrair_estado(localizacao):
        if pd.isna(localizacao):
            return None
        loc_norm = normalizar(localizacao)
        partes = [p.strip() for p in loc_norm.split(',') if p.strip()]
        candidato = None
        if len(partes) >= 2:
            candidato = partes[-1]
        elif len(partes) == 1:
            candidato = partes[0]
        if candidato in ESTADO_NOME_P_SIGLA:
            return ESTADO_NOME_P_SIGLA[candidato]
        for nome_estado, sigla in ESTADO_NOME_P_SIGLA.items():
            if nome_estado in loc_norm.split(',') or nome_estado == loc_norm:
                return sigla
            if len(nome_estado) > 6 and nome_estado in loc_norm:
                return sigla
        return None
    if 'estado' not in df.columns:
        df['estado'] = df['localizacao'].apply(extrair_estado)
    
    sem_estado = df['estado'].isna().sum()
    print(f"Records without identified state: {sem_estado}")
    return df

def transform_data(df):
    """Apply all data transformations"""
    df['cargo'] = df['cargo'].apply(change_cargo)
    df, list_beneficios = process_benefits(df)
    df = extract_state(df)
    return df, list_beneficios

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

def build_salary_histogram(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    fig = px.histogram(
        df.dropna(subset=["salario_base"]),
        x="salario_base",
        nbins=30,
        color_discrete_sequence=["#1f77b4"],
    )
    fig.update_layout(
        title="Distribuição Geral de Salários Base",
        xaxis_title="Salário Base (R$)",
        yaxis_title="Quantidade de Vagas",
        bargap=0.05,
        template="plotly_white",
    )
    fig.update_traces(hovertemplate="Salário: R$ %{x:,.0f}<br>Vagas: %{y}<extra></extra>")
    return _figure_to_dict(fig)

def build_salary_by_level(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    df_level = df.dropna(subset=["salario_base", "nivel"])
    fig = px.histogram(
        df_level,
        x="salario_base",
        color="nivel",
        nbins=25,
        barmode="overlay",
        opacity=0.65,
        labels={"nivel": "Nível"},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(
        title="Distribuição de Salários por Nível de Senioridade",
        xaxis_title="Salário Base (R$)",
        yaxis_title="Quantidade de Vagas",
        template=template,
        legend_title="Nível",
    )
    fig.update_traces(hovertemplate="Nível: %{legendgroup}<br>Salário: R$ %{x:,.0f}<br>Vagas: %{y}<extra></extra>")
    return _figure_to_dict(fig)

def build_boxplot_by_level(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    df_box = df.dropna(subset=["salario_base", "nivel"])
    fig = px.box(
        df_box,
        x="nivel",
        y="salario_base",
        color="nivel",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_layout(
        title="Boxplot de Salário Base por Nível",
        xaxis_title="Nível",
        yaxis_title="Salário Base (R$)",
        template=template,
        showlegend=False,
    )
    return _figure_to_dict(fig)

def build_violin_by_level(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    df_violin = df.dropna(subset=["salario_base", "nivel"])
    fig = px.violin(
        df_violin,
        x="nivel",
        y="salario_base",
        color="nivel",
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
    )
    return _figure_to_dict(fig)

def build_states_bar(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    top_states = df["estado"].value_counts().head(10).sort_values(ascending=True)
    states_df = top_states.reset_index()
    states_df.columns = ["estado", "quantidade"]
    fig = px.bar(
        states_df,
        x="quantidade",
        y="estado",
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
    )
    fig.update_traces(hovertemplate="Estado: %{y}<br>Vagas: %{x}<extra></extra>")
    return _figure_to_dict(fig)

def build_heatmap_state_level(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    pivot = (
        df.dropna(subset=["estado", "nivel", "salario_base"])
        .groupby(["estado", "nivel"])["salario_base"]
        .mean()
        .unstack(fill_value=0)
    )
    relevant_states = df["estado"].value_counts()
    pivot = pivot.loc[relevant_states[relevant_states >= 5].index]

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="YlOrRd",
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
        template="plotly_white",
    )
    return _figure_to_dict(fig)

def build_salary_comparison(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    if "remuneracao_total_mensal" not in df.columns:
        return _figure_to_dict(go.Figure())

    df_comp = df.dropna(subset=["salario_base", "remuneracao_total_mensal"])
    if df_comp.empty:
        return _figure_to_dict(go.Figure())

    q99_base = df_comp["salario_base"].quantile(0.99)
    q99_total = df_comp["remuneracao_total_mensal"].quantile(0.99)
    df_comp = df_comp[(df_comp["salario_base"] <= q99_base) & (df_comp["remuneracao_total_mensal"] <= q99_total)]

    fig = px.scatter(
        df_comp,
        x="salario_base",
        y="remuneracao_total_mensal",
        color="nivel",
        labels={"nivel": "Nível"},
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig.add_trace(
        go.Scatter(
            x=[0, df_comp["salario_base"].max()],
            y=[0, df_comp["salario_base"].max()],
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
    )
    fig.update_traces(hovertemplate="Salário Base: R$ %{x:,.0f}<br>Remuneração Total: R$ %{y:,.0f}<extra></extra>")
    return _figure_to_dict(fig)

def build_work_modality(df: pd.DataFrame, template='plotly_white') -> Dict[str, Any]:
    modalidades = df["modalidade_trabalho"].fillna("Não informado").value_counts()
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
    )
    return _figure_to_dict(fig)

def build_career_analysis(df: pd.DataFrame, template) -> Dict[str, Any]:
    top_roles = df["cargo"].value_counts().head(6).index
    subset = (
        df[df["cargo"].isin(top_roles)]
        .groupby("cargo")["salario_base"]
        .mean()
        .sort_values(ascending=True)
    )
    career_df = subset.reset_index()
    career_df.columns = ["cargo", "salario_medio"]
    fig = px.bar(
        career_df,
        x="salario_medio",
        y="cargo",
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
    )
    fig.update_traces(hovertemplate="Cargo: %{y}<br>Salário Médio: R$ %{x:,.0f}<extra></extra>")
    return _figure_to_dict(fig)

def _top_benefits(df: pd.DataFrame, benefit_list: List[str]) -> pd.Series:
    available = [b for b in benefit_list if b in df.columns]
    if not available:
        return pd.Series(dtype="int64")
    counts = df[available].eq("sim").sum()
    counts = counts.sort_values(ascending=False).head(15)
    return counts

def build_benefits_analysis(df: pd.DataFrame, benefit_list: List[str], template='plotly_white') -> Dict[str, Any]:
    benefits = _top_benefits(df, benefit_list)
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
    )
    fig.update_traces(
        hovertemplate="Benefício: %{y}<br>Vagas: %{x}<extra></extra>"
    )
    return _figure_to_dict(fig)

def build_interactive_map(df: pd.DataFrame, template = 'plotly_white') -> Dict[str, Any]:
    geojson = _get_brazil_geojson()
    grouped = df.groupby("estado", dropna=True).agg(
        num_vagas=("cargo", "count"),
        media_salario_base=("salario_base", "mean"),
        media_remuneracao_total=("remuneracao_total_mensal", "mean"),
        salario_min=("salario_base", "min"),
        salario_max=("salario_base", "max"),
    )
    grouped = grouped.reset_index()
    all_states = pd.DataFrame({"estado": list(BRAZIL_STATE_NAMES.keys())})
    merged = all_states.merge(grouped, on="estado", how="left")
    for column in ["num_vagas", "media_salario_base", "media_remuneracao_total", "salario_min", "salario_max"]:
        if column in merged.columns:
            merged[column] = merged[column].fillna(0)

    merged["estado_nome"] = merged["estado"].map(BRAZIL_STATE_NAMES)

    customdata = merged[["estado_nome", "num_vagas", "media_salario_base", "media_remuneracao_total", "salario_min", "salario_max"]].values

    fig = go.Figure()

    mask_pos = merged["num_vagas"] > 0
    if mask_pos.any():
        fig.add_trace(
            go.Choropleth(
                geojson=geojson,
                locations=merged.loc[mask_pos, "estado"],
                z=merged.loc[mask_pos, "num_vagas"],
                featureidkey="properties.sigla",
                colorscale="Blues",
                marker_line_color="white",
                marker_line_width=0.5,
                colorbar=dict(title="Número de vagas"),
                customdata=merged.loc[mask_pos, ["estado_nome", "num_vagas", "media_salario_base", "media_remuneracao_total", "salario_min", "salario_max"]].values,
                hovertemplate=(
                    "Estado: %{customdata[0]}<br>Vagas: %{customdata[1]}<br>Salário médio: R$ %{customdata[2]:,.0f}<br>Remuneração média: R$ %{customdata[3]:,.0f}<extra></extra>"
                ),
            )
        )
    mask_zero = merged["num_vagas"] == 0
    if mask_zero.any():
        fig.add_trace(
            go.Choropleth(
                geojson=geojson,
                locations=merged.loc[mask_zero, "estado"],
                z=[1] * merged.loc[mask_zero].shape[0],
                featureidkey="properties.sigla",
                colorscale=[[0, "#f0f0f0"], [1, "#f0f0f0"]],
                showscale=False,
                marker_line_color="white",
                marker_line_width=0.5,
                hovertemplate=(
                    "Estado: %{location}<br>Vagas: 0<extra></extra>"
                ),
            )
        )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        title="Distribuição de Vagas por Estado",
        template=template,
        margin=dict(l=0, r=0, t=40, b=0),
    )

    return _figure_to_dict(fig)

def build_summary(df: pd.DataFrame) -> Dict[str, Any]:
    salarios = df["salario_base"].dropna()
    total_comp = df["remuneracao_total_mensal"].dropna() if "remuneracao_total_mensal" in df.columns else pd.Series(dtype=float)
    return {
        "total_registros": int(df.shape[0]),
        "media_salario": float(salarios.mean()) if not salarios.empty else 0.0,
        "mediana_salario": float(salarios.median()) if not salarios.empty else 0.0,
        "media_remuneracao_total": float(total_comp.mean()) if not total_comp.empty else 0.0,
    }

def sample_table(df: pd.DataFrame, limit: int = 15) -> List[Dict[str, Any]]:
    subset_cols = [
        col
        for col in ["cargo", "nivel", "estado", "modalidade_trabalho", "salario_base", "remuneracao_total_mensal"]
        if col in df.columns
    ]
    sample = df[subset_cols].dropna(subset=["salario_base"]).head(limit)
    records: List[Dict[str, Any]] = []
    for row in sample.to_dict(orient="records"):
        row["salario_base"] = int(row.get("salario_base", 0)) if row.get("salario_base") is not None else None
        if "remuneracao_total_mensal" in row:
            value = row.get("remuneracao_total_mensal")
            row["remuneracao_total_mensal"] = int(value) if value is not None else None
        records.append(row)
    return records

def load_dashboard_context(df, benefit_list, template='plotly_white') -> Dict[str, Any]:
    visualizations = [
        {
            "id": "chart-salary-histogram",
            "title": "Distribuição Geral de Salários",
            "description": "Entenda como os salários base estão distribuídos na amostra coletada.",
            "figure": build_salary_histogram(df, template=template),
        },
        {
            "id": "chart-salary-level",
            "title": "Salários por Nível",
            "description": "Compare a distribuição salarial por nível de senioridade.",
            "figure": build_salary_by_level(df, template=template),
        },
        {
            "id": "chart-boxplot-level",
            "title": "Boxplot por Nível",
            "description": "Visualize mediana, quartis e outliers por nível de carreira.",
            "figure": build_boxplot_by_level(df, template=template),
        },
        {
            "id": "chart-violin-level",
            "title": "Densidade Salarial por Nível",
            "description": "Distribuição completa dos salários base por nível, com outliers destacados.",
            "figure": build_violin_by_level(df, template=template),
        },
        {
            "id": "chart-states",
            "title": "Estados com Mais Vagas",
            "description": "Os 10 estados que concentram mais oportunidades na base.",
            "figure": build_states_bar(df, template=template),
        },
        {
            "id": "chart-heatmap",
            "title": "Heatmap Estado x Nível",
            "description": "Salário médio por estado e nível de senioridade.",
            "figure": build_heatmap_state_level(df, template=template),
        },
        {
            "id": "chart-salary-comparison",
            "title": "Salário Base vs Remuneração Total",
            "description": "Entenda o quanto a remuneração total se distancia do salário base.",
            "figure": build_salary_comparison(df, template=template),
        },
        {
            "id": "chart-work-modality",
            "title": "Modalidade de Trabalho",
            "description": "Distribuição de modalidades como presencial, híbrido ou remoto.",
            "figure": build_work_modality(df, template=template),
        },
        {
            "id": "chart-career",
            "title": "Salário Médio por Cargo",
            "description": "Top 6 cargos mais frequentes e seus salários médios.",
            "figure": build_career_analysis(df, template=template),
        },
        {
            "id": "chart-benefits",
            "title": "Benefícios Oferecidos",
            "description": "Os benefícios mais recorrentes nas vagas analisadas.",
            "figure": build_benefits_analysis(df, benefit_list, template=template),
        },
        {
            "id": "chart-map",
            "title": "Mapa Interativo de Vagas",
            "description": "Explore a distribuição de vagas e salários médios por estado.",
            "figure": build_interactive_map(df, template=template),
        },
    ]

    context = {
        "visualizations": visualizations,
        "summary": build_summary(df),
        "sample_jobs": sample_table(df),
    }
    return context

def main(template='plotly_white'):
    df = pd.read_csv('./../../data/raw_data.csv', decimal=',', thousands='.')
    df, benefits = transform_data(df)
    context = load_dashboard_context(df, benefit_list=benefits, template=template)
    output_path = Path('./../static/images/dashboard_context.json')
    with open(output_path, 'w') as f:
        json.dump(context, f)

if __name__ == "__main__":
    main()

