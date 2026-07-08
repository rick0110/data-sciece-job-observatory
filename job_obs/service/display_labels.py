"""Shared display-label mappings for the dashboard and search API.

Centralizes the canonical-value -> human-readable Portuguese label
mappings that used to be duplicated between `job_obs/app.py` and
`job_obs/service/dashboard_data.py`.
"""

from __future__ import annotations

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

WORK_MODEL_DISPLAY_LABELS = {
    "remote": "Remoto",
    "hybrid": "Híbrido",
    "on-site": "Presencial",
    "not_specified": "Não informado",
}

# Covers the role categories that actually occur in a data/tech job
# observatory. Any canonical role key not listed here (e.g. if a future
# LinkedIn scrape brings in less common categories from `ROLE_REGEX`) falls
# back to a humanized version of the key itself via `role_display_label`.
ROLE_DISPLAY_LABELS = {
    "data_scientist": "Cientista de Dados",
    "machine_learning_engineer": "Engenheiro de Machine Learning",
    "ai_engineer": "Engenheiro de IA",
    "ai_general": "IA (geral)",
    "data_engineer": "Engenheiro de Dados",
    "analytics_engineer": "Engenheiro de Analytics",
    "data_analyst": "Analista de Dados",
    "cloud_engineer": "Engenheiro Cloud",
    "system_engineer": "Engenheiro de Sistemas",
    "devops": "DevOps / SRE",
    "qa": "Qualidade / Testes",
    "architect": "Arquiteto de Software",
    "software_engineer": "Engenheiro de Software",
    "backend_engineer": "Engenheiro Backend",
    "frontend_engineer": "Engenheiro Frontend",
    "fullstack_engineer": "Engenheiro Fullstack",
    "mobile_engineer": "Engenheiro Mobile",
    "developer": "Desenvolvedor(a)",
    "product_manager": "Gerente de Produto",
    "project_manager": "Gerente de Projetos",
    "engineering_manager": "Gerente de Engenharia",
    "research": "Pesquisador(a)",
    "consultant": "Consultor(a)",
    "specialist": "Especialista",
    "coordinator": "Coordenador(a)",
}


def role_display_label(role: str | None) -> str:
    """Return a human-readable label for a canonical role key.

    Falls back to a humanized version of the key (underscores -> spaces,
    title case) for roles not explicitly mapped above, so the chart never
    shows a raw, unmapped snake_case string.
    """
    if not role or role in ("not_specified", "nan"):
        return "Não informado"
    if role in ROLE_DISPLAY_LABELS:
        return ROLE_DISPLAY_LABELS[role]
    return role.replace("_", " ").strip().capitalize()
