from flask import Flask, request, jsonify
import requests
import pytesseract
from pdf2image import convert_from_bytes
from io import BytesIO
import re

app = Flask(__name__)

# Browser-like Headers to avoid 403 Forbidden errors
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Referer": "https://www.google.com/"
}

# Extract text from PDF using high-quality OCR
def extract_text_from_pdf(pdf_url):
    try:
        if not pdf_url.startswith("http"):
            return {"error": "Invalid URL. Must start with 'http://' or 'https://'."}

        response = requests.get(pdf_url, headers=HEADERS)  # Mimic browser request
        if response.status_code == 200:
            pdf_bytes = BytesIO(response.content)

            # Convert PDF to images for OCR
            images = convert_from_bytes(pdf_bytes.read())

            extracted_text = []
            for img in images:
                text = pytesseract.image_to_string(img, config="--psm 6")  # PSM 6 optimized for forms
                extracted_text.append(text)

            full_text = "\n".join(extracted_text)

            # Process text into structured HCFA 1500 format
            structured_data = parse_hcfa_1500(full_text)

            return structured_data

        else:
            return {"error": f"Failed to fetch PDF: HTTP {response.status_code}"}

    except Exception as e:
        return {"error": str(e)}

# Parse OCR text into key-value pairs for HCFA 1500 form
def parse_hcfa_1500(ocr_text):
    fields = {
        "Claim Receiver Type": r"(?<=Claim Receiver Type)[\s:]+([\w\s]+)",
        "Insured's ID #": r"(?<=Insured's ID #)[\s:]+([\w\d]+)",
        "Patient's Name": r"(?<=Patient's Name)[\s:]+([\w\s,]+)",
        "Patient's DOB": r"(?<=Patients DOB)[\s:]+([\d/]+)",
        "Patient's SEX": r"(?<=Patients SEX)[\s:]+([MF])",
        "Insured's Name": r"(?<=Insured's Name)[\s:]+([\w\s,]+)",
        "Patient's Address": r"(?<=Patient's Address)[\s:]+([\w\s,]+)",
        "Relationship to Insured": r"(?<=Relationship to Insured)[\s:]+([\w]+)",
        "Group Number": r"(?<=Group Number)[\s:]+([\d]+)",
        "Payment Authorization Signature": r"(?<=Payment Authorization Signature)[\s:]+([\w\s]+)",
        "Diagnosis": r"(?<=Diagnosis)[\s:]+([\w\d\.]+)",
        "Date of Service": r"(?<=DOS)[\s:]+([\d/]+)",
        "Place of Service": r"(?<=Place of Service)[\s:]+([\d]+)",
        "Procedure Code": r"(?<=Procedure Code/CPT code)[\s:]+([\w\d]+)",
        "Procedure Code Modifier": r"(?<=Procedure Code Modifier)[\s:]+([\w]+)",
        "Diagnosis Pointer": r"(?<=Diagnosis pointer)[\s:]+([\d]+)",
        "Charges": r"(?<=Charges)[\s:]+\$(\d+.\d+)",
        "Rendering Provider ID": r"(?<=Rendering Provider ID)[\s:]+([\d]+)",
        "Days/Units": r"(?<=Days/Units)[\s:]+([\d]+)",
        "Federal TIN": r"(?<=Federal TIN SSN or EIN indicator)[\s:]+([\d]+)",
        "Clinical Signature Date": r"(?<=Clinical Signature Date)[\s:]+([\w\s,]+)",
        "Billed By": r"(?<=Billed By)[\s:]+([\w\s,]+)",
        "Billing Provider NPI": r"(?<=NPI)[\s:]+([\d]+)"
    }

    structured_output = {}
    for field, regex in fields.items():
        match = re.search(regex, ocr_text, re.IGNORECASE)
        structured_output[field] = match.group(1).strip() if match else "Not Found"

    return structured_output

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "🚀 HCFA 1500 PDF Parser API. Use /parse?url=your_pdf_link to extract structured data."})

@app.route("/parse", methods=["GET"])
def parse_pdf():
    pdf_url = request.args.get("url")
    if not pdf_url:
        return jsonify({"error": "❗ Provide a PDF URL as a query parameter: `?url=your_pdf_link`"}), 400

    extracted_data = extract_text_from_pdf(pdf_url.strip())
    return jsonify(extracted_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
