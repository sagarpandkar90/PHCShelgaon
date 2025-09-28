import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import io
import json
import base64
import time
import streamlit.components.v1 as components

# Read Postgres secrets from Streamlit secrets.toml
db = st.secrets["postgres"]


def get_connection():
    return psycopg2.connect(
        host=db["host"],
        port=db["port"],
        dbname=db["dbname"],
        user=db["user"],
        password=db["password"],
        sslmode="require"
    )


# ----------------------
# Session init
# ----------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""

st.set_page_config(page_title="M-NO Register", layout="centered")

# ----------------------
# LOGIN
# ----------------------
if not st.session_state["logged_in"]:
    st.title("Login")
    username_input = st.text_input("Enter your username", key="login_username")

    if st.button("Login", key="login_btn"):
        if not username_input.strip():
            st.error("Please enter a username.")
        else:
            try:
                conn = get_connection()
                cur = conn.cursor(cursor_factory=RealDictCursor)
                # attempt to fetch user role from users table (adjust column names if you use different ones)
                cur.execute(
                    "SELECT role FROM users WHERE name = %s OR name = %s LIMIT 1",
                    (username_input, username_input)
                )
                user = cur.fetchone()
                cur.close()
                conn.close()
            except Exception as e:
                st.error(f"Database connection error: {e}")
                user = None

            if user:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username_input
                st.session_state["role"] = user.get("role", "")
                st.success(f"Logged in as {st.session_state['username']} ({st.session_state['role']})")
                st.rerun()
            else:
                st.error("Username not found!")

