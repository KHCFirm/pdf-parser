from flask import Flask, request, jsonify
import requests
import re
import os
from google.cloud import vision
from pdf2image import convert_from_bytes
from io import BytesIO

app = Flask(__name__)

# Initialize Google Cloud Vision OCR client
client = vision.ImageAnnotatorClient()

# Function to extract text from a PDF using Google Cloud OCR
def extract_text_from_pdf(pdf_url):
    try:
        if not pdf_url.startswith("http"):
            return {"error": "Invalid URL. Must start with 'http://' or 'https://'."}

        # Download PDF
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/pdf",
            "Referer": "https://www.google.com/"
        }
        response = requests.get(pdf_url, headers=headers)
        if response.status_code != 200:
            return {"error": f"Failed to fetch PDF: HTTP {response.status_code}"}

        pdf_bytes = BytesIO(response.content)

        # Convert PDF to images
        images = convert_from_bytes(pdf_bytes.read())

        extracted_text = []
        for img in images:
            image_content = BytesIO()
            img.save(image_content, format="JPEG")
            image_content = image_content.getvalue()

            # Google OCR request
            image = vision.Image(content=image_content)
            response = client.document_text_detection(image=image)  # ✅ Use document OCR

            if response.error.message:
                return {"error": f"OCR error: {response.error.message}"}

            # ✅ Extract structured text blocks
            text = response.full_text_annotation.text
            extracted_text.append(text)

        full_text = "\n".join(extracted_text)

        # ✅ Use improved field detection
        structured_data = parse_hcfa_1500(full_text)

        return structured_data

    except Exception as e:
        return {"error": str(e)}

# Function to parse text into HCFA 1500 structured data
def parse_hcfa_1500(ocr_text):
    fields = {
        "Claim Receiver Type": r"Claim Receiver Type\s*:\s*(.*)",
        "Insured's ID #": r"Insured.?s ID #\s*:\s*([\w\d]+)",
        "Patient's Name": r"Patient.?s Name\s*:\s*([\w\s,-]+)",
        "Patient's DOB": r"Patient.?s DOB\s*:\s*(\d{2}\/\d{2}\/\d{4})",
        "Patient's SEX": r"Patient.?s SEX\s*:\s*([MF])",
        "Insured's Name": r"Insured.?s Name\s*:\s*([\w\s,-]+)",
        "Patient's Address": r"Patient.?s Address\s*:\s*([\w\s,-]+)",
        "Relationship to Insured": r"Relationship to Insured\s*:\s*([\w]+)",
        "Group Number": r"Group Number\s*:\s*(\d+)",
        "Payment Authorization Signature": r"Payment Authorization Signature\s*:\s*([\w\s]+)",
        "Diagnosis": r"Diagnosis\s*:\s*([\w\d\.]+)",
        "Date of Service": r"DOS\s*:\s*(\d{2}\/\d{2}\/\d{4})",
        "Place of Service": r"Place of Service\s*:\s*(\d+)",
        "Procedure Code": r"Procedure Code/CPT code\s*:\s*(\d+)",
        "Procedure Code Modifier": r"Procedure Code Modifier\s*:\s*([\w]+)",
        "Diagnosis Pointer": r"Diagnosis pointer\s*:\s*(\d+)",
        "Charges": r"Charges\s*\$\s*([\d,.]+)",
        "Rendering Provider ID": r"Rendering Provider ID\s*:\s*(\d+)",
        "Days/Units": r"Days/Units\s*:\s*(\d+)",
        "Federal TIN": r"Federal TIN\s*:\s*(\d+)",
        "Clinical Signature Date": r"Clinical Signature Date\s*:\s*([\w\s,]+)",
        "Billed By": r"Billed By\s*:\s*([\w\s,]+)",
        "Billing Provider NPI": r"NPI\s*:\s*(\d+)"
    }

    structured_output = {}
    for field, regex in fields.items():
        match = re.search(regex, ocr_text, re.IGNORECASE)
        structured_output[field] = match.group(1).strip() if match else "Not Found"

    return structured_output

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "🚀 HCFA 1500 OCR API. Use /parse?url=your_pdf_link to extract structured data."})

@app.route("/parse", methods=["GET"])
def parse_pdf():
    pdf_url = request.args.get("url")
    if not pdf_url:
        return jsonify({"error": "❗ Provide a PDF URL"}), 400

    extracted_data = extract_text_from_pdf(pdf_url.strip())

    # ✅ Ensure Zapier receives a clean JSON
    return jsonify({
        "status": "success",
        "extracted_fields": extracted_data
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
