import json
import re
from datetime import datetime
from google.generativeai import GenerativeModel, configure

# Provide your API key & model
configure(api_key="AIzaSyDxgwkKSHMBRrPdI0l2R2n7ln-j5slJXfY")
model = GenerativeModel("gemini-1.5-flash")

def parse_event_from_text(text):
    """
    Parse a calendar event from text.
    Returns a dictionary with event_name, date_str, and time_str (if found).
    """
    # Check for exclusion keywords first - words that indicate this is NOT a calendar event
    exclusion_keywords = [
        "what happened", 
        "tell me about", 
        "how was", 
        "remember", 
        "past",
        "last time",
        "village trip",
        "vacation",
        "trip to",
        "journey",
        "travel",
        "holiday"
    ]
    
    # If any exclusion keyword is in the text, this is likely not a calendar event
    if any(keyword in text.lower() for keyword in exclusion_keywords):
        print(f"[Calendar] Excluded text as calendar event due to exclusion keywords: '{text}'")
        return None
    
    # Check common patterns for calendar requests
    date_patterns = [
        r'(?i)(?:on|for|at)?\s*(\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t)?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s+\d{4})',
        r'(?i)(?:on|for|at)?\s*(\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t)?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?))',
        r'(?i)(?:on|for|at)?\s*(\d{4}[- /.]\d{1,2}[- /.]\d{1,2})',
        r'(?i)(?:on|for|at)?\s*(\d{1,2}[- /.]\d{1,2}[- /.]\d{4})',
        r'(?i)(?:on|for|at)?\s*(tomorrow|today|day after tomorrow|next (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))'
    ]
    
    time_patterns = [
        r'(?i)at\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))',
        r'(?i)at\s*(\d{1,2}(?::\d{2})?\s*(?:o\'clock)?)'
    ]
    
    # Default values
    event_name = None
    date_str = ""
    time_str = ""
    
    # First, check if this text is actually asking about a calendar event
    calendar_indicators = [
        "add to calendar", "schedule", "appointment", "meeting", "event", 
        "plan", "remind me", "set a reminder"
    ]
    
    has_calendar_indicator = any(indicator in text.lower() for indicator in calendar_indicators)
    
    if not has_calendar_indicator:
        # If there's no clear calendar indicator, require more specific patterns
        # to avoid false positives
        more_specific = [
            r'(?i)(?:schedule|plan|add|create|make|set up).*(?:meeting|appointment|event|call|reminder)',
            r'(?i)(?:remind me|remember).*(?:to|about)',
            r'(?i)(?:on|for|at)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
        ]
        
        if not any(re.search(pattern, text) for pattern in more_specific):
            # Doesn't appear to be a calendar event - require both date and time patterns
            # for non-explicit calendar requests
            has_date = any(re.search(pattern, text) for pattern in date_patterns)
            has_time = any(re.search(pattern, text) for pattern in time_patterns)
            
            if not (has_date and has_time):
                print(f"[Calendar] Not enough calendar context in: '{text}'")
                return None
    
    # Extract the date
    for pattern in date_patterns:
        date_match = re.search(pattern, text)
        if date_match:
            date_str = date_match.group(1)
            break
    
    # Extract the time
    for pattern in time_patterns:
        time_match = re.search(pattern, text)
        if time_match:
            time_str = time_match.group(1)
            break
    
    # Check for specific event types first (common calendar events)
    event_types = [
        r'(?i)(?:a|an|the)?\s*(meeting)',
        r'(?i)(?:a|an|the)?\s*(appointment)',
        r'(?i)(?:a|an|the)?\s*(doctor\'s appointment)',
        r'(?i)(?:a|an|the)?\s*(dentist(?:\'s)? appointment)',
        r'(?i)(?:a|an|the)?\s*(interview)',
        r'(?i)(?:a|an|the)?\s*(call)',
        r'(?i)(?:a|an|the)?\s*(conference)',
        r'(?i)(?:a|an|the)?\s*(birthday)',
        r'(?i)(?:a|an|the)?\s*(anniversary)',
        r'(?i)(?:a|an|the)?\s*(party)',
        r'(?i)(?:a|an|the)?\s*(dinner)',
        r'(?i)(?:a|an|the)?\s*(lunch)',
        r'(?i)(?:a|an|the)?\s*(breakfast)',
        r'(?i)(?:a|an|the)?\s*(coffee)',
        r'(?i)(?:a|an|the)?\s*(date)'
    ]
    
    for pattern in event_types:
        event_match = re.search(pattern, text)
        if event_match:
            event_name = event_match.group(1)
            print(f"[Calendar] Identified specific event type: '{event_name}'")
            break
    
    # If no specific event type was found, try to extract the event name from the text
    if not event_name:
        # Try to extract the event name
        # First, remove date and time from the text
        cleaned_text = text
        if date_str:
            cleaned_text = cleaned_text.replace(date_str, "")
        if time_str:
            cleaned_text = cleaned_text.replace(time_str, "")
        
        # Remove common phrases
        for phrase in ["add to calendar", "schedule", "appointment", "remind me", "set a reminder"]:
            cleaned_text = re.sub(f"(?i){phrase}", "", cleaned_text)
        
        # Remove prepositions and time indicators
        cleaned_text = re.sub(r'(?i)(?:on|for|at|to|about|in|on the)\s+', " ", cleaned_text)
        
        # Clean up extra spaces
        cleaned_text = re.sub(r'\s+', " ", cleaned_text).strip()
        
        # The remaining text is likely the event name
        if cleaned_text:
            event_name = cleaned_text
    
    # If we have an event name, return the parsed event
    if event_name:
        print(f"[Calendar] Parsed event: '{event_name}' on '{date_str}' at '{time_str}'")
        return {
            "event_name": event_name,
            "date_str": date_str,
            "time_str": time_str
        }
    
    return None

