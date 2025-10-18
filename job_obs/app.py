from flask import Flask, render_template, request, jsonify
import json
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np
import pandas as pd

df = pd.read_csv('./../data/vagas_processadas.csv')
embeddings = np.load('./../data/embeddings.npy')

model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

global context
context = json.load(open('./static/images/dashboard_context.json'))
app = Flask(__name__)

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
            'salario_base', 'remuneracao_total_mensal'
        ]
        cols = [c for c in columns if c in subset.columns]
        records = []
        for i, row in subset[cols].iterrows():
            rec = {
                'cargo': row.get('cargo'),
                'nivel': row.get('nivel'),
                'estado': row.get('estado'),
                'modalidade_trabalho': row.get('modalidade_trabalho'),
                'salario_base': float(row['salario_base']) if pd.notna(row.get('salario_base')) else None,
                'remuneracao_total_mensal': float(row['remuneracao_total_mensal']) if 'remuneracao_total_mensal' in subset.columns and pd.notna(row.get('remuneracao_total_mensal')) else None,
            }
            records.append(rec)
        return jsonify({"results": records})
    except Exception as e:
        return jsonify({"error": str(e), "results": []}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)