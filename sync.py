import os
from playwright.sync_api import sync_playwright
from google import genai
from supabase import create_client
from dotenv import load_dotenv

# 1. Load the secret keys from your .env file
load_dotenv()

# 2. Setup the NEW 2026 Gemini Client
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# 3. Setup Supabase Client
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

def get_embedding(text):
    # New google-genai syntax for embeddings
    response = client.models.embed_content(
        model="text-embedding-004",
        contents=text
    )
    # Extract the vector array
    return response.embeddings[0].values

def run_scraper():
    print("🚀 Starting Scraper...")
    with sync_playwright() as p:
        # Launching with a real user agent to bypass basic bot detection
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        # 1. Load the gallery
        page.goto("https://devpost.com/software", wait_until="networkidle")
        
        # 2. Grab project links
        hrefs = page.eval_on_selector_all('a[href*="/software/"]', "elements => elements.map(e => e.href)")
        unique_urls = list(set(hrefs))[:10] # Grab the 10 latest unique projects

        for url in unique_urls:
            # Check if exists in DB to avoid duplicate work
            if supabase.table("projects").select("id").eq("url", url).execute().data:
                print(f"⏩ Skipping {url} (Already exists)")
                continue

            print(f"🔍 Scraping: {url}")
            page.goto(url)
            
            try:
                title = page.locator("#app-title").inner_text()
                raw_text = page.locator("#app-details-left").inner_text()
                
                # Use Gemini 2.5 Flash to clean up the scraped "mess" using the new syntax
                prompt = f"Summarize this project briefly for a RAG database: {raw_text[:4000]}"
                clean_summary_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                clean_summary = clean_summary_response.text
                
                # Save to Supabase
                supabase.table("projects").insert({
                    "title": title,
                    "description": clean_summary,
                    "url": url,
                    "embedding": get_embedding(clean_summary)
                }).execute()
                print(f"✅ Saved: {title}")
            except Exception as e:
                print(f"❌ Error scraping {url}: {e}")

        browser.close()
    print("🏁 Scraping complete!")

if __name__ == "__main__":
    run_scraper()