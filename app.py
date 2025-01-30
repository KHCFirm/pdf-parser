import streamlit as st
import PyPDF2
import requests
import io

st.title("📄 PDF Parser")

# Input: PDF URL
pdf_url = st.text_input("Enter PDF URL:")

if pdf_url:
    try:
        # Download the PDF file
        response = requests.get(pdf_url)
        if response.status_code != 200:
            st.error("Failed to download PDF. Check the URL.")
        else:
            # Read PDF content
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(response.content))
            extracted_text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])

            st.text_area("Extracted Text:", extracted_text, height=400)
            
            # Allow Zapier or others to retrieve text via URL
            st.write(f"✅ API Endpoint: `/parse?url={pdf_url}`")
    except Exception as e:
        st.error(f"Error: {e}")
