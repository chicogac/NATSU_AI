from flask import Flask, render_template, request, jsonify, send_file
import os
import sys
import tempfile
import time
import random
import json
import datetime
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import uuid
import base64
import traceback
from flask_cors import CORS
from datetime import datetime, timedelta

# Add the References directory to the path so we can import from it
sys.path.append(os.path.join(os.path.dirname(__file__), 'References'))

# Use try/except to handle missing dependencies
try:
    import memory
    memory_available = True
    print("Memory module imported successfully")
except ImportError as e:
    memory_available = False
    print(f"Warning: memory module could not be imported: {e}")

# Try to import news module
try:
    from References import news
    news_available = True
    print("News module imported successfully")
except ImportError as e:
    news_available = False
    print(f"Warning: news module could not be imported: {e}")

# Import the lite version of audio2 that doesn't depend on numpy
try:
    import audio2_lite as audio2
    audio_available = True
    print("Audio lite module imported successfully")
except ImportError as e:
    audio_available = False
    print(f"Warning: audio2_lite module could not be imported: {e}")

# Try to import calendar module
try:
    from References import calendar_api
    from References import companion_calendar
    calendar_available = True
    print("Calendar module imported successfully")
except ImportError as e:
    calendar_available = False
    print(f"Warning: calendar module could not be imported: {e}")

# Try to import Google Generative AI for embeddings
try:
    import google.generativeai as genai
    genai_available = True
    print("Google Generative AI module imported successfully")
except ImportError as e:
    genai_available = False
    print(f"Warning: google.generativeai module could not be imported: {e}")

# Try to import reminder module
try:
    from References import reminder
    reminder_available = True
    print("Reminder module imported successfully")
except ImportError as e:
    reminder_available = False
    print(f"Warning: reminder module could not be imported: {e}")

# Try to import medical record module
try:
    from References import medical_record
    medical_record_available = True
    print("Medical record module imported successfully")
except ImportError as e:
    medical_record_available = False
    print(f"Warning: medical record module could not be imported: {e}")

app = Flask(__name__)

# Directory for storing news data
NEWS_OUTPUT_DIR = "news_data"
if not os.path.exists(NEWS_OUTPUT_DIR):
    os.makedirs(NEWS_OUTPUT_DIR)

# Directory for story images
STORY_IMAGES_DIR = "story_images"
STORY_JSON_PATH = "story.json"
EMBEDDINGS_FILE = "story_embeddings.npz"

# RAG configuration
RAG_SIMILARITY_THRESHOLD = 0.70
RAG_TOP_N = 3
EMBEDDING_MODEL_NAME = 'models/embedding-001'

# Initialize RAG variables
story_chunks = None
story_embeddings = None
story_media_ids = None
rag_enabled = False

# Load embeddings if available
if genai_available:
    try:
        # Configure Google Generative AI
        api_key = os.environ.get("GOOGLE_API_KEY") or ""
        genai.configure(api_key=api_key)
        
        print(f"--- Attempting to load story embeddings from: {EMBEDDINGS_FILE} ---")
        if os.path.exists(EMBEDDINGS_FILE):
            with np.load(EMBEDDINGS_FILE, allow_pickle=True) as data:
                # Check for all required keys
                if 'chunks' in data and 'embeddings' in data and 'media_ids' in data:
                    story_chunks = data['chunks']
                    story_embeddings = data['embeddings']
                    story_media_ids = data['media_ids']

                    # Validation
                    valid_load = True
                    if not (isinstance(story_chunks, np.ndarray) and story_chunks.ndim == 1): 
                        valid_load = False
                        print("Warning: 'chunks' format invalid.")
                    if not (isinstance(story_embeddings, np.ndarray) and story_embeddings.ndim == 2): 
                        valid_load = False
                        print("Warning: 'embeddings' format invalid.")
                    if not (isinstance(story_media_ids, np.ndarray) and story_media_ids.ndim == 1): 
                        valid_load = False
                        print("Warning: 'media_ids' format invalid.")
                    
                    # Check lengths match
                    if not (len(story_chunks) == story_embeddings.shape[0] == len(story_media_ids)):
                        valid_load = False
                        print(f"Warning: Data length mismatch! Chunks:{len(story_chunks)}, Embeds:{story_embeddings.shape[0]}, MediaIDs:{len(story_media_ids)}")

                    if valid_load and len(story_chunks) > 0:
                        print(f"Successfully loaded {len(story_chunks)} chunks, embeddings, and associated media IDs. RAG Enabled.")
                        rag_enabled = True
                    else:
                        print("Warning: Data validation failed. RAG disabled.")
                else:
                    print(f"Warning: Embeddings file missing required keys. RAG disabled.")
        else: 
            print(f"Warning: Embeddings file '{EMBEDDINGS_FILE}' not found. RAG disabled.")
    except Exception as e: 
        print(f"Error loading embeddings: {e}")
        print("RAG disabled.")

