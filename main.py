import os
import asyncio
import re
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

# ১. ফুলস্ক্রিন প্লেয়ার পেজ (ডাউনলোড বাটন মুক্ত)
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
        <title>Full Player Stream</title>
        <link href="https://vjs.zencdn.net/7.20.3/video-js.css" rel="stylesheet" />
        <script src="https://vjs.zencdn.net/7.20.3/video.min.js"></script>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            html, body {{ width: 100vw; height: 100vh; background-color: #000; overflow: hidden; }}
            .video-js {{ width: 100vw !important; height: 100vh !important; }}
            .vjs-control-bar {{ background: rgba(0, 0, 0, 0.7) !important; }}
        </style>
    </head>
    <body>
        <video id="my-video" class="video-js vjs-big-play-centered" controls autoplay playsinline data-setup='{{}}'>
            <source src="{stream_url}" type="video/mp4" />
        </video>
        <script>
            const player = videojs('my-video', {{
                responsive: true,
                fluid: false
            }});
            // কন্ট্রোল থেকে ডাউনলোড এবং কাস্টম মেনু দূর করা
            player.ready(function() {{
                const tech = player.tech({{ IWillNotUseThisInPlugins: true }});
                if (tech && tech.el_) {{
                    tech.el_.setAttribute('controlsList', 'nodownload');
                }}
            }});
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

# ২. Range Requests এবং Chunk Streaming হ্যান্ডলার
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
                'Content-Disposition': f'inline; filename="{file_name}"'
            }
            
            response = web.StreamResponse(status=206, headers=headers)
            await response.prepare(request)
            
            async for chunk in bot.iter_download(msg.media, offset=start, limit=content_length):
                await response.write(chunk)
                
            return response

        # সাধারণ ফ্রেচ হুক
        headers = {
            'Content-Type': 'video/mp4',
            'Content-Length': str(file_size),
            'Accept-Ranges': 'bytes',
            'Content-Disposition': f'inline; filename="{file_name}"'
        }
        response = web.StreamResponse(status=200, headers=headers)
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
        await event.reply("👋 **Send me any video file.**")

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
