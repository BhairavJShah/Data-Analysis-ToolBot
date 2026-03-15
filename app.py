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

# --- Load Environment Variables (Support for Local .env and Streamlit Cloud Secrets) ---
load_dotenv()
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
except:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_REPO = os.getenv("GITHUB_REPO")

# --- Page Configuration ---
st.set_page_config(page_title="Data Analysis ToolBot Pro", page_icon="🤖", layout="wide")

# --- Session State Initialization ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None

# --- Custom CSS ---
st.markdown("""
    <style>
    /* Professional Dark Cards for Metrics */
    [data-testid="stMetric"] {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-size: 1.8rem !important;
    }
    .main { background-color: #0f172a; }
    section[data-testid="stSidebar"] { background-color: #1e293b; border-right: 1px solid #334155; }
    </style>
    """, unsafe_allow_html=True)

# --- GitHub Logic ---
def get_repo():
    if not GITHUB_TOKEN:
        st.error("Missing GITHUB_TOKEN. Please add it to Streamlit Secrets.")
        return None
    if not GITHUB_REPO:
        st.error("Missing GITHUB_REPO. Please add it to Streamlit Secrets.")
        return None
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        # Force a small call to verify connectivity
        _ = repo.full_name
        return repo
    except Exception as e: 
        st.error(f"GitHub API Error: {e}")
        return None

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
        return True
    except Exception as e: 
        st.error(f"DB Error: {e}")
        return False

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
        return

    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        u = st.text_input("Username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        force_login = st.checkbox("Force Login (If you are stuck)")
        
        if st.button("Login"):
            db = get_user_db(repo)
            if u in db and db[u] == hash_password(p):
                is_locked, sid = check_lock(repo, u)
                if is_locked and not force_login:
                    st.error(f"User '{u}' is already logged in elsewhere!")
                    st.info("Check 'Force Login' above if you closed your previous window.")
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
                    if save_user_db(repo, db):
                        st.success("Registration Successful! Please Login.")
                    else:
                        st.error("Failed to save user to Cloud. Check GitHub permissions.")

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
    # 1. Check for File Upload (Priority 1)
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

    # 2. Check for History Selection (Priority 2)
    elif sel != "None":
        f = repo.get_contents(f"users/{user}/data/{sel}")
        df = pd.read_csv(StringIO(f.decoded_content.decode()))
        st.info(f"📂 Currently viewing: **{sel}** (Loaded from History)")

    # 3. Check for Sample Data (Priority 3 - only if no user data)
    elif use_sample:
        # Detailed Sample Data Generator
        @st.cache_data
        def get_sample_data():
            return pd.DataFrame({
                'Date': pd.date_range(start='2024-01-01', periods=50, freq='D'),
                'Category': ['Electronics', 'Clothing', 'Home', 'Beauty', 'Toys'] * 10,
                'Sales': np.random.randint(100, 1000, 50),
                'Expenses': np.random.randint(50, 600, 50),
                'Units_Sold': np.random.randint(1, 100, 50)
            })
        df = get_sample_data()
        st.info("💡 Currently viewing **Detailed Sample Data**.")

    if df is not None:
        # 1. KEY OVERVIEW
        st.markdown("### 📌 Key Overview")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Rows", df.shape[0])
        m2.metric("Total Columns", df.shape[1])
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        m3.metric("Numeric Fields", len(numeric_cols))
        m4.metric("Missing Values", df.isnull().sum().sum())

        st.markdown("---")

        # 2. DATA & STATS SECTION
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.subheader("📋 Data Preview")
            st.dataframe(df, use_container_width=True)
            
        with col_right:
            st.subheader("🧪 Statistics (Mean, Median, etc.)")
            if not numeric_cols.empty:
                target_col = st.selectbox("Select Column for Deep Stats", numeric_cols)
                
                stats_cols = st.columns(2)
                stats_cols[0].write(f"**Mean:**")
                stats_cols[1].write(f"`{df[target_col].mean():,.2f}`")
                
                stats_cols[0].write(f"**Median:**")
                stats_cols[1].write(f"`{df[target_col].median():,.2f}`")
                
                stats_cols[0].write(f"**Mode:**")
                mode_val = df[target_col].mode()
                stats_cols[1].write(f"`{mode_val[0]:,.2f}`" if not mode_val.empty else "`N/A`")
                
                stats_cols[0].write(f"**Std Dev:**")
                stats_cols[1].write(f"`{df[target_col].std():,.2f}`")
                
                stats_cols[0].write(f"**Min/Max:**")
                stats_cols[1].write(f"`{df[target_col].min():,.1f} / {df[target_col].max():,.1f}`")
            else:
                st.info("No numeric data found.")

        st.markdown("---")

        # 3. VISUALIZATION CENTER
        st.subheader("📈 Visualization Center")
        v_col1, v_col2 = st.columns([1, 2.5])

        with v_col1:
            v_type = st.selectbox("Chart Type", ["Bar Chart", "Line Graph", "Scatter Plot", "Box Plot", "Histogram"])
            x_ax = st.selectbox("X-Axis", df.columns)
            y_ax = st.selectbox("Y-Axis", numeric_cols if not numeric_cols.empty else df.columns)
            color_by = st.selectbox("Color Group", [None] + list(df.columns))

        with v_col2:
            if v_type == "Bar Chart":
                fig = px.bar(df, x=x_ax, y=y_ax, color=color_by, barmode='group', template="plotly_dark")
            elif v_type == "Line Graph":
                fig = px.line(df, x=x_ax, y=y_ax, color=color_by, template="plotly_dark")
            elif v_type == "Scatter Plot":
                fig = px.scatter(df, x=x_ax, y=y_ax, color=color_by, template="plotly_dark")
            elif v_type == "Box Plot":
                fig = px.box(df, x=x_ax, y=y_ax, color=color_by, template="plotly_dark")
            else:
                fig = px.histogram(df, x=x_ax, color=color_by, template="plotly_dark")
            
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # 4. AI INSIGHTS BOT
        st.subheader("🤖 AI ToolBot Assistant")
        if not gemini_key:
            st.warning("⚠️ Enter your Gemini API Key in the sidebar to activate the AI ChatBot.")
        else:
            user_msg = st.text_input("Ask about this data:", placeholder="e.g. 'What are the main trends here?'")
            if user_msg:
                with st.spinner("🤖 AI is thinking..."):
                    prompt = f"""Analyze this data: {df.describe().to_string()}\n\nQuestion: {user_msg}"""
                    model = genai.GenerativeModel('gemini-2.0-flash-lite')
                    response = model.generate_content(prompt)
                    st.write(response.text)

# --- Logic Router ---
if not st.session_state.authenticated:
    auth_page()
else:
    main_dashboard()