def get_relevant_context(query):
    """
    Retrieves relevant text chunks AND associated media IDs.
    Returns: tuple (context_string, list_of_media_ids) or (None, None)
    """
    if not rag_enabled or not genai_available: 
        return None, None  # Return tuple indicating failure
    
    global story_chunks, story_embeddings, story_media_ids  # Access all loaded data

    try:
        print(f"   [RAG Debug] Embedding query: '{query[:50]}...'")
        query_embedding_result = genai.embed_content(
            model=EMBEDDING_MODEL_NAME, content=query, task_type="RETRIEVAL_QUERY")
        query_embedding = np.array(query_embedding_result['embedding']).reshape(1, -1)

        similarities = cosine_similarity(query_embedding, story_embeddings)[0]

        if len(similarities) > 0:
            max_similarity_index = np.argmax(similarities)
            max_similarity = similarities[max_similarity_index]
            print(f"   [RAG Debug] Max similarity found: {max_similarity:.4f} (Threshold is {RAG_SIMILARITY_THRESHOLD})")
        else: 
            max_similarity = -1.0

        if max_similarity >= RAG_SIMILARITY_THRESHOLD:
            print(f"   [RAG Info] Similarity meets threshold. Retrieving top {RAG_TOP_N}.")
            num_to_retrieve = min(RAG_TOP_N, len(similarities))
            top_n_indices = np.argsort(similarities)[-num_to_retrieve:][::-1]

            # Retrieve Chunks AND Media IDs
            relevant_chunks_text = [story_chunks[i] for i in top_n_indices]
            relevant_media_lists = [story_media_ids[i] for i in top_n_indices]

            # Combine into context string and unique media IDs
            context_string = "\n---\n".join(relevant_chunks_text)
            # Flatten the list of lists and get unique IDs
            unique_media_ids = sorted(list(set(
                media_id for sublist in relevant_media_lists for media_id in sublist if media_id
            )))

            print(f"   [RAG Debug] Associated Media IDs found: {unique_media_ids if unique_media_ids else 'None'}")
            return context_string, unique_media_ids
        else:
            return None, None  # Return tuple indicating threshold not met
    except Exception as e: 
        print(f"   [RAG Error] {e}")
        return None, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calendar')
