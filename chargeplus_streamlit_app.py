
import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
from datetime import datetime
from io import BytesIO
import streamlit as st

# 🔐 Login using st.secrets
def login():
    st.title("🔒 Charge+ Receipt App Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in st.secrets["users"] and st.secrets["users"][username] == password:
            st.session_state["authenticated"] = True
            st.experimental_rerun()
        else:
            st.error("❌ Invalid username or password")

# 🚪 Check login
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login()
    st.stop()

def extract_chargeplus_data_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()

    data = {}

    try:
        date_match = re.search(r"Date:\s*(\d{1,2} \w+ \d{4})", text)
        data['Date'] = date_match.group(1)
        data['Parsed Date'] = datetime.strptime(data['Date'], "%d %b %Y")
    except:
        data['Date'] = "N/A"
        data['Parsed Date'] = None

    try:
        location_match = re.search(r"Charging Station\s*(.+)", text)
        data['Location'] = location_match.group(1).strip()
    except:
        data['Location'] = "N/A"

    try:
        kwh_match = re.search(r"Energy Consumption\s*([\d.]+)\s*kWh", text)
        data['Energy (kWh)'] = float(kwh_match.group(1))
    except:
        data['Energy (kWh)'] = None

    try:
        cost_match = re.search(r"Charge\+ Credit used.*?S\$ ([\d.]+)", text, re.DOTALL)
        data['Cost (SGD)'] = float(cost_match.group(1))
    except:
        data['Cost (SGD)'] = None

    return data

st.title("Charge+ Receipt Extractor")
st.write("Upload your Charge+ PDF receipts and download an Excel summary.")

uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    records = []
    for file in uploaded_files:
        data = extract_chargeplus_data_from_pdf(file)
        data['Filename'] = file.name
        records.append(data)

    df = pd.DataFrame(records)

    if 'Parsed Date' in df.columns:
        df['Month'] = df['Parsed Date'].dt.to_period('M')
        summary = df.groupby('Month')[['Energy (kWh)', 'Cost (SGD)']].sum().reset_index()
    else:
        summary = pd.DataFrame()

    st.subheader("Extracted Data")
    st.dataframe(df)

    st.subheader("Monthly Summary")
    st.dataframe(summary)

    # Download buttons
    def to_excel_bytes(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return output

    excel_file = to_excel_bytes(df)
    st.download_button("Download Full Log (Excel)", data=excel_file, file_name="ChargePlus_Charging_Log.xlsx")

    summary_file = to_excel_bytes(summary)
    st.download_button("Download Monthly Summary (Excel)", data=summary_file, file_name="ChargePlus_Monthly_Summary.xlsx")
