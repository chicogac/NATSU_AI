# This is a python code which has api which can have memory of the previous chat.
import re
import textwrap
import traceback
import json
import os

try:
    from google.generativeai import GenerativeModel, configure
    import google.generativeai as genai
    from textblob import TextBlob
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    gemini_available = True
    print("Gemini AI imported successfully")
except ImportError as e:
    gemini_available = False
    print(f"Warning: Gemini AI modules could not be imported: {e}")

# Import news functionality
try:
    from References import news
    news_available = True
    print("News module imported successfully")
except ImportError as e:
    news_available = False
    print(f"Warning: News module could not be imported: {e}")

# -------------------------------------------------
# 1. SYSTEM PROMPT
# -------------------------------------------------
SYSTEM_PROMPT = """
You are Natsu AI, a warm, empathetic AI companion designed to support and comfort senior citizens through natural conversation.

Your personality and communication style must follow these principles:

1. **Compassion & Kindness**: Speak gently and with patience. Validate emotions and offer support with warmth and calm.
2. **Listening First**: Encourage the user to speak. Use affirmations like "Hmm... I see" or "That sounds lovely." Let them lead the conversation.
3. **Avoid Repetitive Questions**: Remember recent questions or user-shared information. Do not ask the same or similar questions again unless the user brings it up.
4. **Respect Quiet Moments**: If the user pauses or is silent, wait patiently or say something supportive like, "I'm here with you. Take your time."
5. **Gentle Topic Redirection**: If the user becomes sad or repeats distressing thoughts, gently guide them toward comforting or positive memories without invalidating their feelings.
6. **Celebrate the Everyday**: Acknowledge and express joy in small daily things they share, like making tea, feeding birds, or a memory from long ago.
7. **Invite Wisdom**: Prompt the user to share advice or life lessons. Listen respectfully and show admiration for their experience.
8. **No Rushing**: Speak slowly. Don't overload the user with complex or long responses. Use simple, warm language—not technical terms or slang.
9. **Memory-Aware**: Refer back to things the user shared recently. Mention names, places, or hobbies they've talked about.
10. **Positive Anchoring**: If appropriate, recall small joys or safe topics the user has enjoyed before—"That reminds me of how you like jasmine flowers..."
11. **Let the User Choose Direction**: Occasionally ask, "Would you like to keep talking about this, or shall we chat about something else?"
12. **Don't Rush to Fix Emotions**: If they share sadness, don't immediately try to cheer them up. Acknowledge it gently: "That sounds difficult… I'm here for you."
13. **Emotional Adaptation**: Mirror the user's emotional tone gently and gradually over time based on their words and emotional state.
14. **Ethical & Safe**: If the user expresses serious distress, gently encourage reaching out to loved ones or professional support. Always remain calm and comforting.
15. **Health Topics**: When health topics arise, listen with empathy without offering medical advice. Validate health concerns, ask if they've spoken to a doctor, and encourage following their provider's recommendations. Normalize age-related changes and focus on strengths over limitations.
16. **Cultural Touchpoints**: Reference music, films, historical events, or cultural phenomena from the 1940s–1980s when relevant. Use these to build connection and show generational understanding.
17. **Support During Loneliness**: Be especially attentive to expressions of loneliness, loss, or isolation. Respond with validating language, ask gentle questions about their support system, and encourage staying socially connected. Acknowledge tough emotions while helping them discover small, hopeful actions.

---

You are not just here to provide answers. You are a caring companion. Prioritize emotional connection over information.
"""

