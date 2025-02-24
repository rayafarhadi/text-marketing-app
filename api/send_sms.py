import os
import json
import csv
import boto3
import mimetypes
from fastapi import FastAPI, HTTPException
from twilio.rest import Client
import base64

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

CUSTOMERS_CSV_PATH = "test_customers.csv"


def send_bulk_sms(message_text, image_data=None, image_filename=None):
    """Reads customers.csv and sends messages to non-unsubscribed customers."""
    sent_count = 0
    failed_numbers = []

    # Upload image to S3 if provided
    media_url = None
    if image_data and image_filename:
        media_url = upload_image(image_data, image_filename)

    with open(CUSTOMERS_CSV_PATH, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            phone_number = row["phone"]
            unsubscribed = row["unsubscribed"].strip().lower()

            if unsubscribed == "true":
                continue

            try:
                message = client.messages.create(
                    body=message_text,
                    from_=twilio_number,
                    to=phone_number,
                    media_url=[media_url] if media_url else None
                )
                sent_count += 1

            except Exception as e:
                failed_numbers.append(phone_number)

    return {
        "sent_count": sent_count,
        "failed_numbers": failed_numbers
    }


@app.post("/api/send_sms")
async def send_sms(data: dict):
    """Handles API requests for sending SMS."""
    try:
        message_text = data.get("message")
        image_data = data.get("image")
        image_filename = data.get("image_filename")

        if not message_text:
            raise HTTPException(status_code=400, detail="Message text is required")

        result = send_bulk_sms(message_text, image_data, image_filename)

        return {"message": "Messages sent!", "details": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

