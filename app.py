from flask import Flask, request, jsonify
import requests
import re
import os
import io
from google.cloud import vision
from pdf2image import convert_from_bytes
from PIL import Image, ImageEnhance, ImageFilter

app = Flask(__name__)

# Initialize Google Cloud Vision OCR client
client = vision.ImageAnnotatorClient()

# Function to extract text from a PDF using Google Cloud OCR
def extract_text_from_pdf(pdf_url):
    try:
        if not pdf_url.startswith("http"):
            return {"error": "Invalid URL. Must start with 'http://' or 'https://'."}

        # ✅ Add headers to mimic a browser request
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/pdf",
            "Referer": "https://www.google.com/"
        }

        response = requests.get(pdf_url, headers=headers)
        if response.status_code != 200:
            return {"error": f"Failed to fetch PDF: HTTP {response.status_code}"}

        pdf_bytes = io.BytesIO(response.content)

        # ✅ Convert PDF to images (High DPI for OCR accuracy)
        images = convert_from_bytes(pdf_bytes.read(), dpi=300)

        extracted_text = []
        for img in images:
            # ✅ Preprocess the image (Enhance contrast, remove noise)
            img = img.convert("L")  # Convert to grayscale
            img = img.filter(ImageFilter.SHARPEN)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2)  # Increase contrast

            # ✅ Convert image to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="JPEG")
            img_byte_arr = img_byte_arr.getvalue()

            # ✅ Use Google OCR (Document OCR Mode for Forms)
            image = vision.Image(content=img_byte_arr)
            response = client.document_text_detection(image=image)

            if response.error.message:
                return {"error": f"OCR error: {response.error.message}"}

            text = response.full_text_annotation.text
            extracted_text.append(text)

        full_text = "\n".join(extracted_text)

        # ✅ Parse text into structured HCFA 1500 fields
        structured_data = parse_hcfa_1500(full_text)

        return structured_data

    except Exception as e:
        return {"error": str(e)}

# Function to parse text into HCFA 1500 structured data
def parse_hcfa_1500(ocr_text):
    fields = {
        "Claim Receiver Type": r"Claim Receiver Type[:\s]+([\w\s]+)",
        "Insured's ID #": r"Insured['’]s ID #[:\s]+([\w\d]+)",
        "Patient's Name": r"Patient['’]s Name[:\s]+([\w\s,]+)",
        "Patient's DOB": r"Patient['’]s DOB[:\s]+([\d/]+)",
        "Patient's SEX": r"Patient['’]s SEX[:\s]+([MF])",
        "Insured's Name": r"Insured['’]s Name[:\s]+([\w\s,]+)",
        "Patient's Address": r"Patient['’]s Address[:\s]+([\w\s,]+)",
        "Relationship to Insured": r"Relationship to Insured[:\s]+([\w]+)",
        "Group Number": r"Group Number[:\s]+([\d]+)",
        "Payment Authorization Signature": r"Payment Authorization Signature[:\s]+([\w\s]+)",
        "Diagnosis": r"Diagnosis[:\s]+([\w\d\.]+)",
        "Date of Service": r"Date of Service[:\s]+([\d/]+)",
        "Place of Service": r"Place of Service[:\s]+([\d]+)",
        "Procedure Code": r"Procedure Code[:\s]+([\w\d]+)",
        "Procedure Code Modifier": r"Procedure Code Modifier[:\s]+([\w]+)",
        "Diagnosis Pointer": r"Diagnosis Pointer[:\s]+([\d]+)",
        "Charges": r"Charges[:\s]+\$?([\d,]+\.\d+)",
        "Rendering Provider ID": r"Rendering Provider ID[:\s]+([\d]+)",
        "Days/Units": r"Days/Units[:\s]+([\d]+)",
        "Federal TIN": r"Federal TIN[:\s]+([\d]+)",
        "Clinical Signature Date": r"Clinical Signature Date[:\s]+([\w\s,]+)",
        "Billed By": r"Billed By[:\s]+([\w\s,]+)",
        "Billing Provider NPI": r"Billing Provider NPI[:\s]+([\d]+)"
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

