import os
import asyncio
import re
from hydrogram import Client, filters
from hydrogram.types import Message
from aiohttp import web

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
PORT = int(os.environ.get("PORT", 8080))

# Hydrogram Pure Async Client Initializing
app = Client(
    "stream_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

media_cache = {}
routes = web.RouteTableDef()

@routes.get("/")
async def root_handler(request):
    return web.Response(text="Bot Server is Running Smoothly!")

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
            html, body {{ width:100vw; height:100vh; background:#000; overflow:hidden; display:flex; align-items:center; justify-content:center; }}
            video {{ width:100vw; height:100vh; object-fit:contain; outline:none; }}
        </style>
    </head>
    <body>
        <video controls autoplay playsinline controlsList="nodownload">
            <source src="{stream_url}">
            Your browser does not support playing this video format.
        </video>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

@routes.get("/stream/{msg_id}")
async def stream_handler(request):
    try:
        msg_id = int(request.match_info['msg_id'])
        msg = media_cache.get(msg_id)
        
        if not msg:
            return web.Response(status=404, text="Video expired or Server Restarted. Send video to bot again.")

        media = msg.video or msg.document or msg.animation
        file_size = media.file_size
        mime_type = media.mime_type or "video/mp4"

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
            length = (end - start) + 1
            
            headers = {
                'Content-Type': mime_type,
                'Content-Range': f'bytes {start}-{end}/{file_size}',
                'Accept-Ranges': 'bytes',
                'Content-Length': str(length),
                'Access-Control-Allow-Origin': '*'
            }
            
            response = web.StreamResponse(status=206, headers=headers)
            await response.prepare(request)
            
            # Streaming media in optimized fast chunks
            async for chunk in app.stream_media(msg, offset=start, limit=length):
                await response.write(chunk)
                
            return response

        headers = {
            'Content-Type': mime_type,
            'Content-Length': str(file_size),
            'Accept-Ranges': 'bytes',
            'Access-Control-Allow-Origin': '*'
        }
        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)
        
        async for chunk in app.stream_media(msg):
            await response.write(chunk)
            
        return response

    except Exception as e:
        return web.Response(status=500, text=str(e))

@app.on_message(filters.private & (filters.video | filters.document))
async def handle_video(client, message: Message):
    media_cache[message.id] = message
    
    host_name = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
    if host_name:
        app_url = f"https://{host_name}"
    else:
        app_url = os.environ.get("APP_URL", "http://localhost:8080")

    watch_url = f"{app_url}/watch/{message.id}"
    await message.reply_text(f"🎬 **Stream Link:**\n\n{watch_url}")

async def main():
    await app.start()
    server = web.Application()
    server.add_routes(routes)
    runner = web.AppRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print("Server started successfully!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
