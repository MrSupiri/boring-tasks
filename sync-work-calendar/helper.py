from google.cloud import secretmanager
import google_crc32c
import json
import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

client = secretmanager.SecretManagerServiceClient()

def is_event_declined(attendees):
    for attendee in attendees:
        if 'self' in attendee and attendee['self']:
            return attendee['responseStatus'] == 'declined'
    return False

def get_updated_creds(secret_name, scope):
    secret_id, payload = get_secret(secret_name)
    token = json.loads(payload)
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if token:
        creds = Credentials.from_authorized_user_info(token, [scope])
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            print(f"Token for {secret_name} refreshed")
            update_secret(secret_name, secret_id, creds.to_json())
            return creds
        else:
            raise Exception(f"Unable to get token, please update {secret_name} secret with a valid token")
    return creds

def get_secret(name):
    secret_detail = f"projects/{os.getenv('PROJECT_ID')}/secrets/{name}/versions/latest"
    response = client.access_secret_version(request={"name": secret_detail})
    return response.name, response.payload.data.decode("UTF-8")


def update_secret(secret_name, secret_id, payload):
    parent = client.secret_path(os.getenv('PROJECT_ID'), secret_name)

    # To save money
    client.destroy_secret_version(request={"name": secret_id})

    # Convert the string payload into a bytes. This step can be omitted if you
    # pass in bytes instead of a str for the payload argument.
    payload = payload.encode("UTF-8")

    # Calculate payload checksum. Passing a checksum in add-version request
    # is optional.
    crc32c = google_crc32c.Checksum()
    crc32c.update(payload)

    # Add the secret version.
    response = client.add_secret_version(
        request={
            "parent": parent,
            "payload": {"data": payload, "data_crc32c": int(crc32c.hexdigest(), 16)},
        }
    )

    # Print the new secret version name.
    return response