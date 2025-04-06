import json
import os

# Path to the health data JSON file
HEALTH_DATA_FILE = "health_data.json"

# Default initial data
default_data = {
    "type": {
        "medicine": [
            {
                "name": "Amlodipine 5mg (Blood Pressure)",
                "time": "08:00 AM"
            },
            {
                "name": "Metformin 500mg (Diabetes)",
                "time": "06:30 PM"
            },
            {
                "name": "Atorvastatin 10mg (Cholesterol)",
                "time": "09:00 PM"
            }
        ],
        "food": [
            {
                "name": "Oats with banana and boiled egg",
                "time": "07:30 AM"
            },
            {
                "name": "Grilled chicken with brown rice and vegetables",
                "time": "01:00 PM"
            },
            {
                "name": "Vegetable soup with whole wheat bread",
                "time": "07:00 PM"
            }
        ],
        "exercise": [
            {
                "name": "Morning walk",
                "time": "06:30 AM"
            },
            {
                "name": "Stretching and breathing exercises",
                "time": "04:00 PM"
            },
            {
                "name": "Light yoga (Relaxation routine)",
                "time": "08:30 PM"
            }
        ]
    },
    "originalCounts": {
        "medicine": 3,
        "food": 3,
        "exercise": 3
    }
}

# Load data from JSON file or use default
def load_health_data():
    if os.path.exists(HEALTH_DATA_FILE):
        try:
            with open(HEALTH_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Ensure original counts are present
            if 'originalCounts' not in data:
                data['originalCounts'] = {
                    'medicine': len(data.get('type', {}).get('medicine', [])),
                    'food': len(data.get('type', {}).get('food', [])),
                    'exercise': len(data.get('type', {}).get('exercise', []))
                }
                save_health_data(data)  # Save updated data with counts
                
            return data
        except Exception as e:
            print(f"Error loading health data: {e}")
            # Return a copy of the default data to avoid modifying it directly
            return json.loads(json.dumps(default_data))
    else:
        # Create file with default data
        save_health_data(default_data)
        # Return a copy of the default data to avoid modifying it directly
        return json.loads(json.dumps(default_data))

# Save data to JSON file
def save_health_data(data):
    try:
        with open(HEALTH_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving health data: {e}")
        return False

def mark_done(data, type_name, name, time):
    """
    Marks an item as done by removing it from the data structure.
    
    Args:
        data (dict): The health data dictionary
        type_name (str): Category type ('medicine', 'food', 'exercise')
        name (str): Item name to mark as done
        time (str): Time of the item
        
    Returns:
        bool: True if successful, False otherwise
    """
    if type_name in data['type']:
        original_length = len(data['type'][type_name])
        data['type'][type_name] = [
            item for item in data['type'][type_name]
            if not (item['name'] == name and item['time'] == time)
        ]
        if len(data['type'][type_name]) < original_length:
            print(f"Marked '{name}' at {time} as done under '{type_name}'.")
            # Save data after marking item as done
            save_health_data(data)
            return True
        else:
            print("No match found to mark as done.")
            return False
            
        # Remove type if empty
        if not data['type'][type_name]:
            del data['type'][type_name]
            print(f"Removed empty category: {type_name}")
            # Save data after removing empty category
            save_health_data(data)
    else:
        print(f"Category '{type_name}' not found.")
        return False
    
    return True

# Load data when module is imported
data = load_health_data()

# Function to reset health data to default
def reset_health_data():
    """Reset health data to default values"""
    global data
    data = json.loads(json.dumps(default_data))
    save_health_data(data)
    return True
