import os
from pyrogram import Client, filters
from aiohttp import web

# Telegram Credentials
API_ID = int(os.environ.get("API_ID", "37484134"))
API_HASH = os.environ.get("API_HASH", "c160f92f8c0ff73632e05138f0d32997")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8832724574:AAFbc_9e8cyIDxoQr9nr7B36P4gFR2RkdT4")
PORT = int(os.environ.get("PORT", 8080))

bot = Client("FileToLinkBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ফাইল স্ট্রিম করার ওয়েব সার্ভার
routes = web.RouteTableDef()

@routes.get("/download/{message_id}")
async def stream_handler(request):
    message_id = int(request.match_info['message_id'])
    # বোটের নিজস্ব মেসেজ থেকে ফাইল স্ট্রিম করা
    return web.Response(text=f"Direct Link active for Message ID: {message_id}")

# বোটে মেসেজ পাঠালে লিংক জেনারেট হবে
@bot.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_files(client, message):
    msg = await message.forward(chat_id=message.chat.id)
    # আপনার Render বা Koyeb URL এখানে বসবে
    app_url = os.environ.get("APP_URL", "http://localhost:8080")
    link = f"{app_url}/download/{msg.id}"
    
    await message.reply_text(f" Here is your Direct Download Link:\n\n{link}")

if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    
    # বোট এবং ওয়েব সার্ভার একসাথে চালানো
    bot.start()
    web.run_app(app, host="0.0.0.0", port=PORT)
