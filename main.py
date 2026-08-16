import os
import asyncio
from telethon import TelegramClient, events
from aiohttp import web

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
PORT = int(os.environ.get("PORT", 8080))

bot = TelegramClient('bot_session', API_ID, API_HASH)

# ইন-মেমোরি মেসেজ স্টোরেজ
file_store = {}

routes = web.RouteTableDef()

@routes.get("/")
async def root_route_handler(request):
    return web.Response(text="Bot is Live and Running!")

@routes.get("/download/{msg_id}")
async def stream_handler(request):
    try:
        msg_id = int(request.match_info['msg_id'])
        msg = file_store.get(msg_id)
        
        if not msg or not msg.media:
            return web.Response(status=404, text="File not found or expired")

        file_name = getattr(msg.file, 'name', 'file.mp4') or 'file.mp4'
        mime_type = getattr(msg.file, 'mime_type', 'application/octet-stream')

        response = web.StreamResponse(
            status=200,
            headers={
                'Content-Type': mime_type,
                'Content-Disposition': f'attachment; filename="{file_name}"'
            }
        )
        await response.prepare(request)
        
        async for chunk in bot.iter_download(msg.media):
            await response.write(chunk)
            
        return response
    except Exception as e:
        return web.Response(status=500, text=str(e))

@bot.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_files(event):
    if event.message.media:
        # মেসেজ অবজেক্ট ক্যাশে রাখা
        file_store[event.message.id] = event.message
        
        host_name = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
        if host_name:
            app_url = f"https://{host_name}"
        else:
            app_url = os.environ.get("APP_URL", "http://localhost:8080")

        link = f"{app_url}/download/{event.message.id}"
        await event.reply(f"📥 **Here is your Direct Download Link:**\n\n{link}")
    elif event.raw_text.startswith('/start'):
        await event.reply("👋 **Welcome! Send me any file or video to get a direct link.**")

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
