import streamlit as st
import requests
import PyPDF2
from io import BytesIO

st.set_page_config(layout="wide")  # Ensures better API mode

st.title("PDF Parser API")

# Extract text from PDF
def extract_text_from_pdf(pdf_url):
    try:
        # Ensure URL starts with http or https
        if not pdf_url.startswith("http"):
            return "Error: Invalid URL. Must start with 'http://' or 'https://'."

        response = requests.get(pdf_url)
        if response.status_code == 200:
            pdf_file = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
            return text if text else "No extractable text found in the PDF."
        else:
            return f"Failed to fetch PDF: HTTP {response.status_code}"
    except Exception as e:
        return f"Error processing PDF: {str(e)}"

# Force API Mode
st.write("🚀 This is an API. Use `?url=your_pdf_link` to extract text.")

# ✅ Fix the Query Parameter Extraction
params = st.query_params  # ✅ Ensure no parentheses

if "url" in params:
    pdf_url = params["url"]
    
    # ✅ Handle lists in query parameters (Zapier may send as list)
    if isinstance(pdf_url, list):
        pdf_url = pdf_url[0]  # Take first URL if multiple provided

    extracted_text = extract_text_from_pdf(pdf_url.strip())

    # 🔥 Return pure JSON response
    st.json({"text": extracted_text})  
else:
    st.warning("❗ Provide a PDF URL as a query parameter: `?url=your_pdf_link`")
