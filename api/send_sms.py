import os
import csv
import json
from twilio.rest import Client
import boto3
import mimetypes

# AWS IAM user credentials
AWS_ACCESS_KEY = os.environ["ACCESS_KEY"]
AWS_SECRET_KEY = os.environ["SECRET_KEY"]
BUCKET_NAME = os.environ["BUCKET_NAME"]
ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_NUMBER = os.environ["TWILIO_NUMBER"]
client = Client(ACCOUNT_SID, AUTH_TOKEN)
customers_file_path = "/text-marketing/test_customers.csv"


# Initialize S3 client
s3 = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY,
                  aws_secret_access_key=AWS_SECRET_KEY)


def upload_image(file_path, object_name):
    """Uploads an image to S3 and makes it public."""
    content_type, _ = mimetypes.guess_type(file_path)
    s3.upload_file(file_path, BUCKET_NAME, object_name,
                   ExtraArgs={"ContentType": content_type})
    return f"https://{BUCKET_NAME}.s3.amazonaws.com/{object_name}"


def send_bulk_sms(message_text, image_data=None, image_filename=None):
    sent_count = 0
    failed_numbers = []

    media_url = None
    if image_data and image_filename:
        media_url = upload_image(image_data, image_filename)

    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            phone_number = "+1" + row["Phone"]
            unsubscribed = row["Unsubscribed"]

            if unsubscribed == "true":
                print(f"Skipping unsubscribed number: {phone_number}")
                continue

            try:
                message = client.messages.create(
                    body=message_text,
                    from_=TWILIO_NUMBER,
                    to=phone_number,
                    media_url=[media_url] if media_url else None
                )
                sent_count += 1
                print(f"Message sent to {phone_number}, SID: {message.sid}")

            except Exception as e:
                print(f"Failed to send message to {phone_number}: {str(e)}")
                failed_numbers.append(phone_number)
    return {
        sent_count: sent_count,
        failed_numbers: failed_numbers
    }


def handler(event, context):

    try:
        # Parse incoming request body
        body = json.loads(event["body"])
        message_text = body.get("message")
        image_data = body.get("image")
        image_filename = body.get("image_filename")

        if not message_text:
            return {"statusCode": 400, "body": json.dumps({"error": "Message text is required"})}

        result = send_bulk_sms(message_text, image_data, image_filename)

        return {"statusCode": 200, "body": json.dumps({"message": "Message sent successfully", "result": result})}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
