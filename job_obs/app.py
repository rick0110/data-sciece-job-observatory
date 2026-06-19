import os 
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for, abort
import json
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np
import pandas as pd
import csv
import yaml
import frontmatter 
import markdown

# ========================
# Mapeamentos de display para colunas unificadas
# ========================
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

# ========================
# Load data and model for search
# Paths resolve the project root so modules can be run with `python -m` from repo root
# ========================
from pathlib import Path

def get_project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / 'data').exists():
            return parent
    return Path.cwd()

PROJECT_ROOT = get_project_root()
DATA_DIR = PROJECT_ROOT / 'data'
STATIC_DIR = PROJECT_ROOT / 'job_obs' / 'static'

# Carregar dados unificados (vagas_unificadas.csv gerado pelo merge_data_sources.py)
df = pd.read_csv(DATA_DIR / 'vagas_unificadas.csv')
embeddings = np.load(DATA_DIR / 'embeddings.npy')

model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

global context
context = json.load(open(STATIC_DIR / 'images' / 'dashboard_context.json'))
app = Flask(__name__)

# =========================
# Dashboard page and API for search
# =========================
@app.template_filter('currency')
def currency_filter(value: float | None) -> str:
    """Format a numeric value as Brazilian Real currency."""
    if value is None:
        return "—"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@app.route('/')
def index() -> str:
    """Render the landing page."""
    return render_template('index.html')


@app.route('/dashboard')
def dashboard() -> str:
    """Render the dashboard using the precomputed context."""
    return render_template('dashboard.html', **context)


@app.route('/api/search')
def api_search():
    """Vector search API using embeddings."""
    q = (request.args.get('q') or '').strip()
    try:
        k = int(request.args.get('k', 20))
    except ValueError:
        k = 20
    k = max(1, min(k, 100))

    if not q:
        return jsonify({"results": []})

    try:
        query_emb = model.encode([q])
        scores = cosine_similarity(query_emb, embeddings)[0]
        indices = np.argsort(scores)[::-1][:k]
        subset = df.iloc[indices].copy()
        
        # Colunas unificadas
        unified_columns = ['role', 'seniority', 'region', 'work_model', 'salary', 'total_monthly_compensation']
        cols = [c for c in unified_columns if c in subset.columns]
        
        records = []
        for i, row in subset[cols].iterrows():
            # Mapear seniority e work_model para labels de display
            seniority_display = SENIORITY_DISPLAY_LABELS.get(row.get('seniority'), row.get('seniority'))
            work_model_display = WORK_MODEL_DISPLAY_LABELS.get(row.get('work_model'), row.get('work_model'))
            
            rec = {
                'cargo': row.get('role'),
                'nivel': seniority_display,
                'estado': row.get('region'),
                'modalidade_trabalho': work_model_display,
                'salario_base': float(row['salary']) if pd.notna(row.get('salary')) else None,
                'remuneracao_total_mensal': float(row['total_monthly_compensation']) if 'total_monthly_compensation' in subset.columns and pd.notna(row.get('total_monthly_compensation')) else None,
            }
            records.append(rec)
        return jsonify({"results": records})
    except Exception as e:
        return jsonify({"error": str(e), "results": []}), 500
    
# ==============================
# New job posting page
# ==============================
@app.route('/vaga/nova', methods=['GET', 'POST'])
def nova_vaga():
    """Page for publishing a new job posting."""
    if request.method == 'POST':
        empresa = request.form.get('empresa')
        cargo = request.form.get('cargo')
        nivel = request.form.get('nivel')
        estado = request.form.get('estado')
        modalidade = request.form.get('modalidade')
        salario = request.form.get('salario')
        descricao = request.form.get('descricao') or ""
        
        try:
            salario_float = float(salario) if salario else None
        except ValueError:
            salario_float = None

        nova_linha = {
            'company': empresa,
            'role': cargo,
            'seniority': nivel,
            'region': estado,
            'work_model': modalidade,
            'salary': salario_float,
            'raw_html_description': descricao,
            'source': 'manual',
        }
        
        (DATA_DIR / 'vagas_added_BY_users.json').parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_DIR / 'vagas_added_BY_users.json', 'a', encoding='utf-8') as f:
            f.write(json.dumps(nova_linha, ensure_ascii=False) + ',' + '\n')
        
        

        return render_template('success-new_vag.html', mensagem="Vaga publicada e indexada com sucesso!")

    return render_template('new_vag.html')

# ============================
# Data analysis detailed page
# ============================
@app.route('/analisys_secondary_files/<path:filename>')
def analisys_assets(filename: str):
    """Serve secondary assets for analysis files."""
    base_assets = os.path.abspath('./analisys_secondary_files')
    full_path = os.path.abspath(os.path.join(base_assets, filename))
    if not full_path.startswith(base_assets) or not os.path.isfile(full_path):
        abort(404)
    rel = os.path.relpath(full_path, base_assets)
    resp = send_from_directory(base_assets, rel, conditional=False)
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/analisys_html', methods=['GET', 'POST']) 
def analisys_detailed() -> str:
    """Render the gallery of analysis files."""
    # =============================
    # =============================
    #   FILTRAGEM DE POSTS POSTERIORMENTE
    # =============================
    # =============================
    base_dir = './analisys_html'
    dict_analysis = {}
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            metadata_str = ""
            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if first_line != '---':
                    continue  
                for linha in f:
                    if linha.strip() == '---':
                        break
                    metadata_str += linha
                if metadata_str:
                    metadata = yaml.safe_load(metadata_str)
                    
            metadata['file_path'] = os.path.relpath(os.path.join(root, file), start=base_dir)
            metadata['file_name'] = file

            if metadata.get('image_capa', None):
                slug = os.path.splitext(os.path.basename(file))[0]
                img_name = os.path.basename(str(metadata['image_capa']).lstrip('/'))
                img_rel = f"{slug}/images/{img_name}"
                metadata['image_capa_path'] = url_for(f'analisys_assets', filename=img_rel)
            dict_analysis[file] = metadata
    
    return render_template('analisys-detailed.html', dict_analysis=dict_analysis)

@app.route('/analisys_html/<path:filename>')
def serve_analysis_file(filename: str) -> str:
    """Serve a specific analysis file rendered from Markdown."""
    base_dir = './analisys_html'
    full_path = os.path.join(base_dir, filename)
    post = frontmatter.load(full_path)
    metadata = post.metadata
    content_md = post.content
    html_output = markdown.markdown(content_md, extensions=['fenced_code', 'tables'])
    return render_template('analisys-default.html', metadata=metadata, content=html_output)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)