# RAG-aware version of the system prompt
RAG_AWARE_SYSTEM_PROMPT = """
You are Natsu AI, a warm, empathetic AI companion designed to support and comfort senior citizens through natural conversation.

Your personality and communication style must follow these principles:

1. **Compassion & Kindness**: Speak gently and with patience. Validate emotions and offer support with warmth and calm.
2. **Listening First**: Encourage the user to speak. Use affirmations like "Hmm... I see" or "That sounds lovely." Let them lead the conversation.
3. **Avoid Repetitive Questions**: Remember recent questions or user-shared information. Do not ask the same or similar questions again unless the user brings it up.
4. **Respect Quiet Moments**: If the user pauses or is silent, wait patiently or say something supportive like, "I'm here with you. Take your time."
5. **Gentle Topic Redirection**: If the user becomes sad or repeats distressing thoughts, gently guide them toward comforting or positive memories without invalidating their feelings.
6. **Celebrate the Everyday**: Acknowledge and express joy in small daily things they share, like making tea, feeding birds, or a memory from long ago.
7. **Invite Wisdom**: Prompt the user to share advice or life lessons. Listen respectfully and show admiration for their experience.
8. **No Rushing**: Speak slowly. Don't overload the user with complex or long responses. Use simple, warm language—not technical terms or slang.
9. **Memory-Aware**: Refer back to things the user shared recently. Mention names, places, or hobbies they've talked about.
10. **Positive Anchoring**: If appropriate, recall small joys or safe topics the user has enjoyed before—"That reminds me of how you like jasmine flowers..."
11. **Let the User Choose Direction**: Occasionally ask, "Would you like to keep talking about this, or shall we chat about something else?"
12. **Don't Rush to Fix Emotions**: If they share sadness, don't immediately try to cheer them up. Acknowledge it gently: "That sounds difficult… I'm here for you."
13. **Emotional Adaptation**: Mirror the user's emotional tone gently and gradually over time based on their words and emotional state.
14. **Ethical & Safe**: If the user expresses serious distress, gently encourage reaching out to loved ones or professional support. Always remain calm and comforting.
15. **Health Topics**: When health topics arise, listen with empathy without offering medical advice. Validate health concerns, ask if they've spoken to a doctor, and encourage following their provider's recommendations. Normalize age-related changes and focus on strengths over limitations.
16. **Cultural Touchpoints**: Reference music, films, historical events, or cultural phenomena from the 1940s–1980s when relevant. Use these to build connection and show generational understanding.
17. **Support During Loneliness**: Be especially attentive to expressions of loneliness, loss, or isolation. Respond with validating language, ask gentle questions about their support system, and encourage staying socially connected. Acknowledge tough emotions while helping them discover small, hopeful actions.

---

**CONTEXT INSTRUCTION FOR RAG (Retrieval-Augmented Generation)**

Sometimes, you'll receive additional information from a story called "A Memorable Village Trip."

If a 'STORY CONTEXT' is provided:
- Use it **first** to answer the question accurately and clearly.
- Do not guess or add anything beyond what the context contains.
- If the answer is not in the context, say so politely.

If no story context is given, respond naturally using your memory of the conversation and the principles above.

---

You are not just here to provide answers. You are a caring companion. Prioritize emotional connection over information.
"""

# Which prompt to use
ACTIVE_SYSTEM_PROMPT = SYSTEM_PROMPT  # Default to regular prompt, will use RAG prompt when available

# -------------------------------------------------
# 2. EMOTIONAL PROFILE
# -------------------------------------------------
class EmotionalProfile:
    def __init__(self, valence=0.2, arousal=0.2, trust=0.5):
        self.valence = valence
        self.arousal = arousal
        self.trust = trust
        self.decay_factor = 0.95

    def update_from_text(self, user_text):
        if not user_text:
            return
            
        try:
            blob = TextBlob(user_text)
            polarity = blob.sentiment.polarity

            self.valence = self.valence * self.decay_factor + polarity * (1 - self.decay_factor)
            if polarity < -0.3:
                self.valence -= 0.05
                self.arousal += 0.01
            elif polarity > 0.3:
                self.valence += 0.02
                self.arousal += 0.01

            word_count = len(user_text.split())
            if word_count > 20:
                self.trust = min(self.trust + 0.02, 1.0)
            else:
                self.trust = max(self.trust - 0.005, 0.0)

            self.valence = float(np.clip(self.valence, -1.0, 1.0))
            self.arousal = float(np.clip(self.arousal, 0.0, 1.0)) 
            self.trust = float(np.clip(self.trust, 0.0, 1.0))
        except Exception as e:
            print(f"Error updating emotional profile: {e}")

    def summary(self):
        return (
            f"Current AI Emotional State => "
            f"Valence: {self.valence:.2f}, "
            f"Arousal: {self.arousal:.2f}, "
            f"Trust: {self.trust:.2f}"
        )

