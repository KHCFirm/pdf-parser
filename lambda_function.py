import json

def lambda_handler(event, context):
    """
    AWS Lambda function to handle API Gateway requests.

    :param event: The event data passed by API Gateway
    :param context: The runtime information provided by Lambda
    :return: A structured response for API Gateway
    """
    try:
        # Debugging: Print the event received
        print("Received event:", json.dumps(event))

        # Ensure the request contains a body
        if "body" not in event:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing 'body' in request."})
            }

        # Parse the request body (handle both direct input and Base64-encoded)
        body = event["body"]
        if event.get("isBase64Encoded", False):
            import base64
            body = base64.b64decode(body).decode("utf-8")

        # Convert the body to JSON
        try:
            request_data = json.loads(body)
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid JSON in request body."})
            }

        # Example: Extracting expected parameters
        name = request_data.get("name", "Guest")

        # Construct a response
        response_body = {
            "message": f"Hello, {name}! Your API Gateway Lambda function is working!"
        }

        return {
            "statusCode": 200,
            "body": json.dumps(response_body),
            "headers": {
                "Content-Type": "application/json"
            }
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
