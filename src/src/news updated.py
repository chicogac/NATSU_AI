import requests
import json
import os
from datetime import datetime
from newspaper import Article, Config
from exit import is_exit_command
import audio2
import google.generativeai as genai

# Configuration
OUTPUT_DIR = "news_data"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Setup
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Configure newspaper3k
config = Config()
config.browser_user_agent = USER_AGENT
config.request_timeout = 10

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def fetch_live_news():
    """Fetch top 5 news articles and save as JSON"""
    url = "https://newsdata.io/api/1/news"
    params = {
        "apikey": NEWS_API_KEY,
        "language": "en",
        "category": "technology",
        "size": 5
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        articles = response.json().get("results", [])
        
        saved_files = []
        for idx, article in enumerate(articles, 1):
            filename = f"{OUTPUT_DIR}/article_{idx}.json"
            
            # Enhance article data with full content
            enhanced_article = get_full_article_content(article)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(enhanced_article, f, indent=2, ensure_ascii=False)
            saved_files.append(filename)
            print(f"✅ Saved: {filename}")
        
        return saved_files
        
    except Exception as e:
        print(f"❌ Error fetching news: {str(e)}")
        return []

def get_full_article_content(article_data):
    """Get full article text using newspaper3k"""
    try:
        article = Article(article_data['link'], config=config)
        article.download()
        article.parse()
        return {
            **article_data,
            "full_text": article.text,
            "cleaned_title": article.title,
            "authors": article.authors,
            "publish_date": str(article.publish_date) if article.publish_date else None,
            "top_image": article.top_image,
            "scraped_at": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"⚠️ Couldn't scrape {article_data['link']}: {str(e)}")
        return {
            **article_data,
            "full_text": article_data.get('content', ''),
            "scraped_at": datetime.now().isoformat()
        }

def analyze_with_gemini(article, question):
    """Analyze article content using Gemini"""
    prompt = f"""Analyze this news article and answer the question:
    
    TITLE: {article.get('title')}
    SOURCE: {article.get('source_id')}
    DATE: {article.get('pubDate')}
    
    CONTENT:
    {article.get('full_text', '')[:30000]}
    
    QUESTION: {question}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Analysis failed: {str(e)}"


def news():
    audio2.speak("Sure, here is the latest news")
    json_files = fetch_live_news()
    if not json_files:
        return

    while True:
        try:
            choice = input("\nSelect article (1-5), 'r' to refresh, or 'q' to quit: ").strip().lower()

            if choice == 'q':
                break
            elif choice == 'r':
                json_files = fetch_live_news()
                audio2.speak("News refreshed. Here are the updated headlines.")
                for i, file in enumerate(json_files, 1):
                    with open(file, 'r', encoding='utf-8') as f:
                        article = json.load(f)
                        # audio2.speak(f"{i}. {article.get('title')}")
                continue

            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(json_files):
                with open(json_files[choice_idx], 'r', encoding='utf-8') as f:
                    article = json.load(f)

                audio2.speak(article.get('title'))
                audio2.speak("Do you want to know anything specific?")

                while True:
                    user_question = audio2.listen().strip()   

                    if is_exit_command(user_question):
                        audio2.speak("see ya")
                        break


                    # audio2.speak("Analyzing your question.")
                    answer = analyze_with_gemini(article, user_question)
                    audio2.speak(answer)

            else:
                audio2.speak("Invalid selection. Please choose a number between 1 and 5.")
        except (ValueError, IndexError):
            audio2.speak("Please enter a valid number or command.")
