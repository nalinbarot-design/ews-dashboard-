import pandas as pd
import glob
import os
import re
import time
from datetime import datetime
from sambanova import SambaNova

# ==============================
# 1. PICK LATEST FILE
# ==============================
files = glob.glob("../data/Early_Warning_Report*.xlsx")

def extract_date(file):
    filename = os.path.basename(file)
    match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{2}', filename)
    return datetime.strptime(match.group(0), "%b-%y") if match else datetime.min

latest_file = max(files, key=extract_date)
month_name = extract_date(latest_file).strftime("%b-%y")

current_dt = datetime.strptime(month_name, "%b-%y")
prev_dt = (current_dt.replace(day=1) - pd.DateOffset(months=1)).to_pydatetime()
prev_month_name = prev_dt.strftime("%b-%y")

print(f"📂 Processing: {latest_file}")

# ==============================
# 2. LOAD DATA
# ==============================
df = pd.read_excel(latest_file)
df.columns = df.columns.str.strip()
df.rename(columns={'Employee Code': 'Employee ID'}, inplace=True)
df = df.loc[:, ~df.columns.duplicated()]

# ==============================
# 3. COLUMN DETECTION
# ==============================
def find_col(keywords):
    for col in df.columns:
        if any(k.lower() in col.lower() for k in keywords):
            return col
    return None

col_map = {
    "incentive": find_col(["incentive"]),
    "discount": find_col(["discount"]),
    "coverage": find_col(["coverage"]),
    "compliance": find_col(["compliance"]),
    "budget": find_col(["month budget", "stretch"]),
    "stock": find_col(["stock"]),
    "wap": find_col(["wap"]),
    "visit": find_col(["manager visits"])
}

print("Detected Columns:", col_map)

# ==============================
# 4. VACANT FILTER
# ==============================
df['Is_Vacant'] = df['Employee ID'].isin([0, '0'])
active_df = df[~df['Is_Vacant']].copy()

# ==============================
# 5. SAFE CALC
# ==============================
def safe_calc(df, col, condition):
    if col:
        return condition(df[col]).astype(int)
    return 0

# ==============================
# 6. EWS SCORE
# ==============================
active_df['EWS_Score'] = (
    safe_calc(active_df, col_map['incentive'], lambda x: x >= 12000) +
    safe_calc(active_df, col_map['discount'], lambda x: x > 0.25) +
    safe_calc(active_df, col_map['coverage'], lambda x: x < 0.7) +
    safe_calc(active_df, col_map['compliance'], lambda x: x < 0.7) +
    safe_calc(active_df, col_map['budget'], lambda x: x > 0.12) +
    safe_calc(active_df, col_map['incentive'], lambda x: x == 0) +
    safe_calc(active_df, col_map['stock'], lambda x: x > 60) +
    safe_calc(active_df, col_map['wap'], lambda x: x <= 0.5) +
    safe_calc(active_df, col_map['visit'], lambda x: x <= 5)
)

# ==============================
# 7. RISK LEVEL
# ==============================
def risk(score):
    if score >= 6:
        return "High Risk"
    elif score >= 3:
        return "Medium Risk"
    return "Low Risk"

active_df['Risk_Level'] = active_df['EWS_Score'].apply(risk)
active_df['Month'] = month_name

# ==============================
# 8. SAVE HISTORY (FIXED)
# ==============================
hist_file = "../output/final_ews_data.csv"

if os.path.exists(hist_file):
    old = pd.read_csv(hist_file)
    combined = pd.concat([old, active_df], ignore_index=True)
else:
    combined = active_df.copy()

# Remove duplicates (IMPORTANT)
combined.drop_duplicates(['Employee ID', 'Month'], inplace=True)

# ==============================
# 9. PREVIOUS RISK (FIXED)
# ==============================

# 🔥 Convert Month to proper datetime for correct sorting
combined['Month_dt'] = pd.to_datetime(combined['Month'], format="%b-%y", errors='coerce')

# 🔥 Sort properly
combined = combined.sort_values(['Employee ID', 'Month_dt'])

# 🔥 Calculate Previous Risk
combined['Prev_Risk'] = combined.groupby('Employee ID')['Risk_Level'].shift(1)

# Remove helper column
combined.drop(columns=['Month_dt'], inplace=True)

# ==============================
# SAVE FINAL FILE (AFTER CALCULATION)
# ==============================
combined.to_csv(hist_file, index=False)

# ==============================
# CURRENT MONTH DATA
# ==============================
current = combined[combined['Month'] == month_name].copy()

# ==============================
# 10. METRICS
# ==============================
total_high = (current['Risk_Level'] == "High Risk").sum()

stayed = ((current['Prev_Risk'] == "High Risk") &
          (current['Risk_Level'] == "High Risk")).sum()

improved = ((current['Prev_Risk'] == "High Risk") &
            (current['Risk_Level'] != "High Risk")).sum()

new = (
    ((current['Prev_Risk'] != "High Risk") | (current['Prev_Risk'].isna())) &
    (current['Risk_Level'] == "High Risk")
).sum()

