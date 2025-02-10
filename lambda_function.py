import json
import boto3
import uuid
import requests

# Initialize AWS clients
s3_client = boto3.client("s3")
textract = boto3.client("textract")

# Set the S3 bucket name
BUCKET_NAME = "khcfirm"

def lambda_handler(event, context):
    """
    Lambda function to process a PDF from a URL:
    - Downloads the PDF
    - Uploads it to S3
    - Generates a presigned URL
    - Starts Textract document analysis
    """

    try:
        # Parse event body
        body = json.loads(event.get("body", "{}"))
        pdf_url = body.get("pdf_url")

        if not pdf_url:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No PDF URL provided"})
            }

        # Generate a unique filename
        unique_filename = f"uploads/temp_{uuid.uuid4().hex}.pdf"

        # Download the PDF
        response = requests.get(pdf_url)
        if response.status_code != 200:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Failed to download file from URL"})
            }

        # Upload file to S3
        s3_client.put_object(Bucket=BUCKET_NAME, Key=unique_filename, Body=response.content)

        # Generate a presigned URL for accessing the uploaded file
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": unique_filename},
            ExpiresIn=3600  # URL expires in 1 hour
        )

        # Start Textract document analysis
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
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
