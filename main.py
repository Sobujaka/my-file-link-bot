import os
import re
import asyncio
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

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
async def root_handler(request):
    return web.Response(text="Server Active on Koyeb")

@routes.get("/watch/{msg_id}")
async def watch_handler(request):
    msg_id = int(request.match_info['msg_id'])
    stream_url = f"/stream/{msg_id}"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fast Stream Player</title>
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{ background:#000; display:flex; justify-content:center; align-items:center; height:100vh; overflow:hidden; }}
            video {{ width:100%; height:100%; object-fit:contain; }}
        </style>
    </head>
    <body>
        <video controls autoplay playsinline preload="metadata">
            <source src="{stream_url}" type="video/mp4">
            Your browser does not support video streaming.
        </video>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

@routes.get("/stream/{msg_id}")
async def stream_handler(request):
    try:
        msg_id = int(request.match_info['msg_id'])
        msg = file_store.get(msg_id)
        
        if not msg or not msg.media:
            return web.Response(status=404, text="Video expired or Server Restarted.")

        file_size = getattr(msg.file, 'size', 0)
        mime_type = getattr(msg.file, 'mime_type', 'video/mp4') or 'video/mp4'

        range_header = request.headers.get('Range')
        
        if range_header:
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            start = int(match.group(1)) if match else 0
            end = int(match.group(2)) if match and match.group(2) else file_size - 1
            
            end = min(end, file_size - 1)
            length = (end - start) + 1
            
            headers = {
                'Content-Type': mime_type,
                'Content-Range': f'bytes {start}-{end}/{file_size}',
                'Accept-Ranges': 'bytes',
                'Content-Length': str(length),
                'Access-Control-Allow-Origin': '*',
            }
            
            response = web.StreamResponse(status=206, headers=headers)
            await response.prepare(request)
            
            # Ultra Fast Chunk Size
            async for chunk in bot.iter_download(msg.media, offset=start, limit=length, request_size=1024 * 1024):
                await response.write(chunk)
                
            return response

        headers = {
            'Content-Type': mime_type,
            'Content-Length': str(file_size),
            'Accept-Ranges': 'bytes',
            'Access-Control-Allow-Origin': '*',
        }
        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)
        
        async for chunk in bot.iter_download(msg.media, request_size=1024 * 1024):
            await response.write(chunk)
            
        return response

    except Exception as e:
        return web.Response(status=500, text=str(e))

@bot.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_files(event):
    if event.message.media:
        file_store[event.message.id] = event.message
        
        app_url = os.environ.get("KOYEB_PUBLIC_URL", os.environ.get("APP_URL", "http://localhost:8080"))

        watch_link = f"{app_url}/watch/{event.message.id}"
        await event.reply(f"🎬 **Stream Link:**\n\n{watch_link}")

async def start_services():
    await bot.start(bot_token=BOT_TOKEN)
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        pass
