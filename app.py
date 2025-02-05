from flask import Flask, request, jsonify
import requests
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

        return full_text

    except Exception as e:
        return {"error": str(e)}

# Function to send data to Google Gemini AI for structured HCFA 1500 processing
def send_to_google_gemini(extracted_text):
    try:
        api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": "GeminiKey"}  # 🔹 Replace with a new API Key

        payload = {
            "contents": [{
                "parts": [{"text": f"Extracted OCR Text:\n\n{extracted_text}\n\n"
                                   f"Please extract key-value pairs for a HCFA 1500 medical form, "
                                   f"ensuring that all fields are correctly mapped to their corresponding values."}]
            }]
        }

        response = requests.post(api_url, headers=headers, params=params, json=payload)
        if response.status_code != 200:
            return {"error": f"AI API request failed: HTTP {response.status_code}, {response.text}"}

        result = response.json()
        print("🔍 AI Response:", result)
        return result

    except Exception as e:
        return {"error": str(e)}

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "🚀 HCFA 1500 OCR API with Google Gemini AI Processing. Use /parse?url=your_pdf_link to extract structured data."})

@app.route("/parse", methods=["GET"])
def parse_pdf():
    pdf_url = request.args.get("url")
    if not pdf_url:
        return jsonify({"error": "❗ Provide a PDF URL"}), 400

    # Step 1: Extract text from PDF
    extracted_text = extract_text_from_pdf(pdf_url.strip())
    if "error" in extracted_text:
        return jsonify(extracted_text), 500

    # Step 2: Send extracted text to AI for structured data extraction
    ai_response = send_to_google_gemini(extracted_text)
    return jsonify({"extracted_fields": ai_response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
