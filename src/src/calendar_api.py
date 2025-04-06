import json
import os
import datetime
from pathlib import Path
from References import companion_calendar

# File to store calendar events
CALENDAR_FILE = "calendar.json"

def get_all_events():
    """Get all events from the calendar file"""
    try:
        if os.path.exists(CALENDAR_FILE):
            with open(CALENDAR_FILE, "r") as f:
                events = json.load(f)
                return events
        else:
            # Create empty calendar file if it doesn't exist
            with open(CALENDAR_FILE, "w") as f:
                json.dump([], f)
            return []
    except Exception as e:
        print(f"Error loading calendar events: {e}")
        return []

def convert_relative_date(date_str):
    """Convert relative date strings to YYYY-MM-DD format"""
    today = datetime.date.today()
    
    if not date_str:
        return ""
        
    date_str = date_str.lower().strip()
    
    # Handle common relative date terms
    if date_str == "today":
        return today.strftime("%Y-%m-%d")
    elif date_str == "tomorrow":
        tomorrow = today + datetime.timedelta(days=1)
        return tomorrow.strftime("%Y-%m-%d")
    elif date_str == "day after tomorrow":
        day_after = today + datetime.timedelta(days=2)
        return day_after.strftime("%Y-%m-%d")
    elif date_str.startswith("next "):
        # Handle "next monday", "next tuesday", etc.
        day_name = date_str.split("next ")[1].strip()
        day_mapping = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        if day_name in day_mapping:
            today_weekday = today.weekday()
            target_weekday = day_mapping[day_name]
            days_until = (target_weekday - today_weekday) % 7
            if days_until == 0:
                days_until = 7  # Next week's same day
            target_date = today + datetime.timedelta(days=days_until)
            return target_date.strftime("%Y-%m-%d")
    
    # If it's already in YYYY-MM-DD format, return as is
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        pass
    
    # Try other common formats
    try:
        # MM/DD/YYYY
        date_obj = datetime.datetime.strptime(date_str, "%m/%d/%Y")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        pass
    
    try:
        # MM-DD-YYYY
        date_obj = datetime.datetime.strptime(date_str, "%m-%d-%Y")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        pass
    
    # If we can't parse it, return original string for error handling
    print(f"Cannot convert relative date: {date_str}")
    return date_str

def add_event(event_name, date_str, time_str=""):
    """Add a new event to the calendar"""
    try:
        # Convert relative date to YYYY-MM-DD format
        formatted_date = convert_relative_date(date_str)
        
        # Validate date format (YYYY-MM-DD)
        if formatted_date:
            try:
                datetime.datetime.strptime(formatted_date, "%Y-%m-%d")
                date_str = formatted_date  # Use the converted date
            except ValueError as e:
                print(f"Invalid date format after conversion: {e}")
                return False
            
        # Validate time format if provided (HH:MM)
        if time_str:
            # Try to convert 12-hour format to 24-hour format
            try:
                # Check if it's in 12-hour format (e.g., "2pm", "2:30pm")
                if "am" in time_str.lower() or "pm" in time_str.lower():
                    # Handle formats like "2pm" or "2:30pm"
                    time_str = time_str.lower().replace(" ", "")
                    is_pm = "pm" in time_str
                    time_str = time_str.replace("am", "").replace("pm", "")
                    
                    # Check if it has minutes
                    if ":" in time_str:
                        hour, minute = time_str.split(":")
                        hour = int(hour)
                        if is_pm and hour < 12:
                            hour += 12
                        elif not is_pm and hour == 12:
                            hour = 0
                        time_str = f"{hour:02d}:{minute}"
                    else:
                        hour = int(time_str)
                        if is_pm and hour < 12:
                            hour += 12
                        elif not is_pm and hour == 12:
                            hour = 0
                        time_str = f"{hour:02d}:00"
                
                # Validate the final time format
                datetime.datetime.strptime(time_str, "%H:%M")
            except ValueError as e:
                print(f"Invalid time format: {e}")
                return False
            
        # Add event to calendar
        companion_calendar.add_event_to_calendar(event_name, date_str, time_str)
        return True
    except Exception as e:
        print(f"Error adding event to calendar: {e}")
        return False

def parse_event_from_text(text):
    """Parse event details from natural language text"""
    try:
        parsed = companion_calendar.parse_event_from_text(text)
        return parsed
    except Exception as e:
        print(f"Error parsing calendar event: {e}")
        return {
            "event_name": "",
            "date_str": "",
            "time_str": ""
        }

def get_events_by_date(date_str):
    """Get all events for a specific date"""
    events = get_all_events()
    return [event for event in events if event.get("date") == date_str]

