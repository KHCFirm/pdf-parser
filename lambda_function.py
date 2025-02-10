import json
import boto3
import uuid
import requests

s3_client = boto3.client("s3")
textract = boto3.client("textract")

BUCKET_NAME = "khcfirm"

def lambda_handler(event, context):
    try:
        # Get PDF URL from request
        body = json.loads(event["body"])
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

        # Generate a pre-signed URL
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": unique_filename},
            ExpiresIn=3600
        )

        # Start Textract job
        textract_response = textract.start_document_analysis(
            DocumentLocation={"S3Object": {"Bucket": BUCKET_NAME, "Name": unique_filename}},
            FeatureTypes=["FORMS", "TABLES"]
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "File uploaded and processing started",
                "presigned_url": presigned_url,
                "job_id": textract_response["JobId"]
            })
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
