import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import matplotlib.pyplot as plt
import google.generativeai as genai
from github import Github
import os
from io import BytesIO, StringIO

# --- Page Configuration ---
st.set_page_config(page_title="Data Analysis ToolBot", page_icon="📊", layout="wide")

# --- Sidebar: Configuration & API Keys ---
with st.sidebar:
    st.title("⚙️ Settings")
    st.markdown("---")
    
    # Gemini API Key
    gemini_key = st.text_input("Google Gemini API Key", type="password", help="Get it from https://aistudio.google.com/app/apikey")
    if gemini_key:
        genai.configure(api_key=gemini_key)
    
    # GitHub Token
    github_token = st.text_input("GitHub Token", type="password", help="Enter your GitHub Personal Access Token")
    repo_name = st.text_input("GitHub Repository", value="BhairavJShah/data-analysis-toolbot")
    
    st.markdown("---")
    st.info("Uploaded data and reports will be saved to your GitHub repo.")

# --- Main App Interface ---
st.title("📊 Data Analysis ToolBot")
st.markdown("Upload your data, visualize it, and chat with AI to get insights.")

uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file:
    # Read Data
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.success(f"Successfully loaded: {uploaded_file.name}")
        
        # --- Tabs for different sections ---
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Data Preview", "📈 Visualization", "🧪 Statistics", "🤖 AI ChatBot"])
        
        with tab1:
            st.subheader("Raw Data Preview")
            st.dataframe(df.head(20))
            st.write(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
            
            if st.button("🚀 Push Raw Data to GitHub"):
                if github_token and repo_name:
                    try:
                        g = Github(github_token)
                        repo = g.get_repo(repo_name)
                        content = df.to_csv(index=False)
                        path = f"data/{uploaded_file.name}"
                        repo.create_file(path, f"Upload {uploaded_file.name}", content, branch="main")
                        st.success(f"Pushed to {repo_name}/{path}")
                    except Exception as e:
                        st.error(f"GitHub Error: {e}")
                else:
                    st.warning("Please provide GitHub Token and Repo Name in Settings.")

        with tab2:
            st.subheader("Interactive Visualizations")
            col1, col2 = st.columns([1, 3])
            
            with col1:
                chart_type = st.selectbox("Select Chart Type", ["Bar", "Line", "Scatter", "Histogram", "Box Plot"])
                x_axis = st.selectbox("Select X-axis", df.columns)
                y_axis = st.selectbox("Select Y-axis", df.columns)
                color_var = st.selectbox("Color by (Optional)", [None] + list(df.columns))
            
            with col2:
                if chart_type == "Bar":
                    fig = px.bar(df, x=x_axis, y=y_axis, color=color_var, title=f"{y_axis} by {x_axis}")
                elif chart_type == "Line":
                    fig = px.line(df, x=x_axis, y=y_axis, color=color_var, title=f"{y_axis} trend over {x_axis}")
                elif chart_type == "Scatter":
                    fig = px.scatter(df, x=x_axis, y=y_axis, color=color_var, title=f"{x_axis} vs {y_axis}")
                elif chart_type == "Histogram":
                    fig = px.histogram(df, x=x_axis, title=f"Distribution of {x_axis}")
                elif chart_type == "Box Plot":
                    fig = px.box(df, x=x_axis, y=y_axis, title=f"Spread of {y_axis} by {x_axis}")
                
                st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.subheader("Statistical Summary")
            st.write(df.describe())
            
            st.subheader("Correlation Heatmap")
            numeric_df = df.select_dtypes(include=[np.number])
            if not numeric_df.empty:
                corr = numeric_df.corr()
                fig_corr = px.imshow(corr, text_auto=True, aspect="auto", title="Feature Correlation")
                st.plotly_chart(fig_corr, use_container_width=True)
            else:
                st.info("No numeric columns found for correlation.")

        with tab4:
            st.subheader("🤖 Chat with your Data")
            if not gemini_key:
                st.warning("Please enter your Gemini API Key in the sidebar to use the AI features.")
            else:
                user_question = st.text_input("Ask a question about your data (e.g., 'What are the main trends?', 'Are there any outliers?')")
                
                if user_question:
                    with st.spinner("AI is analyzing..."):
                        # Prepare data summary for Gemini
                        data_summary = f"""
                        Dataset Summary:
                        Columns: {list(df.columns)}
                        Shape: {df.shape}
                        Statistical Description:
                        {df.describe().to_string()}
                        
                        Top 5 rows:
                        {df.head().to_string()}
                        
                        User Question: {user_question}
                        """
                        
                        try:
                            model = genai.GenerativeModel('gemini-2.0-flash-lite')
                            response = model.generate_content(data_summary)
                            st.markdown("### AI Insight:")
                            st.write(response.text)
                            
                            # Option to save insight
                            if st.button("💾 Save AI Insight to GitHub"):
                                if github_token and repo_name:
                                    g = Github(github_token)
                                    repo = g.get_repo(repo_name)
                                    report_content = f"Question: {user_question}\n\nAI Insight:\n{response.text}"
                                    report_path = f"reports/insight_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt"
                                    repo.create_file(report_path, "Save AI Insight", report_content, branch="main")
                                    st.success(f"Report saved to GitHub: {report_path}")
                        except Exception as e:
                            st.error(f"AI Error: {e}")

    except Exception as e:
        st.error(f"Error processing file: {e}")

else:
    st.info("👆 Please upload a CSV or Excel file to begin analysis.")
    
    # Sample data generator for testing
    if st.checkbox("Use Sample Data"):
        sample_df = pd.DataFrame({
            'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'Sales': [100, 150, 120, 200, 180, 250],
            'Expenses': [80, 90, 85, 110, 100, 130],
            'Profit': [20, 60, 35, 90, 80, 120]
        })
        st.write("Using sample data:")
        st.dataframe(sample_df)
        st.session_state['df'] = sample_df # This is just a hint, Streamlit usually needs fresh load or session state
