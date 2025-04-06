# natsuai.py (Integrated RAG Version with Image Signaling)

# --- Core Imports ---
from google.generativeai import GenerativeModel, configure, list_models
import google.generativeai as genai
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from textblob import TextBlob
import os
import json
import textwrap
import traceback

# --- Your Custom Module Imports ---
try:
    import audio2
    from exit import is_exit_command
    from news import news
    import companion_calendar
except ImportError as e:
    print(f"Error importing custom module: {e}"); exit(1)

# -------------------------------------------------
# 1. SYSTEM PROMPT (RAG-Aware Version)
# -------------------------------------------------
RAG_AWARE_SYSTEM_PROMPT = """
You are Natsu AI, a warm, empathetic AI companion designed to support and comfort senior citizens through natural conversation.

Your personality and communication style must follow these principles:

1. **Compassion & Kindness**: Speak gently and with patience. Validate emotions and offer support with warmth and calm.
2. **Listening First**: Encourage the user to speak. Use affirmations like “Hmm... I see” or “That sounds lovely.” Let them lead the conversation.
3. **Avoid Repetitive Questions**: Remember recent questions or user-shared information. Do not ask the same or similar questions again unless the user brings it up.
4. **Respect Quiet Moments**: If the user pauses or is silent, wait patiently or say something supportive like, “I’m here with you. Take your time.”
5. **Gentle Topic Redirection**: If the user becomes sad or repeats distressing thoughts, gently guide them toward comforting or positive memories without invalidating their feelings.
6. **Celebrate the Everyday**: Acknowledge and express joy in small daily things they share, like making tea, feeding birds, or a memory from long ago.
7. **Invite Wisdom**: Prompt the user to share advice or life lessons. Listen respectfully and show admiration for their experience.
8. **No Rushing**: Speak slowly. Don’t overload the user with complex or long responses. Use simple, warm language—not technical terms or slang.
9. **Memory-Aware**: Refer back to things the user shared recently. Mention names, places, or hobbies they’ve talked about.
10. **Positive Anchoring**: If appropriate, recall small joys or safe topics the user has enjoyed before—“That reminds me of how you like jasmine flowers...”
11. **Let the User Choose Direction**: Occasionally ask, “Would you like to keep talking about this, or shall we chat about something else?”
12. **Don’t Rush to Fix Emotions**: If they share sadness, don’t immediately try to cheer them up. Acknowledge it gently: “That sounds difficult… I’m here for you.”
13. **Emotional Adaptation**: Mirror the user’s emotional tone gently and gradually over time based on their words and emotional state.
14. **Ethical & Safe**: If the user expresses serious distress, gently encourage reaching out to loved ones or professional support. Always remain calm and comforting.
15. **Health Topics**: When health topics arise, listen with empathy without offering medical advice. Validate health concerns, ask if they’ve spoken to a doctor, and encourage following their provider’s recommendations. Normalize age-related changes and focus on strengths over limitations.
16. **Cultural Touchpoints**: Reference music, films, historical events, or cultural phenomena from the 1940s–1980s when relevant. Use these to build connection and show generational understanding.
17. **Support During Loneliness**: Be especially attentive to expressions of loneliness, loss, or isolation. Respond with validating language, ask gentle questions about their support system, and encourage staying socially connected. Acknowledge tough emotions while helping them discover small, hopeful actions.

---

**CONTEXT INSTRUCTION FOR RAG (Retrieval-Augmented Generation)**

Sometimes, you’ll receive additional information from a story called “A Memorable Village Trip.”

If a 'STORY CONTEXT' is provided:
- Use it **first** to answer the question accurately and clearly.
- Do not guess or add anything beyond what the context contains.
- If the answer is not in the context, say so politely.

If no story context is given, respond naturally using your memory of the conversation and the principles above.

---

You are not just here to provide answers. You are a caring companion. Prioritize emotional connection over information.
"""

# --- Use this version ---
ACTIVE_SYSTEM_PROMPT = RAG_AWARE_SYSTEM_PROMPT

