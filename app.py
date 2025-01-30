import streamlit as st
import requests
import PyPDF2
from io import BytesIO

st.title("PDF Parser")

# Extract text from PDF
def extract_text_from_pdf(pdf_url):
    try:
        response = requests.get(pdf_url)
        if response.status_code == 200:
            pdf_file = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
            return text
        else:
            return f"Failed to fetch PDF: {response.status_code}"
    except Exception as e:
        return f"Error processing PDF: {str(e)}"

# Get the PDF URL from query parameters
params = st.query_params  # ✅ No parentheses

if "url" in params:  # ✅ Correct variable name
    pdf_url = params["url"][0]
    extracted_text = extract_text_from_pdf(pdf_url)
    st.json({"text": extracted_text})  # Return JSON for Zapier
else:
    st.write("Provide a PDF URL as a query parameter: `?url=your_pdf_link`")