# ==============================
# 11. DRIVER ANALYSIS
# ==============================
def get_names(df):
    return ", ".join(df['Employee Name'].dropna().head(3)) if 'Employee Name' in df.columns else ""

low_cov = current[current[col_map['coverage']] < 0.7] if col_map['coverage'] else pd.DataFrame()
high_disc = current[current[col_map['discount']] > 0.25] if col_map['discount'] else pd.DataFrame()
high_stock = current[current[col_map['stock']] > 60] if col_map['stock'] else pd.DataFrame()

# ==============================
# 12. ADVANCED ANALYSIS
# ==============================
top_risk = current[current['Risk_Level']=="High Risk"] \
    .sort_values(by='EWS_Score', ascending=False).head(5)

top_risk_text = "\n".join(
    [f"- {r['Employee Name']} ({r['Zone Name']}) - Score {r['EWS_Score']}"
     for _, r in top_risk.iterrows()]
)

zone_text = "\n".join(
    [f"- {z}: {c}" for z, c in current[current['Risk_Level']=="High Risk"]
     .groupby('Zone Name').size().sort_values(ascending=False).items()]
)

manager_col = 'Reporting to Territory Name'
manager_text = "Not Available"
if manager_col in current.columns:
    manager_text = "\n".join(
        [f"- {m}: {c}" for m, c in current[current['Risk_Level']=="High Risk"]
         .groupby(manager_col).size().sort_values(ascending=False).items()]
    )

dist_text = "\n".join(
    [f"- {k}: {v}" for k, v in current['Risk_Level'].value_counts().items()]
)

new_names = ", ".join(
    current[
        ((current['Prev_Risk'] != "High Risk") | (current['Prev_Risk'].isna())) &
        (current['Risk_Level'] == "High Risk")
    ]['Employee Name'].head(5)
)

prev_month_df = combined[combined['Month'] == prev_month_name]
prev_high = (prev_month_df['Risk_Level'] == "High Risk").sum()
trend_text = f"{prev_month_name}: {prev_high} -> {month_name}: {total_high}"

actions = """
- Reduce stock levels
- Improve coverage visits
- Control discount practices
- Monitor high-risk employees closely
"""

# ==============================
# 13. AI (WITH RETRY + LOG)
# ==============================
prompt = f"""
You are an HR Analyst.

IMPORTANT:
"Still High Risk" means no improvement. Do NOT talk about retention.

Total High Risk: {total_high}
Still High Risk: {stayed}
Improved: {improved}
New High Risk: {new}

Give 4 short insights in simple language.
"""

client = SambaNova(
    api_key=("458ece5c-f523-4e71-9f15-874013170cab"),
    base_url="https://api.sambanova.ai/v1",
)

ai_text = None

for i in range(2):
    try:
        print(f"AI Attempt {i+1}")
        res = client.chat.completions.create(
            model="Meta-Llama-3.3-70B-Instruct",
            messages=[{"role":"user","content":prompt}],
            temperature=0.3,
            max_tokens=150
        )
        ai_text = res.choices[0].message.content
        break
    except Exception as e:
        print("AI Error:", e)
        with open("../output/error_log.txt","a") as log:
            log.write(f"{datetime.now()} | {str(e)}\n")
        time.sleep(2)

if ai_text is None:
    ai_text = f"""
- {total_high} employees are high risk
- {stayed} still high risk
- {improved} improved
- {new} new risk cases
"""

# ==============================
# 14. FINAL REPORT
# ==============================
report = f"""
==============================
EWS REPORT - {month_name}
==============================

--- SUMMARY ---
Total High Risk: {total_high}
Still High Risk ({prev_month_name} -> {month_name}): {stayed}
Improved: {improved}
New Risk: {new}

--- KEY ISSUES ---
Low Coverage: {len(low_cov)} ({get_names(low_cov)})
High Discount: {len(high_disc)} ({get_names(high_disc)})
High Stock: {len(high_stock)} ({get_names(high_stock)})

--- TOP HIGH RISK EMPLOYEES ---
{top_risk_text}

--- NEW HIGH RISK EMPLOYEES ---
{new_names}

--- ZONE-WISE RISK ---
{zone_text}

--- MANAGER-WISE RISK ---
{manager_text}

--- RISK DISTRIBUTION ---
{dist_text}

--- TREND ---
{trend_text}

--- ACTIONS ---
{actions}

--- AI INSIGHTS ---
{ai_text}
"""

# ==============================
# 15. KEEP ALL COLUMNS
# ==============================
extra_cols = ['EWS_Score','Risk_Level','Prev_Risk','Month']
cols = [c for c in current.columns if c not in extra_cols] + extra_cols
current = current[cols]

# ==============================
# 16. SAVE
# ==============================
current.to_csv(f"../output/ews_{month_name}.csv", index=False)

with open(f"../output/EWS_Report_{month_name}.txt","w",encoding="utf-8") as f:
    f.write(report)

print("EWS Report Generated")