from flask import Flask, request, jsonify
from google.cloud import vision
import requests
import io

app = Flask(__name__)

# ✅ Initialize Google Cloud Vision client
client = vision.ImageAnnotatorClient()

# Extract text from PDF using Google Vision OCR
def extract_text_from_pdf(pdf_url):
    try:
        response = requests.get(pdf_url)
        if response.status_code != 200:
            return {"error": f"Failed to fetch PDF: HTTP {response.status_code}"}

        pdf_bytes = io.BytesIO(response.content)

        # ✅ Use Google Vision OCR to extract text
        image = vision.Image(content=pdf_bytes.read())
        response = client.document_text_detection(image=image)

        extracted_text = response.full_text_annotation.text
        return {"text": extracted_text} if extracted_text else {"error": "No text extracted."}

    except Exception as e:
        return {"error": str(e)}

@app.route("/parse", methods=["GET"])
def parse_pdf():
    pdf_url = request.args.get("url")
    if not pdf_url:
        return jsonify({"error": "❗ Provide a PDF URL as a query parameter."}), 400

    extracted_data = extract_text_from_pdf(pdf_url.strip())
    return jsonify(extracted_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