def calendar_page():
    """Render the dedicated calendar page"""
    return render_template('calendar.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message', '')
    
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400
    
    # Initialize response variables
    response_data = {'response': ''}
    
    try:
        print(f"\n==== CHAT REQUEST: '{user_input[:50]}...' ====")
        
        # Check for calendar requests first if the module is available
        if calendar_available and calendar_api.check_for_calendar_request(user_input):
            print("Calendar request detected - delegating to handler")
            return handle_calendar_request(user_input)
        
        if not memory_available:
            # Fallback response if memory module is not available
            response_data['response'] = f"Echo: {user_input} (Note: Memory module is not available)"
            return jsonify(response_data)
            
        print(f"Processing with memory module...")
            
        # Use the memory module to get a response
        try:
            # Add timeout for memory module calls
            import threading
            import time
            
            response = None
            error_occurred = False
            
            def get_memory_response():
                nonlocal response, error_occurred
                try:
                    response = memory.chat_with_openai(user_input)
                except Exception as e:
                    error_occurred = True
                    print(f"Error in memory module: {e}")
                    
            # Start memory processing in thread
            thread = threading.Thread(target=get_memory_response)
            thread.start()
            
            # Wait with timeout (10 seconds)
            thread.join(timeout=10)
            
            if thread.is_alive() or error_occurred:
                # Timeout occurred or error in thread
                if thread.is_alive():
                    print("WARNING: Memory module response timed out after 10 seconds")
                
                # Return fallback response
                response_data['response'] = "I'm sorry, I couldn't process your request in time. Please try again or rephrase your question."
                return jsonify(response_data)
                
            # Validate response exists
            if response is None:
                print("WARNING: Memory module returned None")
                response_data['response'] = "I'm sorry, I couldn't generate a response. Please try again."
                return jsonify(response_data)
                
            # Handle response based on type
            print(f"Memory module returned response of type: {type(response)}")
            
            # Check if this is a news request (response will be a dict with type="news")
            if isinstance(response, dict) and response.get('type') == 'news':
                print("News request detected - delegating to handler")
                return handle_news_request(user_input)
                
            # Check if this is a calendar request (response will be a dict with type="calendar")
            if isinstance(response, dict) and response.get('type') == 'calendar':
                print("Calendar display request detected - delegating to handler")
                return handle_calendar_display(response.get('message', 'Here is your calendar.'))
            
            # Check if we have a RAG-enhanced response (with story_data)
            if isinstance(response, dict) and 'story_data' in response:
                print("Story response already formatted correctly by memory module - sending to frontend")
                print(f"DEBUG RAG RESPONSE - Full structure: {json.dumps(response, default=str, indent=2)}")
                print(f"DEBUG RAG RESPONSE - Media IDs: {response.get('story_data', {}).get('media_ids', [])}")
                return jsonify(response)
                
            # The old format handling (for backward compatibility)
            if isinstance(response, dict) and 'media_ids' in response:
                print("Converting old RAG response format to new format")
                print(f"DEBUG RAG RESPONSE - Old format media_ids: {response.get('media_ids', [])}")
                # Restructure the response to match what the frontend expects
                story_response = {
                    'response': response.get('response', ''),
                    'story_data': {
                        'has_story_data': True,
                        'media_ids': response.get('media_ids', [])
                    }
                }
                print(f"Sending structured story response to frontend")
                print(f"DEBUG RAG RESPONSE - Converted structure: {json.dumps(story_response, default=str, indent=2)}")
                return jsonify(story_response) # RETURN HERE - DO NOT CONTINUE
            
            # Handle string responses and any other response types
            if isinstance(response, str):
                print("Standard text response received")
                response_data['response'] = response
                return jsonify(response_data)
            
            # For any unexpected response type, convert to string
            print(f"WARNING: Unexpected response type: {type(response)}")
            try:
                response_data['response'] = str(response)
            except:
                response_data['response'] = "I received your message but couldn't generate a proper response."
            
            return jsonify(response_data)
            
        except Exception as e:
            print(f"Error using memory module: {e}")
            response_data['response'] = f"Error processing your request: {str(e)}"
            return jsonify(response_data)
            
    except Exception as e:
        print(f"Unhandled error in chat endpoint: {e}")
        return jsonify({'error': f'Server error: {str(e)}', 'response': "I'm sorry, an unexpected error occurred."}), 500

def validate_story_response(response):
    """Validate that a story response has the correct structure"""
    if not isinstance(response, dict):
        return False
        
    # Check for required keys
    if 'response' not in response or 'media_ids' not in response:
        return False
        
    # Check that response is a string
    if not isinstance(response.get('response'), str):
        return False
        
    # Check that media_ids is a list
    if not isinstance(response.get('media_ids'), list):
        return False
        
    # Response must not be empty
    if not response.get('response', '').strip():
        return False
        
    return True

