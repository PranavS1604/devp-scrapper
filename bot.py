import discord
from discord import app_commands
from google import genai
from supabase import create_client
import os, requests
from keep_alive import keep_alive
from dotenv import load_dotenv

# 1. Load the secret keys from your .env file
load_dotenv()

# 2. Setup the NEW 2026 Gemini Client
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

@bot.tree.command(name="sync", description="Trigger the scraper to find new projects")
async def sync(interaction: discord.Interaction):
    # This calls the GitHub Action "Button"
    url = f"https://api.github.com/repos/{os.environ['GH_REPO']}/dispatches"
    headers = {"Authorization": f"token {os.environ['GH_PAT']}"}
    requests.post(url, headers=headers, json={"event_type": "manual_sync"})
    await interaction.response.send_message("⚡ Scraper started! Checking Devpost for new innovation...")

@bot.tree.command(name="brainstorm", description="Get 20 winning ideas based on history")
async def brainstorm(interaction: discord.Interaction, hackathon_desc: str):
    await interaction.response.defer()
    
    # 1. Vectorize the new hackathon (New google-genai syntax)
    embedding_response = client.models.embed_content(
        model="text-embedding-004", 
        contents=hackathon_desc
    )
    query_vec = embedding_response.embeddings[0].values
    
    # 2. Match against TOP 15 past projects
    matches = sb.rpc('match_projects', {'query_embedding': query_vec, 'match_threshold': 0.3, 'match_count': 15}).execute()
    
    # Format the context safely
    if matches.data:
        context = "\n".join([f"- {m['title']}: {m['description']}" for m in matches.data])
    else:
        context = "No past projects found. Brainstorming from scratch."

    # 3. Generate 20 Ideas
    prompt = f"""
    New Hackathon: {hackathon_desc}
    Past Winners Context: {context}
    
    Task: Based on what worked before, generate 20 UNIQUE, highly innovative project ideas. 
    Format each with:
    1. Catchy Name
    2. The 'Winning Pivot' (Why this stands out)
    3. Tech Stack (Focus on Gemini 2.5 Flash capabilities)
    """
    
    # Generate content (New google-genai syntax)
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    # 4. Handle Discord's 2000 character limit safely
    reply_text = response.text
    if len(reply_text) > 2000:
        # Split into chunks of 1900 characters so it doesn't break
        chunks = [reply_text[i:i+1900] for i in range(0, len(reply_text), 1900)]
        for chunk in chunks:
            await interaction.followup.send(chunk)
    else:
        await interaction.followup.send(reply_text)

keep_alive() # This starts the web server
# Run the bot
bot.run(os.environ["DISCORD_TOKEN"])