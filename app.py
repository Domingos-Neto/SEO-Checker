from flask import Flask, render_template, request, send_file, redirect, url_for, session
import requests
from bs4 import BeautifulSoup
import time
from fpdf import FPDF
import io
import os
import mercadopago
from collections import Counter
import re

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
app.secret_key = 'chave_secreta_super_segura_seo_pro' 

# ⚠️ ALTERA PARA A TUA PALAVRA-PASSE DE ADMIN
ADMIN_PASSWORD = "db2026"

# ⚠️ COLOQUE SEU TOKEN DO MERCADO PAGO AQUI ABAIXO ⚠️
sdk = mercadopago.SDK("APP_USR-430272113998230-011315-b4e2d93f3de6b823f9a8814e2d8576ed-57091170")

def analyze_seo(url):
    try:
        if not url.startswith('http'):
            url = 'https://' + url
            
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        start_time = time.time()
        response = requests.get(url, timeout=10, headers=headers)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        load_time = round(time.time() - start_time, 2)
        
        issues = []
        score = 100
        
        # Análise de SEO básica e avançada
        title = soup.title.string.strip() if soup.title else None
        if not title:
            issues.append("Falta a tag <title>.") [cite: 20]
            score -= 20
        
        h1_tags = soup.find_all('h1')
        if not h1_tags:
            issues.append("Falta uma tag H1 (Título principal).") [cite: 4, 15, 28]
            score -= 20

        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            issues.append("Falta a Meta Descrição.") [cite: 29]
            score -= 20
        
        images_no_alt = [img for img in soup.find_all('img') if not img.get('alt')]
        if images_no_alt:
            issues.append(f"Existem {len(images_no_alt)} imagens sem descrição (alt tag).") [cite: 5, 16, 30]
            score -= 15

        if load_time > 2.0:
            issues.append(f"Site lento ({load_time}s). O ideal é menos de 2s.") [cite: 6, 17, 32]
            score -= 15

        # Extração de palavras-chave
        words = re.findall(r'\w+', soup.get_text().lower())
        stopwords = ['de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não']
        filtered_words = [w for w in words if w not in stopwords and len(w) > 3]
        top_keywords = Counter(filtered_words).most_common(5) [cite: 25, 26]

        return {
            "url": url, "score": max(score, 0), "load_time": load_time,
            "issues": issues, "top_keywords": top_keywords, "word_count": len(words)
        }
    except Exception as e:
        return {"status": "Erro", "msg": str(e)}

@app.route('/', methods=['GET', 'POST'])
def index():
    report = None
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            report = analyze_seo(url)
            session['report'] = report
    return render_template('index.html', report=report)

# --- ROTA PARA DOWNLOAD GRÁTIS COM SENHA ---
@app.route('/liberar_admin', methods=['GET', 'POST'])
def liberar_admin():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['pago'] = True
            return redirect(url_for('download_pdf'))
        return "Senha Incorreta!", 403
    
    return '''
        <form method="post" style="text-align:center; margin-top:50px;">
            <h2>Área do Administrador</h2>
            <input type="password" name="password" placeholder="Digite a senha secreta">
            <button type="submit">Gerar PDF Grátis</button>
        </form>
    '''

@app.route('/comprar')
def comprar():
    if 'report' not in session:
        return redirect(url_for('index'))

    preference_data = {
        "items": [
            {
                "title": f"Relatório SEO Pro - {session['report']['url']}",
                "quantity": 1,
                "unit_price": 29.90,
                "currency_id": "BRL"
            }
        ],
        "back_urls": {
            "success": url_for('pagamento_aprovado', _external=True),
            "failure": url_for('index', _external=True),
            "pending": url_for('index', _external=True)
        },
        "auto_return": "approved",
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        if preference_response["status"] == 201:
            return redirect(preference_response["response"]["init_point"])
        else:
            return f"Erro no Mercado Pago: {preference_response}"
    except Exception as e:
        return f"Erro de conexão: {str(e)}"


@app.route('/pagamento_aprovado')
def pagamento_aprovado():
    if 'report' not in session:
        return redirect(url_for('index'))
    return render_template('checkout.html', report=session['report'])

@app.route('/download_pdf')
def download_pdf():
    if 'report' not in session: return redirect(url_for('index'))
    
    report = session['report']
    pdf = FPDF()
    pdf.add_page()
    
    # Design do PDF Profissional
    pdf.set_fill_color(102, 126, 234) 
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_font("Helvetica", 'B', 24)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 30, "RELATORIO SEO PROFISSIONAL", ln=True, align='C') [cite: 20]
    
    pdf.ln(20)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(190, 10, f"Analise do Site: {report['url']}", ln=True) [cite: 21]
    
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(190, 15, f"PONTUACAO GERAL: {report['score']}/100", ln=True, align='C', fill=True) [cite: 24]
    
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(190, 10, "PROBLEMAS DETECTADOS E SOLUCOES:", ln=True) [cite: 27, 33]
    
    pdf.set_font("Helvetica", size=11)
    for issue in report['issues']:
        pdf.multi_cell(180, 8, txt=f"[X] {issue}") [cite: 28, 29, 30, 32]
        
    pdf.ln(10)
    pdf.set_font("Helvetica", 'I', 10)
    pdf.multi_cell(180, 7, "Relatorio gerado automaticamente por SEO Checker Pro.") [cite: 49]

    output = io.BytesIO()
    pdf_content = pdf.output()
    output.write(pdf_content)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="Relatorio_SEO_Completo.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
