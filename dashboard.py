import streamlit as st
import pandas as pd
import plotly.express as px


# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(
    page_title="EWS Dashboard",
    layout="wide"
)

# ==============================
# CUSTOM CSS
# ==============================
st.markdown("""
<style>

.main {
    background: linear-gradient(135deg,#020617,#0f172a);
}

.block-container{
    padding-top:2rem;
    padding-bottom:2rem;
}

[data-testid="stSidebar"]{
    background-color:#111827;
}

/* KPI CARDS */
.kpi-card{
    background:#111827;
    padding:25px;
    border-radius:15px;
    text-align:center;
    border:1px solid #1f2937;
    box-shadow:0px 8px 25px rgba(0,0,0,0.5);
}

/* SECTION */
.section{
    background:#111827;
    padding:25px;
    border-radius:15px;
    margin-top:20px;
    border:1px solid #1f2937;
    box-shadow:0px 8px 25px rgba(0,0,0,0.5);
}

/* TITLE */
.title{
    text-align:center;
    font-size:42px;
    font-weight:700;
    margin-bottom:20px;
}

/* REPORT BOX */
.report-box{
    background:#0f172a;
    padding:25px;
    border-radius:12px;
    border:1px solid #1f2937;
    line-height:1.8;
    font-size:15px;
    white-space:pre-wrap;
    overflow-x:auto;
}

</style>
""", unsafe_allow_html=True)

# ==============================
# LOAD DATA
# ==============================
#df_full = pd.read_csv(
   # r"C:\Python_Incentives_Calc_Project\EWS Project\output\final_ews_data.csv"
#)
df_full = pd.read_csv("final_ews_data.csv")

# ==============================
# HEADER
# ==============================
st.markdown(
    '<div class="title">EWS Dashboard</div>',
    unsafe_allow_html=True
)

# ==============================
# SIDEBAR FILTERS
# ==============================
st.sidebar.header("🔍 Filters")

month = st.sidebar.selectbox(
    "Month",
    sorted(df_full['Month'].dropna().unique(), reverse=True)
)

df = df_full[df_full['Month'] == month].copy()

division = st.sidebar.multiselect(
    "Division",
    sorted(df['Division'].dropna().unique())
)

zone = st.sidebar.multiselect(
    "Zone",
    sorted(df['Zone Name'].dropna().unique())
)

manager_col = "Reporting to Territory Name"

if manager_col in df.columns:
    manager = st.sidebar.multiselect(
        "Manager",
        sorted(df[manager_col].dropna().unique())
    )
else:
    manager = []

# ==============================
# APPLY FILTERS
# ==============================
if division:
    df = df[df['Division'].isin(division)]

if zone:
    df = df[df['Zone Name'].isin(zone)]

if manager:
    df = df[df[manager_col].isin(manager)]

# ==============================
# KPI VALUES
# ==============================
high = (df['Risk_Level']=="High Risk").sum()
medium = (df['Risk_Level']=="Medium Risk").sum()
low = (df['Risk_Level']=="Low Risk").sum()

# ==============================
# NEW RISK
# ==============================
if 'Prev_Risk' in df.columns:

    new = (
        (df['Prev_Risk']!="High Risk") &
        (df['Risk_Level']=="High Risk")
    ).sum()

else:
    new = 0

# ==============================
# KPI CARDS
# ==============================
c1, c2, c3, c4 = st.columns(4)

c1.markdown(f"""
<div class="kpi-card">
<h3>🔴 High Risk</h3>
<h1>{high}</h1>
</div>
""", unsafe_allow_html=True)

c2.markdown(f"""
<div class="kpi-card">
<h3>🟡 Medium Risk</h3>
<h1>{medium}</h1>
</div>
""", unsafe_allow_html=True)

c3.markdown(f"""
<div class="kpi-card">
<h3>🟢 Low Risk</h3>
<h1>{low}</h1>
</div>
""", unsafe_allow_html=True)

c4.markdown(f"""
<div class="kpi-card">
<h3>🆕 New Risk</h3>
<h1>{new}</h1>
</div>
""", unsafe_allow_html=True)

# ==============================
# CHART SECTION
# ==============================
st.markdown('<div class="section">', unsafe_allow_html=True)

col1, col2 = st.columns(2)

# ==============================
# ZONE-WISE RISK
# ==============================
zone_df = (
    df[df['Risk_Level']=="High Risk"]
    .groupby('Zone Name')
    .size()
    .reset_index(name='Count')
)

fig1 = px.bar(
    zone_df,
    x='Zone Name',
    y='Count',
    text='Count',
    color='Count',
    title="📍 Zone-wise High Risk"
)

fig1.update_traces(textposition='outside')

col1.plotly_chart(
    fig1,
    use_container_width=True
)

# ==============================
# RISK DISTRIBUTION
# ==============================
fig2 = px.pie(
    df,
    names='Risk_Level',
    hole=0.5,
    title="🍩 Risk Distribution"
)