def add_event_to_calendar(event_name, date_str, time_str):
    """
    Append to a JSON file (calendar.json) for demonstration.
    Real usage might integrate with an actual calendar system.
    """
    CALENDAR_FILE = "calendar.json"

    # Clean up the event name - remove common prefixes
    event_name = clean_event_name(event_name)

    # Load existing events
    try:
        with open(CALENDAR_FILE, "r") as f:
            events = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        events = []

    # Create new event
    new_event = {
        "event": event_name,
        "date": date_str,
        "time": time_str
    }
    
    # Check for duplicates before adding
    for event in events:
        if (event.get("event") == new_event["event"] and 
            event.get("date") == new_event["date"] and 
            event.get("time") == new_event["time"]):
            # This is a duplicate, don't add it
            print(f"Skipping duplicate event: {new_event}")
            return

    # Add new event
    events.append(new_event)

    # Save updated list
    with open(CALENDAR_FILE, "w") as f:
        json.dump(events, f, indent=2)

def clean_event_name(event_name):
    """Clean up event names by removing common prefixes and filler phrases"""
    # Common prefixes and phrases to remove
    prefixes_to_remove = [
        "remind me to ", "remind me that ", "remind me ", 
        "i have a ", "i have ", "i have an ", 
        "add a ", "add an ", "add ", 
        "schedule a ", "schedule an ", "schedule "
    ]
    
    # Convert to lowercase for easier matching
    lower_event = event_name.lower()
    
    # Try to remove each prefix
    for prefix in prefixes_to_remove:
        if lower_event.startswith(prefix):
            # Remove the prefix from the original string (preserving case)
            return event_name[len(prefix):]
    
    # Try to remove "I have a meeting" pattern
    meeting_patterns = [
        "i have a meeting", "i have meeting", 
        "a meeting", "the meeting"
    ]
    
    for pattern in meeting_patterns:
        if lower_event == pattern:
            return "meeting"
    
    # If no prefixes match, return the original
    return event_name

def handle_calendar_input(user_input):
    """
    1. Parse the user's input (with today's date).
    2. Add the event to calendar.json.
    3. Return a success string.
    """
    parsed = parse_event_from_text(user_input)
    event_name = parsed["event_name"]
    date_str   = parsed["date_str"]
    time_str   = parsed["time_str"]

    if not event_name:
        return "I'm sorry, I couldn't find an event name in what you said."

    add_event_to_calendar(event_name, date_str, time_str)

    # Construct a user-friendly response
    response_msg = f"I've added '{event_name}'"
    if date_str:
        # Format date in a more readable way
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%A, %B %d, %Y")
            response_msg += f" on {formatted_date}"
        except ValueError:
        response_msg += f" on {date_str}"
    if time_str:
        # Format time in a more readable way
        try:
            time_obj = datetime.strptime(time_str, "%H:%M")
            formatted_time = time_obj.strftime("%I:%M %p").lstrip("0").replace(" 0", " ")
            response_msg += f" at {formatted_time}"
        except ValueError:
        response_msg += f" at {time_str}"
    response_msg += " to your calendar."

    return response_msg


