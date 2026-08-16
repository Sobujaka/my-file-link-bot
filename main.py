import os
import asyncio
from telethon import TelegramClient, events
from aiohttp import web

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
PORT = int(os.environ.get("PORT", 8080))

bot = TelegramClient('bot_session', API_ID, API_HASH)

file_store = {}

routes = web.RouteTableDef()

@routes.get("/")
async def root_route_handler(request):
    return web.Response(text="Bot is Live and Running!")

# ১. ওয়েব ভিডিও প্লেয়ার পেজ (IDM ক্যাচ করবে না)
@routes.get("/watch/{msg_id}")
async def player_handler(request):
    msg_id = int(request.match_info['msg_id'])
    stream_url = f"/stream/{msg_id}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="bn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Web Video Player</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ background-color: #0f0f0f; color: #ffffff; font-family: 'Segoe UI', sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }}
            .player-container {{ width: 100%; max-width: 900px; background: #1a1a1a; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            video {{ width: 100%; display: block; max-height: 70vh; outline: none; background: #000; }}
            .info-bar {{ padding: 18px 24px; display: flex; justify-content: space-between; align-items: center; background: #222; border-top: 1px solid #333; }}
            .title {{ font-size: 16px; font-weight: 600; color: #e1e1e1; }}
            .btn-download {{ background: #0078d4; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; transition: background 0.2s; }}
            .btn-download:hover {{ background: #005a9e; }}
        </style>
    </head>
    <body>
        <div class="player-container">
            <video controls autoplay name="media">
                <source src="{stream_url}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            <div class="info-bar">
                <span class="title">🎬 Playing Telegram Video</span>
                <a href="{stream_url}" class="btn-download" download>Direct Download</a>
            </div>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

# ২. ডাইরেক্ট ভিডিও স্ট্রিম হুক
@routes.get("/stream/{msg_id}")
async def stream_handler(request):
    try:
        msg_id = int(request.match_info['msg_id'])
        msg = file_store.get(msg_id)
        
        if not msg or not msg.media:
            return web.Response(status=404, text="File not found or expired")

        file_name = getattr(msg.file, 'name', 'video.mp4') or 'video.mp4'
        mime_type = getattr(msg.file, 'mime_type', 'video/mp4')

        response = web.StreamResponse(
            status=200,
            headers={
                'Content-Type': mime_type,
                'Content-Disposition': f'inline; filename="{file_name}"',
                'Accept-Ranges': 'bytes'
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
        file_store[event.message.id] = event.message
        
        host_name = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
        if host_name:
            app_url = f"https://{host_name}"
        else:
            app_url = os.environ.get("APP_URL", "http://localhost:8080")

        watch_link = f"{app_url}/watch/{event.message.id}"
        stream_link = f"{app_url}/stream/{event.message.id}"
        
        msg_text = (
            f"🎬 **Watch Video Online:**\n{watch_link}\n\n"
            f"📥 **Direct Stream / Download Link:**\n{stream_link}"
        )
        await event.reply(msg_text)
    elif event.raw_text.startswith('/start'):
        await event.reply("👋 **Welcome! Send me any video to get a streaming link.**")

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
