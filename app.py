from flask import Flask, request, jsonify
import requests
import re
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

        # Parse text into structured HCFA 1500 fields
        structured_data = parse_hcfa_1500(full_text)

        return structured_data

    except Exception as e:
        return {"error": str(e)}

# Function to parse text into HCFA 1500 structured data
def parse_hcfa_1500(ocr_text):
    """ Extracts relevant fields using regex patterns """

    # Normalize text to improve regex matching
    normalized_text = ocr_text.replace("\n", " ").strip()

    fields = {
        "Claim Receiver Type": r"Claim Receiver Type[:\s]+([\w\s]+)",
        "Insured's ID #": r"INSURED['’]?S ID\.? NUMBER[:\s]+([\w\d]+)",
        "Patient's Name": r"PATIENT['’]?S NAME[:\s]+([\w\s,]+)",
        "Patient's DOB": r"PATIENT['’]?S BIRTH DATE[:\s]+(\d{2} \d{2} \d{4})",
        "Patient's SEX": r"PATIENT['’]?S SEX[:\s]+([MF])",
        "Insured's Name": r"INSURED['’]?S NAME[:\s]+([\w\s,]+)",
        "Patient's Address": r"PATIENT['’]?S ADDRESS[:\s]+([\w\s,]+)",
        "Relationship to Insured": r"RELATIONSHIP TO INSURED[:\s]+([\w]+)",
        "Group Number": r"GROUP NUMBER[:\s]+([\d]+)",
        "Payment Authorization Signature": r"PATIENT['’]?S OR AUTHORIZED PERSON['’]?S SIGNATURE[:\s]+([\w\s]+)",
        "Diagnosis": r"DIAGNOSIS[:\s]+([\w\d\.]+)",
        "Date of Service": r"DATE OF SERVICE[:\s]+([\d/]+)",
        "Place of Service": r"PLACE OF SERVICE[:\s]+([\d]+)",
        "Procedure Code": r"PROCEDURE CODE[:\s]+([\w\d]+)",
        "Procedure Code Modifier": r"MODIFIER[:\s]+([\w]+)",
        "Diagnosis Pointer": r"DIAGNOSIS POINTER[:\s]+([\d]+)",
        "Charges": r"CHARGES[:\s]+\$?([\d.]+)",
        "Rendering Provider ID": r"RENDERING PROVIDER ID[:\s]+([\d]+)",
        "Days/Units": r"DAYS/UNITS[:\s]+([\d]+)",
        "Federal TIN": r"FEDERAL TIN[:\s]+([\d]+)",
        "Clinical Signature Date": r"CLINICIAN['’]?S SIGNATURE DATE[:\s]+([\w\s,]+)",
        "Billed By": r"BILLED BY[:\s]+([\w\s,]+)",
        "Billing Provider NPI": r"BILLING PROVIDER NPI[:\s]+([\d]+)"
    }

    structured_output = {}
    for field, regex in fields.items():
        match = re.search(regex, normalized_text, re.IGNORECASE)
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
