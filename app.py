from flask import Flask, render_template, request, send_file, redirect, url_for
import requests
from bs4 import BeautifulSoup
import time
from fpdf import FPDF
import io
import os

app = Flask(__name__)
current_report = {}

# --- CONFIGURAÇÃO DE PAGAMENTO (OPCIONAL PARA TESTE) ---
# Para usar real, instale: pip install mercadopago
# import mercadopago
# sdk = mercadopago.SDK("SEU_ACCESS_TOKEN_AQUI")

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
        if not soup.find('h1'):
            issues.append("Falta uma tag H1 (Título principal).")
            score -= 20
        img_no_alt = len([img for img in soup.find_all('img') if not img.get('alt')])
        if img_no_alt > 0:
            issues.append(f"Existem {img_no_alt} imagens sem descrição (alt tag).")
            score -= 15
        if load_time > 2:
            issues.append(f"Site lento: {load_time}s. O ideal é menos de 2s.")
            score -= 25

        return {
            "url": url, "score": max(score, 0), "load_time": load_time,
            "issues": issues, "status": "Sucesso"
        }
    except:
        return {"status": "Erro"}

@app.route('/', methods=['GET', 'POST'])
def index():
    global current_report
    report = None
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            report = analyze_seo(url)
            current_report = report
    return render_template('index.html', report=report)

@app.route('/comprar')
def comprar():
    # Aqui você integraria o Mercado Pago. 
    # Por enquanto, vamos simular o redirecionamento para o checkout.
    return redirect(url_for('checkout'))

@app.route('/checkout')
def checkout():
    return render_template('checkout.html', report=current_report)

@app.route('/download_pdf')
def download_pdf():
    if not current_report: return redirect(url_for('index'))
    
    pdf = FPDF()
    pdf.add_page()
    
    # --- NOVO LAYOUT PROFISSIONAL ---
    # Cabeçalho Colorido
    pdf.set_fill_color(102, 126, 234) # Roxo do seu site
    pdf.rect(0, 0, 210, 40, 'F')
    
    pdf.set_font("Helvetica", 'B', 24)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 30, "RELATÓRIO DE AUDITORIA SEO", ln=True, align='C')
    
    pdf.ln(20)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(190, 10, f"Análise do Site: {current_report['url']}", ln=True)
    
    # Caixa de Pontuação
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(190, 15, f"PONTUAÇÃO GERAL: {current_report['score']}/100", ln=True, align='C', fill=True)
    
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(190, 10, "PROBLEMAS CRÍTICOS ENCONTRADOS:", ln=True)
    
    pdf.set_font("Helvetica", size=11)
    for issue in current_report['issues']:
        pdf.set_text_color(200, 0, 0) # Vermelho para erros
        pdf.multi_cell(180, 8, txt=f"X {issue}")
        pdf.ln(2)
        
    pdf.ln(20)
    pdf.set_text_color(100, 100, 100)
    pdf.set_font("Helvetica", 'I', 10)
    pdf.multi_cell(180, 7, "Este documento prova que seu site precisa de ajustes técnicos para aparecer no Google. Entre em contato para uma consultoria completa.")

    output = io.BytesIO()
    pdf_content = pdf.output()
    output.write(pdf_content)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="Auditoria_SEO_Premium.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
