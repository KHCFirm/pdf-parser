from flask import Flask, request, jsonify
import requests
import pytesseract
from pdf2image import convert_from_bytes
from io import BytesIO
import re

app = Flask(__name__)

# ✅ Function to extract text from PDF using Tesseract OCR
def extract_text_from_pdf(pdf_url):
    try:
        if not pdf_url.startswith("http"):
            return {"error": "Invalid URL. Must start with 'http://' or 'https://'."}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Accept": "application/pdf",
            "Connection": "keep-alive",
            "Referer": "https://www.google.com/"
        }

        response = requests.get(pdf_url, headers=headers)
        if response.status_code != 200:
            return {"error": f"Failed to fetch PDF: HTTP {response.status_code}"}

        pdf_bytes = BytesIO(response.content)
        images = convert_from_bytes(pdf_bytes.read())

        extracted_text = []
        for img in images:
            text = pytesseract.image_to_string(img, lang="eng", config="--psm 6")
            extracted_text.append(text)

        full_text = "\n".join(extracted_text)

        # ✅ Process extracted text into structured HCFA 1500 format
        structured_data = parse_hcfa_1500(full_text)
        return structured_data

    except Exception as e:
        return {"error": str(e)}

# ✅ Function to parse HCFA 1500 fields
def parse_hcfa_1500(ocr_text):
    fields = {
        "Insured's ID #": r"Insured's ID Number:\s*([\w\d-]+)",
        "Patient's Name": r"Patient's Name:\s*([\w\s,]+)",
        "Patient's DOB": r"Patient's DOB:\s*(\d{2}/\d{2}/\d{4})",
        "Patient's SEX": r"Patient's SEX:\s*([MF])",
        "Insured's Name": r"Insured's Name:\s*([\w\s,]+)",
        "Patient's Address": r"Patient's Address:\s*([\w\s,]+)",
        "Relationship to Insured": r"Relationship to Insured:\s*(\w+)",
        "Diagnosis": r"Diagnosis:\s*([\w\d\.]+)",
        "Date of Service": r"DOS:\s*(\d{2}/\d{2}/\d{4})",
        "Procedure Code": r"Procedure Code:\s*([\w\d]+)",
        "Charges": r"Charges:\s*\$?([\d\.]+)",
        "Rendering Provider ID": r"Rendering Provider ID:\s*([\d]+)",
        "Billing Provider NPI": r"NPI:\s*([\d]+)"
    }

    structured_output = {}
    for field, regex in fields.items():
        match = re.search(regex, ocr_text, re.IGNORECASE)
        structured_output[field] = match.group(1).strip() if match else "Not Found"

    return structured_output

# ✅ Home route for API status check
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "🚀 HCFA 1500 PDF OCR API is running. Use /parse?url=your_pdf_link to extract structured data."})

# ✅ API route to parse PDFs
@app.route("/parse", methods=["GET"])
def parse_pdf():
    pdf_url = request.args.get("url")
    if not pdf_url:
        return jsonify({"error": "❗ Provide a PDF URL as a query parameter: `?url=your_pdf_link`"}), 400

    extracted_data = extract_text_from_pdf(pdf_url.strip())
    return jsonify(extracted_data)

# ✅ Run Flask app on Cloud Run's expected port (8080)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