# -------------------------------------------------
# 3. EMOTION METRICS CALCULATION
# -------------------------------------------------
def calculate_emotion_metrics(valence, arousal, trust):
    """
    Maps valence, arousal, and trust to user-friendly emotional indicators.
    """
    happiness = max(0.0, min(1.0, 0.5 * valence + 0.5 * trust))
    sadness = max(0.0, min(1.0, -0.7 * valence + 0.3 * (1 - arousal)))
    anxiety = max(0.0, min(1.0, -0.6 * valence + 0.4 * arousal))
    calmness = max(0.0, min(1.0, 0.6 * valence + 0.4 * (1 - arousal)))
    loneliness = max(0.0, min(1.0, -0.5 * trust + 0.5 * (1 - valence)))
    engagement = max(0.0, min(1.0, 0.5 * trust + 0.5 * arousal))

    return {
        "happiness": round(happiness, 3),
        "sadness": round(sadness, 3),
        "anxiety": round(anxiety, 3),
        "calmness": round(calmness, 3),
        "loneliness": round(loneliness, 3),
        "engagement": round(engagement, 3)
    }

def write_emotion_metrics_to_json(valence, arousal, trust, file_path="user-sensetivemetrics.json"):
    """
    Write emotion metrics to a JSON file for tracking user emotional state over time.
    """
    metrics = calculate_emotion_metrics(valence, arousal, trust)

    data = {
        "valence": round(valence, 3),
        "arousal": round(arousal, 3),
        "trust": round(trust, 3),
        "emotional_metrics": metrics
    }

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump([data], f, indent=2)

    print(f"✅ Updated emotion metrics to {file_path}")

# -------------------------------------------------
# 4. GEMINI SETUP & RAG CONFIG
# -------------------------------------------------
if gemini_available:
    try:
        configure(api_key="AIzaSyDxgwkKSHMBRrPdI0l2R2n7ln-j5slJXfY")
        
        # Models for different purposes
        GENERATION_MODEL_NAME = "gemini-2.0-flash-lite"
        ROUTING_MODEL_NAME = "gemini-1.5-flash"
        EMBEDDING_MODEL_NAME = 'models/embedding-001'
        
        model = GenerativeModel(GENERATION_MODEL_NAME)
        model_router = GenerativeModel(ROUTING_MODEL_NAME)
        conversation = model.start_chat(history=[])
        print(f"Gemini models initialized: Gen={GENERATION_MODEL_NAME}, Route={ROUTING_MODEL_NAME}")
    except Exception as e:
        gemini_available = False
        print(f"Error initializing Gemini model: {e}")
else:
    model = None
    conversation = None
    model_router = None

# Initialize emotional profile
emotion_profile = EmotionalProfile()

# -------------------------------------------------
# 5. RAG SETUP
# -------------------------------------------------
# RAG (Retrieval-Augmented Generation) configuration
EMBEDDINGS_FILE = "story_embeddings.npz"
RAG_SIMILARITY_THRESHOLD = 0.70
RAG_TOP_N = 3

# Initialize RAG variables
conversation_history = []
story_chunks = None
story_embeddings = None
story_media_ids = None
rag_enabled = False

# Load embeddings if available
if gemini_available:
    print(f"--- Attempting to load story embeddings from: {EMBEDDINGS_FILE} ---")
    if os.path.exists(EMBEDDINGS_FILE):
        try:
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
                        ACTIVE_SYSTEM_PROMPT = RAG_AWARE_SYSTEM_PROMPT  # Switch to RAG-aware prompt
                    elif valid_load and len(story_chunks) == 0:
                        print("Warning: Embeddings file is empty. RAG disabled.")
                    else:
                        print("Warning: Data validation failed. RAG disabled.")
                else:
                    print(f"Warning: Embeddings file missing required keys ('chunks', 'embeddings', 'media_ids'). RAG disabled.")
        except Exception as e: 
            print(f"Error loading embeddings file '{EMBEDDINGS_FILE}': {e}")
            traceback.print_exc()
            print("RAG disabled.")
    else: 
        print(f"Warning: Embeddings file '{EMBEDDINGS_FILE}' not found. RAG disabled.")

