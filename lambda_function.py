import json
import boto3
import uuid
import requests
import time
import openai  # OpenAI API

# AWS clients
s3_client = boto3.client("s3")
textract = boto3.client("textract")

BUCKET_NAME = "khcfirm"

def lambda_handler(event, context):
    try:
        print("Event received:", json.dumps(event))  # Debug log
        
        # Get PDF URL from request
        body = json.loads(event.get("body", "{}"))
        pdf_url = body.get("pdf_url")
        if not pdf_url:
            return {"statusCode": 400, "body": json.dumps({"error": "No PDF URL provided"})}

        # Generate a unique filename
        unique_filename = f"uploads/temp_{uuid.uuid4().hex}.pdf"

        # Download the PDF
        response = requests.get(pdf_url)
        if response.status_code != 200:
            return {"statusCode": 500, "body": json.dumps({"error": "Failed to download file"})}

        # Upload to S3
        s3_client.put_object(Bucket=BUCKET_NAME, Key=unique_filename, Body=response.content)
        print(f"✅ Uploaded to S3: {unique_filename}")

        # Start Textract job
        textract_response = textract.start_document_text_detection(
            DocumentLocation={"S3Object": {"Bucket": BUCKET_NAME, "Name": unique_filename}}
        )

        job_id = textract_response["JobId"]
        print(f"📜 Textract Job Started: {job_id}")

        # Wait for Textract to finish
        while True:
            result = textract.get_document_text_detection(JobId=job_id)
            status = result["JobStatus"]
            if status in ["SUCCEEDED", "FAILED"]:
                break
            print("Processing... Waiting for completion...")
            time.sleep(5)

        if status == "FAILED":
            return {"statusCode": 500, "body": json.dumps({"error": "Textract failed."})}

        # Extract text from Textract response
        extracted_text = []
        for block in result["Blocks"]:
            if block["BlockType"] == "LINE":
                extracted_text.append(block["Text"])

        full_text = "\n".join(extracted_text)
        print(f"📜 Extracted Text:\n{full_text}")

        # Send extracted text to AI for intelligent mapping
        structured_data = map_text_to_fields(full_text)

        return {
            "statusCode": 200,
            "body": json.dumps({"structured_data": structured_data})
        }

    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")  # Log error details
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

# Function to send text to AI for field mapping
def map_text_to_fields(text):
    openai.api_key = OPENAI_API_KEY  # Set OpenAI API key

    # AI Prompt to extract structured fields
    prompt = f"""
    You are an expert at extracting structured data from text.
    The following text is extracted from an insurance form. 
    Map it to a structured JSON format with key-value pairs.

    Extracted Text:
    {text}

    Output only a JSON object containing structured fields like:
    - Insurance Information
    - Patient Information
    - Insured Information
    - Diagnosis and Medical Details
    - Billing and Services Provided

    Example Output Format:
    {{
      "Insurance": {{
        "Type": "",
        "Address": "",
        "Plan Name": "",
        "Insured ID": ""
      }},
      "Patient Information": {{
        "Name": "",
        "Date of Birth": "",
        "Sex": "",
        "Address": "",
        "Relationship to Insured": ""
      }},
      "Medical Information": {{
        "Diagnosis Codes": [""],
        "Current Illness/Injury Date": "",
        "Unable to Work Dates": {{"From": "", "To": ""}}
      }},
      "Services Provided": [
        {{
          "Date of Service": "",
          "Procedure Code": "",
          "Modifier": "",
          "Charge": "",
          "Provider NPI": ""
        }}
      ],
      "Billing Information": {{
        "Total Charge": "",
        "Amount Paid": ""
      }}
    }}
    """

    # Call OpenAI API (GPT-3.5-Turbo)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are an expert at text extraction."},
                  {"role": "user", "content": prompt}],
        max_tokens=800
    )

    # Parse response
    ai_output = response["choices"][0]["message"]["content"]
    print("🔍 AI Structured Data:", ai_output)

    return json.loads(ai_output)  # Convert AI output to JSON
