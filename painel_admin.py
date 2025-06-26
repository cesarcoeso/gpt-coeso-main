# painel_admin.py com integração ao Google Drive (compartilhado com main.py)

import streamlit as st
import sqlite3
import pandas as pd
import re
import bcrypt
from datetime import datetime, timedelta
import io
import plotly.express as px
from drive_utils import download_db_from_drive, upload_db_to_drive  # NOVO

DB_NAME = 'auth.db'

# === BANCO DE DADOS ===
def init_db():
    download_db_from_drive()  # NOVO
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tabela de usuários
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    senha TEXT,
                    created_at TIMESTAMP,
                    last_login TIMESTAMP
                )''')
    # Tabela de logs
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT,
                    acao TEXT,
                    timestamp TIMESTAMP
                )''')
    conn.commit()
    conn.close()

# === UTILITÁRIOS ===
def registrar_log(email, acao):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO logs (email, acao, timestamp) VALUES (?, ?, ?)", (email, acao, datetime.now()))
    conn.commit()
    conn.close()
    upload_db_to_drive()  # NOVO

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def user_exists(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE email=?", (email,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def register_user(email, senha):
    if not is_valid_email(email):
        return False, "E-mail inválido."
    if user_exists(email):
        return False, "E-mail já cadastrado."

    hashed = bcrypt.hashpw(senha.encode(), bcrypt.gensalt())

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now()
    c.execute("INSERT INTO users (email, senha, created_at, last_login) VALUES (?, ?, ?, ?)",
              (email, hashed, now, now))
    conn.commit()
    conn.close()

    registrar_log(email, "Cadastro")
    upload_db_to_drive()  # NOVO
    return True, "✅ Usuário cadastrado com sucesso."

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT email, created_at, last_login FROM users", conn)
    conn.close()
    return df

def delete_user(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE email=?", (email,))
    conn.commit()
    conn.close()
    registrar_log(email, "Remoção")
    upload_db_to_drive()  # NOVO

def get_all_emails():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT email FROM users")
    emails = [row[0] for row in c.fetchall()]
    conn.close()
    return emails

def get_table_structure():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("PRAGMA table_info(users)")
    columns = c.fetchall()
    conn.close()
    return pd.DataFrame(columns, columns=["cid", "name", "type", "notnull", "default_value", "pk"])

def get_logs():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM logs ORDER BY timestamp DESC", conn)
    conn.close()
    return df

def get_user_stats():
    conn = sqlite3.connect(DB_NAME)
    total_users = pd.read_sql_query("SELECT COUNT(*) as total FROM users", conn).iloc[0,0]
    total_logins = pd.read_sql_query("SELECT COUNT(*) as total FROM logs WHERE acao LIKE '%Login%'", conn).iloc[0,0]
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    logins_last_7_days = pd.read_sql_query(
        f"SELECT COUNT(*) as total FROM logs WHERE acao LIKE '%Login%' AND timestamp >= '{seven_days_ago}'",
        conn
    ).iloc[0,0]
    last_registered = pd.read_sql_query(
        "SELECT email, created_at FROM users ORDER BY created_at DESC LIMIT 5",
        conn
    )
    last_logins = pd.read_sql_query(
        "SELECT email, last_login FROM users ORDER BY last_login DESC LIMIT 5",
        conn
    )
    logins_by_day = pd.read_sql_query(
        f"""SELECT date(timestamp) as dia, COUNT(*) as total 
            FROM logs 
            WHERE acao LIKE '%Login%' AND timestamp >= '{seven_days_ago}'
            GROUP BY dia
            ORDER BY dia""",
        conn
    )
    conn.close()
    return {
        'total_users': total_users,
        'total_logins': total_logins,
        'logins_last_7_days': logins_last_7_days,
        'last_registered': last_registered,
        'last_logins': last_logins,
        'logins_by_day': logins_by_day
    }


# === AUTENTICAÇÃO ===
def autenticar_admin():
    st.sidebar.subheader("🔐 Login do Administrador")

    if 'admin_autenticado' not in st.session_state:
        st.session_state.admin_autenticado = False

    if not st.session_state.admin_autenticado:
        email_input = st.sidebar.text_input("E-mail", key="login_email")
        senha_input = st.sidebar.text_input("Senha", type="password", key="login_senha")
        if st.sidebar.button("Entrar"):
            email_ok = email_input == st.secrets["admin"]["email"]
            senha_ok = senha_input == st.secrets["admin"]["senha"]
            if email_ok and senha_ok:
                st.session_state.admin_autenticado = True
                st.success("Acesso autorizado!")
                registrar_log(email_input, "Login Admin")
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")
        st.stop()

# === INTERFACE ===
def main():
    st.set_page_config(page_title="Painel Administrativo - Coeso Cursos", layout="wide")
    autenticar_admin()

    st.sidebar.image("https://coesocursos.com.br/wp-content/uploads/2025/05/logo-e1738083192299.png", use_container_width=True)
    st.sidebar.title("Painel Administrativo")
    menu = st.sidebar.radio("Navegação", [
        "📊 Dashboard",
        "📅 Cadastro",
        "📋 Visualizar Usuários",
        "🚔 Remover Usuário",
        "📊 Estrutura do Banco",
        "🕵️ Log de Atividades"
    ])

    if st.sidebar.button("🚪 Sair"):
        st.session_state.admin_autenticado = False
        st.rerun()

    st.markdown("<h1 style='text-align: center;'>🧑‍💼 Gerenciamento de Usuários</h1>", unsafe_allow_html=True)
    st.divider()

    if menu == "📊 Dashboard":
        st.subheader("📊 Dashboard de Estatísticas")
        
        stats = get_user_stats()
        
        # Métricas principais
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Usuários", stats['total_users'])
        with col2:
            st.metric("Total de Logins", stats['total_logins'])
        with col3:
            st.metric("Logins últimos 7 dias", stats['logins_last_7_days'])
        
        st.divider()
        
        # Gráfico de logins por dia
        if not stats['logins_by_day'].empty:
            st.subheader("Logins por Dia (últimos 7 dias)")
            fig = px.bar(
                stats['logins_by_day'], 
                x='dia', 
                y='total',
                labels={'dia': 'Data', 'total': 'Logins'},
                color='total',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Botão para download
            csv = stats['logins_by_day'].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar dados de logins (CSV)",
                data=csv,
                file_name="logins_por_dia.csv",
                mime="text/csv"
            )
        
        st.divider()
        
        # Últimos cadastros e acessos
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Últimos Cadastros")
            if not stats['last_registered'].empty:
                st.dataframe(
                    stats['last_registered'].rename(columns={
                        'email': 'E-mail',
                        'created_at': 'Data de Cadastro'
                    }),
                    use_container_width=True
                )
            else:
                st.info("Nenhum usuário cadastrado recentemente.")
                
        with col2:
            st.subheader("Últimos Acessos")
            if not stats['last_logins'].empty:
                st.dataframe(
                    stats['last_logins'].rename(columns={
                        'email': 'E-mail',
                        'last_login': 'Último Acesso'
                    }),
                    use_container_width=True
                )
            else:
                st.info("Nenhum acesso registrado recentemente.")

    elif menu == "📅 Cadastro":
        st.subheader("Cadastrar Novo Usuário")
        email = st.text_input("Digite o e-mail:")
        senha = st.text_input("Digite a senha:", type="password")
        if st.button("Cadastrar"):
            if not email or not senha:
                st.warning("Preencha e-mail e senha.")
            else:
                success, msg = register_user(email, senha)
                st.success(msg) if success else st.error(msg)

    elif menu == "📋 Visualizar Usuários":
        st.subheader("Lista de Usuários Cadastrados")
        df = get_all_users()
        if df.empty:
            st.warning("Nenhum usuário cadastrado.")
        else:
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📂 Baixar CSV",
                data=csv,
                file_name="usuarios_coeso.csv",
                mime="text/csv",
                use_container_width=True
            )

    elif menu == "🚔 Remover Usuário":
        st.subheader("Remover Usuário")
        emails = get_all_emails()
        if not emails:
            st.warning("Nenhum usuário encontrado.")
        else:
            selected_email = st.selectbox("Selecione o e-mail a remover:", emails)
            if st.button("Remover"):
                delete_user(selected_email)
                st.success(f"Usuário {selected_email} removido com sucesso.")
                st.rerun()

    elif menu == "📊 Estrutura do Banco":
        st.subheader("Estrutura da Tabela `users`")
        estrutura = get_table_structure()
        st.dataframe(estrutura, use_container_width=True)

    elif menu == "🕵️ Log de Atividades":
        st.subheader("Histórico de Ações no Sistema")
        logs_df = get_logs()
        if logs_df.empty:
            st.info("Nenhum log registrado até agora.")
        else:
            st.dataframe(logs_df, use_container_width=True)

# === EXECUÇÃO ===
if __name__ == "__main__":
    init_db()
    main()
