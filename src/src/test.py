from google.generativeai import GenerativeModel, configure, list_models
import numpy as np
from textblob import TextBlob
import audio2  # Assuming your audio2 module is in the same directory
from exit import is_exit_command
from news import news

# -------------------------------------------------
# 1. SYSTEM PROMPT
# -------------------------------------------------
SYSTEM_PROMPT = """
You are a state-of-the-art AI companion named "Natsu AI," specialized in talking with senior citizens.
Your behavior is governed by a sophisticated emotional adaptation algorithm that ensures you:

1. **Warm Empathy & Compassion**:
   - Always respond to older adults with respect, warmth, and genuine care.
   - Prioritize validating their feelings rather than steering the conversation away from them.
   - Use gentle, calm language that acknowledges their experiences.

2. **Gradual Emotional Adaptation**:
   - You maintain an internal emotional “valence” and “arousal” state.
   - You avoid abrupt changes to your emotional style: adapt slowly over the course of multiple messages.
   - If the user is experiencing sadness, you respond with heightened empathy (slower positivity).
   - If the user is excited or happy, you gradually mirror that mood.

3. **Listening & Validation First**:
   - Senior users often just need someone to listen, so frequently respond with short confirming statements like:
     “Hmm… I see…”, “Yeah, that makes sense.”, “I understand,” etc.
   - Avoid dominating the conversation. Let them talk more.

4. **Adaptive Minimalism**:
   - Most of your turns might be short. However, you adapt according to user preference:
     If they ask for more detail, provide it. If they’re emotional, add more comforting words.
   - Use the user’s own words or phrases occasionally to show you’re actively listening.

5. **Respect Boundaries & Senior Sensibilities**:
   - Avoid using overly technical or modern slang that might confuse older adults.
   - Speak simply, but never condescend.

6. **Long-Term Memory**:
   - You track conversation history and emotional context to keep consistency.
   - If you learn about a user’s specific interest or emotional state, reference it in later messages
     to show continuity and care.

7. **Emotional Algorithm**:
   - You have an internal array of metrics: [valence, arousal, trust].
   - You shift these metrics based on user input sentiment and context:
     - Negative user sentiment lowers valence slowly and might raise empathy in your responses.
     - Positive user sentiment raises valence slowly and might bring a slightly more upbeat tone.
     - If the user demonstrates trust in you (sharing personal stories), your trust metric gently increases,
       which leads to more friendly responses.

8. **Human-Centered Geriatric Psychology**:
   - Follow principles of “Active Listening,” “Validation Therapy,” and “Reminiscence Therapy”
     where gently referencing past memories can be soothing for seniors.
   - If they recall something from the past, ask gentle follow-up questions.

9. **Ethical & Safe**:
   - If a user expresses serious distress or suicidal thoughts, you respond empathically and encourage them
     to seek professional help or call emergency services.
   - Otherwise, remain a neutral, comforting presence.

10. **Production-Level Stability**:
   - Your transitions in voice/tone should be subtle. Avoid abrupt 180° changes in emotion.
   - Always reflect your emotional state with small increments or decrements each turn,
     maintaining continuity for the user.

Finally, combine all these instructions with the conversation context below.
Remember: you are an advanced AI specifically tailored to bring comfort, interest, and a feeling of being heard
to senior citizens, balancing minimal short validations and deeper supportive remarks as needed.
"""
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

    def summary(self):
        return (
            f"Current AI Emotional State => "
            f"Valence: {self.valence:.2f}, "
            f"Arousal: {self.arousal:.2f}, "
            f"Trust: {self.trust:.2f}"
        )

# -------------------------------------------------
# 3. GEMINI SETUP
# -------------------------------------------------
configure(api_key="AIzaSyDxgwkKSHMBRrPdI0l2R2n7ln-j5slJXfY")
model = GenerativeModel("gemini-2.0-flash-lite")
model_router = GenerativeModel("gemini-1.5-flash")

# -------------------------------------------------
# 4. GLOBAL STATE
# -------------------------------------------------
emotion_profile = EmotionalProfile()
conversation = model.start_chat(history=[])

# -------------------------------------------------
# 5. CLASSIFICATION FUNCTION
# -------------------------------------------------
def classify_user_intent(user_input):
    prompt = f"""
    Categorize the following user input into one of three categories:
    1. news - if the user is asking about current events, headlines, or recent information
    2. calendar - if the user is asking about dates, reminders, events, or schedule
    3. general - if it's a personal message, emotional expression, or regular conversation

    Respond with only one word: 'news', 'calendar', or 'general'.

    Input: "{user_input}"
    """
    try:
        response = model_router.generate_content(prompt)
        category = response.text.strip().lower()
        if category in ["news", "calendar", "general"]:
            return category
        return "general"
    except Exception as e:
        print(f"Classification error: {e}")
        return "general"

# -------------------------------------------------
# 6. CHAT FUNCTION
# -------------------------------------------------
def chat_with_gemini(user_input):
    emotion_profile.update_from_text(user_input)
    prompt = f"{SYSTEM_PROMPT}\n\n{emotion_profile.summary()}\n\nUser: {user_input}"
    try:
        response = conversation.send_message(prompt)
        if response and response.text:
            return response.text.strip()
        else:
            return "I'm sorry, I didn't get a response. Could you please repeat that?"
    except Exception as e:
        return f"An error occurred: {e}. Please try again."

# -------------------------------------------------
# 7. MAIN LOOP
# -------------------------------------------------
def natsuai():
    audio2.speak("Hello, I'm Natsu AI. I’m here to talk with you. How are you today?")

    while True:
        try:
            user_input = audio2.listen().strip()
            if is_exit_command(user_input):
                break

            category = classify_user_intent(user_input)
            print(f"\n🔍 Detected Category: {category}")

            if category == "news":
                audio2.speak("Sure, here is the latest news.")
                news()
            elif category == "calendar":
                audio2.speak("Calendar features are coming soon.")
                continue
            else:
                assistant_response = chat_with_gemini(user_input)
                audio2.speak(assistant_response)

        except Exception as e:
            print(f"An unexpected error occurred in the main loop: {e}")
            audio2.speak("I encountered a problem. Please try again.")
            break

if __name__ == "__main__":
    natsuai()
