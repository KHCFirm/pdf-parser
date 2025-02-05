from flask import Flask, request, jsonify
import requests
import os
from pdf2image import convert_from_bytes
from io import BytesIO
import base64

app = Flask(__name__)

# Get Gemini API Key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro-vision:generateContent?key={GEMINI_API_KEY}"

# Function to extract text from a PDF using Gemini's vision model
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
            # Convert image to Base64
            image_buffer = BytesIO()
            img.save(image_buffer, format="JPEG")
            image_base64 = base64.b64encode(image_buffer.getvalue()).decode("utf-8")

            # Send image to Gemini for OCR
            ocr_text = send_image_to_gemini(image_base64)
            extracted_text.append(ocr_text)

        full_text = "\n".join(extracted_text)

        # Log raw OCR output for debugging
        print("🔍 Extracted OCR Text:\n", full_text[:20000])  # Limit to 2000 chars for preview

        # Send extracted text to Gemini for AI-based field extraction
        structured_data = send_to_gemini(full_text)

        return structured_data

    except Exception as e:
        return {"error": str(e)}

# Function to send image to Gemini for OCR
def send_image_to_gemini(image_base64):
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(GEMINI_URL, json=payload)
        if response.status_code == 200:
            structured_data = response.json()
            extracted_text = structured_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return extracted_text
        else:
            return f"OCR API request failed: HTTP {response.status_code}, {response.text}"

    except Exception as e:
        return str(e)

# Function to send extracted text to Gemini for AI-based field extraction
def send_to_gemini(ocr_text):
    prompt_text = f"""
    You are an AI assistant that extracts structured fields from an HCFA 1500 medical claim form.
    Given the following OCR-extracted text from an HCFA 1500 form, return structured JSON with key-value pairs.
    Fields:
    - Patient's Name
    - Patient's DOB
    - Patient's SEX
    - Insured's Name
    - Insured's ID
    - Diagnosis Codes
    - Procedure Codes
    - Place of Service
    - Total Charges
    - Rendering Provider ID
    - Federal Tax ID
    - Billing Provider NPI

    OCR TEXT:
    {ocr_text}

    Return a valid JSON object with the extracted fields.
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
