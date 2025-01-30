import streamlit as st
import pdfplumber
import requests
import io
import json

st.title("📄 KHC's PDF Parser API")

# Get PDF URL from Zapier
pdf_url = st.query_params.get("url")

def extract_pdf_text(pdf_url):
    response = requests.get(pdf_url)
    if response.status_code != 200:
        return {"error": "Failed to fetch PDF"}

    pdf_data = io.BytesIO(response.content)
    
    extracted_text = []
    extracted_fields = []

    with pdfplumber.open(pdf_data) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)

            tables = page.extract_tables()
            for table in tables:
                extracted_fields.append(table)

    return {
        "text": "\n".join(extracted_text),
        "fields": extracted_fields
    }

if pdf_url:
    result = extract_pdf_text(pdf_url)
    st.json(result)
