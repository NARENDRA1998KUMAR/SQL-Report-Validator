import streamlit as st
import pandas as pd
import os
from openai import OpenAI
from pandas.errors import EmptyDataError

# =====================================================
# OPENAI API KEY – SINGLE SOURCE OF TRUTH
# =====================================================
def get_openai_api_key():
    """
    Works in ALL environments:
    - Local (via .streamlit/secrets.toml)
    - Streamlit Cloud (via Secrets UI)
    - Fallback to env var
    Never throws.
    """
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

    return os.getenv("OPENAI_API_KEY")


# =====================================================
# UX EXPLANATION HELPER
# =====================================================
def explain(check, severity):
    messages = {
        "duplicates": {
            "PASS": (
                "No duplicate rows detected.",
                "Duplicate rows usually occur due to incorrect joins.",
                "No action needed."
            ),
            "WARNING": (
                "Duplicate rows found in the report.",
                "Often caused by joins that multiply rows.",
                "Review joins and aggregation grain."
            )
        },
        "pk_duplicates": {
            "PASS": (
                "Primary key is unique.",
                "Uniqueness indicates correct data grain.",
                "No action needed."
            ),
            "WARNING": (
                "Primary key contains duplicate values.",
                "Likely one-to-many joins without pre-aggregation.",
                "Check join keys and table grain."
            )
        },
        "aggregation": {
            "PASS": (
                "Reported revenue matches calculated revenue.",
                "Aggregation logic appears correct.",
                "No action needed."
            ),
            "FAIL": (
                "Reported revenue does not match calculated revenue.",
                "Usually caused by join duplication or wrong formulas.",
                "Validate joins and aggregation logic."
            )
        },
        "join_risk": {
            "LOW": (
                "Low risk of join inflation.",
                "Row count aligns with primary key uniqueness.",
                "No action needed."
            ),
            "MEDIUM": (
                "Moderate risk of join inflation.",
                "Some duplication exists at the key level.",
                "Review joins to many-side tables."
            ),
            "HIGH": (
                "High risk of join inflation.",
                "Primary keys repeat many times, inflating totals.",
                "Pre-aggregate before joins or fix join conditions."
            )
        }
    }
    return messages[check][severity]


# =====================================================
# GPT CONTEXT BUILDER
# =====================================================
def build_gpt_context(
    df,
    duplicate_count,
    pk_duplicate_count,
    null_columns,
    negative_columns,
    agg_status,
    join_risk_status
):
    return f"""
This document is a SQL report exported as CSV.

Dataset overview:
- Rows: {df.shape[0]}
- Columns: {df.shape[1]}

Validation findings:
- Duplicate rows: {duplicate_count}
- Primary key duplicates: {pk_duplicate_count}
- Columns with nulls: {', '.join(null_columns) if null_columns else 'None'}
- Columns with negative values: {', '.join(negative_columns) if negative_columns else 'None'}
- Aggregation sanity status: {agg_status}
- Join inflation risk: {join_risk_status}

Answer strictly using this information.
If unsure, say so clearly.
"""


# =====================================================
# APP UI
# =====================================================
st.title("SQL Report Validator – AI Enhanced MVP")

uploaded_file = st.file_uploader(
    "Upload SQL CSV file",
    type=["csv"]
)

if uploaded_file is None:
    st.info("Please upload a CSV file to begin.")
    st.stop()

# -----------------------------
# SAFE CSV READ
# -----------------------------
try:
    uploaded_file.seek(0)
    df = pd.read_csv(uploaded_file)
except EmptyDataError:
    st.error("Uploaded CSV is empty or invalid.")
    st.stop()

total_rows = df.shape[0]

# -----------------------------
# BASIC INFO
# -----------------------------
st.subheader("Basic File Information")
st.write("Rows:", total_rows)
st.write("Columns:", df.shape[1])
st.dataframe(df.head())

# -----------------------------
# ENTIRE ROW DUPLICATES
# -----------------------------
duplicate_count = df.duplicated().sum()
dup_status = "PASS" if duplicate_count == 0 else "WARNING"
plain, tech, action = explain("duplicates", dup_status)

