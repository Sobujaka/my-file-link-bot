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

# ১. সম্পূর্ণ ডিসপ্লে জুড়ে ফুলস্ক্রিন প্লেয়ার (ডাউনলোড অপশন ছাড়া)
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
        <title>Stream Player</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            html, body {{ width: 100%; height: 100%; background-color: #000000; overflow: hidden; display: flex; align-items: center; justify-content: center; }}
            video {{ width: 100vw; height: 100vh; object-fit: contain; background: #000; outline: none; }}
        </style>
    </head>
    <body>
        <video controls autoplay playsinline controlsList="nodownload">
            <source src="{stream_url}">
            Your browser does not support video playback.
        </video>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

# ২. ভিডিও স্ট্রিম ও ডাইনামিক MIME-Type হ্যান্ডলার
@routes.get("/stream/{msg_id}")
async def stream_handler(request):
    try:
        msg_id = int(request.match_info['msg_id'])
        msg = file_store.get(msg_id)
        
        if not msg or not msg.media:
            return web.Response(status=404, text="File not found")

        file_name = getattr(msg.file, 'name', 'video.mp4') or 'video.mp4'
        mime_type = getattr(msg.file, 'mime_type', '')

        # অডিও-অনলি সমস্যা দূর করার জন্য সঠিক ভিডিও মাইম টাইপ নির্ধারণ
        if not mime_type or 'video' not in mime_type:
            if file_name.endswith('.mkv'):
                mime_type = 'video/x-matroska'
            elif file_name.endswith('.webm'):
                mime_type = 'video/webm'
            else:
                mime_type = 'video/mp4'

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
        await event.reply(f"🎬 **Stream Link:**\n\n{watch_link}")
    elif event.raw_text.startswith('/start'):
        await event.reply("👋 **Welcome! Send me any video to stream.**")

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
