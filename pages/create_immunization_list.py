import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date
import io
import json
import base64
import time
import streamlit.components.v1 as components



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

st.set_page_config(page_title="Beneficiary App", layout="centered")

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
                # Check both possible column names (username or name)
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
                st.session_state["role"] = user["role"]
                st.success(f"Logged in as {user['role']}")
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
        ["Add Beneficiary", "View Beneficiaries", "Edit / Delete Beneficiary", "Export / Download", "Generate PDF", "Logout"],
        index=0,
        key="main_menu"
    )

    # LOGOUT
    if menu == "Logout":
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["role"] = ""
        st.rerun()

    # ---------------- Add Beneficiary ----------------
    if menu == "Add Beneficiary":
        st.header("Add Beneficiary")
        with st.form("add_ben_form", clear_on_submit=True):
            name = st.text_input("Name", key="add_name")
            birthdate = st.date_input("Birth Date", value=date.today(), key="add_dob")
            gender = st.selectbox("Gender", ["M", "F", "O"], key="add_gender")
            booth_no = st.text_input("Booth NO:", key="add_booth_no")

            submit = st.form_submit_button("Add")

        if submit:
            if not name.strip():
                st.error("Name is required.")
            else:
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute(
                        "INSERT INTO beneficiaries (name, dob, gender, boot_no) VALUES (%s,%s,%s, %s)",
                        (name.strip(), birthdate, gender, booth_no)
                    )
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success(f"{name} added successfully!")
                except Exception as e:
                    st.error(f"Insert failed: {e}")

    # ---------------- View Beneficiaries ----------------
    elif menu == "View Beneficiaries":
        st.header("Beneficiaries List")
        try:
            conn = get_connection()
            df = pd.read_sql("SELECT id, name, dob, gender, boot_no FROM beneficiaries ORDER BY id", conn)
            conn.close()
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            df = pd.DataFrame()

        if df.empty:
            st.info("No beneficiaries found.")
        else:
            # format date columns for display
            if "dob" in df.columns:
                df["dob"] = pd.to_datetime(df["dob"]).dt.date

            st.dataframe(df, use_container_width=True)

    # ---------------- Edit / Delete Beneficiary (REPLACE YOUR OLD BLOCK) ----------------
    elif menu == "Edit / Delete Beneficiary":
        st.header("Edit or Delete Beneficiary")

        # Load data
        try:
            conn = get_connection()
            df = pd.read_sql("SELECT id, name, dob, gender, boot_no FROM beneficiaries ORDER BY id", conn)
            conn.close()
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            df = pd.DataFrame()

        if df.empty:
            st.info("No beneficiaries to edit or delete.")
        else:
            # create selector labels
            df["label"] = df["id"].astype(str) + " — " + df["name"]
            selection = st.selectbox("Select beneficiary", df["label"].tolist(), key="edit_select")
            sel_id = int(selection.split(" — ")[0])
            row = df[df["id"] == sel_id].iloc[0]

            # If selection changed, clear other confirmation flags so only current shows
            if "last_selected_ben" not in st.session_state or st.session_state["last_selected_ben"] != sel_id:
                # clear any old show_confirm flags
                for k in list(st.session_state.keys()):
                    if isinstance(k, str) and k.startswith("show_confirm_"):
                        st.session_state.pop(k, None)
                st.session_state["last_selected_ben"] = sel_id

            # Convert dob to date for date_input
            try:
                dob_val = pd.to_datetime(row["dob"]).date()
            except Exception:
                dob_val = date.today()

            # EDIT FORM
            st.subheader("Edit details")
            with st.form(f"edit_form_{sel_id}", clear_on_submit=False):
                edit_name = st.text_input("Name", value=row["name"], key=f"edit_name_{sel_id}")
                edit_dob = st.date_input("Birth Date", value=dob_val, key=f"edit_dob_{sel_id}")
                edit_gender = st.selectbox(
                    "Gender",
                    ["Male", "Female", "Other"],
                    index=(["Male", "Female", "Other"].index(row["gender"]) if row["gender"] in ["Male", "Female",
                                                                                                 "Other"] else 0),
                    key=f"edit_gender_{sel_id}"
                )
                edit_booth_no = st.text_input("Booth No", value=row["boot_no"])

                col1, col2 = st.columns([1, 1])
                with col1:
                    save = st.form_submit_button("Save changes", key=f"save_{sel_id}")
                # NOTE: delete button must NOT be inside the form (move it outside) so clicks act immediately
                with col2:
                    st.write("")  # keep layout aligned

            # Handle Save
            if save:
                if not edit_name.strip():
                    st.error("Name cannot be empty.")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute(
                            "UPDATE beneficiaries SET name=%s, dob=%s, gender=%s, boot_no=%s WHERE id=%s",
                            (edit_name.strip(), edit_dob, edit_gender, edit_booth_no, sel_id)
                        )
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("Record updated successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")

            # ------------------ DELETE FLOW (outside the edit form) ------------------
            # Use a session flag keyed by sel_id so only this record shows confirmation
            flag_name = f"show_confirm_{sel_id}"

            # 1) initial Delete request button (outside form)
            if st.button("Delete beneficiary", key=f"del_btn_{sel_id}"):
                st.session_state[flag_name] = True

            # 2) show confirmation UI only for the selected record when flag set
            if st.session_state.get(flag_name, False):
                st.warning("You are about to permanently delete this record.")
                # confirmation checkbox (unique key)
                confirm_chk = st.checkbox(
                    "Yes — I confirm delete this beneficiary (this cannot be undone)",
                    key=f"confirm_chk_{sel_id}"
                )
                # Only show the final Confirm Delete button after checkbox is checked
                if confirm_chk:
                    if st.button("Confirm Delete", key=f"confirm_del_{sel_id}"):
                        try:
                            conn = get_connection()
                            cur = conn.cursor()
                            cur.execute("DELETE FROM beneficiaries WHERE id=%s", (sel_id,))
                            conn.commit()
                            cur.close()
                            conn.close()
                            # cleanup flag so confirmation UI disappears
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
            df = pd.read_sql("SELECT id, name, dob, gender FROM beneficiaries ORDER BY id", conn)
            conn.close()
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            df = pd.DataFrame()

        if df.empty:
            st.info("No data to export.")
        else:
            # Format dates
            if "dob" in df.columns:
                df["dob"] = pd.to_datetime(df["dob"]).dt.date


            st.dataframe(df, width='stretch')


            # Excel download
            towrite = io.BytesIO()
            with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="beneficiaries")
            towrite.seek(0)
            st.download_button(
                label="⬇️ Download Excel",
                data=towrite,
                file_name="beneficiaries.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # Generate PDF
    elif menu == "Generate PDF":
        st.header("Generate PDF of Beneficiaries")
        ldate = st.date_input("Immunization Date:", value=date.today(), key="add_ldate")
        booth_name = st.text_input("Booth Name:")
        booth_no = st.text_input("Booth No:", value=1)

        ldate = ldate.strftime("%d-%m-%Y")  # उदा. 27-09-2025

        try:
            conn = get_connection()
            query = "SELECT name, dob, gender FROM beneficiaries WHERE boot_no = %s"
            df = pd.read_sql(query, conn, params=(booth_no,))
            conn.close()
            df["dob"] = pd.to_datetime(df["dob"]).dt.date
            df.insert(0, "Sr No", range(1, len(df) + 1))

        except Exception as e:
            st.error(f"Failed to load data: {e}")
            df = pd.DataFrame()

        if df.empty:
            st.info("No data to generate PDF.")
        else:
            # Make a copy of the dataframe
            df_copy = df.copy()

            # Convert 'dob' to DD-MM-YYYY string
            if "dob" in df_copy.columns:
                df_copy["dob"] = pd.to_datetime(df_copy["dob"]).dt.strftime("%d-%m-%Y")

            # Convert to JSON-serializable dict
            data_json = df_copy.to_dict(orient="records")

            form_data = {

                "booth_name": booth_name,
                "booth_no": booth_no,
                "ldate": ldate,
            }

            font_path = "fonts/NotoSerifDevanagari-VariableFont_wdth,wght.ttf"
            with open(font_path, "rb") as f:
                font_bytes = f.read()
                font_b64 = base64.b64encode(font_bytes).decode("utf-8")

            if st.button("Generate PDF") and font_b64:
                with st.spinner("PDF तयार होत आहे..."):
                    time.sleep(2)

                st.success("✅ PDF तयार झाला! खाली प्रीव्ह्यू आणि डाउनलोड 👇")
                components.html(
                    f"""
                    <html>
                    <head>
                      <script src="https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.1.72/pdfmake.min.js"></script>
                      <script src="https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.1.72/vfs_fonts.js"></script>
                    </head>
                    <body>
                      <div style="margin-bottom:10px;">
                        <button onclick="previewPDF()" 
                          style="padding:8px 12px; background:#2196F3; color:white; border:none; border-radius:6px; cursor:pointer; margin-right:8px;">
                          👁️ Preview PDF
                        </button>
                        <button onclick="downloadPDF()" 
                            style="padding:8px 12px; background:#4CAF50; color:white; border:none; border-radius:6px; cursor:pointer;">
                            ⬇️ Download PDF
                        </button>
                      </div>

                      <script>
                        const data = {json.dumps(data_json, ensure_ascii=False)};
                        const form_data = {json.dumps(form_data, ensure_ascii=False)};

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
 
                        // build docDefinition
const docDefinition = {{
  defaultStyle: {{ font: "MarathiFont" }},
  pageMargins: [40, 161, 30, 40], // top margin मोठं header टेबलसाठी

  header: function(currentPage, pageCount) {{
    return {{
      margin: [40, 40, 30, 0],
      stack: [
        {{ text: "पल्स पोलिओ लसीकरण मोहीम " + (form_data?.ldate ? form_data.ldate.split("-")[2] : ""), fontSize: 16, alignment: "center"}},
        {{ text: "प्राथमिक आरोग्य केंद्र शेळगाव", fontSize: 16, alignment: "center"}},
        {{ text: "उपकेंद्र: शेळगाव                                   बुथ क्रमांक: " + (form_data.booth_no || "") + "                              बुथचे नाव: " + (form_data.booth_name || ""), margin:[35,2,0,4] }},
        {{ text: "० ते ५ वर्षे वयोगटातील अपेक्षित लाभार्थी यादी", fontSize: 14, alignment: "center" }},

        // 👉 Table heading row (repeat on every page)
        {{
          margin: [0, 0, 0, 0],
          table: {{
            widths: ["5%", "45%", "15%", "5%", "15%", "15%"],
            body: [[
              {{ text: "अ.क्र.", bold:true, alignment: "center"}},
              {{ text: "लाभार्थीचे नाव", bold:true, alignment: "center"}},
              {{ text: "जन्मदिनांक", bold:true, alignment: "center"}},
              {{ text: "लिंग", bold:true, alignment: "center"}},
              {{ text: form_data.ldate || "", bold:true, alignment: "center"}},
              {{ text: "शेरा", bold:true, alignment: "center"}}
            ]]
          }},
        }}
      ]
    }};
  }},

  content: [
    {{
      table: {{
        widths: ["5%", "45%", "15%", "5%", "15%", "15%"],
        body: [
          // ✅ फक्त data rows
          ...data.map((d, i) => [
            {{ text: i + 1, alignment: 'center' }},
            {{ text: d.name || "" }},
            {{ text: d.dob || "", alignment: 'center' }},
            {{ text: d.gender || "", alignment: 'center' }},
            {{ text: "", alignment: 'center' }},
            {{ text: "", alignment: 'center' }}
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
                          pdfMake.createPdf(docDefinition).download("beneficiaries.pdf");
                        }}
                      </script>
                    </body>
                    </html>
                    """,
                    height=700,
                    scrolling=True
                )