import os.path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import date
from datetime import datetime
from datetime import timedelta
import hashlib
import json
import re
from helper import get_updated_creds, is_event_declined

url_pattern = "^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"

personal_cal_id = os.getenv("PERSONAL_CALENDAR_ID")

# Time range to sync
start_date = date.today() - timedelta(days = 5)
start_date = datetime.combine(start_date, datetime.min.time()).isoformat() + 'Z'
end_date = date.today() + timedelta(days = 10)
end_date = datetime.combine(end_date, datetime.min.time()).isoformat() + 'Z'


work_calendar_creds = get_updated_creds('work_calendar_token', 'https://www.googleapis.com/auth/calendar.events.readonly')
personal_calendar_creds = get_updated_creds('personal_calendar_token', 'https://www.googleapis.com/auth/calendar.events')

def anonymize_events_data(event, title=None):
    # Fallback title
    if not title:
        title = event['summary']

    # Data to be hashed
    data = {
        "start_date": event['start'].get('date'),
        "start_dateTime": event['start'].get('dateTime'),
        "start_timeZone": event['start'].get('timeZone'),
        "end_date": event['end'].get('date'),
        "end_dateTime": event['end'].get('dateTime'),
        "end_timeZone": event['end'].get('timeZone'),
        "title": title,
        "location": event.get('location', None)
    }
    
    # Sometimes people set zoom links as the location
    if data['location'] and (re.match(url_pattern, data['location']) is not None or "zoom" in data['location'].lower()):
        data['location'] = None

    # calculate a hash based on data
    # so if a single data point change it will look like an new event
    # for calculate_changes function
    hash_data = hashlib.md5(str(data).encode()).hexdigest()

    # id changes between calendars so need to exclude it from hashed data
    # but this is still needed when deleting the event
    data["id"] = event["id"]
    return hash_data, data

def get_work_calendar_event():
    # Google Calendar API setup    
    service = build('calendar', 'v3', credentials=work_calendar_creds)

    # List events between the given dates from main calendar
    events_result = service.events().list(
        calendarId='primary', 
        timeMin=start_date, 
        singleEvents=True, 
        timeMax=end_date, 
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    anonymized_events = {}

    # anonymize every event
    for event in events:

        # outOfOffice isn't part of work
        if event['eventType'] == "outOfOffice":
            continue

        # ignore declined events
        if 'attendees' in event and is_event_declined(event['attendees']):
            continue

        title = event['summary']

        # Construct Event title based on the g suite event type
        if event['eventType'] ==  "focusTime":
            title = "👨‍💻 Focus Time"
        else:
            if 'attendees' not in event:
                title = "Work Event"
            elif len(event['attendees']) == 2:
                title = "1:1 Meeting"
            elif len(event['attendees']) > 2:
                title = f"Meeting with {len(event['attendees'])} people"
            else:
                title = "Work Event"

        # anonymize_events_data and get the hash of that
        hash_data, data = anonymize_events_data(event, title)
        anonymized_events[hash_data] = data

    return anonymized_events

def get_personal_calendar_events(calendar_id):
    # Google Calendar API setup
    service = build('calendar', 'v3', credentials=personal_calendar_creds)

    # List events between the given dates from given calendar id
    events_result = service.events().list(
        calendarId=calendar_id, 
        timeMin=start_date, 
        singleEvents=True, 
        timeMax=end_date, 
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])

    anonymized_events = {}

    # Get hashes for events
    for event in events:
        hash_data, data = anonymize_events_data(event)
        anonymized_events[hash_data] = data
    
    return anonymized_events

def calculate_changes(anonymized_events, existing_events):
    new_events = []
    changed_events = []

    # Find the events hashes exists in work calendar but not in the personal calendar
    for event in anonymized_events:
        if event not in existing_events:
            new_events.append(anonymized_events[event])

    # Find the events hashes exists in personal calendar but not in the work calendar
    for event in existing_events:
        if event not in anonymized_events:
            changed_events.append(existing_events[event])

    return new_events, changed_events
    

def update_calendar(personal_cal_id, new_events, changed_events):
    
    service = build('calendar', 'v3', credentials=personal_calendar_creds)

    # Delete the events exists in personal calendar but not in work
    for event in changed_events:
        service.events().delete(calendarId=personal_cal_id, eventId=event['id']).execute()
        print("Deleted", event)

    # Create events existing in work calendar but not in personal
    for event in new_events:
        event = {
            'summary': event['title'],
            'location': event['location'],
            'start': {
                'date': event['start_date'],
                'dateTime': event['start_dateTime'],
                'timeZone': event['start_timeZone'],
            },
            'end': {
                'date': event['end_date'],
                'dateTime': event['end_dateTime'],
                'timeZone': event['end_timeZone'],
            },
            'reminders': {
                'useDefault': False,
                'overrides': [],
            }
        }

        event = service.events().insert(calendarId=personal_cal_id, body=event).execute()
        print('Event created: %s' % (event.get('htmlLink')))

def sync():
    anonymized_events = get_work_calendar_event()
    existing_events = get_personal_calendar_events(personal_cal_id)
    new_events, changed_events = calculate_changes(anonymized_events, existing_events)
    update_calendar(personal_cal_id, new_events, changed_events)

if __name__ == '__main__':
    sync()