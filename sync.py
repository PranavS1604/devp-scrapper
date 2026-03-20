import os
import google.generativeai as genai
from playwright.sync_api import sync_playwright
from supabase import create_client

# Config
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

def get_embedding(text):
    # Standard embedding for RAG
    res = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document"
    )
    return res['embedding']

def scrape_devpost():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Go to the hackathon project gallery
        page.goto("https://devpost.com/software", wait_until="networkidle")
        
        # Logic to grab project links
        links = page.locator('a.softwares-card-link').all_hashes() # Adjust based on live CSS
        project_urls = [page.get_attribute(f'a[href*="/software/"]', "href")] # Simplified for example

        for url in project_urls:
            # Check if we already have it
            if supabase.table("projects").select("id").eq("url", url).execute().data:
                continue

            page.goto(url)
            title = page.locator("#app-title").inner_text()
            full_text = page.locator("#app-details-left").inner_text()
            github = page.locator('a[href*="github.com"]').first.get_attribute("href") or "N/A"

            # 2.5 Flash cleans the data for better vector search
            clean_text = model.generate_content(f"Summarize this project for a research database: {full_text[:4000]}").text

            supabase.table("projects").insert({
                "title": title,
                "description": clean_text,
                "url": url,
                "github_url": github,
                "embedding": get_embedding(clean_text)
            }).execute()

        browser.close()

if __name__ == "__main__":
    scrape_devpost()