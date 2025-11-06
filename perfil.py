import re
import streamlit as st
import matplotlib.pyplot as plt

# Try to import a PDF reader library; if missing show a friendly Streamlit error instead of raising
PDFReader = None
_import_error_msg = (
    "PyPDF2 (or pypdf) is not installed in this environment.\n\n"
    "Install it in the same Python environment used to run Streamlit:\n\n"
    "  /home/adminuser/venv/bin/python -m pip install pypdf\n\n"
    "or (general):\n\n"
    "  python -m pip install pypdf\n\n"
    "After installing, restart the Streamlit process (streamlit run perfil.py)."
)
try:
    from PyPDF2 import PdfReader as PDFReader  # try common name
except Exception:
    try:
        from pypdf import PdfReader as PDFReader  # maintained fork
    except Exception:
        PDFReader = None

st.title('Perfil dos Advogados')

if PDFReader is None:
    st.error(_import_error_msg)
    st.stop()

pdf_file = st.file_uploader("Faça upload do arquivo PDF (página 34 será lida)", type=["pdf"])

if pdf_file is not None:
    try:
        reader = PDFReader(pdf_file)
    except Exception as e:
        st.error(f"Erro ao abrir o PDF: {e}")
    else:
        page_index = 33
        if page_index >= len(reader.pages):
            st.error(f"O PDF tem apenas {len(reader.pages)} páginas; não é possível ler a página {page_index+1}.")
        else:
            page = reader.pages[page_index]
            text = page.extract_text() or ""
            def extract_number(pattern):
                m = re.search(pattern, text, re.IGNORECASE)
                if not m:
                    return 0
                num = m.group(1).replace(".", "").replace(",", "")
                try:
                    return int(num)
                except ValueError:
                    return 0

            homens_count = extract_number(r"([\d\.,]+)\s+homens?")
            mulheres_count = extract_number(r"([\d\.,]+)\s+mulheres?")
            filhos_count = extract_number(r"([\d\.,]+)\s+(?:advogados com filhos|advogadas com filhos|com filhos)")

            labels = ['Homens', 'Mulheres', 'Com Filhos']
            values = [homens_count, mulheres_count, filhos_count]

            st.write("Valores extraídos da página 34:")
            st.write(dict(zip(labels, values)))

            fig, ax = plt.subplots()
            ax.bar(labels, values, color=['#1f77b4', '#ff7f0e', '#2ca02c'])
            ax.set_ylabel('Quantidade')
            ax.set_title('Perfil dos Advogados (página 34)')
            for i, v in enumerate(values):
                ax.text(i, v + (max(values) * 0.01 if max(values) > 0 else 0.1), str(v), ha='center')
            st.pyplot(fig)
else:
    st.info("Faça o upload do arquivo PDF para ver o gráfico.")