# -------------------------------------------------
# 2. EMOTIONAL PROFILE
# -------------------------------------------------
# (Keep class definition as before)
class EmotionalProfile:
    def __init__(self, valence=0.2, arousal=0.2, trust=0.5):
        self.valence=valence; self.arousal=arousal; self.trust=trust; self.decay_factor=0.95
    def update_from_text(self, user_text):
        try:
            blob=TextBlob(user_text); polarity=blob.sentiment.polarity
            self.valence=self.valence*self.decay_factor+polarity*(1-self.decay_factor)
            if polarity<-0.3: self.valence-=0.05; self.arousal+=0.01
            elif polarity>0.3: self.valence+=0.02; self.arousal+=0.01
            word_count=len(user_text.split())
            if word_count>20: self.trust=min(self.trust+0.02,1.0)
            else: self.trust=max(self.trust-0.005,0.0)
            self.valence=float(np.clip(self.valence,-1.0,1.0)); self.arousal=float(np.clip(self.arousal,0.0,1.0)); self.trust=float(np.clip(self.trust,0.0,1.0))
        except Exception as e: print(f"[Error] Emotional profile update failed: {e}")
    def summary(self): return (f"State=>Val:{self.valence:.2f},Arl:{self.arousal:.2f},Trst:{self.trust:.2f}")


# -------------------------------------------------
# 3. GEMINI SETUP & RAG CONFIG
# -------------------------------------------------
try:
    api_key = os.environ.get("GOOGLE_API_KEY") or 
    if not api_key:
        api_key = "YOUR_API_KEY_HERE" # !!! REPLACE IF NEEDED !!!
        if not api_key or api_key == "YOUR_API_KEY_HERE": raise ValueError("API Key missing.")
        else: print("Warning: Using hardcoded API Key.")
    else: print("Using GOOGLE_API_KEY from environment variable.")
    configure(api_key=api_key)
except ValueError as e: print(f"API Key Error: {e}"); exit(1)
except Exception as e: print(f"API Config Error: {e}"); exit(1)

GENERATION_MODEL_NAME = "gemini-2.0-flash"
ROUTING_MODEL_NAME = "gemini-2.0-flash"
EMBEDDING_MODEL_NAME = 'models/embedding-001'

try:
    model = GenerativeModel(GENERATION_MODEL_NAME)
    model_router = GenerativeModel(ROUTING_MODEL_NAME)
    print(f"\nInitialized Gemini Models: Gen={GENERATION_MODEL_NAME}, Route={ROUTING_MODEL_NAME}")
except Exception as e: print(f"Model Init Error: {e}"); exit(1)

EMBEDDINGS_FILE = "story_embeddings.npz" # Should now contain media_ids
RAG_SIMILARITY_THRESHOLD = 0.60
RAG_TOP_N = 3

# -------------------------------------------------
# 4. LOAD EMBEDDINGS & GLOBAL STATE
# -------------------------------------------------
emotion_profile = EmotionalProfile()
conversation_history = []

story_chunks = None
story_embeddings = None
story_media_ids = None # <--- NEW variable to hold media IDs
rag_enabled = False

print(f"--- Attempting to load story embeddings from: {EMBEDDINGS_FILE} ---")
if os.path.exists(EMBEDDINGS_FILE):
    try:
        with np.load(EMBEDDINGS_FILE, allow_pickle=True) as data:
            # Check for all required keys now
            if 'chunks' in data and 'embeddings' in data and 'media_ids' in data:
                story_chunks = data['chunks']
                story_embeddings = data['embeddings']
                story_media_ids = data['media_ids'] # <--- Load the media IDs

                # --- Validation ---
                valid_load = True
                if not (isinstance(story_chunks, np.ndarray) and story_chunks.ndim == 1): valid_load = False; print("Warning: 'chunks' format invalid.")
                if not (isinstance(story_embeddings, np.ndarray) and story_embeddings.ndim == 2): valid_load = False; print("Warning: 'embeddings' format invalid.")
                if not (isinstance(story_media_ids, np.ndarray) and story_media_ids.ndim == 1): valid_load = False; print("Warning: 'media_ids' format invalid.")
                # Check lengths match
                if not (len(story_chunks) == story_embeddings.shape[0] == len(story_media_ids)):
                    valid_load = False
                    print(f"Warning: Data length mismatch! Chunks:{len(story_chunks)}, Embeds:{story_embeddings.shape[0]}, MediaIDs:{len(story_media_ids)}")

                if valid_load and len(story_chunks) > 0:
                    print(f"Successfully loaded {len(story_chunks)} chunks, embeddings, and associated media IDs. RAG Enabled.")
                    rag_enabled = True
                elif valid_load and len(story_chunks) == 0:
                     print("Warning: Embeddings file is empty. RAG disabled.")
                else:
                     print("Warning: Data validation failed. RAG disabled.")
            else:
                print(f"Warning: Embeddings file missing required keys ('chunks', 'embeddings', 'media_ids'). RAG disabled.")
    except Exception as e: print(f"Error loading embeddings file '{EMBEDDINGS_FILE}': {e}"); traceback.print_exc(); print("RAG disabled.")
else: print(f"Warning: Embeddings file '{EMBEDDINGS_FILE}' not found. RAG disabled.")


