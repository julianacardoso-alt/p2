import os
import re
import streamlit as st
import pandas as pd

# Prefer PyPDF2 for text extraction. If not available, show instructions to install.
try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

import altair as alt

st.set_page_config(page_title="Análise de perfil - Advogados", layout="centered")

st.title("Análise de perfil — Advogados")
st.markdown(
    "Este aplicativo lê o PDF 'Microsoft Word - perfil2.mhtml.pdf' (esperado na mesma pasta do app) "
    "e gera dois gráficos: quantidade de advogados homens x mulheres e quantidade com filhos x sem filhos."
)

PDF_DEFAULT = "Microsoft Word - perfil2.mhtml.pdf"

pdf_path = st.text_input("Caminho para o arquivo PDF:", value=PDF_DEFAULT)

if not os.path.exists(pdf_path):
    st.warning(
        f"Arquivo não encontrado em: {pdf_path}. Coloque o arquivo na mesma pasta do app ou ajuste o caminho."
    )

if PdfReader is None:
    st.error(
        "A biblioteca PyPDF2 não está instalada no ambiente. Instale com:\n\n"
        "`pip install PyPDF2 streamlit pandas altair`"
    )

def extract_text_from_pdf(path):
    """Extrai texto de todas as páginas do PDF usando PyPDF2."""
    if PdfReader is None:
        return ""
    try:
        text = ""
        with open(path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        st.error(f"Erro ao ler o PDF: {e}")
        return ""

def split_profiles(text):
    """
    Heurística para dividir o texto em blocos de perfil.
    Tenta usar delimitadores comuns (Nome:, Perfil, duas quebras de linha, 'Advogado', etc).
    """
    # Primeiro normalize quebras de linha múltiplas
    text = re.sub(r'\r\n?', '\n', text)
    # Use delimitadores que aparecem em documentos de perfis
    parts = re.split(r'(?:\n{2,}|Nome:|Perfil|Advogado[a]?:)', text, flags=re.IGNORECASE)
    parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 10]
    return parts

def detect_gender(chunk):
    lower = chunk.lower()
    # padrão explícito
    if re.search(r'\b(sexo[:\s]*feminino|feminino|mulher|advogada)\b', lower):
        return "Feminino"
    if re.search(r'\b(sexo[:\s]*masculino|masculino|homem|advogado)\b', lower):
        return "Masculino"
    # palavras soltas que indicam gênero
    if re.search(r'\bmulher\b', lower):
        return "Feminino"
    if re.search(r'\bhomem\b', lower):
        return "Masculino"
    return None

def detect_children(chunk):
    lower = chunk.lower()
    # negativa explícita
    if re.search(r'\b(sem filhos|não tem filhos|nao tem filhos|não possui filhos|nao possui filhos|filhos[:\s]*0)\b', lower):
        return "Não"
    # positiva explícita
    if re.search(r'\b(tem filhos|filho|filhos|filhos[:\s]*sim|filhos[:\s]*s)\b', lower):
        # evitar falso positivo com "sem filhos" já tratado acima
        return "Sim"
    return None

def fallback_counts(text):
    """Se a divisão por perfil falhar, faz contagem global por ocorrências de palavras-chave."""
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
        # only consider rows where at least one attribute found
        if g is None and c is None:
            continue
        rows.append({"gender": g or "Desconhecido", "children": c or "Desconhecido", "raw": p})
    # If nothing parsed, try a fallback global heuristic
    if not rows:
        m, f, filhos_count, sem_count = fallback_counts(text)
        # Prepare rows based on fallback counts (best-effort)
        rows = []
        if m or f:
            # add aggregated rows so we can plot them
            if m:
                rows.append({"gender": "Masculino", "children": "Desconhecido", "raw": "agregado"} )
            if f:
                rows.append({"gender": "Feminino", "children": "Desconhecido", "raw": "agregado"} )
        if filhos_count or sem_count:
            if filhos_count:
                rows.append({"gender": "Desconhecido", "children": "Sim", "raw": "agregado"} )
            if sem_count:
                rows.append({"gender": "Desconhecido", "children": "Não", "raw": "agregado"} )
    return pd.DataFrame(rows)

if st.button("Processar arquivo"):
    if not os.path.exists(pdf_path):
        st.error("Arquivo não encontrado. Verifique o caminho e tente novamente.")
    elif PdfReader is None:
        st.error("PyPDF2 não está disponível. Instale as dependências e reinicie.")
    else:
        with st.spinner("Extraindo texto do PDF..."):
            text = extract_text_from_pdf(pdf_path)
        if not text.strip():
            st.error("Nenhum texto extraído do PDF. O arquivo pode estar protegido ou em formato não suportado.")
        else:
            st.success("Texto extraído com sucesso (heurística aplicada).")
            df = analyze(text)
            if df.empty:
                st.warning("Não foi possível identificar perfis ou informações relevantes com a heurística atual.")
                st.subheader("Trecho do texto extraído")
                st.text(text[:1000])
            else:
                st.subheader("Dados interpretados (amostra)")
                st.write(df[["gender", "children"]].head(50))

                # Contagens para gênero
                gender_counts = df['gender'].value_counts().reset_index()
                gender_counts.columns = ['gender', 'count']

                # Contagens para filhos
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

                st.markdown(
                    "Observação: a extração usa heurísticas baseadas em palavras-chave. "
                    "Se os rótulos nos perfis estiverem em formatos diferentes (por exemplo, "
                    "'Gênero' em vez de 'Sexo', ou 'Tem filhos: Não'), pode ser necessário "
                    "ajustar as expressões regulares no código para capturar todos os casos."
                )

st.markdown("---")
st.markdown(
    "Como usar:\n"
    "- Coloque 'Microsoft Word - perfil2.mhtml.pdf' na mesma pasta que este arquivo (ou informe o caminho completo).\n"
    "- Instale dependências: pip install streamlit PyPDF2 pandas altair\n"
    "- Execute: streamlit run perfil.py\n"
)
