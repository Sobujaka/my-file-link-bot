import os
import asyncio
from pyrogram import Client, filters
from aiohttp import web

API_ID = int(os.environ.get("37484134", 0))
API_HASH = os.environ.get("c160f92f8c0ff73632e05138f0d32997", "")
BOT_TOKEN = os.environ.get("8832724574:AAFbc_9e8cyIDxoQr9nr7B36P4gFR2RkdT4", "")
PORT = int(os.environ.get("PORT", 8080))

bot = Client("FileToLinkBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

routes = web.RouteTableDef()

@routes.get("/")
async def root_route_handler(request):
    return web.json_response({"status": "running"})

@routes.get("/download/{message_id}")
async def stream_handler(request):
    message_id = int(request.match_info['message_id'])
    return web.Response(text=f"Direct Link active for Message ID: {message_id}")

@bot.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_files(client, message):
    msg = await message.forward(chat_id=message.chat.id)
    app_url = os.environ.get("APP_URL", "http://localhost:8080")
    link = f"{app_url}/download/{msg.id}"
    await message.reply_text(f"Here is your Direct Download Link:\n\n{link}")

async def main():
    await bot.start()
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
