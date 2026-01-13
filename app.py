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
        # Criação do PDF com margens explícitas
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.set_margins(15, 15, 15)
        pdf.add_page()
        
        # Título - Largura ajustada para 180mm (seguro para A4)
        pdf.set_font("Helvetica", 'B', 22)
        pdf.set_text_color(102, 126, 234)
        pdf.cell(180, 20, txt="Relatório SEO Pro", ln=True, align='C')
        
        pdf.ln(10)
        
        # Informações Gerais
        pdf.set_font("Helvetica", 'B', 12)
        pdf.set_text_color(0, 0, 0)
        # Usamos multi_cell para a URL caso ela seja muito longa e precise quebrar linha
        pdf.multi_cell(180, 10, txt=f"Site Analisado: {current_report['url']}")
        pdf.cell(180, 10, txt=f"Pontuação Geral: {current_report['score']}/100", ln=True)
        
        pdf.ln(10)
        
        # Seção de Problemas
        pdf.set_font("Helvetica", 'B', 14)
        pdf.cell(180, 10, txt="Pontos de Melhoria Identificados:", ln=True)
        
        pdf.set_font("Helvetica", size=12)
        # Listagem de erros com largura de 180mm para evitar o erro de espaço horizontal
        for issue in current_report['issues']:
            pdf.multi_cell(180, 8, txt=f"- {issue}")
            pdf.ln(2)
        
        pdf.ln(20)
        
        # Rodapé/Nota final
        pdf.set_font("Helvetica", 'I', 10)
        pdf.set_text_color(128, 128, 128)
        pdf.multi_cell(180, 10, txt="Nota: Este relatório é uma análise técnica automatizada para fins de otimização de mecanismos de busca (SEO).")

        # Gerar o PDF
        pdf_bytes = pdf.output() 
        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name="Relatorio_Otimizacao_SEO.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        return f"Erro técnico ao gerar PDF: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
