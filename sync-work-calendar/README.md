# Sync Work Calendar

Anonymize and copy calendar event from work calendar to personal calendar to make it eaiser manage my time.

## Usage

1. Place [client credentials](https://console.cloud.google.com/apis/credentials) JSON in `secrets/credentials.json`
2. Generate `work_calendar_token` and `personal_calendar_token` using `token_generator.py`
3. Upload `work_calendar_token` and `personal_calendar_token` Google Cloud secret manager.
4. Create a service account with Admin access to secret manager.
5. Download the service account credentials and set `GOOGLE_APPLICATION_CREDENTIALS` as the location for the file.
6. Set following environment variables with relevant values.

        ```
        PERSONAL_CALENDAR_ID=@group.calendar.google.com
        PROJECT_ID=
        GOOGLE_APPLICATION_CREDENTIALS=
        ```
7. Run `python3 sync.py`