st.subheader("Entire Row Duplicate Check")
if dup_status == "PASS":
    st.success(plain)
else:
    st.warning(plain)

with st.expander("Why this happens (technical)"):
    st.write(tech)
with st.expander("What to do next"):
    st.write(action)

# -----------------------------
# PRIMARY KEY DUPLICATES
# -----------------------------
st.subheader("Primary Key Duplicate Check")
primary_key = st.selectbox(
    "Select a column that should be unique",
    df.columns
)

pk_duplicate_count = df[primary_key].duplicated().sum()
pk_status = "PASS" if pk_duplicate_count == 0 else "WARNING"
plain, tech, action = explain("pk_duplicates", pk_status)

if pk_status == "PASS":
    st.success(plain)
else:
    st.warning(plain)

# -----------------------------
# JOIN INFLATION RISK
# -----------------------------
unique_keys = df[primary_key].nunique()
duplication_ratio = (
    round(total_rows / unique_keys, 2)
    if unique_keys > 0 else None
)

if duplication_ratio is not None:
    if duplication_ratio <= 1.05:
        join_risk_status = "LOW"
    elif duplication_ratio <= 2:
        join_risk_status = "MEDIUM"
    else:
        join_risk_status = "HIGH"

    plain, tech, action = explain("join_risk", join_risk_status)

    st.subheader("Join Inflation Risk")
    if join_risk_status == "LOW":
        st.success(f"🟢 {plain}")
    elif join_risk_status == "MEDIUM":
        st.warning(f"🟠 {plain}")
    else:
        st.error(f"🔴 {plain}")

    st.write("Average rows per primary key:", duplication_ratio)

    with st.expander("Why this happens (technical)"):
        st.write(tech)
    with st.expander("What to do next"):
        st.write(action)

# -----------------------------
# NULL & NEGATIVE CHECKS
# -----------------------------
null_columns = df.columns[df.isnull().any()].tolist()
negative_columns = [
    c for c in df.select_dtypes(include="number").columns
    if (df[c] < 0).any()
]

st.subheader("Null / Missing Values")
if not null_columns:
    st.success("No missing values detected.")
else:
    st.warning(f"Missing values in: {', '.join(null_columns)}")

st.subheader("Negative Values")
if not negative_columns:
    st.success("No negative values detected.")
else:
    st.warning(f"Negative values in: {', '.join(negative_columns)}")

# -----------------------------
# AGGREGATION SANITY
# -----------------------------
st.subheader("Aggregation Sanity Check")

quantity_col = st.selectbox("Quantity column", df.columns)
price_col = st.selectbox("Unit Price column", df.columns)
revenue_col = st.selectbox("Reported Revenue column", df.columns)

qty = pd.to_numeric(df[quantity_col], errors="coerce")
price = pd.to_numeric(df[price_col], errors="coerce")
revenue = pd.to_numeric(df[revenue_col], errors="coerce")

diff = revenue.sum() - (qty * price).sum()
agg_status = "PASS" if abs(diff) <= 0.01 else "FAIL"
plain, tech, action = explain("aggregation", agg_status)

if agg_status == "PASS":
    st.success(plain)
else:
    st.error(plain)

# -----------------------------
# GPT Q&A (FINAL, SAFE)
# -----------------------------
st.subheader("Ask Questions About This Report (AI)")

api_key = get_openai_api_key()
user_question = st.text_input("Ask a question about this report")

if st.button("Ask"):
    if not api_key:
        st.error(
            "OpenAI API key not found.\n\n"
            "Local: add it to .streamlit/secrets.toml\n"
            "Cloud: add it in App → Settings → Secrets"
        )
    elif not user_question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Analyzing report..."):
            client = OpenAI(api_key=api_key)

            context = build_gpt_context(
                df,
                duplicate_count,
                pk_duplicate_count,
                null_columns,
                negative_columns,
                agg_status,
                join_risk_status
            )

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior data analyst. "
                            "Answer strictly using the provided report context."
                        )
                    },
                    {"role": "user", "content": context},
                    {"role": "user", "content": user_question}
                ],
                temperature=0.2
            )

            st.markdown("### 🤖 Answer")
            st.write(response.choices[0].message.content)
