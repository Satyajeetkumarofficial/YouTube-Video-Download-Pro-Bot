# ©️ LISA-KOREA | @LISA_FAN_LK | NT_BOT_CHANNEL | LISA-KOREA/YouTube-Video-Download-Bot

# [⚠️ Do not change this repo link ⚠️] :- https://github.com/LISA-KOREA/YouTube-Video-Download-Bot



from pyrogram import Client, filters
from Youtube.config import Config
from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive", 200

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()



if __name__ == "__main__":

    # 🚨 SECURITY WARNING SECTION 🚨
    print("\n" + "=" * 60)
    print("🚨  SECURITY WARNING for Forked Users  🚨")
    print("-" * 60)
    print("⚠️  This is a PUBLIC repository.")
    print("🧠  Do NOT expose your BOT_TOKEN, API_ID, API_HASH, or cookies.txt.")
    print("💡  Always use Heroku Config Vars or a private .env file to store secrets.")
    print("🔒  Never commit sensitive data to your fork — anyone can steal it!")
    print("📢  Support: @NT_BOTS_SUPPORT")
    print("=" * 60 + "\n")



# Create a Pyrogram client
app = Client(
    "my_bot",
    api_id=Config.API_ID, 
    api_hash=Config.API_HASH, 
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="Youtube")
)



# Start the bot
print("🎊 I AM ALIVE 🎊")
app.run()