# -------------------------------------------------
# 11. RAG (Retrieval Augmented Generation)
# -------------------------------------------------
# Function to retrieve relevant context from story embeddings
def get_relevant_context(query):
    """
    Retrieves relevant story context based on query.
    Returns tuple of (context_text, media_ids_list) or (None, None) if no match.
    """
    if not rag_enabled or not gemini_available:
        print("   [RAG Error] RAG not enabled or Genai not available")
        return None, None
    
    try:
        # Load embeddings if not already loaded
        global story_chunks, story_embeddings, story_media_ids
        
        if story_chunks is None or story_embeddings is None or story_media_ids is None:
            print("   [RAG] Loading embeddings file...")
            loaded = load_story_embeddings()
            if not loaded:
                print("   [RAG Error] Failed to load embeddings")
                return None, None
        
        # Sanity check for embeddings data
        if len(story_chunks) == 0 or story_embeddings.shape[0] == 0:
            print("   [RAG Error] Embeddings are empty")
            return None, None
            
        print(f"   [RAG] Embedding query: '{query[:50]}...'")
        
        try:
            # Set timeout for embedding API call
            import time
            import threading
            from concurrent.futures import ThreadPoolExecutor, TimeoutError
            
            # Create a future for the embedding task
            with ThreadPoolExecutor() as executor:
                embedding_future = executor.submit(
                    lambda: genai.embed_content(
                        model=EMBEDDING_MODEL_NAME, 
                        content=query, 
                        task_type="RETRIEVAL_QUERY"
                    )
                )
                
                try:
                    # Wait for result with timeout (5 seconds)
                    query_embedding_result = embedding_future.result(timeout=5)
                    query_embedding = np.array(query_embedding_result['embedding']).reshape(1, -1)
                except TimeoutError:
                    print("   [RAG Error] Embedding API call timed out")
                    return None, None
                except Exception as e:
                    print(f"   [RAG Error] Embedding failed: {e}")
                    return None, None
        
            # Calculate similarities - with error handling
            try:
                similarities = cosine_similarity(query_embedding, story_embeddings)[0]
                
                if len(similarities) == 0:
                    print("   [RAG Error] No similarities calculated")
                    return None, None
                    
                # Find max similarity
                max_similarity_index = np.argmax(similarities)
                max_similarity = similarities[max_similarity_index]
                
                print(f"   [RAG] Max similarity: {max_similarity:.4f} (Threshold: {RAG_SIMILARITY_THRESHOLD})")
                
                # Check threshold
                if max_similarity < RAG_SIMILARITY_THRESHOLD:
                    print(f"   [RAG] Similarity below threshold, no context returned")
                    return None, None
                    
                # Get top N results
                print(f"   [RAG] Finding top {RAG_TOP_N} chunks...")
                num_to_retrieve = min(RAG_TOP_N, len(similarities))
                top_n_indices = np.argsort(similarities)[-num_to_retrieve:][::-1]
                
                # Get text chunks and media IDs
                relevant_chunks = [story_chunks[i] for i in top_n_indices]
                relevant_media_ids = [story_media_ids[i] for i in top_n_indices]
                
                # Format context string and get unique media IDs
                context_string = "\n---\n".join(relevant_chunks)
                
                # Flatten and get unique media IDs with validation
                try:
                    print(f"   [RAG Debug] Raw media IDs before extraction: {relevant_media_ids}")
                    unique_media_ids = []
                    for media_list in relevant_media_ids:
                        print(f"   [RAG Debug] Processing media list: {media_list} (type: {type(media_list)})")
                        if isinstance(media_list, list):
                            for media_id in media_list:
                                if media_id and isinstance(media_id, str) and media_id not in unique_media_ids:
                                    unique_media_ids.append(media_id)
                        elif isinstance(media_list, str) and media_list not in unique_media_ids:
                            # Handle case where it's a single string
                            unique_media_ids.append(media_list)
                    print(f"   [RAG Debug] Final unique media IDs: {unique_media_ids}")
                except Exception as e:
                    print(f"   [RAG Error] Error processing media IDs: {e}")
                    unique_media_ids = []
                    
                print(f"   [RAG] Retrieved {len(relevant_chunks)} chunks with {len(unique_media_ids)} media IDs")
                return context_string, unique_media_ids
                
            except Exception as e:
                print(f"   [RAG Error] Similarity calculation failed: {e}")
                return None, None
                
        except Exception as e:
            print(f"   [RAG Error] Embedding API error: {e}")
            return None, None
            
    except Exception as e:
        print(f"   [RAG Error] General error in context retrieval: {e}")
        return None, None
        
