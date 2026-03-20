from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is awake and ready for Hackathons!"

def run():
    # Render assigns a random port, or defaults to 8080
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()