fig2.update_traces(
    textinfo='percent+label'
)

col2.plotly_chart(
    fig2,
    use_container_width=True
)

st.markdown('</div>', unsafe_allow_html=True)

# ==============================
# TREND + MANAGER
# ==============================
st.markdown('<div class="section">', unsafe_allow_html=True)

col1, col2 = st.columns(2)

# ==============================
# TREND
# ==============================
trend_df = (
    df_full[df_full['Risk_Level']=="High Risk"]
    .groupby('Month')
    .size()
    .reset_index(name='Count')
)

fig3 = px.line(
    trend_df,
    x='Month',
    y='Count',
    text='Count',
    markers=True,
    title="📈 High Risk Trend"
)

fig3.update_traces(
    textposition="top center"
)

col1.plotly_chart(
    fig3,
    use_container_width=True
)

# ==============================
# MANAGER-WISE
# ==============================
if manager_col in df.columns:

    mgr_df = (
        df[df['Risk_Level']=="High Risk"]
        .groupby(manager_col)
        .size()
        .reset_index(name='Count')
    )

    fig4 = px.bar(
        mgr_df,
        x=manager_col,
        y='Count',
        text='Count',
        color='Count',
        title="👨‍💼 Manager-wise Risk"
    )

    fig4.update_traces(
        textposition='outside'
    )

    fig4.update_layout(
        xaxis_tickangle=-45
    )

    col2.plotly_chart(
        fig4,
        use_container_width=True
    )

st.markdown('</div>', unsafe_allow_html=True)

# ==============================
# TOP HIGH RISK EMPLOYEES
# ==============================
st.markdown('<div class="section">', unsafe_allow_html=True)

st.subheader("🔥 Top High Risk Employees")

top_df = (
    df[df['Risk_Level']=="High Risk"]
    .sort_values(by='EWS_Score', ascending=False)
    .head(10)
)

st.dataframe(
    top_df[
        ['Employee Name', 'Zone Name', 'EWS_Score']
    ],
    use_container_width=True
)

st.markdown('</div>', unsafe_allow_html=True)

# ==============================
# NEW HIGH RISK EMPLOYEES
# ==============================
st.markdown('<div class="section">', unsafe_allow_html=True)

st.subheader("🆕 New High Risk Employees")

if 'Prev_Risk' in df.columns:

    new_risk_df = df[
        (
            (df['Prev_Risk'] != "High Risk") |
            (df['Prev_Risk'].isna())
        ) &
        (df['Risk_Level'] == "High Risk")
    ]

else:

    new_risk_df = df[df['Risk_Level']=="High Risk"]

show_cols = [
    'Employee Name',
    'Zone Name',
    'Coverage',
    'Discount Percentage',
    'Closing Stock Days',
    'EWS_Score'
]

available_cols = [
    c for c in show_cols
    if c in new_risk_df.columns
]

st.dataframe(
    new_risk_df[available_cols],
    use_container_width=True
)

st.markdown('</div>', unsafe_allow_html=True)
# ==============================
# EXECUTIVE REPORT
# ==============================
st.markdown('<div class="section">', unsafe_allow_html=True)

st.subheader("📊 Executive Report")

try:

    report_path = rf"""
C:\Python_Incentives_Calc_Project\EWS Project\Output\EWS_Report_{month}.txt
""".strip()

    with open(
        report_path,
        "r",
        encoding="utf-8"
    ) as f:

        report_text = f.read()

except Exception as e:

    report_text = f"""
Report not found for selected month.

Expected:
EWS_Report_{month}.txt

Error:
{e}
"""

# ==============================
# SHOW ONLY TREND/ACTIONS/AI
# ==============================
sections = {}

current_section = None

for line in report_text.splitlines():

    line = line.strip()

    if line.startswith("---") and line.endswith("---"):

        current_section = line.replace("-", "").strip()

        sections[current_section] = []

    elif current_section:

        sections[current_section].append(line)

trend_section = "\n".join(
    sections.get("TREND", [])
)

actions_section = "\n".join(
    sections.get("ACTIONS", [])
)

ai_section = "\n".join(
    sections.get("AI INSIGHTS", [])
)

# ==============================
# DISPLAY
# ==============================
st.markdown(f"""
<div class="report-box">

<h3>📈 Trend</h3>
{trend_section}

<br><br>

<h3>🎯 Actions</h3>
{actions_section}

<br><br>

<h3>🤖 AI Insights</h3>
{ai_section}

</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
# ==============================
# DOWNLOAD
# ==============================
st.markdown("---")

csv = df.to_csv(index=False)

st.download_button(
    "📥 Download Report",
    csv,
    "EWS_Data.csv"
)

# ==============================
# FOOTER
# ==============================
st.markdown("---")
st.caption("Developed by Atul Tembhare")