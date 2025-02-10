import json
import boto3
import uuid
import requests
import time

s3_client = boto3.client("s3")
textract = boto3.client("textract")
BUCKET_NAME = "khcfirm"

def extract_text(job_id):
    """Polls Textract for completed text extraction and returns structured data."""
    while True:
        response = textract.get_document_analysis(JobId=job_id)
        status = response["JobStatus"]
        
        if status in ["SUCCEEDED", "FAILED"]:
            break
        time.sleep(5)
    
    if status == "FAILED":
        return {"error": "Textract failed."}
    
    return map_to_fields(response["Blocks"])

def map_to_fields(blocks):
    """Parses Textract blocks and maps data to structured fields."""
    extracted_data = {
        "Insurance": {},
        "Patient Information": {},
        "Insured Information": {},
        "Other Insurance": {},
        "Authorization": {},
        "Medical Information": {},
        "Services Provided": [],
        "Billing Information": {},
        "Provider Information": {}
    }
    
    lines = []
    for block in blocks:
        if block["BlockType"] == "LINE":
            lines.append(block["Text"])
    
    text = "\n".join(lines)
    
    # Mapping extracted text to fields
    extracted_data["Insurance"] = {
        "Type": extract_value(text, "CARD OUT OF STATE"),
        "Address": extract_value(text, "PO BOX"),
        "Claim Form Approval": extract_value(text, "APPROVED BY"),
        "Plan Name": extract_value(text, "HEALTH PLAN"),
        "Insured ID": extract_value(text, "BTL")
    }
    
    extracted_data["Patient Information"] = {
        "Name": extract_value(text, "PATIENT'S NAME"),
        "Date of Birth": extract_value(text, "PATIENT'S BIRTH DATE"),
        "Sex": extract_value(text, "SEX"),
        "Address": extract_value(text, "PATIENT'S ADDRESS"),
        "Relationship to Insured": extract_value(text, "PATIENT RELATIONSHIP TO INSURED")
    }
    
    extracted_data["Billing Information"] = {
        "Federal Tax ID": extract_value(text, "FEDERAL TAX I.D. NUMBER"),
        "Total Charge": extract_value(text, "TOTAL CHARGE"),
        "Accept Assignment": extract_value(text, "ACCEPT ASSIGNMENT?"),
    }
    
    return extracted_data

def extract_value(text, key):
    """Extracts values from text given a key."""
    for line in text.split("\n"):
        if key in line:
            return line.split(key)[-1].strip()
    return ""

def lambda_handler(event, context):
    try:
        body = json.loads(event["body"])
        pdf_url = body.get("pdf_url")
        if not pdf_url:
            return {"statusCode": 400, "body": json.dumps({"error": "No PDF URL provided"})}
        
        unique_filename = f"uploads/temp_{uuid.uuid4().hex}.pdf"
        response = requests.get(pdf_url)
        if response.status_code != 200:
            return {"statusCode": 500, "body": json.dumps({"error": "Failed to download file"})}
        
        s3_client.put_object(Bucket=BUCKET_NAME, Key=unique_filename, Body=response.content)
        presigned_url = s3_client.generate_presigned_url(
            "get_object", Params={"Bucket": BUCKET_NAME, "Key": unique_filename}, ExpiresIn=3600
        )
        
        textract_response = textract.start_document_analysis(
            DocumentLocation={"S3Object": {"Bucket": BUCKET_NAME, "Name": unique_filename}},
            FeatureTypes=["FORMS", "TABLES"]
        )
        
        job_id = textract_response["JobId"]
        extracted_data = extract_text(job_id)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "File uploaded and Textract processing completed",
                "structured_data": extracted_data,
                "presigned_url": presigned_url,
                "job_id": job_id
            })
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