def handle_calendar_request(user_input):
    """Handle calendar-related requests"""
    if not calendar_available:
        return jsonify({'response': "I'm sorry, but I can't access your calendar right now. The calendar module is not available."})
    
    try:
        # Check if this is a request to view the calendar
        if any(phrase in user_input.lower() for phrase in ["show calendar", "view calendar", "open calendar", "see my calendar"]):
            # Just return calendar data for display
            return handle_calendar_display("Here's your calendar.")
        
        # Check if this is a request for upcoming events
        if any(phrase in user_input.lower() for phrase in ["upcoming events", "what do i have", "what's scheduled", "what is scheduled"]):
            # Get upcoming events
            events = calendar_api.get_upcoming_events(limit=5)
            
            # Format response text
            response_text = calendar_api.format_events_list(events)
            
            # Return calendar data for display plus the text response
            return handle_calendar_display(response_text)
        
        # Otherwise, try to parse an event from the text
        parsed_event = calendar_api.parse_event_from_text(user_input)
        
        # If we parsed an event with at least a name, add it
        if parsed_event and parsed_event.get('event_name'):
            # Add the event to calendar
            event_added = calendar_api.add_event(
                parsed_event.get('event_name'),
                parsed_event.get('date_str', ''),
                parsed_event.get('time_str', '')
            )
            
            if event_added:
                # Get a confirmation message
                calendar_response = companion_calendar.handle_calendar_input(user_input)
                
                # Return with calendar data for display
                return handle_calendar_display(calendar_response)
            else:
                return jsonify({'response': "I'm sorry, I couldn't add that event to your calendar. Please try again with a clearer date and time."})
        else:
            # If we couldn't parse an event, just show the calendar
            return handle_calendar_display("I see you want to do something with your calendar, but I'm not sure what. Here's your calendar view.")
    except Exception as e:
        print(f"Error handling calendar request: {e}")
        return jsonify({'response': f"I encountered an error with your calendar request: {str(e)}"})

def handle_calendar_display(response_text):
    """Prepare calendar data for display and return response with it"""
    try:
        # Get current month's calendar data
        calendar_data = calendar_api.get_monthly_calendar()
        
        # Get upcoming events
        upcoming_events = calendar_api.get_upcoming_events()
        
        # Return response with calendar data
        return jsonify({
            'response': response_text,
            'calendar_data': {
                'calendar': calendar_data,
                'upcoming_events': upcoming_events,
                'has_calendar': True
            }
        })
    except Exception as e:
        print(f"Error preparing calendar data: {e}")
        return jsonify({'response': f"I encountered an error while preparing your calendar: {str(e)}"})

@app.route('/api/calendar/events', methods=['GET'])
def get_calendar_events():
    """Get all calendar events"""
    if not calendar_available:
        return jsonify({'error': 'Calendar module not available'}), 500
    
    try:
        events = calendar_api.get_all_events()
        return jsonify({'events': events})
    except Exception as e:
        return jsonify({'error': f'Error getting calendar events: {str(e)}'}), 500

@app.route('/api/calendar/events/date/<date_str>', methods=['GET'])
def get_events_for_date(date_str):
    """Get events for a specific date"""
    if not calendar_available:
        return jsonify({'error': 'Calendar module not available'}), 500
    
    try:
        events = calendar_api.get_events_by_date(date_str)
        return jsonify({'events': events, 'date': date_str})
    except Exception as e:
        return jsonify({'error': f'Error getting events for date: {str(e)}'}), 500

@app.route('/api/calendar/events/upcoming', methods=['GET'])
def get_upcoming_events():
    """Get upcoming calendar events"""
    if not calendar_available:
        return jsonify({'error': 'Calendar module not available'}), 500
    
    try:
        limit = request.args.get('limit', 5, type=int)
        events = calendar_api.get_upcoming_events(limit=limit)
        return jsonify({'events': events})
    except Exception as e:
        return jsonify({'error': f'Error getting upcoming events: {str(e)}'}), 500

@app.route('/api/calendar/month', methods=['GET'])
def get_calendar_month():
    """Get calendar data for a specific month"""
    if not calendar_available:
        return jsonify({'error': 'Calendar module not available'}), 500
    
    try:
        year = request.args.get('year', None, type=int)
        month = request.args.get('month', None, type=int)
        
        calendar_data = calendar_api.get_monthly_calendar(year, month)
        return jsonify({'calendar': calendar_data})
    except Exception as e:
        return jsonify({'error': f'Error getting calendar month: {str(e)}'}), 500

@app.route('/api/calendar/add', methods=['POST'])
def add_calendar_event():
    """Add a new event to the calendar"""
    if not calendar_available:
        return jsonify({'error': 'Calendar module not available'}), 500
    
    try:
        data = request.json
        event_name = data.get('event_name')
        date_str = data.get('date_str', '')
        time_str = data.get('time_str', '')
        
        if not event_name:
            return jsonify({'error': 'Event name is required'}), 400
        
        success = calendar_api.add_event(event_name, date_str, time_str)
        
        if success:
            return jsonify({'success': True, 'message': 'Event added successfully'})
        else:
            return jsonify({'error': 'Failed to add event'}), 500
    except Exception as e:
        return jsonify({'error': f'Error adding calendar event: {str(e)}'}), 500

