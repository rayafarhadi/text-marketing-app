import os
import csv
from twilio.rest import Client
import boto3
import mimetypes

# AWS IAM user credentials
AWS_ACCESS_KEY = os.environ["ACCESS_KEY"]
AWS_SECRET_KEY = os.environ["SECRET_KEY"]
BUCKET_NAME = os.environ["BUCKET_NAME"]

# Initialize S3 client
s3 = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY,
                  aws_secret_access_key=AWS_SECRET_KEY)


def upload_image(file_path, object_name):
    """Uploads an image to S3 and makes it public."""
    content_type, _ = mimetypes.guess_type(file_path)
    s3.upload_file(file_path, BUCKET_NAME, object_name,
                   ExtraArgs={"ContentType": content_type})
    return f"https://{BUCKET_NAME}.s3.amazonaws.com/{object_name}"


# Example Usage
image_url = upload_image("twilio_env/test_flyer.jpg", "test_flyer.jpg")
print("Uploaded Image URL:", image_url)


# Your Account SID and Auth Token from twilio.com/console
account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
client = Client(account_sid, auth_token)

csv_file_path = "text-marketing/test_customers.csv"

with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)

    for row in reader:
        phone_number = row["Phone"]
        unsubscribed = row["Unsubscribed"].strip().lower()

        if unsubscribed == "true":
            continue

    message = client.messages.create(
        body="Hello, this is a test message with an image!",
        from_='+13656591776',  # Your Twilio number
        to='+14168079262',      # Customer's phone number
        media_url=[image_url]
    )

    print(message.sid)
