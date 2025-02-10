import json
import boto3
import uuid
import requests
import time

# Initialize AWS Clients
s3_client = boto3.client("s3")
textract = boto3.client("textract")

# Set S3 Bucket Name
BUCKET_NAME = "khcfirm"  # 🔹 Change this to your S3 bucket name

def lambda_handler(event, context):
    try:
        # 🔹 Parse JSON input
        body = json.loads(event["body"])
        pdf_url = body.get("pdf_url")

        if not pdf_url:
            return {"statusCode": 400, "body": json.dumps({"error": "No PDF URL provided"})}

        # 🔹 Generate a unique filename
        unique_filename = f"uploads/temp_{uuid.uuid4().hex}.pdf"

        # 🔹 Download the PDF from URL
        response = requests.get(pdf_url)
        if response.status_code != 200:
            return {"statusCode": 500, "body": json.dumps({"error": "Failed to download file"})}

        # 🔹 Upload file to S3
        s3_client.put_object(Bucket=BUCKET_NAME, Key=unique_filename, Body=response.content)

        # 🔹 Generate a pre-signed URL for downloading
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": unique_filename},
            ExpiresIn=3600
        )

        # 🔹 Start Textract Document Analysis (Extract Forms & Tables)
        textract_response = textract.start_document_analysis(
            DocumentLocation={"S3Object": {"Bucket": BUCKET_NAME, "Name": unique_filename}},
            FeatureTypes=["FORMS", "TABLES"]
        )

        # 🔹 Return the Job ID for tracking
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

# 🔹 Function to retrieve extracted text once processing is complete
def get_textract_results(event, context):
    try:
        # 🔹 Get Job ID from request
        body = json.loads(event["body"])
        job_id = body.get("job_id")

        if not job_id:
            return {"statusCode": 400, "body": json.dumps({"error": "No Job ID provided"})}

        # 🔹 Poll Textract until processing is complete
        while True:
            response = textract.get_document_text_detection(JobId=job_id)
            status = response["JobStatus"]

            if status in ["SUCCEEDED", "FAILED"]:
                break

            print("Processing... Waiting for completion...")
            time.sleep(5)  # Wait before checking again

        if status == "FAILED":
            return {"statusCode": 500, "body": json.dumps({"error": "Textract processing failed"})}

        # 🔹 Extract text from Textract response
        extracted_text = []
        for block in response["Blocks"]:
            if block["BlockType"] == "LINE":
                extracted_text.append(block["Text"])

        full_text = "\n".join(extracted_text)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Text extraction completed",
                "extracted_text": full_text
            })
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
