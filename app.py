from flask import Flask, request, jsonify
import requests
from google.cloud import vision
from pdf2image import convert_from_bytes
from io import BytesIO
from transformers import pipeline

app = Flask(__name__)

# Initialize Google Cloud Vision OCR client
client = vision.ImageAnnotatorClient()

# Load Hugging Face Model for Field Classification
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# Predefined target fields
TARGET_FIELDS = [
    "Billed By", "Billing Provider NPI", "Charges", "Claim Receiver Type",
    "Clinical Signature Date", "Date of Service", "Days Units", "Diagnosis",
    "Diagnosis Pointer", "Federal TIN", "Group Number", "Insured's ID",
    "Insured's Name", "Patient's Address", "Patient's DOB", "Patient's Name",
    "Patient's SEX", "Payment Authorization Signature", "Place of Service",
    "Procedure Code", "Procedure Code Modifier", "Relationship to Insured",
    "Rendering Provider ID"
]

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
        print("🔍 Extracted OCR Text:\n", full_text[:2000])  # Limit to 2000 chars for preview

        # AI-based field classification
        structured_data = ai_field_mapping(full_text)

        return structured_data

    except Exception as e:
        return {"error": str(e)}

# AI-based function to classify text into HCFA 1500 fields
def ai_field_mapping(ocr_text):
    # Normalize OCR text
    normalized_text = ocr_text.replace("\n", " ").strip()

    # Split text into smaller parts for classification
    text_chunks = normalized_text.split(" ")
    classified_fields = {}

    # Iterate through each chunk and classify it
    for chunk in text_chunks:
        # Perform zero-shot classification
        result = classifier(chunk, TARGET_FIELDS, multi_label=True)
        predictions = result["labels"]
        scores = result["scores"]

        # Map the chunk to the highest-scoring target field
        if scores and scores[0] > 0.5:  # Confidence threshold
            field = predictions[0]
            if field not in classified_fields:
                classified_fields[field] = chunk
            else:
                classified_fields[field] += f" {chunk}"  # Combine chunks

    # Post-process the classified fields
    for field in TARGET_FIELDS:
        classified_fields.setdefault(field, "Not Found")

    return classified_fields

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "🚀 HCFA 1500 OCR API with AI. Use /parse?url=your_pdf_link to extract structured data."})

@app.route("/parse", methods=["GET"])
def parse_pdf():
    pdf_url = request.args.get("url")
    if not pdf_url:
        return jsonify({"error": "❗ Provide a PDF URL"}), 400

    extracted_data = extract_text_from_pdf(pdf_url.strip())
    return jsonify(extracted_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
