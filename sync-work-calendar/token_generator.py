from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
# SCOPES = ['https://www.googleapis.com/auth/calendar.events.readonly']

flow = InstalledAppFlow.from_client_secrets_file('secrets/credentials.json', SCOPES)
creds = flow.run_local_server(port=8080, open_browser=False)

with open('secrets/token.json', 'w') as token:
    token.write(creds.to_json())