# ----------------------
# MAIN APP (after login)
# ----------------------
else:
    st.sidebar.title(f"Welcome, {st.session_state['username']} ({st.session_state['role']})")
    menu = st.sidebar.radio(
        "Menu",
        ["Add M No Record", "View M No Records", "Edit / Delete M No Record", "Export / Download", "Generate PDF", "Logout"],
        index=0,
        key="main_menu"
    )

    # LOGOUT
    if menu == "Logout":
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["role"] = ""
        st.rerun()


    # ---------------- Add Family Record ----------------
    if menu == "Add M No Record":
        st.header("Add M No Record")
        with st.form("add_fam_form", clear_on_submit=True):
            m_no = st.number_input("M No:", min_value=0, step=1, format="%d", key="add_no")
            family_head = st.text_input("कुटुंब प्रमुखाचे नाव:", key="add_f_head_name")
            member = st.number_input("घरातील एकूण सदस्य:", min_value=0, step=1, format="%d", key="add_f_members")
            ranjan = st.number_input("रांजण:", min_value=0, step=1, format="%d", key="add_ranjan")
            balar = st.number_input("बॅलर:", min_value=0, step=1, format="%d", key="add_balar")
            taki = st.number_input("टाकी:", min_value=0, step=1, format="%d", key="add_taki")
            dera = st.number_input("डेरा:", min_value=0, step=1, format="%d", key="add_dera")
            frize = st.number_input("फ्रिज:", min_value=0, step=1, format="%d", key="add_frize")
            e_bhandi = st.number_input("इतर भांडी:", min_value=0, step=1, format="%d", key="add_e_bhandi")
            submit = st.form_submit_button("Add")

        if submit:
            if not str(family_head).strip():
                st.error("Family head name is required.")
            else:
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute(
                        f"INSERT INTO m_no_register (m_no, family_head, member, ranjan, balar, taki, dera, freezer, exta_bhandi) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (int(m_no), family_head.strip(), int(member), int(ranjan), int(balar), int(taki), int(dera), int(frize), int(e_bhandi))
                    )
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success(f"M No {m_no} added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Insert failed: {e}")

    # ---------------- View Family Records ----------------
    elif menu == "View M No Records":
        st.header("M No Records")
        try:
            conn = get_connection()
            df = pd.read_sql(f"SELECT m_no, family_head, member, ranjan, balar, taki, dera, freezer, exta_bhandi FROM m_no_register ORDER BY m_no", conn)
            conn.close()
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            df = pd.DataFrame()

        if df.empty:
            st.info("No family records found.")
        else:
            st.dataframe(df, use_container_width=True)

    # ---------------- Edit / Delete family Record ----------------
    elif menu == "Edit / Delete M No Record":
        st.header("Edit or Delete M No Record")

        try:
            conn = get_connection()
            df = pd.read_sql(f"SELECT m_no, family_head, member, ranjan, balar, taki, dera, freezer, exta_bhandi FROM m_no_register ORDER BY m_no", conn)
            conn.close()
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            df = pd.DataFrame()

        if df.empty:
            st.info("No records to edit or delete.")
        else:
            # create selector labels
            df["label"] = df["m_no"].astype(str) + " — " + df["family_head"].astype(str)
            selection = st.selectbox("Select family record", df["label"].tolist(), key="edit_select")
            sel_m_no = int(selection.split(" — ")[0])
            row = df[df["m_no"] == sel_m_no].iloc[0]

            # If selection changed, clear other confirmation flags so only current shows
            if "last_selected_rec" not in st.session_state or st.session_state["last_selected_rec"] != sel_m_no:
                for k in list(st.session_state.keys()):
                    if isinstance(k, str) and k.startswith("show_confirm_"):
                        st.session_state.pop(k, None)
                st.session_state["last_selected_rec"] = sel_m_no

            # EDIT FORM
            st.subheader("Edit details")
            with st.form(f"edit_form_{sel_m_no}", clear_on_submit=False):
                edit_family_head = st.text_input("कुटुंब प्रमुखाचे नाव:", value=row["family_head"], key=f"edit_family_head_{sel_m_no}")
                edit_member = st.number_input("घरातील एकूण सदस्य:", min_value=0, step=1, value=int(row["member"] or 0), key=f"edit_member_{sel_m_no}")
                edit_ranjan = st.number_input("रांजण:", min_value=0, step=1, value=int(row["ranjan"] or 0), key=f"edit_ranjan_{sel_m_no}")
                edit_balar = st.number_input("बॅलर:", min_value=0, step=1, value=int(row["balar"] or 0), key=f"edit_balar_{sel_m_no}")
                edit_taki = st.number_input("टाकी:", min_value=0, step=1, value=int(row["taki"] or 0), key=f"edit_taki_{sel_m_no}")
                edit_dera = st.number_input("डेरा:", min_value=0, step=1, value=int(row["dera"] or 0), key=f"edit_dera_{sel_m_no}")
                edit_frize = st.number_input("फ्रिज:", min_value=0, step=1, value=int(row["freezer"] or 0), key=f"edit_frize_{sel_m_no}")
                edit_e_bhandi = st.number_input("इतर भांडी:", min_value=0, step=1, value=int(row["exta_bhandi"] or 0), key=f"edit_e_bhandi_{sel_m_no}")

                col1, col2 = st.columns([1, 1])
                with col1:
                    save = st.form_submit_button("Save changes", key=f"save_{sel_m_no}")
                with col2:
                    st.write("")

            # Handle Save
            if save:
                if not str(edit_family_head).strip():
                    st.error("Family head name cannot be empty.")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute(
                            f"UPDATE m_no_register SET family_head=%s, member=%s, ranjan=%s, balar=%s, taki=%s, dera=%s, freezer=%s, exta_bhandi=%s WHERE m_no=%s",
                            (edit_family_head.strip(), int(edit_member), int(edit_ranjan), int(edit_balar), int(edit_taki), int(edit_dera), int(edit_frize), int(edit_e_bhandi), sel_m_no)
                        )
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("Record updated successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")

            # ------------------ DELETE FLOW (outside the edit form) ------------------
            flag_name = f"show_confirm_{sel_m_no}"

            if st.button("Delete record", key=f"del_btn_{sel_m_no}"):
                st.session_state[flag_name] = True

            if st.session_state.get(flag_name, False):
                st.warning("You are about to permanently delete this record.")
                confirm_chk = st.checkbox(
                    "Yes — I confirm delete this record (this cannot be undone)",
                    key=f"confirm_chk_{sel_m_no}"
                )
                if confirm_chk:
                    if st.button("Confirm Delete", key=f"confirm_del_{sel_m_no}"):
                        try:
                            conn = get_connection()
                            cur = conn.cursor()
                            cur.execute(f"DELETE FROM m_no_register WHERE m_no=%s", (sel_m_no,))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.session_state.pop(flag_name, None)
                            st.success("Record deleted successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Delete failed: {e}")

    # ---------------- Export / Download ----------------
    elif menu == "Export / Download":
        st.header("Export Data")
        try:
            conn = get_connection()
            df = pd.read_sql(f"SELECT m_no, family_head, member, ranjan, balar, taki, dera, freezer, exta_bhandi FROM m_no_register ORDER BY m_no", conn)
            conn.close()
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            df = pd.DataFrame()

        if df.empty:
            st.info("No data to export.")
        else:
            st.dataframe(df, width='stretch')

            # Excel download
            towrite = io.BytesIO()
            with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="m_no_register")
            towrite.seek(0)
            st.download_button(
                label="⬇️ Download Excel",
                data=towrite,
                file_name="m_no_register.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # CSV download
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", data=csv, file_name="m_no_register.csv", mime="text/csv")

    # ---------------- Generate PDF ----------------
    elif menu == "Generate PDF":
        st.header("Generate PDF of Family Records")

        # --- remove inputs: automatically select ALL records ---
        try:
            conn = get_connection()
            query = "SELECT m_no, family_head, member, ranjan, balar, taki, dera, freezer, exta_bhandi FROM m_no_register ORDER BY m_no"
            df = pd.read_sql(query, conn)
            conn.close()

            df.insert(0, "Sr No", range(1, len(df) + 1))
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            df = pd.DataFrame()

        if df.empty:
            st.info("No data to generate PDF.")
        else:
            # prepare data for client-side pdfMake
            df_copy = df.copy().astype(str)  # ensure JSON serializable
            data_json = df_copy.to_dict(orient="records")



            # Use pdfMake in an embedded HTML component to create downloadable PDF client-side
            font_path = "fonts/NotoSerifDevanagari-VariableFont_wdth,wght.ttf"
            with open(font_path, "rb") as f:
                font_bytes = f.read()
                font_b64 = base64.b64encode(font_bytes).decode("utf-8")

            if st.button("Generate PDF") and font_b64:
                with st.spinner("PDF तयार होत आहे..."):
                    time.sleep(2)

        components.html(
            f"""
            <html>
            <head>
              <meta charset='utf-8' />
              <script src="https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.1.72/pdfmake.min.js"></script>
              <script src="https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.1.72/vfs_fonts.js"></script>
            </head>
            <body>
              <div style="margin-bottom:10px;">
                <button onclick="previewPDF()" style="padding:8px 12px; background:#2196F3; color:white; border:none; border-radius:6px; cursor:pointer; margin-right:8px;">👁️ Preview PDF</button>
                <button onclick="downloadPDF()" style="padding:8px 12px; background:#4CAF50; color:white; border:none; border-radius:6px; cursor:pointer;">⬇️ Download PDF</button>
              </div>

              <script>
                const data = {json.dumps(data_json, ensure_ascii=False)};

                // inject custom font
                pdfMake.vfs["CustomFont.ttf"] = "{font_b64}";
                pdfMake.fonts = {{
                  MarathiFont: {{
                    normal: "CustomFont.ttf",
                    bold: "CustomFont.ttf",
                    italics: "CustomFont.ttf",
                    bolditalics: "CustomFont.ttf"
                  }}
                }};

                const docDefinition = {{
                  defaultStyle: {{ font: "MarathiFont" }},
                  pageMargins: [45, 70, 20, 30],   // space for header/footer

                  header: function(currentPage, pageCount) {{
                    return {{
                      margin: [45, 43.5, 20, 0],
                      table: {{
                        widths: ['8%','45%','10%','6%','5%','5%','4%','5%', '10%'],
                        body: [[
                          {{ text: 'M-No', bold:true, alignment: 'center' }},
                          {{ text: 'कुटुंब प्रमुखाचे नाव', fontSize: 13, bold:true, alignment: 'center' }},
                          {{ text: 'ए.सदस्य', fontSize: 13, bold:true, alignment: 'center' }},
                          {{ text: 'रांजण', fontSize: 13, bold:true, alignment: 'center' }},
                          {{ text: 'बॅलर', fontSize: 13, bold:true, alignment: 'center' }},
                          {{ text: 'टाकी', fontSize: 13, bold:true, alignment: 'center' }},
                          {{ text: 'डेरा', fontSize: 13, bold:true, alignment: 'center' }},
                          {{ text: 'फ्रिज', fontSize: 13, bold:true, alignment: 'center' }},
                          {{ text: 'इतर भांडी', fontSize: 13, bold:true, alignment: 'center' }}
                        ]]
                      }},
                    }};
                  }},

                  footer: function(currentPage, pageCount) {{
                    return {{
                      text: currentPage.toString(),
                      alignment: 'center',
                      margin: [0, 10, 0, 0],
                      fontSize: 9
                    }};
                  }},

                  content: [
                    {{
                      table: {{
                        widths: ['8%','45%','10%','6%','5%','5%','4%','5%', '10%'],
                        body: [
                          ...data.map(d => [
                            {{ text: d['m_no'], alignment: 'center' }},
                            {{ text: d['family_head'] }},
                            {{ text: d['member'], alignment: 'center' }},
                            {{ text: d['ranjan'], alignment: 'center' }},
                            {{ text: d['balar'], alignment: 'center' }},
                            {{ text: d['taki'], alignment: 'center' }},
                            {{ text: d['dera'], alignment: 'center' }},
                            {{ text: d['freezer'], alignment: 'center' }},
                            {{ text: d['exta_bhandi'], alignment: 'center' }}
                          ])
                        ]
                      }}
                    }}
                  ]
                }};

                function previewPDF() {{
                  pdfMake.createPdf(docDefinition).open();
                }}

                function downloadPDF() {{
                  pdfMake.createPdf(docDefinition).download('m_no_register.pdf');
                }}
              </script>
            </body>
            </html>
            """,
            height=700,
            scrolling=True
        )