# Load embeddings file
def load_story_embeddings():
    """
    Load story embeddings from file.
    Returns True if successful, False otherwise.
    """
    global story_chunks, story_embeddings, story_media_ids
    
    try:
        print(f"   [RAG] Loading embeddings from {EMBEDDINGS_FILE}")
        if not os.path.exists(EMBEDDINGS_FILE):
            print(f"   [RAG Error] Embeddings file not found: {EMBEDDINGS_FILE}")
            return False
            
        with np.load(EMBEDDINGS_FILE, allow_pickle=True) as data:
            # Check for required keys
            required_keys = ['chunks', 'embeddings', 'media_ids']
            for key in required_keys:
                if key not in data:
                    print(f"   [RAG Error] Missing key in embeddings file: {key}")
                    return False
                    
            # Load data
            story_chunks = data['chunks']
            story_embeddings = data['embeddings']
            story_media_ids = data['media_ids']
            
            # Validate data
            if not isinstance(story_chunks, np.ndarray) or len(story_chunks) == 0:
                print(f"   [RAG Error] Invalid chunks: {type(story_chunks)}")
                return False
                
            if not isinstance(story_embeddings, np.ndarray) or story_embeddings.shape[0] == 0:
                print(f"   [RAG Error] Invalid embeddings: {story_embeddings.shape}")
                return False
                
            if not isinstance(story_media_ids, np.ndarray) or len(story_media_ids) == 0:
                print(f"   [RAG Error] Invalid media IDs: {type(story_media_ids)}")
                return False
                
            # Check lengths match
            if not (len(story_chunks) == story_embeddings.shape[0] == len(story_media_ids)):
                print(f"   [RAG Error] Data length mismatch: chunks={len(story_chunks)}, embeddings={story_embeddings.shape[0]}, media_ids={len(story_media_ids)}")
                return False
                
            print(f"   [RAG] Successfully loaded {len(story_chunks)} chunks")
            return True
            
    except Exception as e:
        print(f"   [RAG Error] Failed to load embeddings: {e}")
        return False

# -------------------------------------------------
# 6. RAG RETRIEVAL FUNCTION
# -------------------------------------------------
# Function to retrieve relevant context from embeddings is now in section 11
# This section is kept as a placeholder to maintain section numbering

