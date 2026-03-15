import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from github import Github
import os

# --- Page Configuration ---
st.set_page_config(page_title="All-In-One Data ToolBot", page_icon="🤖", layout="wide")

# --- Custom CSS for a Clean Dashboard Look ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    section[data-testid="stSidebar"] {
        background-color: #1e293b;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar: Configuration ---
with st.sidebar:
    st.title("🤖 ToolBot Config")
    st.markdown("---")
    
    # Gemini API Key Section
    st.subheader("🔑 AI Connection")
    gemini_key = st.text_input("Gemini API Key", type="password")
    if not gemini_key:
        st.info("💡 [Get a FREE API Key here](https://aistudio.google.com/app/apikey)")
    else:
        genai.configure(api_key=gemini_key)
    
    st.markdown("---")
    st.subheader("📁 GitHub Backup")
    github_token = st.text_input("GitHub Token", type="password")
    repo_name = st.text_input("Repository", value="BhairavJShah/Data-Analysis-ToolBot")

# --- Header ---
st.title("📊 Data Analysis ToolBot: All-In-One Dashboard")
st.markdown("Upload your dataset or use the sample data below to start your analysis.")

# --- Data Loading Logic ---
uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

# Sample Data Generator
@st.cache_data
def get_sample_data():
    return pd.DataFrame({
        'Date': pd.date_range(start='2024-01-01', periods=20, freq='D'),
        'Category': ['Electronics', 'Clothing', 'Home', 'Electronics', 'Clothing'] * 4,
        'Sales': np.random.randint(100, 1000, 20),
        'Expenses': np.random.randint(50, 500, 20),
        'Units_Sold': np.random.randint(1, 50, 20)
    })

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
else:
    st.warning("No file uploaded. Using **Sample Data** for demonstration.")
    df = get_sample_data()

# --- THE DASHBOARD ---

# 1. KEY METRICS ROW
st.markdown("### 📌 Key Overview")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Rows", df.shape[0])
m2.metric("Total Columns", df.shape[1])
numeric_cols = df.select_dtypes(include=[np.number]).columns
m3.metric("Numeric Fields", len(numeric_cols))
m4.metric("Missing Values", df.isnull().sum().sum())

st.markdown("---")

# 2. DATA & STATS SECTION (Side by Side)
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📋 Data Preview")
    st.dataframe(df.head(10), use_container_width=True)
    
    if st.button("🚀 Push this Data to GitHub"):
        if github_token and repo_name:
            try:
                g = Github(github_token)
                repo = g.get_repo(repo_name)
                content = df.to_csv(index=False)
                repo.create_file(f"data/upload_{pd.Timestamp.now().strftime('%Y%m%d')}.csv", "Auto Upload", content)
                st.success("Successfully backed up to GitHub!")
            except Exception as e: st.error(f"Error: {e}")
        else: st.warning("Add GitHub credentials in the sidebar.")

with col_right:
    st.subheader("🧪 Statistics (Mean, Median, etc.)")
    if not numeric_cols.empty:
        target_col = st.selectbox("Select Column for Deep Stats", numeric_cols)
        stats = {
            "Mean": df[target_col].mean(),
            "Median": df[target_col].median(),
            "Mode": df[target_col].mode()[0] if not df[target_col].mode().empty else "N/A",
            "Std Dev": df[target_col].std(),
            "Min": df[target_col].min(),
            "Max": df[target_col].max()
        }
        for label, val in stats.items():
            st.write(f"**{label}:** `{val:,.2f}`" if isinstance(val, (int, float)) else f"**{label}:** `{val}`")
    else:
        st.info("No numeric data found.")

st.markdown("---")

# 3. VISUALIZATION CENTER
st.subheader("📈 Visualization Center")
v_col1, v_col2 = st.columns([1, 2])

with v_col1:
    v_type = st.radio("Chart Type", ["Bar Chart", "Line Graph", "Scatter Plot", "Box Plot", "Histogram"])
    x_ax = st.selectbox("X-Axis", df.columns)
    y_ax = st.selectbox("Y-Axis", numeric_cols if not numeric_cols.empty else df.columns)
    color_by = st.selectbox("Group By", [None] + list(df.columns))

with v_col2:
    if v_type == "Bar Chart":
        fig = px.bar(df, x=x_ax, y=y_ax, color=color_by, barmode='group', template="plotly_white")
    elif v_type == "Line Graph":
        fig = px.line(df, x=x_ax, y=y_ax, color=color_by, template="plotly_white")
    elif v_type == "Scatter Plot":
        fig = px.scatter(df, x=x_ax, y=y_ax, color=color_by, template="plotly_white")
    elif v_type == "Box Plot":
        fig = px.box(df, x=x_ax, y=y_ax, color=color_by, template="plotly_white")
    else:
        fig = px.histogram(df, x=x_ax, color=color_by, template="plotly_white")
    
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 4. AI INSIGHTS BOT
st.subheader("🤖 AI ToolBot Assistant")
if not gemini_key:
    st.warning("⚠️ Enter your Gemini API Key in the sidebar to activate the AI ChatBot (It's free!).")
else:
    chat_col1, chat_col2 = st.columns([2, 1])
    
    with chat_col1:
        user_msg = st.text_input("Ask anything about this data:", placeholder="e.g. 'What are the main trends here?' or 'Which category is performing best?'")
        if user_msg:
            with st.spinner("🤖 Analyzing data..."):
                prompt = f"""
                You are a Data Scientist. Analyze this data:
                Columns: {list(df.columns)}
                Stats: {df.describe().to_string()}
                Sample: {df.head(3).to_string()}
                
                Question: {user_msg}
                """
                model = genai.GenerativeModel('gemini-2.0-flash-lite')
                response = model.generate_content(prompt)
                st.markdown("**AI Response:**")
                st.write(response.text)
                
                if st.button("💾 Save this AI Report to GitHub"):
                    try:
                        g = Github(github_token)
                        repo = g.get_repo(repo_name)
                        repo.create_file(f"reports/ai_report_{pd.Timestamp.now().strftime('%H%M%S')}.md", "AI Report", f"# AI Data Report\n\n**Query:** {user_msg}\n\n**Response:**\n{response.text}")
                        st.success("Report saved!")
                    except: st.error("Check GitHub credentials.")

    with chat_col2:
        st.markdown("""
        **Try these questions:**
        1. Summarize the key findings.
        2. Are there any unusual outliers?
        3. Suggest 3 ways to improve these numbers.
        """)

st.markdown("---")
st.caption("Data Analysis ToolBot v1.0 | Created with Streamlit and Gemini AI")
