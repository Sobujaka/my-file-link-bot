import os
import asyncio
from pyrogram import Client, filters
from aiohttp import web

API_ID = int(os.environ.get("37484134", 0))
API_HASH = os.environ.get("c160f92f8c0ff73632e05138f0d32997", "")
BOT_TOKEN = os.environ.get("8832724574:AAFbc_9e8cyIDxoQr9nr7B36P4gFR2RkdT4", "")
PORT = int(os.environ.get("PORT", 8080))

bot = Client(
    "FileToLinkBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

routes = web.RouteTableDef()

@routes.get("/")
async def root_route_handler(request):
    return web.Response(text="Bot is Live and Running!")

@routes.get("/download/{message_id}")
async def stream_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        msg = await bot.get_messages("me", message_id)
        
        media = msg.video or msg.document or msg.audio
        if not media:
            return web.Response(status=404, text="File not found")

        response = web.StreamResponse(
            status=200,
            headers={
                'Content-Type': getattr(media, 'mime_type', 'application/octet-stream'),
                'Content-Disposition': f'attachment; filename="{getattr(media, "file_name", "file.mp4")}"'
            }
        )
        await response.prepare(request)
        
        async for chunk in bot.stream_media(msg):
            await response.write(chunk)
            
        return response
    except Exception as e:
        return web.Response(status=500, text=str(e))

@bot.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_files(client, message):
    msg = await message.forward("me")
    app_url = os.environ.get("APP_URL", "")
    if not app_url:
        app_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}"

    link = f"{app_url}/download/{msg.id}"
    await message.reply_text(f"📥 **Here is your Direct Download Link:**\n\n{link}")

async def start_services():
    await bot.start()
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
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        pass
