from flask import Flask, render_template, request, send_file, redirect, url_for
import requests
from bs4 import BeautifulSoup
import time
from fpdf import FPDF
import io
import os

app = Flask(__name__)

# Armazenamento temporário para o relatório
current_report = {}

def analyze_seo(url):
    try:
        if not url.startswith('http'):
            url = 'https://' + url
            
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        start_time = time.time()
        response = requests.get(url, timeout=15, headers=headers)
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
            score -= 25
            issues.append(f"Site lento: {load_time}s. O ideal é menos de 2s para SEO.")

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
            current_report = report
    return render_template('index.html', report=report)

@app.route('/checkout')
def checkout():
    if not current_report:
        return redirect(url_for('index'))
    return render_template('checkout.html', report=current_report)

@app.route('/download_pdf')
def download_pdf():
    global current_report
    if not current_report or current_report.get('status') != "Sucesso":
        return "Nenhum relatório disponível para download", 400

    try:
        # Criação do PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 22)
        pdf.set_text_color(102, 126, 234)
        pdf.cell(200, 20, txt="Relatório SEO Pro", ln=True, align='C')
        
        pdf.ln(10)
        pdf.set_font("Helvetica", 'B', 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(200, 10, txt=f"Site Analisado: {current_report['url']}", ln=True)
        pdf.cell(200, 10, txt=f"Pontuação Geral: {current_report['score']}/100", ln=True)
        
        pdf.ln(10)
        pdf.set_font("Helvetica", 'B', 14)
        pdf.cell(200, 10, txt="Pontos de Melhoria Identificados:", ln=True)
        
        pdf.set_font("Helvetica", size=12)
        # CORREÇÃO AQUI: Usando hífen '-' em vez de '•'
        for issue in current_report['issues']:
            pdf.multi_cell(0, 10, txt=f"- {issue}")
        
        pdf.ln(20)
        pdf.set_font("Helvetica", 'I', 10)
        pdf.set_text_color(128, 128, 128)
        pdf.multi_cell(0, 10, txt="Este relatório é uma amostra técnica. Para correções completas e serviços de otimização, entre em contato conosco.")

        pdf_bytes = pdf.output() 
        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name="Relatorio_Otimizacao.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        # Mostra o erro exato se algo der errado, facilitando a depuração
        return f"Erro ao gerar PDF: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
