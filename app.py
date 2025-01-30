import streamlit as st
import fitz  # PyMuPDF
import requests
import io

st.title("📄 HCFA-1500 PDF Parser (Extract All Text & Form Data)")

# Input: PDF URL
pdf_url = st.text_input("Enter PDF URL:")

if pdf_url:
    try:
        # Download the PDF
        response = requests.get(pdf_url)
        if response.status_code != 200:
            st.error("Failed to download PDF. Check the URL.")
        else:
            # Read the PDF using PyMuPDF
            pdf_data = io.BytesIO(response.content)
            doc = fitz.open(stream=pdf_data, filetype="pdf")

            # Extract static text
            extracted_text = ""
            for page in doc:
                extracted_text += page.get_text("text") + "\n"

            # Extract form fields
            form_data = {}
            for field in doc.widgets():
                form_data[field.field_name] = field.text

            # Display extracted data
            st.subheader("📝 Extracted Text (Static Content)")
            st.text_area("Extracted Text", extracted_text, height=300)

            st.subheader("📋 Extracted Form Fields")
            for key, value in form_data.items():
                st.write(f"**{key}:** {value}")

            # Allow Zapier to retrieve data
            st.write(f"✅ API Endpoint: `/parse?url={pdf_url}`")

    except Exception as e:
        st.error(f"Error: {e}")
