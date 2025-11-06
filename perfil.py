import panda as pd
import streamlit as st
import matplotlib.pyplot as plt

st.title('Perfil dos Advogados')

dataset = pd.read_csv ('perfil1.pdf')

if pdf_file is not None:
    reader = PyPDF2.PdfReader(pdf_file)
    try:
        page = reader.pages[33]  # Página 34 = índice 33
        text = page.extract_text()
    except Exception as e:
        st.error(f"Erro ao tentar ler a página 34 do PDF: {e}")
        st.stop()

    # Busca número de homens advogados
    homens = re.search(r"([0-9]+)\s+homens", text)
    homens_count = int(homens.group(1)) if homens else 0

    # Busca número de mulheres advogadas
    mulheres = re.search(r"([0-9]+)\s+mulheres", text)
    mulheres_count = int(mulheres.group(1)) if mulheres else 0

    # Busca número de advogados com filhos
    filhos = re.search(r"([0-9]+)\s+advogados com filhos", text)
    filhos_count = int(filhos.group(1)) if filhos else 0

    labels = ['Homens', 'Mulheres', 'Com Filhos']
    values = [homens_count, mulheres_count, filhos_count]

    fig, ax = plt.subplots()
    ax.bar(labels, values, color=['blue', 'pink', 'green'])
    ax.set_ylabel('Quantidade')
    st.pyplot(fig)
else:
    st.info("Faça o upload do arquivo PDF para ver o gráfico.")
