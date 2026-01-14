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

# ⚠️ COLOQUE SEU TOKEN DO MERCADO PAGO AQUI ABAIXO ⚠️
sdk = mercadopago.SDK("APP_USR-430272113998230-011315-b4e2d93f3de6b823f9a8814e2d8576ed-57091170")

def analyze_seo(url):
    try:
        if not url.startswith('http'):
            url = 'https://' + url
            
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        start_time = time.time()
        response = requests.get(url, timeout=10, headers=headers)
        end_time = time.time()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        load_time = round(end_time - start_time, 2)
        
        issues = []
        score = 100
        
        # 1. Análise de Título
        title = soup.title.string.strip() if soup.title else None
        if not title:
            issues.append("Falta a tag <title>.")
            score -= 20
        elif len(title) < 10:
            issues.append("Título da página muito curto (menos de 10 caracteres).")
            score -= 10
        elif len(title) > 60:
            issues.append("Título muito longo (ideal é até 60 caracteres).")
            score -= 5

        # 2. Análise de H1
        h1_tags = soup.find_all('h1')
        if not h1_tags:
            issues.append("Falta uma tag H1 (Título principal). O Google precisa disso para entender o tema.")
            score -= 20
        elif len(h1_tags) > 1:
            issues.append("Muitas tags H1 encontradas. Use apenas uma por página.")
            score -= 10

        # 3. Meta Descrição (Novo!)
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc or not meta_desc.get('content'):
            issues.append("Falta a Meta Descrição. Seu site não tem resumo nos resultados do Google.")
            score -= 20
        
        # 4. Viewport / Mobile (Novo!)
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if not viewport:
            issues.append("Site não otimizado para celulares (Falta tag Viewport).")
            score -= 20

        # 5. Imagens e Alt Text
        images = soup.find_all('img')
        images_no_alt = [img for img in images if not img.get('alt')]
        if images_no_alt:
            issues.append(f"Existem {len(images_no_alt)} imagens sem texto alternativo (alt). O Google não consegue 'ler' essas imagens.")
            score -= 15

        # 6. Performance
        if load_time > 2.0:
            issues.append(f"Site lento ({load_time}s). O ideal é carregar em menos de 2s.")
            score -= 15

        # 7. Contagem de Palavras e Keywords (Novo!)
        text_content = soup.get_text()
        words = re.findall(r'\w+', text_content.lower())
        word_count = len(words)
        
        # Filtra palavras comuns (stopwords simples) para achar as keywords
        stopwords = ['de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não', 'uma', 'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'foi', 'ao', 'ele', 'das', 'tem', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'nos', 'já', 'está']
        filtered_words = [w for w in words if w not in stopwords and len(w) > 3]
        top_keywords = Counter(filtered_words).most_common(5)

        if word_count < 300:
            issues.append(f"Conteúdo muito curto ({word_count} palavras). O Google prefere textos acima de 300 palavras.")
            score -= 10

        return {
            "url": url,
            "status": "Sucesso",
            "score": max(score, 0),
            "load_time": load_time,
            "title": title or "Não encontrado",
            "issues": issues,
            "word_count": word_count,
            "top_keywords": top_keywords
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

@app.route('/gerar_gratis')
def gerar_gratis():
    if 'report' not in session:
        return "Analise um site primeiro na home!", 400
    return redirect(url_for('download_pdf'))

@app.route('/pagamento_aprovado')
def pagamento_aprovado():
    if 'report' not in session:
        return redirect(url_for('index'))
    return render_template('checkout.html', report=session['report'])

@app.route('/download_pdf')
def download_pdf():
    if 'report' not in session: 
        return redirect(url_for('index'))
    
    report = session['report']
    
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    
    # --- PÁGINA 1: RESUMO ---
    # Cabeçalho
    pdf.set_fill_color(102, 126, 234) 
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_font("Helvetica", 'B', 24)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(180, 30, "RELATORIO SEO PROFISSIONAL", ln=True, align='C')
    
    pdf.ln(15)
    pdf.set_text_color(0, 0, 0)
    
    # Informações do Site
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(180, 10, f"Site Analisado: {report['url']}", ln=True)
    pdf.cell(90, 10, f"Tempo de Carregamento: {report['load_time']}s")
    pdf.cell(90, 10, f"Total de Palavras: {report['word_count']}", ln=True)
    
    pdf.ln(5)
    
    # Score Box
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(180, 15, f"NOTA DE DESEMPENHO: {report['score']}/100", ln=True, align='C', fill=True)
    
    pdf.ln(10)
    
    # Palavras-chave principais
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(180, 10, "Principais Palavras-Chave Detectadas:", ln=True)
    pdf.set_font("Helvetica", size=11)
    keywords_text = ", ".join([f"{word} ({count}x)" for word, count in report['top_keywords']])
    pdf.multi_cell(180, 8, txt=keywords_text)
    
    pdf.ln(10)

    # Lista de Problemas (Resumo)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(180, 10, "DIAGNOSTICO DE PROBLEMAS:", ln=True)
    
    pdf.set_font("Helvetica", size=11)
    pdf.set_text_color(50, 50, 50)
    
    if not report['issues']:
        pdf.set_text_color(0, 150, 0)
        pdf.multi_cell(180, 10, txt="Parabens! Nenhum erro critico foi encontrado.")
    else:
        for issue in report['issues']:
            pdf.multi_cell(180, 8, txt=f"[X] {issue}")
            pdf.ln(1)

    # --- PÁGINA 2: PLANO DE AÇÃO ---
    pdf.add_page()
    pdf.set_fill_color(50, 50, 50)
    pdf.rect(0, 0, 210, 30, 'F')
    pdf.set_y(10)
    pdf.set_font("Helvetica", 'B', 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(180, 10, "GUIA DE CORRECAO PASSO-A-PASSO", ln=True, align='C')
    
    pdf.ln(25)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", size=11)
    
    pdf.multi_cell(180, 8, txt="Abaixo estao as solucoes tecnicas para os problemas mais comuns encontrados. Entregue este guia ao seu desenvolvedor ou aplique as correcoes voce mesmo.\n")
    pdf.ln(5)

    # Dicionário de Soluções Educativas
    solucoes = [
        ("Tag H1", "SOLUCAO: No codigo HTML, certifique-se de que o titulo principal da pagina esteja dentro de tags <h1>Seu Titulo</h1>. Deve haver apenas um H1 por pagina."),
        ("Meta Descrição", "SOLUCAO: Adicione <meta name='description' content='Resumo do seu site aqui'> dentro da tag <head>. Isso aumenta seus cliques no Google."),
        ("Imagens sem texto", "SOLUCAO: Em todas as tags <img>, adicione o atributo alt. Exemplo: <img src='foto.jpg' alt='Descricao da foto'>."),
        ("Site lento", "SOLUCAO: Comprima suas imagens usando sites como TinyPNG. Evite scripts desnecessarios e use cache no servidor."),
        ("Viewport", "SOLUCAO: Para funcionar no celular, adicione esta linha no <head>: <meta name='viewport' content='width=device-width, initial-scale=1.0'>."),
        ("Conteúdo curto", "SOLUCAO: O Google prioriza paginas com conteudo rico. Tente expandir seus textos para pelo menos 500 palavras explicando melhor seu servico.")
    ]

    for item, explicacao in solucoes:
        pdf.set_font("Helvetica", 'B', 12)
        pdf.set_text_color(102, 126, 234)
        pdf.cell(180, 8, txt=f"Como corrigir erros de {item}:", ln=True)
        pdf.set_font("Helvetica", size=11)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(180, 7, txt=explicacao)
        pdf.ln(5)

    # Rodapé final
    pdf.set_y(-30)
    pdf.set_font("Helvetica", 'I', 9)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 10, "Relatorio gerado automaticamente por SEO Checker Pro.", align='C')

    output = io.BytesIO()
    output.write(pdf.output())
    output.seek(0)
    
    return send_file(output, as_attachment=True, download_name="Relatorio_SEO_Completo.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)


