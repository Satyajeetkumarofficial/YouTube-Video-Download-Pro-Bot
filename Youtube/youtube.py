# ©️ LISA-KOREA | @LISA_FAN_LK | NT_BOT_CHANNEL

import os
import yt_dlp
import logging
import uuid
import aiohttp
import aiofiles

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from Youtube.config import Config
from Youtube.fix_thumb import fix_thumb
from Youtube.forcesub import handle_force_subscribe, humanbytes

YT_CACHE = {}

# ==============================
# FETCH FORMATS
# ==============================
@Client.on_message(filters.regex(r'^(http(s)?://)?(www\.)?(youtube\.com|youtu\.be)/.+'))
async def youtube_downloader(client, message):

    if Config.CHANNEL:
        fsub = await handle_force_subscribe(client, message)
        if fsub == 400:
            return

    url = message.text.strip()
    status = await message.reply_text("🔍 **Fetching available qualities...**")

    buttons = []

    try:
        ydl_opts = {
            "quiet": True,
            "cookiefile": "cookies.txt",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = info.get("formats", [])
        duration = info.get("duration", 0)
        title = info.get("title", "YouTube Video")

        vid_key = str(uuid.uuid4())[:8]
        YT_CACHE[vid_key] = url

        used_res = set()

        for f in formats:
            if f.get("vcodec") == "none":
                continue

            height = f.get("height")
            if not height or height in used_res:
                continue

            # Only show common qualities
            if height not in [144, 240, 360, 480, 720, 1080]:
                continue

            used_res.add(height)

            fmt_id = f.get("format_id")

            size = f.get("filesize") or f.get("filesize_approx")
            if not size:
                tbr = f.get("tbr")  # kbps
                if tbr and duration:
                    size = int((tbr * 1024 / 8) * duration)

            size_text = humanbytes(size) if size else "Unknown"

            text = f"{height}p • {size_text}"
            cb = f"ytdl|{vid_key}|{fmt_id}+bestaudio|mp4|video"

            if len(cb.encode()) <= 64:
                buttons.append([InlineKeyboardButton(text, callback_data=cb)])

        # Audio option
        buttons.append([
            InlineKeyboardButton("🎵 Audio MP3", callback_data=f"ytdl|{vid_key}|bestaudio|mp3|audio")
        ])

        await message.reply_text(
            f"🎬 **Select Quality:**\n`{title}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        await status.delete()

    except Exception as e:
        logging.exception("Format fetch error")
        await status.edit_text(f"❌ Error: `{e}`")


# ==============================
# DOWNLOAD HANDLER
# ==============================
@Client.on_callback_query(filters.regex(r"^ytdl\|"))
async def handle_download(client, cq):

    try:
        _, vid_key, fmt_id, ext, mode = cq.data.split("|")
        url = YT_CACHE.get(vid_key)

        if not url:
            await cq.message.edit_text("⚠️ Session expired. Please resend link.")
            return

        await cq.message.edit_text("⬇️ **Downloading...**")

        os.makedirs("downloads", exist_ok=True)
        output = f"downloads/{vid_key}.%(ext)s"

        if mode == "audio":
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": output,
                "quiet": True,
                "cookiefile": "cookies.txt",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }
        else:
            ydl_opts = {
                "format": fmt_id,  # ex: 137+bestaudio
                "outtmpl": output,
                "quiet": True,
                "cookiefile": "cookies.txt",
                "merge_output_format": "mp4",
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        title = info.get("title", "YouTube Video")
        duration = info.get("duration", 0)
        width = info.get("width")
        height = info.get("height")
        thumb_url = info.get("thumbnail")

        filesize = info.get("filesize") or info.get("filesize_approx")
        size_text = humanbytes(filesize) if filesize else "Unknown"

        file_path = f"downloads/{vid_key}.{ext if mode != 'audio' else 'mp3'}"

        # Thumbnail
        thumb_path = None
        if thumb_url:
            async with aiohttp.ClientSession() as s:
                async with s.get(thumb_url) as r:
                    if r.status == 200:
                        thumb_path = f"{vid_key}.jpg"
                        async with aiofiles.open(thumb_path, "wb") as f:
                            await f.write(await r.read())

        width, height, thumb_path = await fix_thumb(thumb_path)

        await cq.message.edit_text("📤 **Uploading...**")

        if mode == "audio":
            await client.send_audio(
                chat_id=cq.message.chat.id,
                audio=file_path,
                caption=f"🎵 **{title}**\n📦 Size: `{size_text}`",
                duration=duration,
                thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
            )
        else:
            await client.send_video(
                chat_id=cq.message.chat.id,
                video=file_path,
                caption=f"🎬 **{title}**\n📦 Size: `{size_text}`",
                width=width,
                height=height,
                duration=duration,
                supports_streaming=True,
                thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
            )

        await cq.message.edit_text("✅ **Done!**")

        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)

    except Exception as e:
        logging.exception("Download error")
        await cq.message.edit_text(f"❌ Error: `{e}`")
