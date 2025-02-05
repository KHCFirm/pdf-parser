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

# Get Gemini API Key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

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

        # Convert PDF to images (high-quality for OCR)
        images = convert_from_bytes(pdf_bytes.read(), dpi=300)

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

        # Log raw OCR output for debugging
        print("🔍 Extracted OCR Text:\n", full_text[:20000])  # Limit to 2000 chars for preview

        # Send extracted text to Gemini for AI-based field extraction
        structured_data = send_to_gemini(full_text)

        # ✅ Standardize Field Names Before Returning Data
        return standardize_field_names(structured_data)

    except Exception as e:
        return {"error": str(e)}

# Function to send extracted text to Gemini for AI-based field extraction
def send_to_gemini(ocr_text):
    prompt_text = f"""
    You are an AI assistant that extracts structured fields from an HCFA 1500 medical claim form.
    Given the following OCR-extracted text from an HCFA 1500 form, return structured JSON with key-value pairs.
    **Use these exact field names:**
    - insured_id
    - insured_name
    - patient_name
    - patient_birth_date
    - patient_sex
    - patient_relationship_to_insured
    - patient_address
    - patient_city
    - patient_state
    - patient_zip
    - patient_phone
    - diagnosis_codes
    - procedure_codes
    - place_of_service
    - total_charges
    - rendering_provider_id
    - federal_tax_id
    - billing_provider_npi

    OCR TEXT:
    {ocr_text}

    Return only a valid JSON object with the extracted fields.
    """

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt_text}]
            }
        ]
    }

    try:
        response = requests.post(GEMINI_URL, json=payload)
        if response.status_code == 200:
            structured_data = response.json()
            extracted_text = structured_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return {"structured_data": extracted_text}
        else:
            return {"error": f"AI API request failed: HTTP {response.status_code}, {response.text}"}

    except Exception as e:
        return {"error": str(e)}

# Function to map extracted AI fields to standardized HCFA 1500 field names
def standardize_field_names(data):
    mapping = {
        "INSURED_ID_NUMBER": "insured_id",
        "INSURED_LAST_NAME": "insured_name",
        "PATIENT_LAST_NAME": "patient_name",
        "PATIENT_BIRTH_DATE": "patient_birth_date",
        "PATIENT_SEX": "patient_sex",
        "PATIENT_RELATIONSHIP_TO_INSURED": "patient_relationship_to_insured",
        "PATIENT_ADDRESS": "patient_address",
        "PATIENT_CITY": "patient_city",
        "PATIENT_STATE": "patient_state",
        "PATIENT_ZIP_CODE": "patient_zip",
        "PATIENT_PHONE_NUMBER": "patient_phone",
        "DIAGNOSIS_CODES": "diagnosis_codes",
        "SERVICE_LINES": "procedure_codes",
        "PLACE_OF_SERVICE": "place_of_service",
        "TOTAL_CHARGE": "total_charges",
        "RENDERING_PROVIDER_ID": "rendering_provider_id",
        "FEDERAL_TIN": "federal_tax_id",
        "BILLING_PROVIDER_NPI": "billing_provider_npi",
    }

    standardized_data = {}
    for key, value in data.get("structured_data", {}).items():
        standardized_data[mapping.get(key, key)] = value  # Rename keys if found in mapping

    return standardized_data

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
