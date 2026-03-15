import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import os

# --- Page Configuration ---
st.set_page_config(page_title="Data Analysis ToolBot", page_icon="🤖", layout="wide")

# --- Custom CSS for Dark Professional Dashboard ---
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
    /* Main Background */
    .main {
        background-color: #0f172a;
    }
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #1e293b;
        border-right: 1px solid #334155;
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
    st.subheader("🛠️ Options")
    use_sample = st.checkbox("Load Sample Data", value=False)

# --- Header ---
st.title("📊 Data Analysis ToolBot")
st.markdown("Upload your dataset to begin your professional analysis.")

# --- Data Loading Logic ---
uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

# Sample Data Generator
@st.cache_data
def get_sample_data():
    return pd.DataFrame({
        'Date': pd.date_range(start='2024-01-01', periods=50, freq='D'),
        'Category': ['Electronics', 'Clothing', 'Home', 'Beauty', 'Toys'] * 10,
        'Sales': np.random.randint(100, 1000, 50),
        'Expenses': np.random.randint(50, 600, 50),
        'Units_Sold': np.random.randint(1, 100, 50)
    })

df = None

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
elif use_sample:
    df = get_sample_data()
    st.info("💡 Currently viewing **Sample Data**.")

# --- THE DASHBOARD ---
if df is not None:
    # 1. KEY OVERVIEW (Fixed Colors)
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
        
    with col_right:
        st.subheader("🧪 Statistical Deep-Dive")
        if not numeric_cols.empty:
            target_col = st.selectbox("Select Column", numeric_cols)
            
            # Detailed Statistics calculation
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

else:
    st.info("👆 Please upload a file to start or check 'Load Sample Data' in the sidebar.")

st.markdown("---")
st.caption("Data Analysis ToolBot v1.1 | Professional Mode")
