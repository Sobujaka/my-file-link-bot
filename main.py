import os
import asyncio
from telethon import TelegramClient, events
from aiohttp import web

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
PORT = int(os.environ.get("PORT", 8080))

bot = TelegramClient('bot_session', API_ID, API_HASH)

routes = web.RouteTableDef()

@routes.get("/")
async def root_route_handler(request):
    return web.Response(text="Bot is Live and Running!")

@routes.get("/download/{message_id}")
async def stream_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        msg = await bot.get_messages("me", ids=message_id)
        
        if not msg or not msg.media:
            return web.Response(status=404, text="File not found")

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

@bot.on(events.NewMessage(incoming=True, func=lambda e: e.is_private and (e.document or e.video or e.audio)))
async def handle_files(event):
    msg = await event.message.forward_to("me")
    app_url = os.environ.get("APP_URL", "")
    if not app_url:
        app_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}"

    link = f"{app_url}/download/{msg.id}"
    await event.reply(f"📥 **Here is your Direct Download Link:**\n\n{link}")

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
