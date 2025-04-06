import requests
import json
import os
from datetime import datetime
from newspaper import Article, Config
import audio2
import google.generativeai as genai
import re

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

def search_web(query):
    """
    Search for recent information using NewsData.io API
    Returns a list of search result files
    """
    print(f"🔍 Searching web for: '{query}'")
    
    # Extract important keywords for a more effective search
    keywords = extract_search_keywords(query)
    
    # Construct the search API URL
    url = "https://newsdata.io/api/1/news"
    params = {
        "apikey": NEWS_API_KEY,
        "language": "en",
        "q": keywords,  # Use extracted keywords for search
        "size": 5       # Limit to 5 results for speed
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        search_results = response.json().get("results", [])
        
        saved_files = []
        for idx, result in enumerate(search_results, 1):
            filename = f"{OUTPUT_DIR}/search_{idx}.json"
            
            # Enhance results with full content when available
            enhanced_result = get_full_article_content(result)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(enhanced_result, f, indent=2, ensure_ascii=False)
            saved_files.append(filename)
            print(f"✅ Saved search result: {filename}")
        
        return saved_files
        
    except Exception as e:
        print(f"❌ Error searching web: {str(e)}")
        return []

def extract_search_keywords(query):
    """
    Extract important keywords from a query to improve search results
    """
    # Remove common question words and filler words
    cleaned_query = re.sub(r'\b(what|where|when|who|how|why|is|are|was|were|will|do|does|did|can|could|would|should|tell|me|about|today|now|latest|new|recent|currently|please)\b', 
                          '', query.lower(), flags=re.IGNORECASE)
    
    # Extract possible named entities (words starting with uppercase)
    named_entities = re.findall(r'\b[A-Z][a-z]+\b', query)
    
    # If we have named entities, prioritize those
    if named_entities:
        keywords = ' '.join(named_entities)
        print(f"🔍 Extracted search keywords: '{keywords}' from query: '{query}'")
        return keywords
    
    # Otherwise, use the cleaned query
    keywords = cleaned_query.strip()
    print(f"🔍 Extracted search keywords: '{keywords}' from query: '{query}'")
    return keywords if keywords else query  # Fallback to original query if nothing left

def analyze_search_results(query, search_files):
    """
    Analyze search results to answer a specific query
    """
    if not search_files:
        return "I couldn't find any relevant information online for your question."
    
    # Collect content from all search results
    context = "Based on recent information found online:\n\n"
    
    for file in search_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                result = json.load(f)
                
            title = result.get('title', 'Untitled')
            source = result.get('source_id', 'Unknown Source')
            content = result.get('full_text', result.get('content', result.get('description', '')))
            
            if content:
                # Limit content length for each result
                context += f"- From {source}: {title}\n{content[:1000]}...\n\n"
        except Exception as e:
            print(f"Error processing search result file {file}: {e}")
    
    # Use Gemini to analyze the search results and answer the query
    prompt = f"""
    Based on the following information from recent search results, please answer this question:
    
    QUESTION: {query}
    
    SEARCH RESULTS:
    {context}
    
    If the search results don't contain relevant information to answer the question, 
    please be honest and say that you don't have enough information rather than making up an answer.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"I found some information, but couldn't analyze it properly: {str(e)}"

def news():
    audio2.speak("Fetching the latest news for you now.")
    json_files = fetch_live_news()
    if not json_files:
        return

    audio2.speak("Here are the top five latest news headlines.")
    for i, file in enumerate(json_files, 1):
        with open(file, 'r', encoding='utf-8') as f:
            article = json.load(f)
            audio2.speak(f"{i}. {article.get('title')}")

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
                audio2.speak("You can now ask a question about this article or say 'back' to choose another.")

                while True:
                    user_question = audio2.listen().strip()
                    if user_question.lower() in ['back', 'quit']:
                        audio2.speak("Going back to the article list.")
                        break

                    # audio2.speak("Analyzing your question.")
                    answer = analyze_with_gemini(article, user_question)
                    audio2.speak(answer)
            else:
                audio2.speak("Invalid selection. Please choose a number between 1 and 5.")
        except (ValueError, IndexError):
            audio2.speak("Please enter a valid number or command.")
