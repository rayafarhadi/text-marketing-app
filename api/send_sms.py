import os
import csv
import boto3
import mimetypes
import re
from fastapi import FastAPI, HTTPException
from twilio.rest import Client
import base64

app = FastAPI()

# AWS S3 Configuration
AWS_ACCESS_KEY = os.environ["ACCESS_KEY"]
AWS_SECRET_KEY = os.environ["SECRET_KEY"]
BUCKET_NAME = os.environ["BUCKET_NAME"]

s3 = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY,
                  aws_secret_access_key=AWS_SECRET_KEY)


def upload_image(image_data, object_name):
    """Uploads an image to S3 and returns the public URL."""
    content_type, _ = mimetypes.guess_type(object_name)

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=object_name,
        Body=base64.b64decode(image_data),
        ContentType=content_type
    )

    return f"https://{BUCKET_NAME}.s3.amazonaws.com/{object_name}"


# Twilio Configuration
account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
twilio_number = os.environ["TWILIO_NUMBER"]
client = Client(account_sid, auth_token)

# Get the absolute path to the project root (where customers.csv is located)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUSTOMERS_CSV_PATH = os.path.join(PROJECT_ROOT, "test_customers.csv")


def send_bulk_sms(message_text, image_data=None, image_filename=None):
    """Reads customers.csv and sends messages to non-unsubscribed customers."""
    sent_count = 0
    failed_numbers = []

    # Upload image to S3 if provided
    media_url = None
    if image_data and image_filename:
        print("Uploading image...")
        image_filename = image_filename.strip().lower().replace(" ", "_")
        image_filename = re.sub(r"[^a-zA-Z0-9_.-]", "", image_filename)
        media_url = upload_image(image_data, image_filename)
        print(f"Image uploaded: {media_url}")

    print("Opening customers.csv...")
    with open(CUSTOMERS_CSV_PATH, newline="", encoding="utf-8") as csvfile:
        print("Reading customers.csv...")
        reader = csv.DictReader(csvfile)

        print("Sending messages...")
        for row in reader:
            phone_number = row["Phone"]
            unsubscribed = row["Unsubscribed"].strip().lower()

            if unsubscribed == "true":
                print(f"Skipping unsubscribed customer: {phone_number}")
                continue

            try:
                print(f"Sending message to {phone_number}...")
                message = client.messages.create(
                    body=message_text,
                    from_=twilio_number,
                    to=phone_number,
                    media_url=[media_url] if media_url else None
                )
                sent_count += 1
                print(f"Message sent to {phone_number}: {message.sid}")

            except Exception as e:
                print(f"Failed to send message to {phone_number}: {e}")
                failed_numbers.append(phone_number)

    return {
        "sent_count": sent_count,
        "failed_numbers": failed_numbers
    }


@app.post("/api/send_sms")
async def send_sms(data: dict):
    """Handles API requests for sending SMS."""
    try:
        print("Received API request.")
        message_text = data.get("message")
        image_data = data.get("image")
        image_filename = data.get("image_filename")

        if not message_text:
            print("Error: Message text is required")
            raise HTTPException(
                status_code=400, detail="Message text is required")

        print("Calling send_bulk_sms...")
        result = send_bulk_sms(message_text, image_data, image_filename)

        print("Messages sent!")
        return {"message": "Messages sent!", "details": result}

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
