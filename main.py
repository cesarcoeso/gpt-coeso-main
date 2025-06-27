# main.py otimizado com SYSTEM_PROMPT e CSS externos

import streamlit as st
from openai import OpenAI
import time
import re
import sqlite3
import bcrypt
from datetime import datetime
from drive_utils import download_db_from_drive, upload_db_to_drive  # NOVO
from config_prompt import SYSTEM_PROMPT  # AGORA EXTERNO
import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# === CONFIG PÁGINA ===
st.set_page_config(
    page_title="Assistente Excel - Coeso Cursos",
    page_icon="https://coesocursos.com.br/wp-content/uploads/2025/05/cropped-favicon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

download_db_from_drive()  # NOVO

# === CSS EXTERNO ===
with open("custom_style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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

# === TELA DE LOGIN ===
def login_screen():
    with st.container():
        st.markdown("""
        <div style="text-align: center; margin-bottom: 1rem;">
            <img src="https://coesocursos.com.br/wp-content/uploads/2025/05/logo-e1738083192299.png" 
                 alt="Logo Coeso Cursos" style="max-width: 300px; width: 100%;">
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            "<h2 style='text-align: center; color: #122a29;'>🔒 Acesso ao Assistente de Excel - Exclusivo para Alunos da Coeso Cursos</h2>",
            unsafe_allow_html=True
        )

        email = st.text_input("Digite seu e-mail:")
        senha = st.text_input("Digite sua senha:", type="password")

        if st.button("Acessar"):
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

# === INTERFACE ===
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

st.sidebar.markdown(f"<div style='color: white;'>**Usuário:** {st.session_state['user_email']}</div>", unsafe_allow_html=True)
with st.sidebar:
    st.image("https://coesocursos.com.br/wp-content/uploads/2025/05/logo-e1738083192299.png", width=250)
    st.markdown("""
    ### ℹ️ Como usar:
    - Pergunte sobre fórmulas, cálculos e planilhas
    - Exemplos:
      - `Como calcular área de laje?`
      - `Fórmula para previsão de materiais`
      - `Como usar PROCV em orçamentos?`
    
    🛠️ **Dicas técnicas:**
    - Todas as fórmulas em português
    - Exemplos práticos incluídos

    📌 **Como usar as fórmulas:**
    - As fórmulas do item **3** da resposta podem ser copiadas direto para o Excel
    - Cole na célula **B4**
    - Preencha os dados em **B2** (diâmetro em metros) e **C2** (altura em metros)
    """)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🪟 Limpar Conversa"):
            st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            st.rerun()
    with col2:
        if st.button("🚪 Sair"):
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
    text = re.sub(r'\{.*?\}', '', text)
    text = re.sub(r'\\[a-z]+', '', text)
    sections = re.split(r'(\d+\.)', text)
    formatted = ""
    for i in range(1, len(sections), 2):
        num = sections[i].replace('.', '')
        content = sections[i+1].strip()
        if num == '1':
            formatted += f"**1. Explicação técnica breve**\n\n{content}\n\n"
        elif num == '2':
            formatted += f"**2. Fórmula matemática clara**\n\n{content}\n\n"
        elif num == '3':
            content = re.sub(r'`(.*?)`', r'`\1`', content)
            formatted += f"**3. Fórmula Excel aplicável**\n\n{content}\n\n"
        elif num == '4':
            formatted += f"**4. Exemplo numérico completo**\n\n{content}\n\n"
    return formatted.strip()

def limit_history(messages, max=10):
    if len(messages) > max + 1:
        return [messages[0]] + messages[-max:]
    return messages

for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

if prompt := st.chat_input("Digite sua dúvida sobre Excel para construção civil..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages = limit_history(st.session_state.messages)

    with st.chat_message("assistant"):
        try:
            with st.spinner('Processando sua pergunta...'):
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=st.session_state.messages,
                    temperature=0.7,
                    max_tokens=600
                )
                content = response.choices[0].message.content
                content = re.sub(r'\{.*?\}', '', content)
                content = re.sub(r'\\[a-z]+', '', content)
                formatted = format_response(content)
                msg_box = st.empty()
                full_resp = ""
                for para in formatted.split('\n\n'):
                    if para.strip():
                        full_resp += para + "\n\n"
                        msg_box.markdown(full_resp + "▌", unsafe_allow_html=True)
                        time.sleep(0.2)
                msg_box.markdown(full_resp, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": formatted})
        except Exception:
            err = "⚠️ Ocorreu um erro ao processar sua pergunta. Por favor, tente novamente."
            st.error(err)
            st.session_state.messages.append({"role": "assistant", "content": err})
