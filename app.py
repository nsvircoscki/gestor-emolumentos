import streamlit as st
from google import genai
import pandas as pd
from PIL import Image
import json
import io

# Configuração da Página
st.set_page_config(page_title="Gestor de Emolumentos", layout="wide")

st.title("📑 Registro de Emolumentos (Versão 2.5)")

# Conexão com a IA
try:
    if "GOOGLE_API_KEY" in st.secrets:
        client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        # SUA CHAVE
        chave_secreta = "" 
        client = genai.Client(api_key=chave_secreta)
except Exception as e:
    st.error(f"Erro na configuração: {e}")
    st.stop()

# Upload da foto
arquivo_foto = st.file_uploader("Tire uma foto ou suba o recibo", type=["jpg", "png", "jpeg"])

if arquivo_foto:
    image = Image.open(arquivo_foto)
    st.image(image, caption="Recibo carregado", width=300)
    
    if st.button("Processar Recibo"):
        with st.spinner("IA processando com Gemini 2.5..."):
            try:
                # Prompt pedindo dados + DATA
                prompt = """
                Analise a imagem deste recibo. Extraia os dados e retorne APENAS um objeto JSON (sem ```json):
                {
                    "apresentante": "Nome completo do apresentante",
                    "vinculo": "O código do vínculo (ex: M-54439)",
                    "natureza": "O motivo/natureza do serviço",
                    "valor": 0.00 (apenas números com ponto),
                    "data": "A data do recibo (DD/MM/AAAA)"
                }
                """

                # MODELO MANTIDO COMO 2.5 CONFORME SUA SOLICITAÇÃO
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt, image]
                )
                
                # Limpeza e conversão
                texto_resposta = response.text.replace("```json", "").replace("```", "").strip()
                dados = json.loads(texto_resposta)
                
                # --- Lógica do Excel ---
                caminho_excel = 'clientes.xlsx'
                
                try:
                    df = pd.read_excel(caminho_excel)
                except FileNotFoundError:
                    # Cria do zero se não existir
                    df = pd.DataFrame(columns=["Codigo", "Nome", "Motivo", "Valor", "Data"])

                # Garante coluna Data
                if "Data" not in df.columns:
                    df["Data"] = ""

                df['Codigo'] = df['Codigo'].astype(str)
                vinculo_alvo = str(dados['vinculo'])

                # Verifica se existe
                filtro = df['Codigo'] == vinculo_alvo
                
                if filtro.any():
                    # ATUALIZA
                    idx = df.index[filtro][0]
                    df.at[idx, 'Motivo'] = dados['natureza']
                    df.at[idx, 'Valor'] = float(dados['valor'])
                    df.at[idx, 'Data'] = dados['data']
                    msg = f"✅ Atualizado: {dados['apresentante']} | Data: {dados['data']}"
                else:
                    # CRIA NOVO
                    novo_cliente = {
                        "Codigo": vinculo_alvo,
                        "Nome": dados['apresentante'],
                        "Motivo": dados['natureza'],
                        "Valor": float(dados['valor']),
                        "Data": dados['data']
                    }
                    df = pd.concat([df, pd.DataFrame([novo_cliente])], ignore_index=True)
                    msg = f"🆕 Novo Cliente Criado: {dados['apresentante']}"

                # Salva
                df.to_excel(caminho_excel, index=False)
                st.success(msg)
                
                st.write("### Planilha Atualizada:")
                st.dataframe(df)

            except Exception as e:
                st.error(f"Ocorreu um erro: {e}")