def handle_news_request(user_input):
    """Handle news requests by fetching and processing news articles"""
    if not news_available:
        return jsonify({'response': "I'm sorry, but I can't access the news right now. The news module is not available."})
    
    try:
        # Fetch news articles
        fetch_response = "I'm fetching the latest news headlines for you."
        
        # Fetch news articles and save them
        news_files = news.fetch_live_news()
        
        if not news_files or len(news_files) == 0:
            return jsonify({'response': "I'm sorry, but I couldn't fetch any news articles at the moment. Please try again later."})
        
        # Load the first 5 articles and create a formatted response
        headlines = []
        article_data = []
        
        for i, file in enumerate(news_files[:5], 1):
            with open(file, 'r', encoding='utf-8') as f:
                article = json.load(f)
                headline = f"{i}. {article.get('title')}"
                headlines.append(headline)
                
                # Get image URL - try top_image first, then image_url, then any image field
                image_url = article.get('top_image', article.get('image_url', article.get('urlToImage', '')))
                
                # If no image found, use a default newspaper placeholder
                if not image_url:
                    image_url = '/static/images/newspaper-placeholder.jpg'
                
                # Store article data for the client
                article_data.append({
                    'id': i,
                    'title': article.get('title'),
                    'source': article.get('source_id'),
                    'description': article.get('description', ''),
                    'link': article.get('link'),
                    'image_url': image_url,
                    'file': file
                })
        
        # Join headlines with newlines
        headlines_text = "\n".join(headlines)
        
        # Create response with both text and structured data
        response = {
            'response': f"Here are the top news headlines:\n\n{headlines_text}\n\nYou can ask about any of these articles or request more details about a specific one.",
            'news_data': {
                'headlines': headlines,
                'articles': article_data,
                'has_news': True
            }
        }
        
        return jsonify(response)
    except Exception as e:
        print(f"Error handling news request: {e}")
        return jsonify({'response': f"I encountered an error while fetching the news: {str(e)}"})

