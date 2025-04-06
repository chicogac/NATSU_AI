# create_embeddings.py (Modified to store Image IDs)
import google.generativeai as genai
import json
import numpy as np
import os
import textwrap
import argparse # For command-line arguments

# --- Configuration ---
try:
    api_key = os.environ.get("GOOGLE_API_KEY") 
    if not api_key:
        api_key = "YOUR_API_KEY_HERE" # !!! REPLACE WITH YOUR KEY IF NEEDED !!!
        if not api_key or api_key == "YOUR_API_KEY_HERE":
             raise ValueError("No valid API Key found. Set GOOGLE_API_KEY or replace placeholder.")
        else: print("Warning: Using hardcoded API Key from script (less secure).")
    else: print("Using GOOGLE_API_KEY from environment variable.")
    genai.configure(api_key=api_key)
except ValueError as e: print(f"Error: {e}"); exit(1)
except Exception as e: print(f"An unexpected error during API configuration: {e}"); exit(1)

EMBEDDING_MODEL = 'models/embedding-001' # Or text-embedding-004 etc.

# --- Modified Extract Chunks Function ---
def extract_chunks_and_media(data):
    """
    Extracts text chunks and associated media IDs from the diary JSON.
    Returns two lists: text_chunks and media_ids_per_chunk.
    """
    text_chunks = []
    media_ids_per_chunk = [] # Parallel list to store associated media IDs for each chunk
    all_characters = set()

    # 1. Process metadata (no associated media)
    metadata = data.get('metadata', {})
    if metadata:
        meta_chunk = f"Diary Metadata:\n"
        meta_chunk += f"  Title: {metadata.get('title', 'N/A')}\n"
        meta_chunk += f"  Author: {metadata.get('author', 'N/A')}\n"
        meta_chunk += f"  Timeframe: {metadata.get('timeframe', 'N/A')}\n"
        # Add other metadata fields if needed...
        text_chunks.append(meta_chunk.strip())
        media_ids_per_chunk.append([]) # Empty list for metadata chunk

    # 2. Process each diary entry
    for entry in data.get('entries', []):
        entry_media_ids = [] # Media IDs specific to *this* entry chunk
        # --- Extract media IDs FIRST ---
        for media in entry.get('media', []):
            media_id = media.get('id')
            if isinstance(media_id, str) and media_id:
                entry_media_ids.append(media_id) # Collect IDs like 'car_packed.jpg'

        # --- Create the text chunk ---
        entry_chunk = f"Diary Entry ({entry.get('date', 'N/A')} {entry.get('time', 'N/A')})\n"
        entry_chunk += f"Title: {entry.get('title', 'No Title')}\n"
        entry_chunk += f"Mood: {entry.get('mood', 'N/A')}\n"
        entry_chunk += f"Content: {entry.get('content', '')}"
        # Important: DO NOT include media IDs directly in the text chunk anymore
        # unless you want the AI to potentially read them out.

        text_chunks.append(entry_chunk.strip())
        media_ids_per_chunk.append(entry_media_ids) # Add the list of IDs for this chunk

        # Collect unique characters mentioned in this entry
        for char_name in entry.get('characters', []):
            if isinstance(char_name, str) and char_name:
                all_characters.add(char_name)

    # 3. Create character summary chunk (no associated media)
    if all_characters:
        sorted_chars = sorted(list(all_characters))
        text_chunks.append(f"Characters Mentioned Across Diary: {', '.join(sorted_chars)}")
        media_ids_per_chunk.append([]) # Empty list

    # Filter out potentially empty chunks (and their corresponding empty media lists)
    final_chunks = []
    final_media_ids = []
    for i, chunk in enumerate(text_chunks):
        if chunk:
            final_chunks.append(chunk)
            final_media_ids.append(media_ids_per_chunk[i])

    return final_chunks, final_media_ids

# --- Main ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate embeddings for a diary JSON file.")
    parser.add_argument("json_file", default="story.json", nargs='?',
                        help="Path to the input diary JSON file (default: story.json)")
    parser.add_argument("-o", "--output", default="story_embeddings.npz",
                        help="Path to save the output embeddings file (default: story_embeddings.npz)")
    args = parser.parse_args()

    input_json_path = args.json_file
    output_npz_path = args.output

    print(f"\n📄 Loading diary data from: {input_json_path}")
    try:
        with open(input_json_path, 'r', encoding='utf-8') as f:
            diary_json_data = json.load(f)
    except FileNotFoundError: print(f"❌ Error: File not found: {input_json_path}"); exit(1)
    except json.JSONDecodeError as e: print(f"❌ Error: JSON Decode Error: {e}"); exit(1)
    except Exception as e: print(f"❌ Error loading JSON: {e}"); exit(1)

    print("🧠 Extracting text chunks and associated media IDs...")
    # Use the modified function
    text_chunks, media_ids_per_chunk = extract_chunks_and_media(diary_json_data)
    if not text_chunks: print("❌ No text chunks extracted."); exit(1)
    print(f"✅ Extracted {len(text_chunks)} chunks.")

    print(f"\n📡 Generating embeddings using Gemini model: {EMBEDDING_MODEL}")
    try:
        print(f"   Sending {len(text_chunks)} chunks for embedding...")
        embedding_result = genai.embed_content(
            model=EMBEDDING_MODEL, content=text_chunks, task_type="RETRIEVAL_DOCUMENT")
        corpus_embeddings = np.array(embedding_result['embedding'])
        if corpus_embeddings.shape[0] != len(text_chunks):
             print(f"❌ Error: Embedding result shape mismatch."); exit(1)
        print(f"✅ Generated {corpus_embeddings.shape[0]} embeddings (Dim: {corpus_embeddings.shape[1]})")
    except Exception as e: print(f"❌ Error during embedding generation: {e}"); exit(1)

    print(f"\n💾 Saving embeddings, chunks, and media IDs to: {output_npz_path}")
    try:
        np.savez_compressed(
            output_npz_path,
            chunks=np.array(text_chunks, dtype=object),
            embeddings=corpus_embeddings,
            media_ids=np.array(media_ids_per_chunk, dtype=object) # Save the new parallel array
        )
        print("✅ Data saved successfully.")
    except Exception as e: print(f"❌ Error saving embeddings: {e}"); exit(1)

    print("\n🏁 Embedding process complete.")
