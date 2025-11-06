 url=https://github.com/julianacardoso-alt/p2/blob/main/perfil.py
import os
import re
import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Análise de perfil - Advogados", layout="centered")
st.title("Análise de perfil — Advogados")
st.markdown(
    "Este app lê o PDF 'Microsoft Word - perfil2.mhtml.pdf' (padrão na mesma pasta do app) "
    "e gera dois gráficos: homens x mulheres e possuem filhos x não possuem. "
    "O extractor tenta pdfplumber primeiro (melhor para PDFs), depois PyPDF2 como alternativa."
)

PDF_DEFAULT = "Microsoft Word - perfil2.mhtml.pdf"
pdf_path = st.text_input("Caminho para o arquivo PDF:", value=PDF_DEFAULT)

# Tenta importar pdfplumber e PyPDF2 (não é obrigatório que ambos existam)
try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

def extract_text_from_pdf(path):
    """Tenta extrair texto com pdfplumber, em seguida PyPDF2. Retorna string com todo o texto."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    text = ""
    # pdfplumber (recomendado)
    if pdfplumber is not None:
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                return text
        except Exception:
            # falhou, vamos tentar PyPDF2
            text = ""
    # PyPDF2 fallback
    if PdfReader is not None:
        try:
            with open(path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                return text
        except Exception:
            pass
    # Se chegar aqui, nada funcionou
    return ""

def split_profiles(text):
    text = re.sub(r'\r\n?', '\n', text)
    parts = re.split(r'(?:\n{2,}|Nome:|Perfil|Advogado[a]?:)', text, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 10]
    return parts

def detect_gender(chunk):
    lower = chunk.lower()
    if re.search(r'\b(sexo[:\s]*feminino|feminino|mulher|advogada)\b', lower):
        return "Feminino"
    if re.search(r'\b(sexo[:\s]*masculino|masculino|homem|advogado)\b', lower):
        return "Masculino"
    if re.search(r'\bmulher\b', lower):
        return "Feminino"
    if re.search(r'\bhomem\b', lower):
        return "Masculino"
    return None

def detect_children(chunk):
    lower = chunk.lower()
    if re.search(r'\b(sem filhos|não tem filhos|nao tem filhos|não possui filhos|nao possui filhos|filhos[:\s]*0)\b', lower):
        return "Não"
    if re.search(r'\b(tem filhos|filho|filhos|filhos[:\s]*sim|filhos[:\s]*s)\b', lower):
        return "Sim"
    return None

def fallback_counts(text):
    lower = text.lower()
    masculino = len(re.findall(r'\b(masculino|homem|advogado)\b', lower))
    feminino = len(re.findall(r'\b(feminino|mulher|advogada)\b', lower))
    filhos = len(re.findall(r'\b(filho|filhos|tem filhos)\b', lower))
    sem_filhos = len(re.findall(r'\b(sem filhos|não tem filhos|nao tem filhos|não possui filhos|nao possui filhos)\b', lower))
    return masculino, feminino, filhos, sem_filhos

def analyze(text):
    profiles = split_profiles(text)
    rows = []
    for p in profiles:
        g = detect_gender(p)
        c = detect_children(p)
        if g is None and c is None:
            continue
        rows.append({"gender": g or "Desconhecido", "children": c or "Desconhecido", "raw": p})
    if not rows:
        m, f, filhos_count, sem_count = fallback_counts(text)
        rows = []
        if m:
            rows.append({"gender": "Masculino", "children": "Desconhecido", "raw": "agregado"})
        if f:
            rows.append({"gender": "Feminino", "children": "Desconhecido", "raw": "agregado"})
        if filhos_count:
            rows.append({"gender": "Desconhecido", "children": "Sim", "raw": "agregado"})
        if sem_count:
            rows.append({"gender": "Desconhecido", "children": "Não", "raw": "agregado"})
    return pd.DataFrame(rows)

if st.button("Processar arquivo"):
    if not os.path.exists(pdf_path):
        st.error("Arquivo não encontrado. Verifique o caminho e tente novamente.")
    else:
        if pdfplumber is None and PdfReader is None:
            st.error(
                "Nenhuma biblioteca de extração de PDF disponível. Instale pdfplumber ou PyPDF2.\n"
                "Ex.: pip install pdfplumber PyPDF2"
            )
        else:
            with st.spinner("Extraindo texto do PDF..."):
                text = extract_text_from_pdf(pdf_path)
            if not text.strip():
                st.error(
                    "Nenhum texto extraído do PDF. Tente instalar pdfplumber (melhor para muitos PDFs) "
                    "ou verifique se o PDF está protegido/scan (imagem)."
                )
                st.subheader("Sugestões")
                st.write("- Tentar instalar pdfplumber: pip install pdfplumber")
                st.write("- Se o PDF for imagem escaneada, será necessário OCR (p.ex. Tesseract).")
            else:
                st.success("Texto extraído com sucesso.")
                df = analyze(text)
                if df.empty:
                    st.warning("Não foi possível identificar perfis com a heurística atual.")
                    st.subheader("Trecho do texto extraído")
                    st.text(text[:1500])
                else:
                    st.subheader("Dados interpretados (amostra)")
                    st.write(df[["gender", "children"]].head(50))

                    gender_counts = df['gender'].value_counts().reset_index()
                    gender_counts.columns = ['gender', 'count']

                    children_counts = df['children'].value_counts().reset_index()
                    children_counts.columns = ['children', 'count']

                    st.subheader("Gráfico: Homens x Mulheres")
                    bar1 = alt.Chart(gender_counts).mark_bar().encode(
                        x=alt.X('gender:N', sort='-y', title='Gênero'),
                        y=alt.Y('count:Q', title='Quantidade'),
                        color=alt.Color('gender:N', legend=None)
                    ).properties(width=600, height=350)
                    text1 = bar1.mark_text(dx=0, dy=-10, color='black').encode(text='count:Q')
                    st.altair_chart(bar1 + text1, use_container_width=True)

                    st.subheader("Gráfico: Possuem filhos x Não possuem filhos")
                    bar2 = alt.Chart(children_counts).mark_bar().encode(
                        x=alt.X('children:N', sort='-y', title='Possui filhos?'),
                        y=alt.Y('count:Q', title='Quantidade'),
                        color=alt.Color('children:N', legend=None)
                    ).properties(width=600, height=350)
                    text2 = bar2.mark_text(dx=0, dy=-10, color='black').encode(text='count:Q')
                    st.altair_chart(bar2 + text2, use_container_width=True)

st.markdown("---")
st.markdown(
    "Como usar:\n"
    "- Coloque 'Microsoft Word - perfil2.mhtml.pdf' na mesma pasta que este arquivo ou informe o caminho.\n"
    "- Instale dependências (exemplo): pip install -r requirements.txt\n"
    "- Execute: streamlit run perfil.py\n"
)