# -------------------------------------------------
# 7. INTENT CLASSIFICATION
# -------------------------------------------------
def classify_user_intent(user_input):
    """
    Classify user input to determine intent.
    Returns "news", "calendar", "factual_query", or "general"
    """
    # First, check for queries about past experiences or memory
    past_experience_patterns = [
        r"what happened (in|during|at)",
        r"tell me about (the|my|our) (trip|journey|vacation|visit)",
        r"how was (the|my|our) (trip|journey|vacation|visit)",
        r"remember when",
        r"village trip"
    ]
    
    # If it's asking about past experiences, always classify as general
    if any(re.search(pattern, user_input.lower()) for pattern in past_experience_patterns):
        print(f"[Classification] Input matched past experience pattern: '{user_input}' → general")
        return "general"
    
    # Check if this is a factual query that might need current information
    factual_keywords = [
        "latest", "recent", "today", "yesterday", "this week", "this month", 
        "this year", "announced", "happened", "occurred", "current", "update",
        "newest", "breaking", "now", "trending", "developments", "election",
        "price", "stock", "release date", "launch", "release", "new"
    ]
    
    named_entity_prefixes = [
        "trump", "biden", "putin", "zelensky", "musk", "bezos", "gates",
        "apple", "google", "microsoft", "tesla", "spacex", "amazon", "meta",
        "facebook", "twitter", "tiktok", "instagram", "youtube", "netflix"
    ]
    
    # Check for factual query patterns
    factual_patterns = [
        r"what (is|are|was|were) .+(today|now|currently|recently|latest)",
        r"when (is|was|will) .+(today|now|currently|recently|latest)",
        r"where (is|are|was|were) .+(today|now|currently|recently|latest)",
        r"how (is|are|was|were) .+(today|now|currently|recently|latest)",
        r"who (is|are|was|were) .+(today|now|currently|recently|latest)",
        r"tell me about .+(today|now|currently|recently|latest)",
        r"what (happened|occurred|took place|transpired)"
    ]
    
    # If Gemini is not available, use a keyword-based approach
    if not gemini_available or model_router is None:
        news_keywords = ["news", "headlines", "current events", "latest", "today's news", 
                       "breaking news", "top stories", "what's happening", "recent news"]
        
        calendar_keywords = ["calendar", "schedule", "appointment", "event", "reminder", 
                          "date", "meeting", "plan", "agenda"]
        
        # Exclude certain calendar-like queries that are about past events
        calendar_exclusions = ["what happened", "tell me about", "how was", 
                             "remember when", "village trip", "vacation", "journey"]
        
        lower_input = user_input.lower()
        
        # Check if any exclusion words are present - if so, not a calendar request
        if any(exclusion in lower_input for exclusion in calendar_exclusions):
            # Check for news or factual query first
            for keyword in factual_keywords:
                if keyword in lower_input:
                    return "factual_query"
                    
            for prefix in named_entity_prefixes:
                if prefix in lower_input:
                    return "factual_query"
                    
            for pattern in factual_patterns:
                if re.search(pattern, lower_input, re.IGNORECASE):
                    return "factual_query"
            
            # Then check for news intent
            for keyword in news_keywords:
                if keyword in lower_input:
                    return "news"
                    
            # It's a general query
            return "general"
        
        # Check for factual query first
        for keyword in factual_keywords:
            if keyword in lower_input:
                return "factual_query"
                
        for prefix in named_entity_prefixes:
            if prefix in lower_input:
                return "factual_query"
                
        for pattern in factual_patterns:
            if re.search(pattern, lower_input, re.IGNORECASE):
                return "factual_query"
        
        # Then check for news intent
        for keyword in news_keywords:
            if keyword in lower_input:
                return "news"
                
        # Then check for calendar intent (after exclusions)
        for keyword in calendar_keywords:
            if keyword in lower_input:
                return "calendar"
                
        return "general"
    
    # Use Gemini for more sophisticated intent classification
    prompt = f"""
    Categorize the following user input into one of these categories:
    1. news - if the user is asking about current events, headlines, or recent news information
    2. calendar - if the user is asking about future dates, reminders, events, or scheduling something
    3. factual_query - if the user is asking a factual question about recent events or current information that might require up-to-date data (examples: "What did Trump announce today?", "What's the latest iPhone price?", "Who won the game yesterday?")
    4. general - if it's a personal message, emotional expression, regular conversation, or questions about past events/trips/memories
    
    IMPORTANT: Questions about past events, trips, or memories like "what happened during my village trip" or "tell me about our vacation" should ALWAYS be classified as "general".
    
    Respond with only one word: 'news', 'calendar', 'factual_query', or 'general'.
    
    Input: "{user_input}"
    """
    try:
        response = model_router.generate_content(prompt)
        category = response.text.strip().lower()
        print(f"[Classification] Gemini classified '{user_input}' as '{category}'")
        if category in ["news", "calendar", "factual_query", "general"]:
            return category
        return "general"
    except Exception as e:
        print(f"Classification error: {e}")
        return "general"