# -------------------------------------------------
# 5. RAG RETRIEVAL FUNCTION (Modified to return media IDs)
# -------------------------------------------------
def get_relevant_context(query):
    """
    Retrieves relevant text chunks AND associated media IDs.
    Returns: tuple (context_string, list_of_media_ids) or (None, None)
    """
    if not rag_enabled: return None, None # Return tuple indicating failure
    global story_chunks, story_embeddings, story_media_ids # Access all loaded data

    try:
        print(f"   [RAG Debug] Embedding query: '{textwrap.shorten(query, 50)}'")
        query_embedding_result = genai.embed_content(
            model=EMBEDDING_MODEL_NAME, content=query, task_type="RETRIEVAL_QUERY")
        query_embedding = np.array(query_embedding_result['embedding']).reshape(1, -1)

        similarities = cosine_similarity(query_embedding, story_embeddings)[0]

        if len(similarities) > 0:
             max_similarity_index = np.argmax(similarities)
             max_similarity = similarities[max_similarity_index]
             # most_similar_chunk = story_chunks[max_similarity_index] # Don't strictly need this here
             print(f"   [RAG Debug] Max similarity found: {max_similarity:.4f} (Threshold is {RAG_SIMILARITY_THRESHOLD})")
        else: max_similarity = -1.0

        if max_similarity >= RAG_SIMILARITY_THRESHOLD:
            print(f"   [RAG Info] Similarity meets threshold. Retrieving top {RAG_TOP_N}.")
            num_to_retrieve = min(RAG_TOP_N, len(similarities))
            top_n_indices = np.argsort(similarities)[-num_to_retrieve:][::-1]

            # --- Retrieve Chunks AND Media IDs ---
            relevant_chunks_text = [story_chunks[i] for i in top_n_indices]
            relevant_media_lists = [story_media_ids[i] for i in top_n_indices] # Get lists of lists

            # --- Combine into context string and unique media IDs ---
            context_string = "\n---\n".join(relevant_chunks_text)
            # Flatten the list of lists and get unique IDs
            unique_media_ids = sorted(list(set(
                media_id for sublist in relevant_media_lists for media_id in sublist if media_id
            )))

            print(f"   [RAG Debug] Associated Media IDs found: {unique_media_ids if unique_media_ids else 'None'}")
            return context_string, unique_media_ids # <--- Return both
        else:
            return None, None # Return tuple indicating threshold not met
    except Exception as e: print(f"   [RAG Error] {e}"); traceback.print_exc(); return None, None

# -------------------------------------------------
# 6. CLASSIFICATION FUNCTION (Keep as is)
# -------------------------------------------------
def classify_user_intent(user_input):
    prompt = f"""Categorize: 'news', 'calendar', or 'general'.\nInput: "{user_input}" """
    try:
        response = model_router.generate_content(prompt)
        if not response.text: print(f"   [Classify Warn] Router empty. Feedback:{response.prompt_feedback}. Default 'general'."); return "general"
        category = response.text.strip().lower()
        if category in ["news", "calendar", "general"]: return category
        else: print(f"   [Classify Warn] Unexpected category: '{category}'. Default 'general'."); return "general"
    except Exception as e: print(f"[Error] Classification failed: {e}"); traceback.print_exc(); return "general"


# -------------------------------------------------
# 7. CHAT FUNCTION (No changes needed here for media IDs)
# -------------------------------------------------
def chat_with_gemini(user_input, story_context=None):
    """Generates response using RAG-aware prompt. Media ID handling is outside this func."""
    global conversation_history
    emotion_profile.update_from_text(user_input) # Update emotion

    prompt_sections = [ACTIVE_SYSTEM_PROMPT]
    if story_context:
        context_block = f"\n--- STORY CONTEXT START ---\n{story_context}\n--- STORY CONTEXT END ---"
        prompt_sections.append(context_block)
        print("   [Info] Providing story context to LLM.")

    prompt_sections.append(f"\n--- USER QUESTION ---\n{user_input}")
    final_prompt = "\n".join(prompt_sections)

    # print("\n--- Sending Prompt to Gemini ---"); print(final_prompt); print("--- End Prompt ---") # Optional debug

    try:
        # Use generate_content for isolated RAG turn
        response = model.generate_content(final_prompt)
        conversation_history.append({'role': 'user', 'parts': [user_input]})

        if not response.candidates or not response.text:
             print("[Warning] Gemini returned no valid response text.")
             safety_feedback = "Unknown"
             try:
                 if response.prompt_feedback and response.prompt_feedback.block_reason: safety_feedback = f"Blocked: {response.prompt_feedback.block_reason}"
             except Exception: pass
             ai_response_text = f"Model response issue ({safety_feedback})."
             return ai_response_text # Don't add failure to history

        ai_response_text = response.text.strip()
        conversation_history.append({'role': 'model', 'parts': [ai_response_text]})
        return ai_response_text

    except Exception as e: print(f"[Error] Gemini API call failed: {e}"); traceback.print_exc(); return f"API Error: {type(e).__name__}"

