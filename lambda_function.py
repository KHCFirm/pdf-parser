import json
import boto3
import uuid
import requests

s3_client = boto3.client("s3")
textract = boto3.client("textract")

BUCKET_NAME = "khcfirm"

def lambda_handler(event, context):
    try:
        # 🔹 Debugging: Print event to CloudWatch logs
        print("Received Event:", json.dumps(event, indent=2))

        # 🔹 Check which endpoint is being called
        path = event.get("resource", "")

        # 🔹 Process PDF Upload
        if path == "/process-pdf":
            return process_pdf(event)

        # 🔹 Get Textract Results
        elif path == "/get-text":
            return get_text(event)

        # 🔹 Handle unknown routes
        else:
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid API path."})}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def process_pdf(event):
    """Handles uploading a PDF from URL, saving to S3, and starting Textract"""
    try:
        body = json.loads(event["body"])
        pdf_url = body.get("pdf_url")

        if not pdf_url:
            return {"statusCode": 400, "body": json.dumps({"error": "No PDF URL provided"})}

        # Generate a unique filename
        unique_filename = f"uploads/temp_{uuid.uuid4().hex}.pdf"

        # Download the PDF from the given URL
        response = requests.get(pdf_url)
        if response.status_code != 200:
            return {"statusCode": 500, "body": json.dumps({"error": "Failed to download file"})}

        # Upload file to S3
        s3_client.put_object(Bucket=BUCKET_NAME, Key=unique_filename, Body=response.content)

        # Generate a pre-signed URL for access
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": unique_filename},
            ExpiresIn=3600
        )

        # Start Textract analysis
        textract_response = textract.start_document_analysis(
            DocumentLocation={"S3Object": {"Bucket": BUCKET_NAME, "Name": unique_filename}},
            FeatureTypes=["FORMS", "TABLES"]
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "File uploaded and Textract processing started",
                "presigned_url": presigned_url,
                "job_id": textract_response["JobId"]
            })
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def get_text(event):
    """Retrieves extracted text from Textract using Job ID"""
    try:
        body = json.loads(event["body"])
        job_id = body.get("job_id")

        if not job_id:
            return {"statusCode": 400, "body": json.dumps({"error": "No Job ID provided"})}

        # Poll for job status
        while True:
            result = textract.get_document_analysis(JobId=job_id)
            status = result["JobStatus"]

            if status in ["SUCCEEDED", "FAILED"]:
                break

        if status == "FAILED":
            return {"statusCode": 500, "body": json.dumps({"error": "Textract processing failed."})}

        # Extract text from Textract response
        extracted_text = []
        for block in result["Blocks"]:
            if block["BlockType"] == "LINE":
                extracted_text.append(block["Text"])

        # Join text into a single response
        full_text = "\n".join(extracted_text)

        return {"statusCode": 200, "body": json.dumps({"extracted_text": full_text})}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
