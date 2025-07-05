
import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(page_title="Prostate Cancer Risk Stratifier", layout="centered")

st.sidebar.header("Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload your .xls file", type=["xls"])

# === Helper functions ===
def get_grade_group(gleason):
    match = re.match(r"(\d)\+(\d)", str(gleason).replace(" ", ""))
    if not match:
        return None
    g1, g2 = int(match[1]), int(match[2])
    score = g1 + g2
    if g1 == 3 and g2 == 3:
        return 1
    elif g1 == 3 and g2 == 4:
        return 2
    elif g1 == 4 and g2 == 3:
        return 3
    elif score == 8:
        return 4
    elif score >= 9:
        return 5
    return None

def get_t_stage_severity(tnm):
    stage_map = {"1c": 1, "2a": 2, "2b": 3, "2c": 4, "3a": 5, "3b": 6, "4": 7}
    match = re.search(r"[Tt](\d[a-c]?)", str(tnm))
    if match:
        stage = match.group(1).lower()
        return stage_map.get(stage, 0)
    return 0

def is_metastatic(tnm):
    tnm = str(tnm).upper()
    if re.search(r"N(?!0)\d", tnm) or re.search(r"M(?!0)\d", tnm):
        return True
    return False

def classify_risk_group(psa, raw_gle1, raw_gle2, tnm1, tnm2):
    try:
        psa = float(psa)
    except:
        return "Unknown"

    gg1 = get_grade_group(raw_gle1)
    gg2 = get_grade_group(raw_gle2)

    ggs = list(filter(None, [gg1, gg2]))
    worst_gg = max(ggs) if ggs else None

    t1 = get_t_stage_severity(tnm1)
    t2 = get_t_stage_severity(tnm2)
    t_stage_severity = max(t1, t2)

    if worst_gg is None or t_stage_severity == 0:
        return "Unknown"

    primary_pattern_5 = any(str(g).replace(" ", "").startswith("5+") for g in [raw_gle1, raw_gle2])

    if primary_pattern_5 or t_stage_severity >= 6:
        return "VHR"

    all_ggs_low = all(gg <= 3 for gg in ggs)
    if all_ggs_low and psa <= 20 and t_stage_severity <= 4:
        return "LR"

    return "HR"

def process_row(row):
    psa = row["PSA_preoperation"]
    g1 = row["Gleason_preoperation"]
    g2 = row["Gleason_postoperation"]
    tnm1 = row["TNM_preoperation"]
    tnm2 = row["TNM_postoperation"]

    if is_metastatic(tnm1) or is_metastatic(tnm2):
        return pd.Series({"Grouped_Risk": "M"})

    risk = classify_risk_group(psa, g1, g2, tnm1, tnm2)
    return pd.Series({"Grouped_Risk": risk})

# Main logic
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, engine="xlrd")
    results = df.apply(process_row, axis=1)
    df_final = pd.concat([df, results], axis=1)
        
    # Determine the first column from the original Excel
    original_columns = df.columns.tolist()
    first_column = original_columns[0]

    # Define target columns to insert
    insert_cols = ["Grouped_Risk", "PSA_preoperation", "Gleason_preoperation",
                "Gleason_postoperation", "TNM_preoperation", "TNM_postoperation"]

    # Build the new order: first column + insert_cols + rest
    all_columns = [first_column] + insert_cols + [col for col in df_final.columns
                                                if col not in insert_cols and col != first_column]

    # Reorder df_final
    df_final = df_final[all_columns]

    st.success("Risk stratification complete!")
    st.dataframe(df_final)

    # Export to Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_final.to_excel(writer, index=False, sheet_name="Risk Grouped")
    st.download_button(
        label="📥 Download Result as Excel",
        data=output.getvalue(),
        file_name="prostate_risk_grouped.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Please upload an `.xls` file to get started.")
