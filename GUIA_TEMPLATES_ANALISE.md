# Guia para Atualizar app.py - Templates de Análise

## 📋 Templates Criados

### 1. `analisys-default.html`
Template que **estende base.html** e renderiza análises dentro do layout do site.

**Quando usar:**
- Análises em Markdown convertidas para HTML
- Conteúdo HTML simples sem estrutura completa
- Quer manter navbar, footer e estilos do site

**Variáveis necessárias:**
- `content`: HTML do conteúdo da análise (obrigatório)
- `metadata`: Dicionário com metadados (opcional)
  - `titulo`: Título da análise
  - `autor`: Nome do autor
  - `data`: Data da análise
  - `resumo`: Resumo/descrição
  - `tags`: Lista de tags (opcional)

### 2. `analysis-standalone.html`
Template **mínimo** que só adiciona navbar, sem estender base.html.

**Quando usar:**
- Análises HTML completas (já têm `<html>`, `<head>`, etc)
- Análises com Bootstrap próprio e scripts
- Análises com gráficos Plotly já configurados
- Quer apenas adicionar navegação básica

**Variáveis necessárias:**
- `content`: HTML completo da análise (obrigatório)
- `metadata`: Dicionário com metadados (opcional, apenas para `<title>`)

---

## 🔧 Como Atualizar `app.py`

### Opção 1: Usar `analisys-default.html` (recomendado para Markdown)

```python
@app.route('/analisys/<path:filename>')
def serve_analysis_file(filename):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), './../analisys'))
    full_path = os.path.normpath(os.path.join(base_dir, filename))
    
    # Proteção contra path traversal
    try:
        if os.path.commonpath([base_dir, full_path]) != base_dir:
            return "Acesso negado", 403
    except Exception:
        return "Acesso negado", 403
    
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        return "Arquivo não encontrado", 404
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse frontmatter manual
        metadata = {}
        content_body = content
        
        if content.startswith('---\n') or content.startswith('---\r\n'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                    content_body = parts[2]
                except:
                    pass
        
        # Se é HTML completo (tem <html>), use standalone
        if '<html' in content_body.lower() or '<body' in content_body.lower():
            # Remover apenas o frontmatter, manter todo o HTML
            return render_template('analysis-standalone.html', 
                                 content=content_body, 
                                 metadata=metadata)
        else:
            # Para Markdown ou HTML parcial
            html_output = markdown.markdown(content_body, extensions=['fenced_code', 'tables'])
            return render_template('analisys-default.html', 
                                 content=html_output, 
                                 metadata=metadata)
            
    except Exception as e:
        return f"Erro ao carregar arquivo: {str(e)}", 500
```

### Opção 2: Sempre usar `analisys-default.html` (mais simples)

```python
@app.route('/analisys/<path:filename>')
def serve_analysis_file(filename):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), './../analisys'))
    full_path = os.path.normpath(os.path.join(base_dir, filename))
    
    # Security
    try:
        if os.path.commonpath([base_dir, full_path]) != base_dir:
            return "Acesso negado", 403
    except Exception:
        return "Acesso negado", 403
    
    if not os.path.exists(full_path):
        return "Arquivo não encontrado", 404
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse frontmatter
        metadata = {}
        content_body = content
        
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                    content_body = parts[2]
                except:
                    pass
        
        # Converter Markdown para HTML se necessário
        if filename.endswith(('.md', '.markdown')):
            html_output = markdown.markdown(content_body, extensions=['fenced_code', 'tables'])
        else:
            # Para .html, usar diretamente
            html_output = content_body
        
        return render_template('analisys-default.html', 
                             content=html_output, 
                             metadata=metadata)
            
    except Exception as e:
        return f"Erro: {str(e)}", 500
```

### Opção 3: Retornar HTML puro (sem template)

```python
@app.route('/analisys/<path:filename>')
def serve_analysis_file(filename):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), './../analisys'))
    full_path = os.path.normpath(os.path.join(base_dir, filename))
    
    # Security
    try:
        if os.path.commonpath([base_dir, full_path]) != base_dir:
            return "Acesso negado", 403
    except Exception:
        return "Acesso negado", 403
    
    if not os.path.exists(full_path):
        return "Arquivo não encontrado", 404
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Se é HTML completo, retornar direto
        if filename.endswith('.html'):
            # Remover frontmatter se existir
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    return parts[2]
            return content
        
        # Para Markdown, converter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1]) or {}
                content = parts[2]
        
        html_output = markdown.markdown(content, extensions=['fenced_code', 'tables'])
        return render_template('analisys-default.html', 
                             content=html_output, 
                             metadata={})
            
    except Exception as e:
        return f"Erro: {str(e)}", 500
```

---

## 📝 Exemplo de Frontmatter

```yaml
---
titulo: Análise de Salários em São Paulo
autor: Richard Viana
data: 23/11/2025
resumo: Estudo completo sobre a evolução salarial no mercado de tecnologia
tags:
  - salários
  - tecnologia
  - são paulo
---
```

---

## 🎯 Recomendação

**Use a Opção 1** (detectar tipo de conteúdo):
- ✅ Suporta arquivos HTML completos com gráficos
- ✅ Suporta Markdown simples
- ✅ Adiciona navbar automaticamente
- ✅ Mantém compatibilidade com análises existentes

**Para arquivos HTML completos** (como `analise_teste.html`):
- Terão navbar adicionada automaticamente via `analysis-standalone.html`
- Mantêm todos os estilos, scripts e gráficos originais

**Para Markdown ou HTML simples**:
- Renderizado dentro do layout do site via `analisys-default.html`
- Herda estilos e comportamento do `base.html`

---

## ✅ Checklist de Implementação

1. [ ] Verificar se `yaml` está importado no `app.py`
2. [ ] Verificar se `markdown` está importado no `app.py`
3. [ ] Adicionar a função `serve_analysis_file` com uma das opções acima
4. [ ] Testar com arquivo HTML completo (ex: `analise_teste.html`)
5. [ ] Testar com arquivo Markdown simples
6. [ ] Verificar se frontmatter é parseado corretamente
7. [ ] Testar proteção contra path traversal
8. [ ] Verificar responsividade em mobile

---

## 🐛 Troubleshooting

**Problema**: Gráficos Plotly não aparecem
- **Solução**: Use `analysis-standalone.html` para HTML completo

**Problema**: Estilos do site sobrescrevem a análise
- **Solução**: Use `analysis-standalone.html` ou adicione `!important` nos estilos da análise

**Problema**: Metadata não aparece
- **Solução**: Verifique formato do frontmatter YAML (precisa ter `---` no início e fim)

**Problema**: Erro 403 ao acessar
- **Solução**: Verifique se o arquivo está dentro da pasta `analisys/`
