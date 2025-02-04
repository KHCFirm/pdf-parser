from flask import Flask, request, jsonify
import requests
import PyPDF2
from io import BytesIO

app = Flask(__name__)

# Extract text from PDF
def extract_text_from_pdf(pdf_url):
    try:
        # Ensure URL starts with http or https
        if not pdf_url.startswith("http"):
            return "Error: Invalid URL. Must start with 'http://' or 'https://'."

        response = requests.get(pdf_url)
        if response.status_code == 200:
            pdf_file = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
            return text if text else "No extractable text found in the PDF."
        else:
            return f"Failed to fetch PDF: HTTP {response.status_code}"
    except Exception as e:
        return f"Error processing PDF: {str(e)}"

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "🚀 This is a PDF Parser API. Use /parse?url=your_pdf_link to extract text."})

@app.route("/parse", methods=["GET"])
def parse_pdf():
    pdf_url = request.args.get("url")
    if not pdf_url:
        return jsonify({"error": "❗ Provide a PDF URL as a query parameter: `?url=your_pdf_link`"}), 400

    extracted_text = extract_text_from_pdf(pdf_url.strip())
    return jsonify({"text": extracted_text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
