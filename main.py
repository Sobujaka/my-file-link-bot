import os
import asyncio
import re
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
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

@routes.get("/watch/{msg_id}")
async def player_handler(request):
    msg_id = int(request.match_info['msg_id'])
    stream_url = f"/stream/{msg_id}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Video Stream</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            html, body {{ width: 100vw; height: 100vh; background-color: #000000; overflow: hidden; display: flex; align-items: center; justify-content: center; }}
            video {{ width: 100vw; height: 100vh; object-fit: contain; outline: none; }}
        </style>
    </head>
    <body>
        <video controls autoplay playsinline controlsList="nodownload">
            <source src="{stream_url}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

@routes.get("/stream/{msg_id}")
async def stream_handler(request):
    try:
        msg_id = int(request.match_info['msg_id'])
        msg = file_store.get(msg_id)
        
        if not msg or not msg.media:
            return web.Response(status=404, text="File not found")

        file_size = getattr(msg.file, 'size', 0)
        file_name = getattr(msg.file, 'name', 'video.mp4') or 'video.mp4'

        range_header = request.headers.get('Range')
        
        if range_header:
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else file_size - 1
            else:
                start = 0
                end = file_size - 1

            end = min(end, file_size - 1)
            content_length = (end - start) + 1
            
            headers = {
                'Content-Type': 'video/mp4',
                'Content-Range': f'bytes {start}-{end}/{file_size}',
                'Accept-Ranges': 'bytes',
                'Content-Length': str(content_length),
                'Content-Disposition': f'inline; filename="{file_name}"',
                'Access-Control-Allow-Origin': '*'
            }
            
            response = web.StreamResponse(status=206, headers=headers)
            await response.prepare(request)
            
            async for chunk in bot.iter_download(msg.media, offset=start, limit=content_length, request_size=128 * 1024):
                await response.write(chunk)
                
            return response

        headers = {
            'Content-Type': 'video/mp4',
            'Content-Length': str(file_size),
            'Accept-Ranges': 'bytes',
            'Content-Disposition': f'inline; filename="{file_name}"',
            'Access-Control-Allow-Origin': '*'
        }
        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)
        
        async for chunk in bot.iter_download(msg.media, request_size=128 * 1024):
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
        await event.reply("👋 **Send me any video to stream.**")

async def start_app():
    while True:
        try:
            await bot.start(bot_token=BOT_TOKEN)
            break
        except FloodWaitError as e:
            print(f"Waiting for {e.seconds} seconds due to Flood Wait...")
            await asyncio.sleep(e.seconds + 5)

    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_app())
    except KeyboardInterrupt:
        pass
