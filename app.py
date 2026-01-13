from flask import Flask, render_template, request, send_file, redirect, url_for, session
import requests
from bs4 import BeautifulSoup
import time
from fpdf import FPDF
import io
import os
import mercadopago # Biblioteca oficial

app = Flask(__name__)

# --- CONFIGURAÇÃO OBRIGATÓRIA ---
# 1. Troque isso por uma chave secreta aleatória qualquer
app.secret_key = 'sua_chave_secreta_super_segura' 

# 2. COLOCAR SEU TOKEN DO MERCADO PAGO AQUI
# Pegue em: https://www.mercadopago.com.br/developers/panel
sdk = mercadopago.SDK("SEU_ACCESS_TOKEN_AQUI_COLE_DENTRO_DAS_ASPAS")

def analyze_seo(url):
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        headers = {'User-Agent': 'Mozilla/5.0'}
        start_time = time.time()
        response = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        load_time = round(time.time() - start_time, 2)
        
        issues = []
        score = 100
        
        # Regras de Pontuação
        if not soup.find('h1'):
            issues.append("Falta uma tag H1 (Título principal).")
            score -= 20
        img_no_alt = len([img for img in soup.find_all('img') if not img.get('alt')])
        if img_no_alt > 0:
            issues.append(f"Existem {img_no_alt} imagens sem descrição (alt tag).")
            score -= 15
        if len(soup.title.text) < 10 if soup.title else True:
            issues.append("Título da página muito curto ou inexistente.")
            score -= 15
        if load_time > 2:
            issues.append(f"Site lento: {load_time}s. O ideal é menos de 2s.")
            score -= 25

        return {
            "url": url, "score": max(score, 0), "load_time": load_time,
            "issues": issues, "status": "Sucesso"
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
            # Salvamos na sessão do usuário, não em variável global (mais seguro)
            session['report'] = report
    return render_template('index.html', report=report)

@app.route('/comprar')
def comprar():
    # Verifica se existe um relatório gerado
    if 'report' not in session:
        return redirect(url_for('index'))

    # Cria a preferência de pagamento no Mercado Pago
    preference_data = {
        "items": [
            {
                "title": f"Relatório SEO - {session['report']['url']}",
                "quantity": 1,
                "unit_price": 29.90,
                "currency_id": "BRL" # Moeda Real
            }
        ],
        "back_urls": {
            # Onde o usuário vai parar depois de pagar
            "success": url_for('pagamento_aprovado', _external=True),
            "failure": url_for('index', _external=True),
            "pending": url_for('index', _external=True)
        },
        "auto_return": "approved", # Retorna automático assim que o Pix compensar
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        pay_link = preference_response["response"]["init_point"]
        return redirect(pay_link)
    except Exception as e:
        return f"Erro ao conectar com Mercado Pago: {str(e)}", 500

@app.route('/pagamento_aprovado')
def pagamento_aprovado():
    # Página de sucesso que libera o download
    if 'report' not in session:
        return redirect(url_for('index'))
    return render_template('checkout.html', report=session['report'])

@app.route('/download_pdf')
def download_pdf():
    if 'report' not in session: 
        return redirect(url_for('index'))
    
    report = session['report']
    
    pdf = FPDF()
    pdf.add_page()
    
    # --- LAYOUT CORRIGIDO ---
    # Cabeçalho Roxo
    pdf.set_fill_color(102, 126, 234) 
    pdf.rect(0, 0, 210, 40, 'F')
    
    pdf.set_font("Helvetica", 'B', 24)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 30, "RELATORIO DE AUDITORIA SEO", ln=True, align='C') # Sem acento no PDF pra evitar erro
    
    pdf.ln(20)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(190, 10, f"Site Analisado: {report['url']}", ln=True)
    
    # Caixa de Pontuação
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(190, 15, f"PONTUACAO GERAL: {report['score']}/100", ln=True, align='C', fill=True)
    
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(190, 10, "PROBLEMAS CRITICOS ENCONTRADOS:", ln=True)
    
    pdf.set_font("Helvetica", size=11)
    pdf.set_text_color(200, 0, 0) # Texto Vermelho
    
    for issue in report['issues']:
        # Usamos [X] em vez de caracteres especiais para garantir compatibilidade
        pdf.multi_cell(180, 8, txt=f"[X] {issue}")
        pdf.ln(2)
        
    pdf.ln(20)
    pdf.set_text_color(100, 100, 100) # Cinza
    pdf.set_font("Helvetica", 'I', 10)
    pdf.multi_cell(180, 7, "Este documento e uma analise tecnica automatizada. Entre em contato para servicos de correcao.")

    output = io.BytesIO()
    pdf_content = pdf.output()
    output.write(pdf_content)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="Auditoria_SEO_Premium.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