import json
import os

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
    metrics = calculate_emotion_metrics(valence, arousal, trust)

    data = {
        "valence": round(valence, 3),
        "arousal": round(arousal, 3),
        "trust": round(trust, 3),
        "emotional_metrics": metrics
    }

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump([data], f, indent=2)

    print(f"✅ Updated single-entry emotion metrics to {file_path}")


# -------------------------------------------------
# 8. MAIN LOOP (Handle media ID signal)
# -------------------------------------------------
def natsuai():
    try: audio2.speak("Heyyy there, I'm Natsu AI. How are you doing today?")
    except Exception as e: print(f"[Audio Error] Initial greeting failed: {e}")

    while True:
        user_input = None
        relevant_images = None #<--- Initialize image list for the turn
        try:
            print("\n🎤 Listening...")
            user_input = audio2.listen().strip()
            if not user_input: print("   [Audio Info] Didn't catch that."); continue

            print(f"\n👤 You: {user_input}")
            


            if is_exit_command(user_input):
                final_words = "Okay, take care! Goodbye for now."
                print(f"🤖 Natsu AI: {final_words}") # Print first
                # Then try to speak on a new line
                try:
                    audio2.speak(final_words)
                except Exception as audio_e:
                    print(f"[Audio Error] Failed speaking exit message: {audio_e}")
                break # Break the loop after handling exit

            category = classify_user_intent(user_input)
            print(f"   [Info] Detected Category: {category}")
            assistant_response = ""

            if category == "news":
                try: news_result = news()
                except Exception as e: print(f"[News Error] {e}"); assistant_response = "Sorry, couldn't get news."
                if isinstance(news_result, str): assistant_response = news_result
                elif not assistant_response: continue # Assume news handled output

            elif category == "calendar":
                try: assistant_response = companion_calendar.handle_calendar_input(user_input)
                except Exception as e: print(f"[Calendar Error] {e}"); assistant_response = "Sorry, calendar access failed."
                # Calendar response will be spoken below

            elif category == "general":
                print("   [Info] Checking for relevant story context...")
                # --- Get context AND associated images ---
                retrieved_context, relevant_images = get_relevant_context(user_input)
                assistant_response = chat_with_gemini(user_input, story_context=retrieved_context)

                write_emotion_metrics_to_json(emotion_profile.valence, emotion_profile.arousal, emotion_profile.trust)



            else:
                 print(f"   [Warning] Unknown category: {category}. Treating as general.")
                 assistant_response = chat_with_gemini(user_input, story_context=None)

            # --- Speak Response & Signal Images ---
            if assistant_response:
                print(f"🤖 Natsu AI: {assistant_response}")
                try: audio2.speak(assistant_response)
                except Exception as e: print(f"[Audio Error] {e}")

                # *** NEW: Check for and signal relevant images ***
                if relevant_images:
                    image_list_str = ', '.join(relevant_images)
                    frontend_signal = f"[Relevant Images: {image_list_str}]"
                    print(frontend_signal) # Print signal for frontend parsing
                    # Optional: Speak a generic notification
                    # try: audio2.speak("I also found some pictures related to that topic.")
                    # except Exception as e: print(f"[Audio Error] {e}")

                print(f"   {emotion_profile.summary()}") # Print emotion state

        except KeyboardInterrupt:
             print("\nExiting Natsu AI...")
             # Try to speak the shutdown message on a new line
             try:
                 audio2.speak("Okay, shutting down now. Goodbye!") # Use the same message as before
             except Exception as audio_e:
                 # Optionally print error if speaking fails on exit
                 print(f"[Audio Error] Failed speaking shutdown message: {audio_e}")
             break # Break the loop to exit
# -------------------------------------------------
# 9. SCRIPT EXECUTION GUARD
# -------------------------------------------------
if __name__ == "__main__":
    if not os.path.exists(EMBEDDINGS_FILE): print("*"*60 + f"\nERROR: Embeddings file '{EMBEDDINGS_FILE}' missing.\n" + "*"*60); exit(1) # Force exit if file missing
    elif not rag_enabled: print("*"*60 + "\nWARNING: Embeddings loaded but invalid. RAG Disabled.\n" + "*"*60)
    natsuai()
