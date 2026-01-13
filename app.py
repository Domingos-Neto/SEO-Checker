from flask import Flask, render_template, request, send_file, redirect, url_for
import requests
from bs4 import BeautifulSoup
import time
from fpdf import FPDF
import io

app = Flask(__name__)

# Simulação de banco de dados simples para o relatório atual
current_report = {}

def analyze_seo(url):
    try:
        if not url.startswith('http'):
            url = 'https://' + url
            
        headers = {'User-Agent': 'Mozilla/5.0'}
        start_time = time.time()
        response = requests.get(url, timeout=10, headers=headers)
        end_time = time.time()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        load_time = round(end_time - start_time, 2)
        title = soup.title.string.strip() if soup.title else "Não encontrado"
        h1 = [h.text.strip() for h in soup.find_all('h1')]
        images = soup.find_all('img')
        images_without_alt = [img for img in images if not img.get('alt')]
        
        score = 100
        issues = []
        
        if len(title) < 10:
            score -= 20
            issues.append("O título da página é muito curto ou inexistente.")
        if not h1:
            score -= 20
            issues.append("Falta uma tag H1 (Título principal).")
        if images_without_alt:
            score -= 15
            issues.append(f"Existem {len(images_without_alt)} imagens sem descrição (alt tag).")
        if load_time > 2.0:
            score -= 20
            issues.append(f"Site lento: {load_time}s. O ideal é menos de 2s.")

        return {
            "url": url,
            "status": "Sucesso",
            "score": max(score, 0),
            "load_time": load_time,
            "title": title,
            "h1_count": len(h1),
            "images_count": len(images),
            "issues": issues
        }
    except Exception as e:
        return {"status": "Erro", "message": str(e)}

@app.route('/', methods=['GET', 'POST'])
def index():
    global current_report
    report = None
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            report = analyze_seo(url)
            current_report = report # Salva para o PDF
    return render_template('index.html', report=report)

@app.route('/checkout')
def checkout():
    # Aqui você redirecionaria para o link do Mercado Pago ou Stripe
    # Por agora, vamos simular que o pagamento foi feito e liberar o PDF
    return render_template('checkout.html', report=current_report)

@app.route('/download_pdf')
def download_pdf():
    if not current_report:
        return redirect(url_for('index'))

    # Criando o PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(30, 60, 114)
    pdf.cell(200, 10, txt="Relatório de Auditoria SEO Pro", ln=True, align='C')
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(200, 10, txt=f"Análise para: {current_report['url']}", ln=True)
    pdf.cell(200, 10, txt=f"Pontuação Geral: {current_report['score']}/100", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Problemas Detectados:", ln=True)
    
    pdf.set_font("Arial", size=12)
    for issue in current_report['issues']:
        pdf.multi_cell(0, 10, txt=f"- {issue}")
    
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.multi_cell(0, 10, txt="Este relatório técnico indica melhorias vitais para o ranqueamento no Google. Para consultoria completa, entre em contato com o desenvolvedor.")

    # Gerar o arquivo em memória para download
    output = io.BytesIO()
    pdf_content = pdf.output(dest='S')
    output.write(pdf_content)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name=f"Relatorio_SEO_{int(time.time())}.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)