def get_upcoming_events(limit=5):
    """Get upcoming events (today and future)"""
    events = get_all_events()
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    # Filter events that have a date and the date is today or in the future
    future_events = [
        event for event in events 
        if event.get("date") and event.get("date") >= today
    ]
    
    # Sort by date and time
    sorted_events = sorted(
        future_events,
        key=lambda e: (
            e.get("date", "9999-12-31"),
            e.get("time", "23:59")
        )
    )
    
    return sorted_events[:limit]

def format_event_response(event):
    """Format an event for display in chat"""
    date_part = f" on {event['date']}" if event.get("date") else ""
    time_part = f" at {event['time']}" if event.get("time") else ""
    
    return f"• {event['event']}{date_part}{time_part}"

def format_events_list(events):
    """Format a list of events for display in chat"""
    if not events:
        return "You don't have any upcoming events scheduled."
    
    formatted = ["Here are your upcoming events:"]
    for event in events:
        formatted.append(format_event_response(event))
    
    return "\n".join(formatted)

def get_monthly_calendar(year=None, month=None):
    """
    Generate a calendar for a specific month with events
    Returns a dict with calendar data for display
    """
    # Use current year/month if not specified
    today = datetime.date.today()
    year = year or today.year
    month = month or today.month
    
    # Ensure month and year are integers
    try:
        year = int(year)
        month = int(month)
    except (TypeError, ValueError):
        year = today.year
        month = today.month
    
    # Validate month range (1-12)
    if month < 1 or month > 12:
        month = today.month
        
    # Create calendar data
    calendar_data = {
        "year": year,
        "month": month,
        "month_name": datetime.date(year, month, 1).strftime("%B"),
        "days": [],
        "today": today.strftime("%Y-%m-%d")
    }
    
    # Calculate first and last day of the month properly
    first_day = datetime.date(year, month, 1)
    
    # For the last day, we need to handle the case of December correctly
    if month == 12:
        last_day = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        last_day = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
    
    # Get the weekday of the first day (0 = Monday, 6 = Sunday in Python's datetime)
    # But we want Sunday as 0, so we need to adjust
    first_weekday = first_day.weekday()
    first_weekday = (first_weekday + 1) % 7  # Adjust to Sunday = 0
    
    # Start from the first day of the week containing the first day of the month
    start_date = first_day - datetime.timedelta(days=first_weekday)
    
    # End on the last day of the week containing the last day of the month
    last_weekday = last_day.weekday()
    last_weekday = (last_weekday + 1) % 7  # Adjust to Sunday = 0
    end_date = last_day + datetime.timedelta(days=(6 - last_weekday))
    
    # Get all events for the displayed period
    all_events = get_all_events()
    
    # Fill in the days
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        
        # Find events for this date
        day_events = [event for event in all_events if event.get("date") == date_str]
        
        # Create day data
        day_data = {
            "date": date_str,
            "day": current_date.day,
            "month": current_date.month,
            "year": current_date.year,
            "is_current_month": current_date.month == month,
            "is_today": current_date.strftime("%Y-%m-%d") == today.strftime("%Y-%m-%d"),
            "events": day_events,
            "has_events": len(day_events) > 0
        }
        
        calendar_data["days"].append(day_data)
        current_date += datetime.timedelta(days=1)
    
    return calendar_data

def check_for_calendar_request(text):
    """Check if a message is calendar related"""
    # Keywords and phrases that might indicate calendar-related requests
    calendar_keywords = [
        "calendar", "schedule", "appointment", "remind", "event", 
        "meeting", "plan", "book a", "set a", "create a", "add to calendar",
        "put in my calendar", "save the date", "mark my calendar",
        "upcoming", "what do i have", "what's on my", "what is on my"
    ]
    
    lower_text = text.lower()
    
    # Date-related words that often appear in calendar requests
    date_indicators = [
        "today", "tomorrow", "next week", "next month", "monday", "tuesday",
        "wednesday", "thursday", "friday", "saturday", "sunday", "january",
        "february", "march", "april", "may", "june", "july", "august",
        "september", "october", "november", "december"
    ]
    
    # Check if the text contains calendar keywords
    contains_calendar_keyword = any(keyword in lower_text for keyword in calendar_keywords)
    
    # Check if the text contains date indicators
    contains_date_indicator = any(indicator in lower_text for indicator in date_indicators)
    
    # Check for phrases asking about schedule
    asks_about_schedule = (
        "what's my schedule" in lower_text or
        "what is my schedule" in lower_text or
        "do i have any" in lower_text or
        "show me my calendar" in lower_text or
        "show calendar" in lower_text or
        "view calendar" in lower_text or
        "open calendar" in lower_text
    )
    
    return (contains_calendar_keyword and contains_date_indicator) or asks_about_schedule 