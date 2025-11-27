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
# Load data and model for search
# ========================
df = pd.read_csv('./../data/vagas_processadas.csv')
embeddings = np.load('./../data/embeddings.npy')

model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

global context
context = json.load(open('./static/images/dashboard_context.json'))
app = Flask(__name__)

# =========================
# Dashboard page and API for search
# =========================
@app.template_filter('currency')
def currency_filter(value):
    if value is None:
        return "—"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', **context)


@app.route('/api/search')
def api_search():
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
        columns = [
            'cargo', 'nivel', 'estado', 'modalidade_trabalho',
            'salario_base'
        ]
        cols = [c for c in columns if c in subset.columns]
        records = []
        for i, row in subset[cols].iterrows():
            rec = {
                'cargo': row.get('cargo'),
                'nivel': row.get('nivel'),
                'estado': row.get('estado'),
                'modalidade_trabalho': row.get('modalidade_trabalho'),
                'salario_base': float(row['salario_base']) if pd.notna(row.get('salario_base')) else None
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
    if request.method == 'POST':
        cargo = request.form.get('cargo')
        nivel = request.form.get('nivel')
        estado = request.form.get('estado')
        modalidade = request.form.get('modalidade')
        salario = request.form.get('salario')
        beneficios = request.form.get('beneficios') or ""
        
        try:
            salario_float = float(salario) if salario else None
        except ValueError:
            salario_float = None

        nova_linha = {
            'cargo': cargo,
            'nivel': nivel,
            'estado': estado,
            'modalidade_trabalho': modalidade,
            'salario_base': salario_float,
            'beneficios': beneficios 
        }

        global df, embeddings
        
        nova_linha_df = pd.DataFrame([nova_linha])
        df = pd.concat([df, nova_linha_df], ignore_index=True)

        texto_para_embedding = f"{cargo} {beneficios}"
        novo_embedding = model.encode([texto_para_embedding])
        
        embeddings = np.vstack([embeddings, novo_embedding])

        nova_linha_df.to_csv('./../data/vagas_processadas.csv', mode='a', header=False, index=False)
        
        np.save('./../data/embeddings.npy', embeddings)

        return render_template('success-new_vag.html', mensagem="Vaga publicada e indexada com sucesso!")

    return render_template('new_vag.html')

# ============================
# Data analysis detailed page
# ============================
@app.route('/analisys_secondary_files/<path:filename>')
def analisys_assets(filename):
    base_assets = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'analisys_secondary_files'))
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
def analisys_detailed():
    # =============================
    # =============================
    #   FILTRAGEM DE POSTS POSTERIORMENTE
    # =============================
    # =============================
    base_dir = './../analisys_html'
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
def serve_analysis_file(filename):
    base_dir = './../analisys_html'
    full_path = os.path.join(base_dir, filename)
    post = frontmatter.load(full_path)
    metadata = post.metadata
    content_md = post.content
    html_output = markdown.markdown(content_md, extensions=['fenced_code', 'tables'])
    return render_template('analisys-default.html', metadata=metadata, content=html_output)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)