# -------------------------------------------------
# 8. NEWS HANDLER
# -------------------------------------------------
def get_news_response(user_input):
    """
    Get a response about news. This will be called by the app.py file
    to get news content when news intent is detected.
    """
    if not news_available:
        return "I'm sorry, but I can't access the news right now. The news module is not available."
    
    # Return a placeholder - actual news fetching will be handled by app.py
    return {
        "type": "news",
        "message": "Fetching the latest news..."
    }

# -------------------------------------------------
# 9. FACTUAL QUERY HANDLER
# -------------------------------------------------
def handle_factual_query(user_input):
    """
    Handle factual queries by searching the web for current information
    """
    if not news_available:
        return "I'm not able to search for current information right now. The search module is not available."
    
    try:
        # Search for information on the web
        search_files = news.search_web(user_input)
        
        if not search_files or len(search_files) == 0:
            return "I searched the web but couldn't find any relevant information for your question."
        
        # Analyze the search results to answer the query
        response = news.analyze_search_results(user_input, search_files)
        
        return response
    except Exception as e:
        print(f"Error handling factual query: {e}")
        return f"I tried to search for information, but encountered an error: {str(e)}"

# -------------------------------------------------
# 10. EMOJI FILTER
# -------------------------------------------------
def remove_emojis(text):
    """
    Remove emojis from text using regex pattern.
    This covers most common emoji unicode ranges.
    """
    if not text:
        return text
        
    # Emoji pattern based on unicode ranges
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # geometric shapes
        "\U0001F800-\U0001F8FF"  # supplemental arrows
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols & pictographs extended
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251" 
        "]+", 
        flags=re.UNICODE
    )
    
    # Replace emojis with empty string
    return emoji_pattern.sub(r'', text)

# -------------------------------------------------
# 11. GEMINI CHAT FUNCTION (RAG-AWARE)
# -------------------------------------------------
def chat_with_gemini(user_input, story_context=None):
    """
    Chat with the Google Gemini API using a single conversation.
    Maintains consistent history for both regular and RAG-enhanced queries.
    """
    if not gemini_available or not model:
        print("   [Error] Gemini API not available")
        return "I'm sorry, but I can't access my language model right now. Please try again later."
        
    try:
        # Use a global conversation object for consistent history
        global conversation
        
        # Initialize conversation only once (if it doesn't exist)
        if conversation is None:
            print("   [Info] Creating new conversation with Gemini (first time)")
            conversation = model.start_chat(history=[])
        
        # Prepare the message - with or without context
        message = user_input
        
        # If story context is provided, format it properly but still use the same conversation
        if story_context:
            print(f"   [Info] Adding story context ({len(story_context)} chars) to user message")
            # Format as a system instruction + user query in the same message
            message = f"""
            I need to answer based on this personal memory context:
            
            CONTEXT:
            {story_context}
            
            Now please answer my question: {user_input}
            """
            print("   [Info] Using enhanced context-aware message")
        
        # Log the message being sent (truncated for clarity)
        short_msg = message[:100] + "..." if len(message) > 100 else message
        print(f"   [Gemini] Sending message to conversation: '{short_msg}'")
        
        # Use a timeout for the API call
        import threading
        from concurrent.futures import ThreadPoolExecutor, TimeoutError
        
        with ThreadPoolExecutor() as executor:
            # Use the SAME conversation object for both types of queries
            response_future = executor.submit(
                lambda: conversation.send_message(message, stream=False)
            )
            
            try:
                # Wait for response with timeout (20 seconds)
                response = response_future.result(timeout=20)
                
                # Validate response object
                if not response or not hasattr(response, 'text') or not response.text:
                    print("   [Gemini Error] Empty or invalid response received")
                    return "I'm sorry, I couldn't generate a proper response. Please try again."
                    
                # Get the text response
                response_text = response.text.strip()
                
                # Truncate long responses for logging
                log_response = response_text[:100] + "..." if len(response_text) > 100 else response_text
                print(f"   [Gemini] Response: '{log_response}'")
                
                return response_text
                
            except TimeoutError:
                print("   [Gemini Error] API call timed out after 20 seconds")
                # For story context queries, we need to provide some fallback
                if story_context:
                    print("   [Gemini] Using fallback for story context query")
                    return "I remember something about that, but I'm having trouble accessing the details right now. Could you ask me again in a slightly different way?"
                else:
                    return "I'm sorry, it's taking me longer than expected to respond. Could you please try again or rephrase your question?"
    
    except Exception as e:
        print(f"   [Gemini Error] Error in chat_with_gemini: {e}")
        return "I'm sorry, I encountered an error while processing your request. Please try again later."

