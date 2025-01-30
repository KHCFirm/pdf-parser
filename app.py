import streamlit as st
import pdfplumber
import requests
import io

st.title("📄 KHC PDF Parser")

# Input: PDF URL
pdf_url = st.text_input("Enter PDF URL:")

if pdf_url:
    try:
        # Download the PDF
        response = requests.get(pdf_url)
        if response.status_code != 200:
            st.error("Failed to download PDF. Check the URL.")
        else:
            # Read the PDF using pdfplumber
            pdf_data = io.BytesIO(response.content)
            with pdfplumber.open(pdf_data) as pdf:
                extracted_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

                # Extract form field data (for HCFA-1500)
                extracted_tables = []
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        extracted_tables.append(table)

            # Display extracted text
            st.subheader("📝 Extracted Text (Static Content)")
            st.text_area("Extracted Text", extracted_text, height=300)

            # Display extracted form data
            st.subheader("📋 Extracted Table Data (HCFA Fields)")
            for table in extracted_tables:
                st.write(table)

            # Allow Zapier to retrieve data
            st.write(f"✅ API Endpoint: `/parse?url={pdf_url}`")

    except Exception as e:
        st.error(f"Error: {e}")
