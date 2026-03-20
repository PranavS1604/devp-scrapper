import discord
from discord import app_commands
import google.generativeai as genai
from supabase import create_client
import os, requests

# Setup
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

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
    url = f"https://api.github.com/repos/{os.environ['GH_USER']}/{os.environ['GH_REPO']}/dispatches"
    headers = {"Authorization": f"token {os.environ['GH_PAT']}"}
    requests.post(url, headers=headers, json={"event_type": "manual_sync"})
    await interaction.response.send_message("⚡ Scraper started! Checking Devpost for new innovation...")

@bot.tree.command(name="brainstorm", description="Get 20 winning ideas based on history")
async def brainstorm(interaction: discord.Interaction, hackathon_desc: str):
    await interaction.response.defer()
    
    # 1. Vectorize the new hackathon
    query_vec = genai.embed_content(model="models/text-embedding-004", content=hackathon_desc)['embedding']
    
    # 2. Match against TOP 15 past projects
    matches = sb.rpc('match_projects', {'query_embedding': query_vec, 'match_threshold': 0.3, 'match_count': 15}).execute()
    context = "\n".join([f"- {m['title']}: {m['description']}" for m in matches.data])

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
    
    response = model.generate_content(prompt)
    await interaction.followup.send(response.text[:2000]) # Handle Discord character limit

bot.run(os.environ["DISCORD_TOKEN"])