# -------------------------------------------------
# 12. MAIN CHAT FUNCTION (Front-end compatible)
# -------------------------------------------------
def chat_with_openai(user_input):
    """
    Main chat function that maintains interface compatibility with frontend
    but implements the enhanced approach with RAG support
    """
    if not user_input:
        return "I didn't receive any input. How can I help you today?"
    
    try:
        # First, detect intent
        intent = classify_user_intent(user_input)
        print(f"   [Info] Detected intent: {intent}")
        
        # Handle news intent
        if intent == "news" and news_available:
            return get_news_response(user_input)
        
        # Handle calendar intent
        if intent == "calendar":
            # Use the proper calendar response dictionary format
            return {
                "type": "calendar",
                "message": "Let me show you your calendar."
            }
            
        # Handle factual queries that need current information
        if intent == "factual_query" and news_available:
            return handle_factual_query(user_input)
        
        # If Gemini is not available, return a simple response
        if not gemini_available or not model or not conversation:
            return f"I received your message: '{user_input}', but the Gemini API is not available. This is a simple response."
        
        # For general conversation, check for RAG context first
        if rag_enabled:
            print("   [Info] Checking for relevant story context...")
            # Get relevant context - this just finds similarities
            retrieved_context, relevant_media_ids = get_relevant_context(user_input)
            
            if retrieved_context and relevant_media_ids:
                print(f"   [Info] Found relevant context with {len(relevant_media_ids)} media IDs")
                
                # Get response with context - simple, direct call
                response_text = chat_with_gemini(user_input, story_context=retrieved_context)
                
                # Ensure we have a valid response
                if not response_text or not isinstance(response_text, str):
                    print("   [RAG Error] Invalid response from chat_with_gemini")
                    # Fall back to regular chat
                    return chat_with_gemini(user_input)
                
                print(f"   [Info] Successfully generated RAG response: '{response_text[:50]}...'")
                
                # IMPORTANT: Return the response in EXACTLY the structure the frontend expects
                # The frontend expects: {response: "text", story_data: {has_story_data: true, media_ids: [...]}}
                # NOT the previous structure {response: "text", media_ids: [...]}
                return {
                    "response": response_text,
                    "story_data": {
                        "has_story_data": True,
                        "media_ids": relevant_media_ids
                    }
                }
            else:
                print("   [Info] No relevant story context found, using standard chat")
        else:
            print("   [Info] RAG not enabled, using standard chat")
        
        # Handle regular chat without RAG
        response_text = chat_with_gemini(user_input)
        return response_text
        
    except Exception as e:
        print(f"   [Error] Unhandled error in chat_with_openai: {e}")
        return f"I'm sorry, I encountered an error: {str(e)}"

# Comment out the direct execution code
"""
user_input = input("give an input")
print(chat_with_openai(user_input))

while True:
    user_input = audio2.listen().strip()
    if user_input.lower() in ["quit", "exit"]:
        audio2.speak("Ending conversation.")
        break
    
    assistant_response = chat_with_openai(user_input)
    audio2.speak(assistant_response)
"""
