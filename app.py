import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import google.generativeai as genai
from github import Github
from dotenv import load_dotenv
import os
import hashlib
import json
from datetime import datetime, timedelta
from io import StringIO

# --- Load Environment Variables ---
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

# --- Page Configuration ---
st.set_page_config(page_title="Data Analysis ToolBot", page_icon="🤖", layout="wide")

# --- Session State Initialization ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None

# --- Custom CSS ---
st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #334155;
    }
    .main { background-color: #0f172a; }
    section[data-testid="stSidebar"] { background-color: #1e293b; border-right: 1px solid #334155; }
    </style>
    """, unsafe_allow_html=True)

# --- GitHub Logic ---
def get_repo():
    try:
        g = Github(GITHUB_TOKEN)
        return g.get_repo(GITHUB_REPO)
    except: return None

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def get_user_db(repo):
    try:
        content = repo.get_contents("users/users.json")
        return json.loads(content.decoded_content.decode())
    except:
        return {}

def save_user_db(repo, db):
    try:
        path = "users/users.json"
        content = json.dumps(db)
        try:
            file = repo.get_contents(path)
            repo.update_file(path, "Update user DB", content, file.sha)
        except:
            repo.create_file(path, "Create user DB", content)
    except Exception as e: st.error(f"DB Error: {e}")

# --- Concurrency Lock Logic ---
def check_lock(repo, username):
    path = f"users/{username}/lock.json"
    try:
        content = repo.get_contents(path)
        data = json.loads(content.decoded_content.decode())
        last_active = datetime.fromisoformat(data['last_active'])
        # If active in the last 2 minutes, it's locked
        if datetime.now() - last_active < timedelta(minutes=2):
            return True, data['session_id']
    except: pass
    return False, None

def update_lock(repo, username):
    path = f"users/{username}/lock.json"
    session_id = st.session_state.get('session_id', str(np.random.randint(1000, 9999)))
    st.session_state.session_id = session_id
    data = json.dumps({"last_active": datetime.now().isoformat(), "session_id": session_id})
    try:
        file = repo.get_contents(path)
        repo.update_file(path, "Heartbeat", data, file.sha)
    except:
        repo.create_file(path, "Create Lock", data)

# --- Auth UI ---
def auth_page():
    st.title("🔐 Data Analysis ToolBot Login")
    repo = get_repo()
    if not repo:
        st.error("GitHub Connection Failed. Check your Token.")
        return

    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("Login"):
            db = get_user_db(repo)
            if u in db and db[u] == hash_password(p):
                is_locked, sid = check_lock(repo, u)
                if is_locked:
                    st.error(f"User '{u}' is already logged in elsewhere!")
                else:
                    st.session_state.authenticated = True
                    st.session_state.username = u
                    update_lock(repo, u)
                    st.rerun()
            else: st.error("Invalid Credentials")

    with tab2:
        nu = st.text_input("New Username", key="reg_u")
        np1 = st.text_input("New Password", type="password", key="reg_p1")
        np2 = st.text_input("Confirm Password", type="password", key="reg_p2")
        if st.button("Register"):
            if np1 != np2: st.error("Passwords do not match")
            elif len(np1) < 6: st.error("Password too short")
            else:
                db = get_user_db(repo)
                if nu in db: st.error("Username already exists")
                else:
                    db[nu] = hash_password(np1)
                    save_user_db(repo, db)
                    st.success("Registration Successful! Please Login.")

# --- Main Dashboard ---
def main_dashboard():
    repo = get_repo()
    user = st.session_state.username
    
    # Update heartbeat lock
    update_lock(repo, user)

    with st.sidebar:
        st.title(f"👋 Hi, {user}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
        st.markdown("---")
        
        # User-specific history
        st.subheader("📂 My Data History")
        try:
            contents = repo.get_contents(f"users/{user}/data")
            files = [c.name for c in contents if c.name.endswith('.csv')]
            sel = st.selectbox("Reload My Data", ["None"] + files)
        except: sel = "None"
        
        st.markdown("---")
        gemini_key = st.text_input("Gemini API Key", type="password")
        if gemini_key: genai.configure(api_key=gemini_key)
        use_sample = st.checkbox("Load Sample Data")

    st.title("📊 Data Analysis ToolBot")
    
    df = None
    up = st.file_uploader("Upload CSV", type=["csv"])
    
    if up:
        df = pd.read_csv(up)
        # Save to user-specific folder
        path = f"users/{user}/data/{up.name}"
        csv = df.to_csv(index=False)
        try:
            f = repo.get_contents(path)
            repo.update_file(path, "Update", csv, f.sha)
        except:
            repo.create_file(path, "Upload", csv)
        st.success(f"Saved to your private folder: {path}")
    elif sel != "None":
        f = repo.get_contents(f"users/{user}/data/{sel}")
        df = pd.read_csv(StringIO(f.decoded_content.decode()))
    elif use_sample:
        df = pd.DataFrame({'Date': pd.date_range('2024-01-01', periods=10), 'Sales': np.random.randint(100, 500, 10)})

    if df is not None:
        st.markdown("### 📌 Key Overview")
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows", df.shape[0])
        c2.metric("Cols", df.shape[1])
        c3.metric("Numeric", len(df.select_dtypes(include=[np.number]).columns))
        
        st.subheader("📈 Visualization")
        x = st.selectbox("X", df.columns)
        y = st.selectbox("Y", df.select_dtypes(include=[np.number]).columns)
        st.plotly_chart(px.line(df, x=x, y=y, template="plotly_dark"), use_container_width=True)

        st.subheader("🤖 AI Chat")
        if not gemini_key: st.warning("Enter Gemini Key in Sidebar")
        else:
            msg = st.text_input("Ask about data:")
            if msg:
                model = genai.GenerativeModel('gemini-2.0-flash-lite')
                resp = model.generate_content(f"Analyze: {df.describe().to_string()}\n\nQuestion: {msg}")
                st.write(resp.text)

# --- Logic Router ---
if not st.session_state.authenticated:
    auth_page()
else:
    main_dashboard()
