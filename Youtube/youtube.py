# ©️ LISA-KOREA | @LISA_FAN_LK | NT_BOT_CHANNEL | LISA-KOREA/YouTube-Video-Download-Bot
# [⚠️ Do not change this repo link ⚠️] :- https://github.com/LISA-KOREA/YouTube-Video-Download-Bot

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

def video_label(f):
    h = f.get("height")
    fps = f.get("fps")
    if h:
        lbl = f"{h}p"
        if fps and fps > 30:
            lbl += f"{int(fps)}"
        return lbl
    return "Video"

@Client.on_message(filters.regex(r'^(http(s)?://)?(www\.)?(youtube\.com|youtu\.be)/.+'))
async def youtube_downloader(client, message):
    if Config.CHANNEL:
        if await handle_force_subscribe(client, message) == 400:
            return

    url = message.text.strip()
    msg = await message.reply_text("🔍 **Fetching info...**")

    ydl_opts = {"quiet": True, "cookiefile": "cookies.txt"}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "YouTube Video")

        vid_key = str(uuid.uuid4())[:8]
        YT_CACHE[vid_key] = url

        buttons = [
            [InlineKeyboardButton("🎬 Video", callback_data=f"menu|{vid_key}|video")],
            [InlineKeyboardButton("🎵 Audio", callback_data=f"menu|{vid_key}|audio")],
            [InlineKeyboardButton("⭐ Best Quality", callback_data=f"best|{vid_key}")]
        ]

        await msg.edit_text(
            f"**Select download type:**\n`{title}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logging.exception(e)
        await msg.edit_text(f"❌ Error: `{e}`")

@Client.on_callback_query(filters.regex(r"^menu\|"))
async def show_menu(client, cq):
    _, vid_key, mode = cq.data.split("|")
    url = YT_CACHE.get(vid_key)

    if not url:
        return await cq.message.edit_text("⚠️ Session expired")

    ydl_opts = {"quiet": True}
    buttons = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    for f in info.get("formats", []):
        size = f.get("filesize") or f.get("filesize_approx")
        size_text = humanbytes(size) if size else "Unknown"

        if mode == "video":
            if f.get("vcodec") == "none":
                continue
            label = video_label(f)
        else:
            if f.get("acodec") == "none":
                continue
            abr = f.get("abr") or "Audio"
            label = f"{abr}kbps"

        cb = f"ytdl|{vid_key}|{f['format_id']}|{f.get('ext')}|{mode}"
        if len(cb.encode()) <= 64:
            buttons.append([InlineKeyboardButton(f"{label} • {size_text}", callback_data=cb)])

    await cq.message.edit_text(
        f"**Select {mode} quality:**",
        reply_markup=InlineKeyboardMarkup(buttons[:25])
    )

@Client.on_callback_query(filters.regex(r"^best\|"))
async def best_quality(client, cq):
    _, vid_key = cq.data.split("|")
    url = YT_CACHE.get(vid_key)

    if not url:
        return await cq.message.edit_text("⚠️ Session expired")

    await cq.message.edit_text("⬇️ **Downloading best quality...**")

    os.makedirs("downloads", exist_ok=True)
    out = f"downloads/{vid_key}.%(ext)s"

    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": out,
        "quiet": True,
        "cookiefile": "cookies.txt"
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    file_path = f"downloads/{vid_key}.mp4"
    title = info.get("title")
    duration = info.get("duration")

    await client.send_video(
        chat_id=cq.message.chat.id,
        video=file_path,
        caption=f"🎬 **{title}**",
        duration=duration,
        supports_streaming=True
    )

    await cq.message.edit_text("✅ **Uploaded!**")
    if os.path.exists(file_path):
        os.remove(file_path)

@Client.on_callback_query(filters.regex(r"^ytdl\|"))
async def handle_download(client, cq):
    try:
        _, vid_key, fmt_id, ext, mode = cq.data.split("|")
        url = YT_CACHE.get(vid_key)

        if not url:
            return await cq.message.edit_text("⚠️ Session expired")

        await cq.message.edit_text("⬇️ **Downloading...**")
        os.makedirs("downloads", exist_ok=True)
        out = f"downloads/{vid_key}.%(ext)s"

        if mode == "audio":
            ydl_opts = {
                "format": fmt_id,
                "outtmpl": out,
                "quiet": True,
                "cookiefile": "cookies.txt",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3"
                }]
            }
        else:
            ydl_opts = {
                "format": fmt_id,
                "outtmpl": out,
                "quiet": True,
                "cookiefile": "cookies.txt",
                "merge_output_format": "mp4"
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        file_path = f"downloads/{vid_key}.{'mp3' if mode=='audio' else 'mp4'}"
        size = info.get("filesize") or info.get("filesize_approx")
        size_text = humanbytes(size) if size else "Unknown"

        if mode == "audio":
            await client.send_audio(
                cq.message.chat.id,
                audio=file_path,
                caption=f"🎵 **{info.get('title')}**\n📦 `{size_text}`"
            )
        else:
            await client.send_video(
                cq.message.chat.id,
                video=file_path,
                caption=f"🎬 **{info.get('title')}**\n📦 `{size_text}`",
                supports_streaming=True
            )

        await cq.message.edit_text("✅ **Successfully Uploaded!**")
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        logging.exception(e)
        await cq.message.edit_text(f"❌ Error: `{e}`")
