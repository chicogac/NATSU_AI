import json
from datetime import datetime, timedelta
import audio2  # Natsu AI's voice module

def check_and_remind(json_file_path, notify_only=False):
    """
    Reads calendar events from a JSON file and reminds if any event matches today.
    
    Args:
        json_file_path (str): Path to the calendar JSON file
        notify_only (bool): If True, returns reminders without speaking them
        
    Returns:
        list: List of reminder messages if notify_only is True, otherwise None
    """
    today = datetime.now().strftime("%Y-%m-%d")
    reminders = []

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            calendar = json.load(f)

        for event in calendar:
            if event.get("date") == today:
                reminder_text = f"Reminder: {event.get('event')} is today."
                if event.get("time"):
                    reminder_text += f" at {event.get('time')}"
                reminders.append({
                    "text": reminder_text,
                    "event": event.get("event"),
                    "time": event.get("time", ""),
                    "date": event.get("date"),
                    "is_today": True
                })
            
        # Check for tomorrow's events too
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        for event in calendar:
            if event.get("date") == tomorrow:
                reminder_text = f"Reminder: {event.get('event')} is tomorrow."
                if event.get("time"):
                    reminder_text += f" at {event.get('time')}"
                reminders.append({
                    "text": reminder_text,
                    "event": event.get("event"),
                    "time": event.get("time", ""),
                    "date": event.get("date"),
                    "is_today": False
                })

        if notify_only:
            return reminders
            
        for reminder in reminders:
            print(f"🔔 {reminder['text']}")
            try:
                audio2.speak(reminder['text'])
            except Exception as e:
                print(f"[Audio Error] Failed to speak reminder: {e}")

    except Exception as e:
        print(f"[Error] Could not load or parse {json_file_path}: {e}")
        if notify_only:
            return []
    
    return None if notify_only else None
