# app.py
import streamlit as st
import pandas as pd
import html
from rapidfuzz import fuzz   # pip install rapidfuzz

# CONFIG
EXCEL_FILENAME = "Shelgaon.xlsx"  # place your Excel file in project folder with this name
TOP_N = 15

st.set_page_config(page_title="Name search - Screening statuses (Top 15 matches)", layout="wide")
st.title("Search Person & show Screening Status (Top 15 matches)")

st.info("Search Now...")

@st.cache_data
def load_df_from_project(path):
    # read everything as string to avoid NaNs; if file missing, raise
    df = pd.read_excel(path, dtype=str).fillna("")
    # ensure name columns exist
    for c in ["First Name", "Middle Name", "Last Name"]:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].astype(str).str.strip()
    # build normalized full name string (single spaces)
    df["_full"] = (
        df["First Name"].str.strip() + " " +
        df["Middle Name"].str.strip() + " " +
        df["Last Name"].str.strip()
    ).str.split().str.join(" ")
    # lowercase helpers for exact-equality checks
    df["_full_lc"] = df["_full"].str.casefold()
    df["_first_lc"] = df["First Name"].str.casefold()
    df["_middle_lc"] = df["Middle Name"].str.casefold()
    df["_last_lc"] = df["Last Name"].str.casefold()
    return df

# try load
try:
    df = load_df_from_project(EXCEL_FILENAME)
except FileNotFoundError:
    st.error(f"Could not find file `{EXCEL_FILENAME}` in the app folder. Please add the Excel file and restart the app.")
    st.stop()
except Exception as e:
    st.error(f"Error reading `{EXCEL_FILENAME}`: {e}")
    st.stop()


# input
query_raw = st.text_input("Enter name to search (full / first+middle / middle+last)", "")
query = query_raw.strip()
query_lc = query.casefold()

# columns to display
screening_cols = [
    "HTN_Screening_Status",
    "DM_Screening_Status",
    "OC_Screening_Status",
    "BC_Screening_Status",
    "CC_Screening_Status"
]
for col in screening_cols:
    if col not in df.columns:
        df[col] = ""

context_cols = ["First Name", "Middle Name", "Last Name", "Age", "Sex", "Village", "Mobile #"]

def make_display_name(row):
    name = " ".join([s for s in [row.get("First Name",""), row.get("Middle Name",""), row.get("Last Name","")] if s])
    village = str(row.get("Village","")).strip()
    extra = ""
    if village:
        extra += f" — {village}"
    return f"{name}{extra}"

def color_cell(val):
    text = html.escape(str(val))
    if str(val).strip().casefold() == "pending screening".casefold():
        return f"<span style='color:red; font-weight:700'>{text}</span>"
    return text

# ---------- Improved matching routine ----------
def compute_best_score_for_row(row, query, query_lc):
    """
    Build several name variants for a row and compute similarity scores.
    Return final score (0-100).
    """
    # Candidate name strings (raw)
    full = str(row["_full"]).strip()
    first = str(row["First Name"]).strip()
    middle = str(row["Middle Name"]).strip()
    last = str(row["Last Name"]).strip()

    # If First Name contains multiple tokens, treat them as possible first+middle
    first_tokens = [t for t in first.split() if t]
    first_variants = []
    if first_tokens:
        # e.g. if First = "Ram Kumar", variants: "Ram", "Ram Kumar"
        for i in range(1, len(first_tokens)+1):
            first_variants.append(" ".join(first_tokens[:i]))
    else:
        first_variants.append(first)

    # Build candidate strings to compare with query
    candidates = set()
    # full
    if full:
        candidates.add(full)
    # first + middle (if middle exists)
    if first and middle:
        candidates.add((first + " " + middle).strip())
    # first variants + last
    if last:
        for fv in first_variants:
            if fv:
                candidates.add((fv + " " + last).strip())
    # first only and middle+last (if middle exists)
    candidates.add(first)
    if middle and last:
        candidates.add((middle + " " + last).strip())
    # also add middle and last alone
    if middle:
        candidates.add(middle)
    if last:
        candidates.add(last)

    # compute similarity scores
    scores = []
    exact_match_found = False
    for cand in candidates:
        if not cand:
            continue
        cand_lc = cand.casefold()
        # exact equality (case-insensitive) -> huge boost
        if cand_lc == query_lc and query_lc != "":
            exact_match_found = True
            scores.append(100.0)
            continue
        # else compute WRatio (good general-purpose)
        try:
            s = fuzz.WRatio(query, cand)  # 0-100
        except Exception:
            s = 0.0
        scores.append(s)

    # if nothing scored (empty candidates) return 0
    if not scores:
        base = 0.0
    else:
        base = max(scores)

    # slight boost if query is substring of full name or vice-versa
    try:
        if query_lc and query_lc in str(row["_full_lc"]):
            base = max(base, 90.0)
        if row["_full_lc"] and row["_full_lc"] in query_lc:
            base = max(base, 90.0)
    except Exception:
        pass

    # final boost for exact match
    if exact_match_found:
        final = 100.0
    else:
        final = min(100.0, base)

    return final

# ---------- End improved matching ----------

if query:
    # prepare display names
    df["__display"] = df.apply(make_display_name, axis=1)

    # compute best score per row
    scores = []
    for idx, row in df.iterrows():
        s = compute_best_score_for_row(row, query, query_lc)
        scores.append(s)
    df["_score"] = scores

    # pick top N by score (then by name tie-breaker)
    top_df = df.sort_values(by=["_score", "_full"], ascending=[False, True]).head(TOP_N).copy()
    # filter out very low scores (optional) - comment out if you prefer always TOP_N
    # top_df = top_df[top_df["_score"] >= 25]  # uncomment to require minimum similarity

    if top_df.empty:
        st.info("No related names found.")
        st.stop()

    # Show list with similarity score
    st.markdown(f"**Top {len(top_df)} matches (sorted by computed similarity):**")
    # create options with score
    options = [f"{row['__display']}  —  {int(row['_score'])}% " for _, row in top_df.iterrows()]
    selected_opt = st.selectbox("Select a person", options=options)

    # find corresponding display string (strip trailing score)
    selected_display = selected_opt.rsplit("  —  ", 1)[0]
    sel_row = top_df[top_df["__display"] == selected_display].iloc[0]

    # Show basic info
    st.subheader("Selected person")
    info_html = "<table style='border-collapse: collapse;'>"
    for c in context_cols:
        info_html += f"<tr><td style='padding:4px 8px; font-weight:600'>{html.escape(c)}</td><td style='padding:4px 8px'>{html.escape(str(sel_row.get(c,'')))}</td></tr>"
    info_html += "</table>"
    st.markdown(info_html, unsafe_allow_html=True)

    # Screening statuses
    st.subheader("Screening Statuses")
    headers = ["Screening"] + screening_cols
    table_html = "<table style='border-collapse: collapse; width:100%'>"
    table_html += "<tr>" + "".join([f"<th style='border:1px solid #ddd; padding:6px; text-align:left'>{html.escape(h)}</th>" for h in headers]) + "</tr>"
    row_cells = [f"<td style='border:1px solid #ddd; padding:6px'>Selected</td>"]
    for c in screening_cols:
        row_cells.append(f"<td style='border:1px solid #ddd; padding:6px'>{color_cell(sel_row.get(c,''))}</td>")
    table_html += "<tr>" + "".join(row_cells) + "</tr>"
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)
    st.caption("`Pending Screening` statuses are highlighted in red.")
else:
    st.info("Type a name to get the top related 15 matches.")
