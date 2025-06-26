# main.py com integração ao Google Drive para banco de dados compartilhado

import streamlit as st
from openai import OpenAI
import time
import re
import sqlite3
import bcrypt
from datetime import datetime
from drive_utils import download_db_from_drive, upload_db_to_drive  # NOVO
import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# === CONFIGURAÇÃO INICIAL DA PÁGINA ===
st.set_page_config(
    page_title="Assistente Excel - Coeso Cursos",
    page_icon="https://coesocursos.com.br/wp-content/uploads/2025/05/cropped-favicon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Baixa o banco de dados do Google Drive
download_db_from_drive()  # NOVO

# === CONSTANTES ===
SYSTEM_PROMPT = """
Você é um assistente especializado em Excel para construção civil com as seguintes regras:

1️⃣ **Formação:**
- Funções SEMPRE em português (SE, PROCV, ÍNDICE)
- Fórmulas Excel entre ``` ``` (ex: ```=PI()*A2^2```)
- Fórmulas matemáticas em Markdown (ex: Área = π × raio²)
- Unidades em metros, kg, m³
- Sempre usar vírgula como separador decimal

2️⃣ **Estrutura de Resposta:**
1. Explicação técnica breve
2. Fórmula matemática clara
3. Fórmula Excel aplicável
4. Exemplo numérico completo

3️⃣ **Exemplos CORRETOS:**
- Para área: "Área = comprimento × largura → ```=B2*C2```"
- Para volume: "Volume = π × raio² × altura → ```=PI()*B2^2*C2```"
- Para conversão de barras: "5 barras de 10mm ≈ 8 barras de 8mm (considerando áreas equivalentes)"

4️⃣ **PROIBIDO:**
- Usar caracteres como {, }, |, \\text, \\frac
- Fórmulas sem formatação adequada
- Unidades inconsistentes ou misturadas
"""

# === CSS PERSONALIZADO ===
CUSTOM_CSS = """
<style>
...
</style>
"""

# === BANCO DE DADOS ===
def init_db():
    conn = sqlite3.connect('auth.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    senha TEXT,
                    created_at TIMESTAMP,
                    last_login TIMESTAMP
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT,
                    acao TEXT,
                    timestamp TIMESTAMP
                )''')
    conn.commit()
    conn.close()

# === LOG ===
def registrar_log(email, acao):
    conn = sqlite3.connect('auth.db')
    c = conn.cursor()
    c.execute("INSERT INTO logs (email, acao, timestamp) VALUES (?, ?, ?)", (email, acao, datetime.now()))
    conn.commit()
    conn.close()
    upload_db_to_drive()  # NOVO

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def update_last_login(email):
    conn = sqlite3.connect('auth.db')
    c = conn.cursor()
    c.execute("UPDATE users SET last_login=? WHERE email=?", (datetime.now(), email))
    conn.commit()
    conn.close()
    upload_db_to_drive()  # NOVO

def validar_login(email, senha):
    conn = sqlite3.connect('auth.db')
    c = conn.cursor()
    c.execute("SELECT senha FROM users WHERE email=?", (email,))
    result = c.fetchone()
    conn.close()
    if result and bcrypt.checkpw(senha.encode(), result[0]):
        return True
    return False

# CSS personalizado
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# === TELA DE LOGIN ===
def login_screen():
    with st.container():
        st.markdown("""
        <div style="text-align: center; margin-bottom: 1rem;">
            <a href="https://www.instagram.com/coesocursos" target="_blank">
                <img src="https://coesocursos.com.br/wp-content/uploads/2025/05/logo-e1738083192299.png" 
                    alt="Logo Coeso Cursos" style="width: 100%; max-width: 600px;">
            </a>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #122a29;'>🔒 Acesso ao Assistente de Excel - Exclusivo para Alunos da Coeso Cursos</h2>", unsafe_allow_html=True)

        email = st.text_input("Digite seu e-mail:", key="login_email_input")
        senha = st.text_input("Digite sua senha:", type="password", key="login_password_input")

        if st.button("Acessar", key="login_access_button"):
            if is_valid_email(email) and senha:
                if validar_login(email, senha):
                    update_last_login(email)
                    registrar_log(email, "Login Usuário")
                    st.session_state['authenticated'] = True
                    st.session_state['user_email'] = email
                    st.session_state['sidebar_state'] = 'expanded'
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")
            else:
                st.error("Por favor, preencha e-mail e senha válidos.")

# === EXECUÇÃO ===
init_db()

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['sidebar_state'] = 'expanded'

if not st.session_state['authenticated']:
    login_screen()
    st.stop()


# === INTERFACE AUTENTICADA ===
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

st.sidebar.markdown(f"<div style='color: white;'>**Usuário:** {st.session_state['user_email']}</div>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <div class="sidebar-content">
        <div style="text-align: center; margin-bottom: 20px;">
            <a href="https://www.instagram.com/coesocursos" target="_blank">
                <img src="https://coesocursos.com.br/wp-content/uploads/2025/05/logo-e1738083192299.png" 
                    alt="Logo Coeso Cursos" style="width: 80%; max-width: 250px;">
            </a>
        </div>
        <div style="color: white;"><strong>Assistente de Excel para Construção Civil</strong></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("### ℹ️ Como usar:")
    st.markdown("- Pergunte sobre fórmulas, cálculos e planilhas")
    st.markdown("- Exemplos:")
    st.markdown("  - `Como calcular área de laje?`")
    st.markdown("  - `Fórmula para previsão de materiais`")
    st.markdown("  - `Como usar PROCV em orçamentos?`")
    
    st.divider()
    
    st.markdown("🛠️ **Dicas técnicas:**")
    st.markdown("- Todas as fórmulas em português")
    st.markdown("- Exemplos práticos incluídos")
    
    st.divider()
    
    st.caption("Versão 1.0 | © 2025 Coeso Cursos")
    
    # Botões em colunas
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🪟 Limpar Conversa", key="clear_chat"):
            st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            st.rerun()
    with col2:
        if st.button("🚪 Sair", key="logout"):
            st.session_state['authenticated'] = False
            st.session_state.pop('user_email', None)
            st.rerun()

st.title("🏗️ Assistente de Excel para Construção Civil")
st.caption("Obtenha fórmulas prontas para usar em suas planilhas de obra")

if 'openai' not in st.secrets:
    st.error("API Key não configurada. Verifique o arquivo secrets.toml")
    st.stop()

client = OpenAI(api_key=st.secrets["openai"]["api_key"])

def format_response(text):
    # Primeiro limpa caracteres indesejados
    text = re.sub(r'\{.*?\}', '', text)
    text = re.sub(r'\\[a-z]+', '', text)
    
    # Divide em seções
    sections = re.split(r'(\d+\.)', text)
    formatted_text = ""
    
    for i in range(1, len(sections), 2):
        section_num = sections[i].replace('.', '')
        section_content = sections[i+1].strip()
        
        if section_num == '1':
            formatted_text += f"**1. Explicação técnica breve**\n\n{section_content}\n\n"
        elif section_num == '2':
            formatted_text += f"**2. Fórmula matemática clara**\n\n{section_content}\n\n"
        elif section_num == '3':
            # Formata fórmulas Excel
            section_content = re.sub(r'`(.*?)`', r'`\1`', section_content)
            formatted_text += f"**3. Fórmula Excel aplicável**\n\n{section_content}\n\n"
        elif section_num == '4':
            formatted_text += f"**4. Exemplo numérico completo**\n\n{section_content}\n\n"
    
    return formatted_text.strip()

def limit_message_history(messages, max_messages=10):
    if len(messages) > max_messages + 1:
        return [messages[0]] + messages[-(max_messages):]
    return messages

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

with st.container():
    if prompt := st.chat_input("Digite sua dúvida sobre Excel para construção civil...", key="chat_input"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages = limit_message_history(st.session_state.messages)
        with st.chat_message("assistant"):
            try:
                with st.spinner('Processando sua pergunta...'):
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=st.session_state.messages,
                        temperature=0.7,
                        max_tokens=600
                    )
                    assistant_response = response.choices[0].message.content
                    assistant_response = re.sub(r'\{.*?\}', '', assistant_response)
                    assistant_response = re.sub(r'\\[a-z]+', '', assistant_response)
                    formatted_response = format_response(assistant_response)
                    message_placeholder = st.empty()
                    full_response = ""
                    paragraphs = formatted_response.split('\n\n')
                    for paragraph in paragraphs:
                        if paragraph.strip():
                            full_response += paragraph + "\n\n"
                            message_placeholder.markdown(full_response + "▌", unsafe_allow_html=True)
                            time.sleep(0.2)
                    message_placeholder.markdown(full_response, unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": formatted_response})
            except Exception:
                error_msg = "⚠️ Ocorreu um erro ao processar sua pergunta. Por favor, tente novamente."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
