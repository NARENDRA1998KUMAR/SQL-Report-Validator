SQL Report Validator – AI Enhanced

A lightweight Streamlit-based tool to validate SQL report outputs (CSV) and identify common data quality issues before dashboards or stakeholder reporting.

This app also includes an AI-powered analyst assistant to explain issues and suggest next steps.

**What This Tool Checks**

Duplicate rows

Primary key violations

Join inflation risk

Missing (null) values

Negative values in numeric fields

Aggregation mismatches (Quantity × Price vs Revenue)

**🤖 AI-Powered Q&A
**
Ask natural language questions about the uploaded report, such as:

Why is revenue mismatching?

Is there join inflation risk in this report?

What should I fix before sharing this data?

The AI answers strictly based on the uploaded report and validation results.

**🛠 Tech Stack**

Python

Streamlit

Pandas

OpenAI API (gpt-4o-mini)

**▶️ How to Run Locally**

Install dependencies:

pip install streamlit pandas openai


Add your OpenAI API key:

.streamlit/secrets.toml
OPENAI_API_KEY = "sk-..."


Run the app:

streamlit run streamlit_app.py

**🌐 Deployment**

The app can be deployed on Streamlit Cloud.
Add the OpenAI API key via App → Settings → Secrets.

**🎯 Who This Is For
**
Data Analysts

BI / Analytics Engineers

Anyone validating SQL-based reports before publishing

**🚀 Status**

MVP – actively improving

Built to demonstrate real-world data validation, debugging, and AI-assisted analysis.

Add screenshots / demo section

Just tell me what you want next
