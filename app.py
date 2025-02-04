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
            response = client.text_detection(image=image)

            if response.error.message:
                return {"error": f"OCR error: {response.error.message}"}

            text = response.full_text_annotation.text
            extracted_text.append(text)

        full_text = "\n".join(extracted_text)

        # Parse text into structured HCFA 1500 fields
        structured_data = parse_hcfa_1500(full_text)

        return structured_data

    except Exception as e:
        return {"error": str(e)}

# Function to parse text into HCFA 1500 structured data
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
    return jsonify({"message": "🚀 HCFA 1500 OCR API. Use /parse?url=your_pdf_link to extract structured data."})

@app.route("/parse", methods=["GET"])
def parse_pdf():
    pdf_url = request.args.get("url")
    if not pdf_url:
        return jsonify({"error": "❗ Provide a PDF URL"}), 400

    extracted_data = extract_text_from_pdf(pdf_url.strip())
    return jsonify(extracted_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