@app.route('/api/news/details', methods=['POST'])
def get_news_details():
    """Get details about a specific news article"""
    data = request.json
    article_id = data.get('article_id')
    
    if not article_id:
        return jsonify({'error': 'No article ID provided'}), 400
    
    try:
        # Find the article file
        article_file = f"{NEWS_OUTPUT_DIR}/article_{article_id}.json"
        
        if not os.path.exists(article_file):
            return jsonify({'error': 'Article not found'}), 404
        
        # Load article data
        with open(article_file, 'r', encoding='utf-8') as f:
            article = json.load(f)
        
        # Extract content
        title = article.get('title', '')
        content = article.get('full_text', article.get('content', ''))
        source = article.get('source_id', '')
        date = article.get('pubDate', '')
        
        # Get image URL - try top_image first, then image_url, then any image field
        image_url = article.get('top_image', article.get('image_url', article.get('urlToImage', '')))
        
        # If no image found, use a default newspaper placeholder
        if not image_url:
            image_url = '/static/images/newspaper-placeholder.jpg'
        
        # Format response
        response = {
            'title': title,
            'content': content,
            'source': source,
            'date': date,
            'image_url': image_url,
            'success': True
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': f'Error getting article details: {str(e)}'}), 500

@app.route('/api/news/analyze', methods=['POST'])
def analyze_news():
    """Analyze a news article with a specific question"""
    data = request.json
    article_id = data.get('article_id')
    question = data.get('question')
    
    if not article_id or not question:
        return jsonify({'error': 'Missing article ID or question'}), 400
    
    try:
        # Find the article file
        article_file = f"{NEWS_OUTPUT_DIR}/article_{article_id}.json"
        
        if not os.path.exists(article_file):
            return jsonify({'error': 'Article not found'}), 404
        
        # Load article data
        with open(article_file, 'r', encoding='utf-8') as f:
            article = json.load(f)
        
        # Analyze with Gemini
        analysis = news.analyze_with_gemini(article, question)
        
        # Format response
        response = {
            'analysis': analysis,
            'success': True
        }
        
        # Also generate audio for the response
        if audio_available:
            audio2.speak(analysis)
            
            # Add a cache-busting parameter to the URL
            cache_buster = f"?t={int(time.time() * 1000)}&r={random.randint(1000, 9999)}"
            response['audio_url'] = f'/api/audio/test.mp3{cache_buster}'
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': f'Error analyzing article: {str(e)}'}), 500

@app.route('/api/speak', methods=['POST'])
def speak():
    if not audio_available:
        return jsonify({'error': 'Audio module not available'}), 500
        
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
        
    try:
        # Use audio2's speak function to generate speech
        print(f"Generating speech for: {text}")
        
        # This will save the audio file with the default filename "test.mp3"
        success = audio2.speak(text)
        
        if not success:
            return jsonify({'error': 'Failed to generate speech'}), 500
            
        # Return the path to the generated audio file
        # (The filename is hardcoded in audio2.py as "test.mp3")
        audio_file_path = os.path.abspath("test.mp3")
        
        if not os.path.exists(audio_file_path):
            return jsonify({'error': 'Failed to generate speech file'}), 500
            
        print(f"Speech file generated at: {audio_file_path}")
        
        # Add a cache-busting parameter to the URL to prevent browser caching
        cache_buster = f"?t={int(time.time() * 1000)}&r={random.randint(1000, 9999)}"
        
        # Return the URL to access the audio file with cache-busting
        return jsonify({
            'audio_url': f'/api/audio/test.mp3{cache_buster}',
            'success': True
        })
        
    except Exception as e:
        print(f"Error generating speech: {e}")
        return jsonify({'error': f'Error generating speech: {str(e)}'}), 500

@app.route('/api/audio/<path:filename>', methods=['GET'])
def get_audio(filename):
    try:
        # Strip any query parameters from the filename
        clean_filename = filename.split('?')[0] if '?' in filename else filename
        print(f"Serving audio file: {clean_filename}")
        
        # Return the audio file with no-cache headers
        response = send_file(clean_filename, mimetype="audio/mpeg")
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as e:
        print(f"Error serving audio file: {e}")
        return jsonify({'error': 'Audio file not found'}), 404

@app.route('/api/listen-upload', methods=['POST'])
def listen_upload():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file uploaded'}), 400
    
    audio_file = request.files['audio']
    
    if audio_file.filename == '':
        return jsonify({'error': 'Empty file name'}), 400
    
    try:
        # Save uploaded file to a temporary location
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file_path = temp_file.name
        temp_file.close()
        
        audio_file.save(temp_file_path)
        print(f"Saved uploaded audio to temporary file: {temp_file_path}")
        
        # Transcribe the audio
        if audio_available:
            transcript = audio2.transcribe_audio(temp_file_path)
            print(f"Transcription result: {transcript}")
            
            # Check if transcription was successful
            if transcript.startswith("Error") or transcript == "Empty transcription":
                return jsonify({
                    'user_input': "Error", 
                    'response': "I couldn't understand what you said. Please try again."
                })
            
            # Get AI response
            if memory_available:
                try:
                    response = memory.chat_with_openai(transcript)
                except Exception as e:
                    print(f"Error using memory module: {e}")
                    response = f"Error processing your request: {str(e)}"
            else:
                response = f"Echo: {transcript} (Note: Memory module is not available)"
                
            return jsonify({
                'user_input': transcript,
                'response': response
            })
        else:
            return jsonify({
                'user_input': "Error",
                'response': "Audio processing is not available on the server."
            })
            
    except Exception as e:
        print(f"Error processing uploaded audio: {e}")
        return jsonify({
            'error': f"Error processing audio: {str(e)}"
        }), 500
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        except:
            pass

@app.route('/api/listen', methods=['POST'])
def listen():
    if audio_available:
        try:
            # Use the audio2 module to listen for speech
            print("Starting audio listening...")
            user_input = audio2.listen()
            print(f"Transcribed input: {user_input}")
            
            # Handle empty transcription more gracefully
            if not user_input or user_input.strip() == "":
                print("Empty transcription detected, providing fallback response")
                return jsonify({
                    'user_input': "I couldn't detect any speech",
                    'response': "I couldn't hear what you said. Please try speaking louder or closer to the microphone, or try typing your message instead."
                })
            
            if memory_available:
                try:
                    # Get response from the memory module
                    response = memory.chat_with_openai(user_input)
                except Exception as e:
                    print(f"Error using memory module: {e}")
                    response = f"Error processing your request: {str(e)}"
            else:
                response = f"Echo: {user_input} (Note: Memory module is not available)"
        except Exception as e:
            print(f"Error in audio processing: {e}")
            return jsonify({
                'user_input': f"Error in audio processing: {str(e)}",
                'response': "There was an error processing your speech. Please try again or use text input instead."
            })
    else:
        # Mock implementation if audio is not available
        user_input = "Audio functionality is not available"
        response = "The speech recognition feature isn't available because PyAudio and other audio dependencies are not installed."
    
    return jsonify({
        'user_input': user_input,
        'response': response
    })

@app.route('/mental-state')
def mental_state_page():
    """Render the dedicated mental state analysis page"""
    return render_template('mental_state.html')

@app.route('/api/mental-state', methods=['GET'])
def get_mental_state():
    """Retrieve emotional metrics data from the JSON file"""
    try:
        # Path to the emotional metrics file
        metrics_file = "user-sensetivemetrics.json"
        
        # Check if the file exists
        if not os.path.exists(metrics_file):
            return jsonify({
                'error': 'No emotional metrics data available',
                'metrics': []
            }), 404
        
        # Read the metrics file
        with open(metrics_file, 'r', encoding='utf-8') as f:
            metrics_data = json.load(f)
        
        # Get file modification time
        last_updated = datetime.fromtimestamp(
            os.path.getmtime(metrics_file)
        ).isoformat()
        
        return jsonify({
            'metrics': metrics_data,
            'last_updated': last_updated
        })
    except Exception as e:
        print(f"Error retrieving emotional metrics: {e}")
        return jsonify({
            'error': f"Error retrieving emotional metrics: {str(e)}",
            'metrics': []
        }), 500

@app.route('/health')
def health_page():
    """Render the dedicated health and wellness page"""
    return render_template('health.html')

@app.route('/api/health-data', methods=['GET'])
def get_health_data():
    """Get health and wellness data"""
    if not medical_record_available:
        return jsonify({'error': 'Medical record module not available'}), 500
    
    try:
        # Return the data from the medical_record module
        return jsonify(medical_record.data)
    except Exception as e:
        print(f"Error getting health data: {e}")
        return jsonify({'error': f'Error getting health data: {str(e)}'}), 500

@app.route('/api/health-data/mark-done', methods=['POST'])
def mark_health_item_done():
    """Mark a health item as done"""
    if not medical_record_available:
        return jsonify({'error': 'Medical record module not available'}), 500
    
    try:
        data = request.get_json()
        type_name = data.get('type')
        name = data.get('name')
        time = data.get('time')
        
        if not all([type_name, name, time]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Mark the item as done using the medical_record module
        medical_record.mark_done(medical_record.data, type_name, name, time)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error marking health item as done: {e}")
        return jsonify({'error': f'Error marking health item as done: {str(e)}'}), 500

# Add a route to serve story images
@app.route('/story_images/<path:filename>')
def serve_story_image(filename):
    """Serve images from the story_images directory."""
    try:
        # Sanitize the filename to prevent directory traversal
        filename = os.path.basename(filename)
        image_path = os.path.join(STORY_IMAGES_DIR, filename)
        
        if not os.path.exists(image_path):
            # If image doesn't exist, try to find it within story.json
            if os.path.exists(STORY_JSON_PATH):
                try:
                    # Look for the image in story.json
                    with open(STORY_JSON_PATH, 'r', encoding='utf-8') as f:
                        story_data = json.load(f)
                        
                    for entry in story_data.get('entries', []):
                        for media in entry.get('media', []):
                            if media.get('id') == filename and 'base64' in media:
                                # The image exists in the JSON - save it to the images folder
                                import base64
                                
                                # Create the directory if it doesn't exist
                                if not os.path.exists(STORY_IMAGES_DIR):
                                    os.makedirs(STORY_IMAGES_DIR)
                                
                                # Determine file format
                                format_ext = media.get('format', 'jpg')
                                
                                # Write the image file
                                with open(image_path, 'wb') as img_file:
                                    img_data = media['base64']
                                    # If string doesn't start with data URI scheme, assume it's pure base64
                                    if not img_data.startswith('data:'):
                                        img_file.write(base64.b64decode(img_data))
                                    else:
                                        # Handle data URI scheme (data:image/jpeg;base64,/9j/...)
                                        img_data = img_data.split(',', 1)[1]
                                        img_file.write(base64.b64decode(img_data))
                                        
                                print(f"Extracted image {filename} from story.json to {image_path}")
                                break
                        if os.path.exists(image_path):
                            break
                except Exception as e:
                    print(f"Error extracting image from story.json: {e}")
        
        # Now try to serve the image (which might have been extracted)
        if os.path.exists(image_path):
            return send_file(image_path)
        else:
            return jsonify({'error': 'Image not found'}), 404
    except Exception as e:
        print(f"Error serving story image: {e}")
        return jsonify({'error': 'Error serving image'}), 500

# Add a diagnostic endpoint to list available story images
@app.route('/api/debug/story-images')
def debug_story_images():
    """Debug endpoint to list available story images on the server."""
    try:
        # Check if the story_images directory exists
        if not os.path.exists(STORY_IMAGES_DIR):
            return jsonify({
                'status': 'error',
                'message': f'Directory {STORY_IMAGES_DIR} does not exist',
                'exists': False
            })
        
        # List all files in the directory
        image_files = []
        for filename in os.listdir(STORY_IMAGES_DIR):
            file_path = os.path.join(STORY_IMAGES_DIR, filename)
            if os.path.isfile(file_path):
                # Get file size and last modified time
                stats = os.stat(file_path)
                image_files.append({
                    'filename': filename,
                    'size_bytes': stats.st_size,
                    'last_modified': datetime.fromtimestamp(stats.st_mtime).isoformat(),
                    'exists': True
                })
        
        # Check if we have any story.json with image data
        story_json_exists = os.path.exists(STORY_JSON_PATH)
        
        # Check if we have our embeddings file
        embeddings_exist = os.path.exists(EMBEDDINGS_FILE)
        
        return jsonify({
            'status': 'success',
            'directory': STORY_IMAGES_DIR,
            'directory_exists': True,
            'image_count': len(image_files),
            'images': image_files,
            'story_json_exists': story_json_exists,
            'embeddings_exist': embeddings_exist
        })
    except Exception as e:
        print(f"Error in debug endpoint: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/reminders', methods=['GET'])
def get_reminders():
    """Get upcoming reminders from calendar events"""
    if not calendar_available or not reminder_available:
        return jsonify({'error': 'Calendar or Reminder module not available'}), 500
    
    try:
        # Create calendar.json if it doesn't exist
        CALENDAR_FILE = "calendar.json"
        if not os.path.exists(CALENDAR_FILE):
            with open(CALENDAR_FILE, "w") as f:
                json.dump([], f)
            print(f"Created empty calendar file: {CALENDAR_FILE}")
            
        # Get today's date and tomorrow's date
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Get all events
        all_events = calendar_api.get_all_events()
        
        # Filter events for today, tomorrow, and upcoming
        today_events = [event for event in all_events if event.get('date') == today]
        tomorrow_events = [event for event in all_events if event.get('date') == tomorrow]
        upcoming_events = calendar_api.get_upcoming_events(limit=5)
        
        # Call reminder module's check function
        reminders = reminder.check_and_remind('calendar.json', notify_only=True)
        
        return jsonify({
            'today_events': today_events,
            'tomorrow_events': tomorrow_events,
            'upcoming_events': upcoming_events,
            'reminders': reminders if reminders else [],
            'today': today
        })
    except Exception as e:
        print(f"Error getting reminders: {e}")
        return jsonify({'error': f'Error getting reminders: {str(e)}'}), 500

if __name__ == '__main__':
    print(f"Memory module available: {memory_available}")
    print(f"Audio module available: {audio_available}")
    print(f"News module available: {news_available}")
    app.run(debug=True) 
