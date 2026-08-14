import gradio as gr
import asyncio
import edge_tts
import re
import os
import datetime
import requests
import gspread
import json
import urllib.parse
import base64
import subprocess
import tempfile
import shutil
import socket
import time
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
from gtts import gTTS
import firebase_admin
from firebase_admin import credentials, auth, firestore
from youtube_transcript_api import YouTubeTranscriptApi
from oauth2client.service_account import ServiceAccountCredentials
from user_agents import parse
from pymongo import MongoClient
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path

try:
    from pydub import AudioSegment
    from pydub.silence import detect_nonsilent
except ImportError:
    raise ImportError("Please install pydub: pip install pydub")

# ==========================================
# CONFIGURATION & ENVIRONMENT VARIABLES
# ==========================================
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://myowinhlaing374_db_user:GP6tAVurcbDxgQjj@cluster0.7nq5qht.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

GOOGLE_CREDENTIALS_JSON_STR = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
if GOOGLE_CREDENTIALS_JSON_STR:
    try:
        GOOGLE_SHEETS_CREDENTIALS = json.loads(GOOGLE_CREDENTIALS_JSON_STR)
    except Exception as e:
        print(f"⚠️ Error parsing GOOGLE_CREDENTIALS_JSON: {e}")
        GOOGLE_SHEETS_CREDENTIALS = None
else:
    GOOGLE_SHEETS_CREDENTIALS = None

# ==========================================
# TRANSLATIONS DICTIONARY (MYANMAR ONLY)
# ==========================================
LANG = {
    "my": {
        "welcome": "ကြိုဆိုပါတယ်",
        "welcome_title": "ကြိုဆိုပါတယ်",
        "welcome_sub": "သင့်ရဲ့ ဖန်တီးမှုနေရာကို ဝင်ရောက်ပါ",
        "sign_in": "🔑 ဝင်ရောက်ရန်",
        "sign_up": "📝 အကောင့်ဖွင့်ရန်",
        "email_placeholder": "အီးမေးလ် လိပ်စာ",
        "password_placeholder": "စကားဝှက်",
        "login_success": "✅ ကြိုဆိုပါတယ်!",
        "signup_success": "✅ အကောင့်ဖွင့်ပြီး ဝင်ရောက်ပြီးပါပြီ!",
        "enter_credentials": "❌ အီးမေးလ်နှင့် စကားဝှက် ထည့်ပါ",
        "password_short": "❌ စကားဝှက် အနည်းဆုံး ၆ လုံး ရှိရမည်",
        "user_not_found": "❌ သုံးစွဲသူ မတွေ့ပါ။ အကောင့်အရင်ဖွင့်ပါ။",
        "email_exists": "❌ ဒီအီးမေးလ် ပြီးသားရှိပါသည်။ ဝင်ရောက်ပါ။",
        "logout": "🚪 ထွက်ရန်",
        "profile": "ပရိုဖိုင်",
        "not_logged_in": "⚠️ ကျေးဇူးပြု၍ ဝင်ရောက်ပါ",
        "admin_dashboard": "🛡️ အက်ဒမင် ဒက်ရှ်ဘုတ်",
        "chat_success": "စကားဝိုင်း အောင်မြင်ပါသည်",
        "enter_text": "⚠️ စာသားထည့်ပါ",
        "tts_generating": "⏳ အသံထုတ်လုပ်နေသည်...",
        "tts_processing": "⏳ အသံအပိုင်းများ ပြင်ဆင်နေသည်...",
        "tts_success": "🎉 အသံနှင့် စာတန်းထိုး အောင်မြင်စွာ ထုတ်လုပ်ပြီးပါပြီ!",
        "tts_failed": "❌ အသံထုတ်လုပ်ခြင်း မအောင်မြင်ပါ။ ထပ်ကြိုးစားပါ။",
        "no_sentences": "❌ စာကြောင်းများ မတွေ့ပါ",
        "input_text": "📝 စာသားထည့်ရန်",
        "replacement_rules": "🔄 အစားထိုးစည်းမျဉ်းများ",
        "filename": "📁 ဖိုင်အမည်",
        "voice_selection": "🗣️ အသံရွေးချယ်မှု",
        "subtitle_style": "📺 စာတန်းထိုးပုံစံ",
        "speed_adjust": "⚡ အမြန်နှုန်း ချိန်ညှိမှု",
        "volume_adjust": "🔊 အသံအတိုးအကျယ် ချိန်ညှိမှု",
        "generate_audio": "🚀 အသံထုတ်လုပ်ရန်",
        "audio_preview": "🎵 အသံနမူနာ",
        "download_mp3": "📥 MP3 ဒေါင်းလုဒ်",
        "download_srt": "📥 စာတန်းထိုး ဒေါင်းလုဒ်",
        "video_export": "🎬 ဗီဒီယိုထုတ်လုပ်ရန် (၁၀ စက္ကန့်)",
        "bg_image": "🖼️ နောက်ခံပုံ (ရွေးချယ်နိုင်သည်)",
        "video_preview": "ဗီဒီယိုနမူနာ",
        "yt_analyzing": "🔍 YouTube ဗီဒီယိုကို ခွဲခြမ်းစိတ်ဖြာနေသည်...",
        "yt_no_transcript": "❌ စာတန်းထိုး မရရှိနိုင်ပါ။ ဗီဒီယိုတွင် စာတန်းထိုးမပါဝင်နိုင်ပါ။",
        "yt_invalid_url": "❌ YouTube လိပ်စာ မမှန်ကန်ပါ။",
        "yt_gemini_error": "❌ Gemini စာသားထုတ်လုပ်ခြင်း အမှားအယွင်း",
        "yt_link": "🔗 YouTube ဗီဒီယို လိပ်စာ",
        "analyze_yt": "🔍 YouTube ခွဲခြမ်းစိတ်ဖြာပြီး စာသားထုတ်ရန်",
        "raw_script": "📜 ထုတ်ယူထားသော ဇာတ်ညွှန်း",
        "polish_script": "✨ ဇာတ်ညွှန်းကို ပြုပြင်ရန်",
        "social_post": "📱 ဆိုရှယ်မီဒီယာ ပို့စ်ထုတ်ရန်",
        "send_to_tts": "➡️ TTS သို့ တိုက်ရိုက်ပို့ရန်",
        "polished_script": "✨ ပြုပြင်ထားသော ဇာတ်ညွှန်း",
        "social_content": "📱 ဆိုရှယ်မီဒီယာ အကြောင်းအရာ",
        "trans_upload": "❌ ကျေးဇူးပြု၍ အသံဖိုင် တင်ပါ",
        "trans_no_token": "❌ HF_TOKEN သတ်မှတ်မထားပါ။ ပြင်ဆင်ပါ။",
        "trans_processing": "⏳ စာသားပြောင်းနေသည်...",
        "trans_success": "✅ စာသားပြောင်းခြင်း အောင်မြင်ပါသည်!",
        "upload_audio": "အသံဖိုင် တင်ရန်",
        "detect_lang": "ဘာသာစကား ရှာဖွေရန်",
        "transcribe_btn": "🎤 Whisper-v3 ဖြင့် စာသားပြောင်းရန်",
        "transcript": "📜 စာသားပြောင်းထားသော အကြောင်းအရာ",
        "thumb_prompt": "❌ စာသားထည့်ပါ",
        "thumb_no_token": "❌ HF Token ထည့်ပါ",
        "thumb_success": "✅ ပုံထုတ်လုပ်ခြင်း အောင်မြင်ပါသည်!",
        "image_prompt": "🎨 ပုံဖော်ပြချက်",
        "gen_thumb": "🎨 ပုံထုတ်လုပ်ရန်",
        "generated_image": "ထုတ်လုပ်ထားသော ပုံ",
        "clone_text": "❌ စကားပြောရန် စာသားထည့်ပါ",
        "clone_gtts": "✅ gTTS ဖြင့် အသံထုတ်လုပ်ခြင်း အောင်မြင်ပါသည်!",
        "clone_edge": "✅ Edge TTS ဖြင့် အသံထုတ်လုပ်ခြင်း အောင်မြင်ပါသည်!",
        "text_to_speak": "📝 စကားပြောရန် စာသား",
        "voice_engine": "🎙️ အသံအင်ဂျင်",
        "speed": "⚡ အမြန်နှုန်း",
        "select_edge_voice": "Edge အသံရွေးချယ်ရန်",
        "gen_voice": "🎤 အသံထုတ်လုပ်ရန်",
        "audio_preview_label": "🔊 အသံနမူနာ",
        "bg_upload": "❌ ပုံတင်ပါ",
        "bg_success": "✅ နောက်ခံဖယ်ရှားခြင်း အောင်မြင်ပါသည်!",
        "upload_image": "ပုံတင်ရန်",
        "transparent_result": "နောက်ခံဖယ်ထားသော ပုံ",
        "remove_bg_btn": "✂️ နောက်ခံဖယ်ရှားရန်",
        "srt_upload": "❌ SRT ဖိုင်တင်ပါ",
        "srt_no_key": "❌ DeepL API Key ထည့်ပါ",
        "srt_success": "✅ SRT ဖိုင် ဘာသာပြန်ခြင်း အောင်မြင်ပါသည်!",
        "upload_srt": "📂 SRT ဖိုင်တင်ရန်",
        "source_lang": "ရင်းမြစ်ဘာသာစကား",
        "target_lang": "ပစ်မှတ်ဘာသာစကား",
        "translate_srt_btn": "🌍 SRT ဘာသာပြန်ရန်",
        "download_translated": "📄 ဘာသာပြန်ထားသော SRT",
        "payment_email": "❌ အီးမေးလ် လိပ်စာ ထည့်ပါ",
        "payment_phone": "❌ ဖုန်းနံပါတ် ထည့်ပါ",
        "payment_screenshot": "❌ ငွေလွှဲပုံတူ တင်ပါ",
        "payment_transaction": "❌ ငွေလွှဲအမှတ် ထည့်ပါ",
        "payment_success": "✅ ငွေပေးချေမှု အောင်မြင်စွာ တင်ပြပြီးပါပြီ!",
        "upgrade_pro": "💎 Pro အဆင့်မြှင့်ရန်",
        "unlock_features": "အင်္ဂါရပ်အားလုံးကို ဖွင့်လှစ်ရန်",
        "account_email": "📧 အကောင့် အီးမေးလ်",
        "payment_contact": "📱 ငွေပေးချေမှု ဆက်သွယ်ရန်",
        "subscription_tier": "💎 အသင်းဝင်အဆင့်",
        "payment_method": "💳 ငွေပေးချေမှုနည်းလမ်း",
        "transaction_ref": "🆔 ငွေလွှဲအကိုးအကား",
        "upload_receipt": "📷 ငွေလွှဲပုံတူ တင်ရန်",
        "submit_payment": "✅ ငွေပေးချေမှု အတည်ပြုတင်ပြရန်",
        "vip_benefits": "💎 VIP အကျိုးခံစားခွင့်များ",
        "access_denied": "❌ ဝင်ခွင့်မရှိပါ။ VIP သို့ အဆင့်မြှင့်ပါ။",
        "vip_access": "✅ VIP အသုံးပြုခွင့်",
        "free_limit": "❌ အခမဲ့အသုံးပြုခွင့် ကုန်ဆုံးပါပြီ။ VIP သို့ အဆင့်မြှင့်ပါ။",
        "vip_days": "👑 VIP ({} ရက် ကျန်ပါသည်)",
        "free_status": "🆓 အခမဲ့ ({}/၂ ကြိမ် ကျန်ပါသည်)",
        "db_error": "⚠️ ဒေတာဘေ့စ် အမှားအယွင်း၊ ယာယီခွင့်ပြုထားပါသည်",
        "tab_vip": "💎 Pro အဆင့်မြှင့်ရန်",
        "tab_tts": "🎙️ စာသားမှအသံ",
        "tab_youtube": "🎬 YouTube မှ စာသား",
        "tab_transcribe": "📝 အသံမှစာသား",
        "tab_thumbnail": "🖼️ AI ပုံထုတ်လုပ်ရေး",
        "tab_voiceclone": "🎤 အသံကူးယူရေး",
        "tab_bgremoval": "✂️ နောက်ခံဖယ်ရှားရေး",
        "tab_srt": "🌍 စာတန်းထိုးဘာသာပြန်ရေး",
        "tab_chat": "💬 AI စကားဝိုင်း",
        "tab_podcast": "🎙️ ပေါ့ကတ်စတူဒီယို",
        "tab_content": "📝 အကြောင်းအရာရေးသားရေး",
        "tab_movie_recap": "🎬 တစ်ချက်နှိပ်ရုံ ရုပ်ရှင်အကျဉ်းချုပ်",
        "tab_keys": "🔑 Key Management",
        "footer_credit": "✦ Myo Win Hlaing မှ ဖန်တီးထားသည် ✦",
        "telegram": "📲 တယ်လီဂရမ်",
        "support": "💬 အကူအညီ",
        "chat_title": "💬 AI စကားဝိုင်း",
        "chat_sub": "သင့်မေးခွန်းများကို AI နဲ့ မေးမြန်းပါ",
        "chat_placeholder": "မေးခွန်းထည့်ပါ...",
        "chat_ask": "🤖 မေးမြန်းရန်",
        "chat_clear": "🗑️ ရှင်းလင်းရန်",
        "chat_response": "🤖 AI အဖြေ",
        "chat_history": "📜 စကားဝိုင်းမှတ်တမ်း",
        "chat_thinking": "⏳ စဉ်းစားနေသည်...",
        "chat_error": "❌ AI အဖြေရယူရန် မအောင်မြင်ပါ",
        "podcast_title": "🎙️ ပေါ့ကတ်စတူဒီယို",
        "podcast_sub": "AI ဖြင့် ပေါ့ကတ်စ်ထုတ်လုပ်ပါ",
        "podcast_topic": "📝 အကြောင်းအရာ",
        "podcast_topic_placeholder": "ပေါ့ကတ်စ် အကြောင်းအရာ ထည့်ပါ...",
        "podcast_speakers": "🎙️ စကားပြောသူအရေအတွက်",
        "podcast_duration": "⏱️ ကြာချိန် (မိနစ်)",
        "podcast_style": "🎨 ပုံစံ",
        "podcast_style_casual": "ပေါ့ပေါ့ပါးပါး",
        "podcast_style_formal": "တရားဝင်",
        "podcast_style_interview": "အင်တာဗျူး",
        "podcast_style_story": "ပုံပြင်",
        "podcast_generate": "🎙️ ပေါ့ကတ်စ်ထုတ်လုပ်ရန်",
        "podcast_script": "📜 ဇာတ်ညွှန်း",
        "podcast_audio": "🔊 အသံဖိုင်",
        "podcast_status": "📊 အခြေအနေ",
        "podcast_generating": "⏳ ပေါ့ကတ်စ်ထုတ်လုပ်နေသည်...",
        "podcast_success": "✅ ပေါ့ကတ်စ်ထုတ်လုပ်ခြင်း အောင်မြင်ပါသည်!",
        "podcast_error": "❌ ပေါ့ကတ်စ်ထုတ်လုပ်ခြင်း မအောင်မြင်ပါ",
        "content_title": "📝 AI အကြောင်းအရာရေးသားရေး",
        "content_sub": "AI ဖြင့် အကြောင်းအရာများ ဖန်တီးပါ",
        "content_topic": "📝 အကြောင်းအရာ",
        "content_topic_placeholder": "ရေးသားလိုသော အကြောင်းအရာ ထည့်ပါ...",
        "content_type": "📋 အကြောင်းအရာအမျိုးအစား",
        "content_type_blog": "ဘလော့ဂ်ပို့စ်",
        "content_type_article": "ဆောင်းပါး",
        "content_type_social": "ဆိုရှယ်မီဒီယာပို့စ်",
        "content_type_email": "အီးမေးလ်",
        "content_type_story": "ဇာတ်လမ်း",
        "content_type_product": "ကုန်ပစ္စည်းဖော်ပြချက်",
        "content_length": "📏 အရှည်",
        "content_length_short": "တိုတို",
        "content_length_medium": "အလယ်အလတ်",
        "content_length_long": "ရှည်လျား",
        "content_tone": "🎭 ဟန်ပန်",
        "content_tone_professional": "ကျွမ်းကျင်သော",
        "content_tone_casual": "ပေါ့ပေါ့ပါးပါး",
        "content_tone_enthusiastic": "စိတ်လှုပ်ရှားဖွယ်",
        "content_tone_informative": "သတင်းအချက်အလက်",
        "content_tone_persuasive": "ဆွဲဆောင်မှုရှိသော",
        "content_generate": "📝 အကြောင်းအရာထုတ်လုပ်ရန်",
        "content_output": "📄 ထုတ်လုပ်ထားသော အကြောင်းအရာ",
        "content_status": "📊 အခြေအနေ",
        "content_generating": "⏳ အကြောင်းအရာထုတ်လုပ်နေသည်...",
        "content_success": "✅ အကြောင်းအရာထုတ်လုပ်ခြင်း အောင်မြင်ပါသည်!",
        "content_error": "❌ အကြောင်းအရာထုတ်လုပ်ခြင်း မအောင်မြင်ပါ",
        "content_copy": "📋 ကူးယူရန်",
        "content_export": "📥 ဒေါင်းလုဒ်လုပ်ရန်",
        "movie_recap_title": "🎬 တစ်ချက်နှိပ်ရုံ ရုပ်ရှင်အကျဉ်းချုပ်",
        "movie_recap_sub": "ဗီဒီယိုတင်ပါ သို့မဟုတ် YouTube လင့်ခ်ထည့်ပြီး ရုပ်ရှင်အကျဉ်းချုပ် အပြည့်အစုံ ရယူလိုက်ပါ",
        "movie_recap_link": "🔗 YouTube ဗီဒီယို လင့်ခ်",
        "movie_recap_link_placeholder": "https://youtube.com/watch?v=...",
        "movie_recap_voice": "🗣️ အသံ",
        "movie_recap_lang": "🌐 ဘာသာစကား",
        "movie_recap_generate": "🚀 ရုပ်ရှင်အကျဉ်းချုပ် ထုတ်လုပ်ရန်",
        "movie_recap_status": "📊 အခြေအနေ",
        "movie_recap_transcript": "📝 မူရင်းစာသား",
        "movie_recap_script": "📜 AI ဇာတ်ညွှန်း",
        "movie_recap_audio": "🎵 အသံဖိုင်",
        "movie_recap_thumbnail": "🎨 ပိုစတာ/သင်္ကေတပုံ",
        "movie_recap_subtitles": "📄 စာတန်းထိုး (SRT)",
        "movie_recap_video": "🎬 နောက်ဆုံးဗီဒီယို",
        "movie_recap_how_it_works": "💡 အလုပ်လုပ်ပုံ",
        "movie_recap_step1": "1. **ဗီဒီယိုတင်ခြင်း သို့မဟုတ် YouTube လင့်ခ်ထည့်ခြင်း**",
        "movie_recap_step2": "2. **စာသားထုတ်ယူခြင်း** - အသံမှ စာသားပြောင်းခြင်း သို့မဟုတ် YouTube စာတန်းထိုး",
        "movie_recap_step3": "3. **AI ဇာတ်ညွှန်းပြန်ရေးခြင်း** - Gemini AI ဖြင့် ဆွဲဆောင်မှုရှိသော ဇာတ်ညွှန်း",
        "movie_recap_step4": "4. **အသံထုတ်လုပ်ခြင်း** - Edge TTS ဖြင့် သဘာဝကျသော အသံ",
        "movie_recap_step5": "5. **ပိုစတာနှင့် စာတန်းထိုးထုတ်လုပ်ခြင်း** - AI ပိုစတာနှင့် SRT စာတန်းထိုး",
        "movie_recap_step6": "6. **ဗီဒီယိုထုတ်လုပ်ခြင်း** - အားလုံးကို ပေါင်းစပ်ပြီး နောက်ဆုံးဗီဒီယို",
        "movie_recap_upload": "📹 ဗီဒီယိုဖိုင် တင်ရန်",
        "movie_recap_upload_hint": "💡 သင့်ဗီဒီယိုဖိုင်ကို တင်ပါ (MP4/MOV/AVI - အများဆုံး 150MB)",
        "movie_recap_or": "— သို့မဟုတ် —",
        "movie_recap_input_method": "📤 ထည့်သွင်းနည်းရွေးချယ်မှု",
        "key_mgmt_title": "🔑 Key Management",
        "key_mgmt_sub": "Manage your API keys securely. Keys are stored per user and auto‑rotated when exhausted.",
        "key_gemini": "Gemini API Keys (comma‑separated or line-separated)",
        "key_hf": "Hugging Face Tokens (comma‑separated or line-separated)",
        "key_deepl": "DeepL API Keys (comma‑separated or line-separated)",
        "key_gmail": "Gmail App Passwords (comma‑separated or line-separated)",
        "key_firebase": "Firebase Service Account JSON (optional)",
        "key_google_sheets": "Google Sheets Credentials JSON (optional)",
        "key_other": "Other Keys (JSON, one per line)",
        "save_keys": "💾 Save Keys",
        "keys_saved": "✅ Keys saved successfully!",
        "keys_error": "❌ Error saving keys",
        "key_status": "📊 Key Status",
        "key_rotation": "🔄 Auto‑rotation enabled",
        "key_used": "Key used: {}",
        "key_exhausted": "Key exhausted, rotating...",
        "key_rotated": "Rotated to next key",
        "admin_message": "📢 Admin Message",
        "read_button": "✅ ဖတ်ပြီးပါပြီ",
        "no_notification": "No notifications available."
    }
}

def t(key, lang="my", *args):
    text = LANG.get(lang, LANG["my"]).get(key, key)
    if args:
        try:
            return text.format(*args)
        except:
            return text
    return text

# ==========================================
# FIREBASE INITIALIZATION
# ==========================================
try:
    if not firebase_admin._apps:
        fb_key = os.getenv("FIREBASE_KEY")
        if fb_key:
            cred = credentials.Certificate(json.loads(fb_key))
            firebase_admin.initialize_app(cred)
        else:
            cred = credentials.Certificate("firebase-key.json")
            firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase connected successfully!")
except Exception as e:
    print(f"⚠️ Firebase error: {e}")
    db = None

# ==========================================
# DATABASE HELPER
# ==========================================
def get_mongo_client():
    try:
        return MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    except Exception as e:
        print(f"⚠️ MongoDB Connection Error: {e}")
        return None

# ==========================================
# 🔥 NEW: TTS USAGE TRACKING (WITH AUTO-DELETE AFTER 2 DAYS)
# ==========================================

def setup_tts_ttl_index():
    """
    Setup TTL index for TTS collection (auto-delete after 2 days)
    Called on app startup
    """
    try:
        client = get_mongo_client()
        if client:
            db_mongo = client["vip_database"]
            tts_col = db_mongo["tts_usage"]
            
            # Drop existing index if any (to avoid duplicates)
            try:
                tts_col.drop_index("created_at_1")
            except:
                pass
            
            # Create TTL index: auto-delete after 2 days (172800 seconds)
            tts_col.create_index(
                "created_at", 
                expireAfterSeconds=172800  # 2 days = 48 hours
            )
            client.close()
            print("✅ TTS TTL index created successfully (auto-delete after 2 days)")
            return True
    except Exception as e:
        print(f"⚠️ TTS TTL index error: {e}")
        return False

def track_tts_usage(email, voice, engine, text_length, duration_seconds):
    """
    Track TTS usage for both Free and VIP users
    Saves to MongoDB tts_usage collection with auto-delete after 2 days
    """
    try:
        client = get_mongo_client()
        if client:
            db_mongo = client["vip_database"]
            tts_col = db_mongo["tts_usage"]
            
            # Ensure TTL index exists
            setup_tts_ttl_index()
            
            doc = {
                "email": email,
                "voice": voice,
                "engine": engine,  # "edge_tts" or "gtts"
                "text_length": text_length,
                "duration_seconds": duration_seconds,
                "created_at": datetime.datetime.now(),  # ✅ datetime object for TTL
                "date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
            tts_col.insert_one(doc)
            client.close()
            print(f"✅ TTS usage tracked: {email} - {voice} - {text_length} chars - {duration_seconds:.1f}s (auto-delete in 2 days)")
            return True
    except Exception as e:
        print(f"⚠️ TTS tracking error: {e}")
        return False

# ==========================================
# KEY MANAGEMENT SYSTEM
# ==========================================
def get_user_keys(email):
    if not email:
        return {}
    try:
        client = get_mongo_client()
        if client:
            db_mongo = client["vip_database"]
            keys_col = db_mongo["user_keys"]
            doc = keys_col.find_one({"email": email})
            client.close()
            if doc:
                return doc.get("keys", {})
        return {}
    except Exception as e:
        print(f"⚠️ Error getting user keys: {e}")
        return {}

def save_user_keys(email, keys_dict):
    if not email:
        return False, "No email provided"
    
    cleaned_keys = {}
    for service, keys in keys_dict.items():
        if isinstance(keys, list):
            cleaned = [k.strip() for k in keys if k and k.strip()]
            if cleaned:
                cleaned_keys[service] = cleaned
        elif isinstance(keys, str) and keys.strip():
            cleaned_keys[service] = [keys.strip()]
    
    try:
        client = get_mongo_client()
        if client:
            db_mongo = client["vip_database"]
            keys_col = db_mongo["user_keys"]
            
            if cleaned_keys:
                result = keys_col.update_one(
                    {"email": email},
                    {"$set": {
                        "keys": cleaned_keys, 
                        "updated_at": datetime.datetime.now().isoformat()
                    }},
                    upsert=True
                )
            else:
                result = keys_col.delete_one({"email": email})
            
            client.close()
            
            if result.acknowledged:
                total_count = sum(len(v) for v in cleaned_keys.values())
                return True, f"✅ Keys saved successfully! 📊 Total Keys: {total_count} keys"
            else:
                return False, "❌ Database write not acknowledged"
        return False, "❌ MongoDB connection failed"
    except Exception as e:
        print(f"⚠️ Error saving keys: {e}")
        return False, f"❌ Error saving keys: {str(e)}"

def get_key_with_rotation(email, service, default_env=None):
    keys = get_user_keys(email)
    service_keys = keys.get(service, [])
    
    if not service_keys and default_env:
        return default_env
    
    if not service_keys:
        return None
    
    current_idx = keys.get(f"{service}_current_idx", 0)
    
    if current_idx >= len(service_keys):
        current_idx = 0
        keys[f"{service}_current_idx"] = 0
        save_user_keys(email, keys)
    
    return service_keys[current_idx]

def rotate_key(email, service):
    try:
        keys = get_user_keys(email)
        service_keys = keys.get(service, [])
        
        if not service_keys:
            return False
        
        current_idx = keys.get(f"{service}_current_idx", 0)
        next_idx = (current_idx + 1) % len(service_keys)
        
        keys[f"{service}_current_idx"] = next_idx
        keys[f"{service}_last_rotation"] = datetime.datetime.now().isoformat()
        
        success, msg = save_user_keys(email, keys)
        
        if success:
            print(f"✅ Rotated {service} key from {current_idx} to {next_idx}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"⚠️ Rotate key error: {e}")
        return False

def check_gemini_key_validity(api_key):
    if not api_key or not api_key.strip():
        return False, "No key provided"
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key.strip()}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return True, "✅ Active"
        elif response.status_code == 403 or response.status_code == 401:
            return False, "❌ Invalid/Expired"
        elif "quota" in response.text.lower() or "rate" in response.text.lower():
            return False, "⚠️ Quota Exceeded"
        else:
            return False, f"❌ Error {response.status_code}"
    except Exception as e:
        return False, "❌ Connection Error"

def check_deepl_key_validity(api_key):
    if not api_key or not api_key.strip():
        return False, "No key provided"
    try:
        url = "https://api-free.deepl.com/v2/usage"
        headers = {"Authorization": f"DeepL-Auth-Key {api_key.strip()}"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return True, "✅ Active"
        elif response.status_code == 403:
            return False, "❌ Invalid/Expired"
        else:
            return False, f"❌ Error {response.status_code}"
    except Exception:
        return False, "❌ Connection Error"

def check_hf_key_validity(api_key):
    if not api_key or not api_key.strip():
        return False, "No key provided"
    try:
        url = "https://api-inference.huggingface.co/models/openai/whisper-large-v3"
        headers = {"Authorization": f"Bearer {api_key.strip()}"}
        response = requests.options(url, headers=headers, timeout=10)
        if response.status_code in [200, 401, 403]:
            if response.status_code == 401 or response.status_code == 403:
                return False, "❌ Invalid/Expired"
            return True, "✅ Active"
        return False, f"❌ Error {response.status_code}"
    except Exception:
        return False, "❌ Connection Error"

def refresh_keys_display(email):
    if not email:
        return """<div style="color: #9CA3AF; text-align: center; padding: 40px;">Please login first</div>"""
    keys = get_user_keys(email)
    gemini_keys = keys.get("gemini", [])
    deepl_keys = keys.get("deepl", [])
    hf_keys = keys.get("hf", [])
    
    env_gemini_valid = False
    env_gemini_status = "❌ Not Set"
    if GEMINI_API_KEY:
        valid, status = check_gemini_key_validity(GEMINI_API_KEY)
        env_gemini_valid = valid
        env_gemini_status = status

    html = """
    <div class="key-manager-container">
        <div class="status-header">
            <div class="status-title"><i class="icon-check-circle"></i> API Key Status</div>
            <span class="live-badge">LIVE</span>
        </div>
    """

    env_color = "#10B981" if env_gemini_valid else "#EF4444"
    env_icon = "✅" if env_gemini_valid else "❌"
    html += f"""
    <div class="status-card env-card">
        <div class="card-row">
            <div class="card-label"><span class="icon-globe">🌍</span> Environment Variable</div>
            <div class="status-badge" style="color:{env_color}; border-color:{env_color};">{env_icon} {env_gemini_status}</div>
        </div>
        <div class="card-subtext">GEMINI_API_KEY: {GEMINI_API_KEY[:20] + "..." if GEMINI_API_KEY else "Not Set"}</div>
    </div>
    """

    if gemini_keys:
        current_idx = keys.get("gemini_current_idx", 0)
        if current_idx >= len(gemini_keys):
            current_idx = 0
        html += f"""
        <div class="status-card key-card">
            <div class="card-header">
                <div class="card-label"><span class="icon-key">🔑</span> Gemini Keys</div>
                <div class="key-count">{len(gemini_keys)}/{len(gemini_keys)} keys</div>
            </div>
            <div class="key-list">
        """
        for i, key in enumerate(gemini_keys):
            valid, status = check_gemini_key_validity(key)
            color = "#10B981" if valid else "#EF4444"
            icon = "✅" if valid else "❌"
            is_active = "👉 " if i == current_idx else ""
            masked = key[:15] + "..." + key[-5:] if len(key) > 20 else key
            delete_btn = f"""
            <button onclick="deleteKey('{email}', 'gemini', {i})" class="delete-btn">
                🗑️ Delete
            </button>
            """
            html += f"""
            <div class="key-item">
                <span class="key-name">{is_active}{i+1}. {masked}</span>
                <div class="key-actions">
                    <span class="key-status" style="color:{color};">{icon} {status}</span>
                    {delete_btn}
                </div>
            </div>
            """
        html += "</div></div>"
    else:
        html += """
        <div class="status-card key-card empty-card">
            <div class="card-header">
                <div class="card-label"><span class="icon-key">🔑</span> Gemini Keys</div>
                <div class="key-count empty">No keys saved</div>
            </div>
        </div>
        """

    if deepl_keys:
        current_idx = keys.get("deepl_current_idx", 0)
        if current_idx >= len(deepl_keys):
            current_idx = 0
        html += f"""
        <div class="status-card key-card">
            <div class="card-header">
                <div class="card-label"><span class="icon-deepl">🌐</span> DeepL Keys</div>
                <div class="key-count">{len(deepl_keys)}/{len(deepl_keys)} keys</div>
            </div>
            <div class="key-list">
        """
        for i, key in enumerate(deepl_keys):
            valid, status = check_deepl_key_validity(key)
            color = "#10B981" if valid else "#EF4444"
            icon = "✅" if valid else "❌"
            is_active = "👉 " if i == current_idx else ""
            masked = key[:15] + "..." + key[-5:] if len(key) > 20 else key
            delete_btn = f"""
            <button onclick="deleteKey('{email}', 'deepl', {i})" class="delete-btn">
                🗑️ Delete
            </button>
            """
            html += f"""
            <div class="key-item">
                <span class="key-name">{is_active}{i+1}. {masked}</span>
                <div class="key-actions">
                    <span class="key-status" style="color:{color};">{icon} {status}</span>
                    {delete_btn}
                </div>
            </div>
            """
        html += "</div></div>"
    else:
        html += """
        <div class="status-card key-card empty-card">
            <div class="card-header">
                <div class="card-label"><span class="icon-deepl">🌐</span> DeepL Keys</div>
                <div class="key-count empty">No keys saved</div>
            </div>
        </div>
        """

    if hf_keys:
        current_idx = keys.get("hf_current_idx", 0)
        if current_idx >= len(hf_keys):
            current_idx = 0
        html += f"""
        <div class="status-card key-card">
            <div class="card-header">
                <div class="card-label"><span class="icon-hf">🤗</span> Hugging Face Keys</div>
                <div class="key-count">{len(hf_keys)}/{len(hf_keys)} keys</div>
            </div>
            <div class="key-list">
        """
        for i, key in enumerate(hf_keys):
            valid, status = check_hf_key_validity(key)
            color = "#10B981" if valid else "#EF4444"
            icon = "✅" if valid else "❌"
            is_active = "👉 " if i == current_idx else ""
            masked = key[:15] + "..." + key[-5:] if len(key) > 20 else key
            delete_btn = f"""
            <button onclick="deleteKey('{email}', 'hf', {i})" class="delete-btn">
                🗑️ Delete
            </button>
            """
            html += f"""
            <div class="key-item">
                <span class="key-name">{is_active}{i+1}. {masked}</span>
                <div class="key-actions">
                    <span class="key-status" style="color:{color};">{icon} {status}</span>
                    {delete_btn}
                </div>
            </div>
            """
        html += "</div></div>"
    else:
        html += """
        <div class="status-card key-card empty-card">
            <div class="card-header">
                <div class="card-label"><span class="icon-hf">🤗</span> Hugging Face Keys</div>
                <div class="key-count empty">No keys saved</div>
            </div>
        </div>
        """

    total_keys = len(gemini_keys) + len(deepl_keys) + len(hf_keys)
    js_code = """
    <script>
    function deleteKey(email, service, index) {
        if (!confirm("Are you sure you want to delete this API key? This action cannot be undone.")) {
            return;
        }
        fetch('/delete_key', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
                service: service,
                index: index
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("✅ Key deleted successfully!");
                location.reload();
            } else {
                alert("❌ Error: " + data.message);
            }
        })
        .catch(error => {
            alert("❌ Error: " + error);
        });
    }
    </script>
    """
    html += f"""
        <div class="status-footer">
            <div class="footer-item"><span class="icon-rotation">⚡</span> Auto-Rotation: <span class="highlight">Enabled</span></div>
            <div class="footer-item"><span class="icon-total">📊</span> Total Keys: <span class="highlight">{total_keys}</span> keys in database</div>
        </div>
    </div>
    {js_code}
    """
    return html

# ==========================================
# BROADCAST & ADS SETTINGS
# ==========================================
def get_broadcast_settings():
    try:
        client = get_mongo_client()
        if client:
            db_mongo = client["vip_database"]
            settings_col = db_mongo["system_settings"]
            settings = settings_col.find_one({"type": "broadcast"})
            client.close()
            if settings:
                return {
                    "message": settings.get("message", "⚡ Welcome to Recap Creator Studio! Supercharge your content creation with AI-powered audio, video, and text tools."),
                    "vpn_message": settings.get("vpn_message", ""),
                    "ad_image_url": settings.get("ad_image_url", ""),
                    "ad_redirect_url": settings.get("ad_redirect_url", ""),
                    "app_download_link": settings.get("app_download_link", "https://t.me/yufei199"),
                    "updated_at": settings.get("updated_at", "")
                }
    except Exception as e:
        print(f"⚠️ Broadcast settings error: {e}")
    return {
        "message": "⚡ Welcome to Recap Creator Studio! Supercharge your content creation with AI-powered audio, video, and text tools.",
        "vpn_message": "",
        "ad_image_url": "",
        "ad_redirect_url": "",
        "app_download_link": "https://t.me/yufei199",
        "updated_at": ""
    }

def get_broadcast_html():
    settings = get_broadcast_settings()
    message = settings.get("message", "⚡ Welcome to Recap Creator Studio!")
    return f"""
    <div class="broadcast-marquee">
        <div class="broadcast-marquee-inner">
            {message}
        </div>
    </div>
    """

# ==========================================
# AUTH FUNCTIONS
# ==========================================
def create_user_with_email(email, password):
    if not db:
        return "❌ Firebase is not configured.", None, False
    try:
        try:
            users_ref = db.collection('users')
            query = users_ref.where('email', '==', email).limit(1).get()
            if query:
                return "❌ This email is already registered. Please login instead.", None, False
        except:
            pass
        user = auth.create_user(email=email, password=password)
        users_ref = db.collection('users')
        users_ref.document(user.uid).set({
            'email': email,
            'is_vip': False,
            'vip_expiry': None,
            'created_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'last_login': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return "✅ Account created and logged in successfully!", email, True
    except Exception as e:
        error_msg = str(e)
        if "EMAIL_EXISTS" in error_msg:
            return "❌ This email is already registered. Please login instead.", None, False
        return f"❌ Error: {error_msg}", None, False

def login_with_email_password(email, password):
    if not db:
        return "❌ Firebase is not configured.", None, False
    try:
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', email).limit(1).get()
        if not query:
            return "❌ User not found. Please sign up first.", None, False
        for doc in query:
            try:
                doc.reference.update({'last_login': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            except:
                pass
        try:
            user = auth.get_user_by_email(email)
            if user:
                return "✅ Welcome back!", email, True
        except:
            return "✅ Welcome back!", email, True
    except Exception as e:
        return f"❌ Login error: {str(e)}", None, False

def get_user_vip_info(email):
    if not email or db is None:
        return None, None, "⚠️ Not logged in"
    try:
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', email).limit(1).get()
        for doc in query:
            data = doc.to_dict()
            is_vip = data.get('is_vip', False)
            vip_expiry = data.get('vip_expiry', None)
            if is_vip and vip_expiry:
                try:
                    expiry_date = datetime.datetime.strptime(vip_expiry, "%Y-%m-%d") if isinstance(vip_expiry, str) else vip_expiry
                    days_left = (expiry_date - datetime.datetime.now()).days
                    if days_left > 0:
                        return True, days_left, f"👑 VIP ({days_left} days left)"
                    else:
                        doc.reference.update({'is_vip': False})
                        return False, None, "🆓 Free"
                except Exception:
                    return False, None, "🆓 Free"
            else:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                try:
                    client = get_mongo_client()
                    if client:
                        db_mongo = client["vip_database"]
                        count = db_mongo["usage_counts"].count_documents({"email": email, "date": today})
                        client.close()
                        remaining = max(0, 2 - count)
                        return False, remaining, f"🆓 Free ({remaining}/2 left today)"
                except Exception:
                    pass
                return False, None, "🆓 Free"
        return None, None, "⚠️ Not found"
    except Exception:
        return None, None, "⚠️ Error checking status"

def update_profile_display(email, lang="my"):
    if not email:
        return f"""
        <div class='profile-badge-empty'>
            <div class='text-muted'>{t('not_logged_in', lang)}</div>
        </div>
        """
    is_vip, days, status_text = get_user_vip_info(email)
    if is_vip and days:
        status_text = t('vip_days', lang, days)
    elif is_vip is False and days is not None:
        status_text = t('free_status', lang, days)
    elif is_vip is False:
        status_text = t('free_status', lang, 2)
    else:
        status_text = t('db_error', lang)
    try:
        res = requests.get("http://ip-api.com/json/", timeout=3).json()
        country = res.get("country", "Unknown")
        cc = res.get("countryCode", "").lower()
        flag = chr(ord(cc[0]) + 127397) + chr(ord(cc[1]) + 127397) if len(cc) == 2 else "🌐"
    except Exception:
        flag, country = "🌐", "Unknown"
    initial = email[0].upper() if email else "U"
    return f"""
    <div class='profile-dropdown-container' onclick="this.classList.toggle('active')">
        <div class='profile-avatar'>
            <img src="https://ui-avatars.com/api/?name={initial}&background=8A2BE2&color=fff&rounded=true&bold=true" alt="Profile" />
        </div>
        <div class='profile-dropdown-menu'>
            <div class='profile-email' title='{email}'>{email}</div>
            <div class='profile-location'>{flag} {country}</div>
            <div class='profile-status-box'>{status_text}</div>
        </div>
    </div>
    """

def check_tool_access(email, lang="my"):
    if not email:
        return False, t('not_logged_in', lang)
    is_vip, days, status_text = get_user_vip_info(email)
    if is_vip:
        return True, t('vip_access', lang)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        client = get_mongo_client()
        if client:
            db_mongo = client["vip_database"]
            count = db_mongo["usage_counts"].count_documents({"email": email, "date": today})
            client.close()
            if count >= 2:
                return False, t('free_limit', lang)
            return True, t('free_status', lang, 2-count)
    except Exception:
        pass
    return True, t('db_error', lang)

def increment_usage(email):
    if not email: return
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        client = get_mongo_client()
        if client:
            db_mongo = client["vip_database"]
            db_mongo["usage_counts"].insert_one({"email": email, "date": today})
            client.close()
    except Exception as e:
        print(f"⚠️ Usage track error: {e}")

# ==========================================
# NOTIFICATION SYSTEM
# ==========================================
def check_notifications(email):
    """Check for unread notifications"""
    if not email or db is None:
        return "🔔", "", ""
    
    try:
        email = email.strip().lower()
        notif_ref = db.collection('user_notifications')
        query = notif_ref.where('target_email', '==', email).where('is_read', '==', False).limit(1).get()
        
        if not query:
            return "🔔", "", ""
        
        doc = query[0]
        data = doc.to_dict()
        msg = data.get("message", "📢 You have a new admin message!")
        doc_id = doc.id
        
        red_dot_html = """
        <span style="position:relative; display:inline-block;">
            <span style="display:inline-block; width:14px; height:14px; background:#EF4444; border-radius:50%; border:2px solid #0B0A15;"></span>
        </span>
        """
        return red_dot_html, doc_id, msg
    except Exception as e:
        print(f"❌ Error fetching notifications: {e}")
        return "", "", ""

def open_notification(doc_id, msg):
    if not doc_id:
        return gr.update(visible=False), ""
    return gr.update(visible=True), msg

def close_notification(doc_id):
    if doc_id and db:
        try:
            db.collection('user_notifications').document(doc_id).update({"is_read": True})
        except Exception as e:
            print(f"❌ Error updating notification: {e}")
    return gr.update(visible=False, elem_styles={"display": "none !important"}), ""

# ==========================================
# TTS FUNCTIONS
# ==========================================
def format_srt_time(seconds):
    millis = int(seconds * 1000)
    hours, millis = divmod(millis, 3600000)
    minutes, millis = divmod(millis, 60000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def clean_and_split_text(text, max_chars=50):
    if not text: return []
    for char in ["“", "”", '"', "‘", "’", "'", "…", "—", "--"]: 
        text = text.replace(char, " ")
    raw = re.split(r'([၁၂၃၄၅၆၇၈၉၀။၊!?\n])', text)
    sentences, current = [], ""
    for item in raw:
        current += item
        if item in ['။', '၊', '?', '!', '\n']:
            if current.strip(): sentences.append(current.strip())
            current = ""
    if current.strip(): sentences.append(current.strip())
    final = []
    for s in sentences:
        if len(s) <= max_chars: final.append(s)
        else:
            words = s.split(" ")
            chunk = ""
            for w in words:
                if len(chunk) + len(w) + 1 <= max_chars:
                    chunk += (" " if chunk else "") + w
                else:
                    if chunk: final.append(chunk.strip())
                    chunk = w
            if chunk: final.append(chunk.strip())
    return [c for c in final if c.strip()]

async def process_voice_generation(email, text, rules, filename, voice, srt_type, speed, volume, lang="my", progress=gr.Progress()):
    if not text.strip(): 
        return None, None, None, t('enter_text', lang)
    can_access, msg = check_tool_access(email, lang)
    if not can_access:
        return None, None, None, f"❌ {msg}"
    if rules.strip():
        for line in rules.strip().split("\n"):
            if "=" in line:
                k, v = line.split("=", 1)
                text = text.replace(k.strip(), v.strip())
    voice_map = {
        "သီဟ (အမျိုးသား)": "my-MM-ThihaNeural",
        "နီလာ (အမျိုးသမီး)": "my-MM-NilarNeural",
    }
    selected_voice = voice_map.get(voice, "my-MM-ThihaNeural")
    pitch_rate = "+0Hz"
    base_speed = speed + 20
    speed_rate = f"{'+' if base_speed >= 0 else ''}{base_speed}%"
    volume_rate = f"+{volume}%"
    output_name = filename.strip() if filename.strip() else "Myanmar_TTS"
    output_mp3 = f"{output_name}.mp3"
    output_srt = f"{output_name}_subtitle.srt"
    max_chars = 35 if srt_type == "TikTok" else 65
    sentences = clean_and_split_text(text, max_chars=max_chars)
    if not sentences: 
        return None, None, None, t('no_sentences', lang)
    progress(0.1, desc="⏳ Initializing TTS (1/5)...")
    sem = asyncio.Semaphore(10)
    async def fetch_audio(idx, sentence):
        async with sem:
            try:
                comm = edge_tts.Communicate(text=sentence, voice=selected_voice, rate=speed_rate, volume=volume_rate, pitch=pitch_rate)
                audio = bytearray()
                async for chunk in comm.stream():
                    if chunk["type"] == "audio": 
                        audio.extend(chunk["data"])
                return idx, audio
            except Exception as e: 
                print(f"TTS fetch error for chunk {idx}: {e}")
                return idx, b""
    progress(0.2, desc=f"⏳ Generating {len(sentences)} audio segments (2/5)...")
    tasks = [fetch_audio(i, s) for i, s in enumerate(sentences)]
    results = await asyncio.gather(*tasks)
    results.sort(key=lambda x: x[0])
    combined = AudioSegment.empty()
    subs = []
    current_time = 0.0
    pause = AudioSegment.silent(duration=150)
    progress(0.5, desc="⏳ Merging audio segments (3/5)...")
    for idx, chunk in results:
        if not chunk: continue
        temp = f"temp_{idx}.mp3"
        try:
            with open(temp, "wb") as f: 
                f.write(chunk)
            seg = AudioSegment.from_mp3(temp)
            ranges = detect_nonsilent(seg, min_silence_len=40, silence_thresh=-45)
            if ranges: 
                seg = seg[ranges[0][0]:ranges[-1][1]]
            seg += pause
            dur = len(seg) / 1000.0
            if dur > 0:
                subs.append({"start": current_time, "end": current_time + dur, "text": sentences[idx]})
                current_time += dur
                combined += seg
        except Exception as e:
            print(f"Error processing chunk {idx}: {e}")
        finally:
            if os.path.exists(temp):
                os.remove(temp)
    if len(combined) == 0: 
        return None, None, None, t('tts_failed', lang)
    progress(0.8, desc="⏳ Exporting final audio (4/5)...")
    try:
        combined.export(output_mp3, format="mp3")
        progress(0.9, desc="⏳ Generating subtitles (5/5)...")
        with open(output_srt, "w", encoding="utf-8-sig") as f:
            for i, sub in enumerate(subs, 1):
                f.write(f"{i}\n{format_srt_time(sub['start'])} --> {format_srt_time(sub['end'])}\n{sub['text'].strip()}\n\n")
        
        # ✅ TRACK TTS USAGE FOR ALL USERS (VIP + FREE)
        audio_duration = len(combined) / 1000.0
        track_tts_usage(
            email=email,
            voice=voice,
            engine="edge_tts",
            text_length=len(text),
            duration_seconds=audio_duration
        )
        
        # Keep existing free user limit tracking
        is_vip, _, _ = get_user_vip_info(email)
        if not is_vip:
            increment_usage(email)
        
        file_size = os.path.getsize(output_mp3) / (1024 * 1024)
        minutes = int(audio_duration // 60)
        seconds = int(audio_duration % 60)
        progress(1.0, desc="✅ Complete!")
        status_msg = f"""
🎉 {t('tts_success', lang)}

⏱️ **Duration:** **{minutes}:{seconds:02d}** (မိနစ်:စက္ကန့်)
📦 **File Size:** {file_size:.1f} MB
🎤 **Voice:** {voice}

💡 **အသံကြားရန် အပေါ်က Audio Player ကိုနှိပ်ပါ**
📥 **ဒေါင်းလုဒ်လုပ်ရန် အောက်က MP3 ကိုနှိပ်ပါ**
"""
        return output_mp3, output_mp3, output_srt, status_msg
    except Exception as e:
        return None, None, None, f"❌ Error saving files: {e}"

def tts_wrapper(email, text, rules, filename, voice, srt_type, speed, volume, lang="my"):
    return asyncio.run(process_voice_generation(email, text, rules, filename, voice, srt_type, speed, volume, lang))

# ==========================================
# YOUTUBE SCRIPT GENERATION
# ==========================================
def call_gemini_api(prompt, key, lang="my", max_retries=2):
    """
    Helper function to call Gemini API using REST (supports AQ... keys)
    """
    if not key:
        return "❌ No Gemini API Key provided."
    
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    if "content" in data["candidates"][0]:
                        return data["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        return f"❌ Error: No content in response"
                else:
                    return f"❌ Error: {data}"
            elif response.status_code in [403, 401]:
                return "❌ Invalid/Expired Key"
            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return "❌ Rate Limit Exceeded. Please try again later."
            else:
                return f"❌ Gemini API Error: {response.status_code} - {response.text}"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return f"❌ Connection Error: {str(e)}"
    return "❌ Max retries exceeded."

def analyze_youtube_link(url, email, lang="my"):
    if not email: 
        return t('not_logged_in', lang)
    can_access, msg = check_tool_access(email, lang)
    if not can_access: 
        return f"❌ {msg}"
    key = get_key_with_rotation(email, "gemini", GEMINI_API_KEY)
    if not key: 
        return t('yt_gemini_error', lang)
    vid = None
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.query:
            query = urllib.parse.parse_qs(parsed.query)
            vid = query.get("v", [None])[0]
        if not vid:
            patterns = [r'youtu\.be/([a-zA-Z0-9_-]{11})', r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})', r'youtube\.com/embed/([a-zA-Z0-9_-]{11})']
            for pattern in patterns:
                match = re.search(pattern, url)
                if match: 
                    vid = match.group(1)
                    break
        if not vid:
            match = re.search(r'/([a-zA-Z0-9_-]{11})(?:[?&]|$)', url)
            if match: vid = match.group(1)
        if not vid: 
            return t('yt_invalid_url', lang)
    except Exception as e: 
        return f"❌ URL Parse error: {e}"
    try:
        transcript = YouTubeTranscriptApi.get_transcript(vid)
        full_text = " ".join([t['text'] for t in transcript])
    except Exception as e:
        return f"{t('yt_no_transcript', lang)} Error: {str(e)}"
    try:
        if lang == "my":
            prompt = f"""သင်သည် ရုပ်ရှင်အကျဉ်းချုပ် ဇာတ်ညွှန်းရေးဆရာတစ်ဦးဖြစ်သည်။ အောက်ပါ စာတန်းထိုးကို အခြေခံ၍ ဆွဲဆောင်မှုရှိသော မြန်မာလို ရုပ်ရှင်အကျဉ်းချုပ် ဇာတ်ညွှန်းကို ရေးသားပါ။ အဓိကဇာတ်ဝင်ခန်းများ၊ ဇာတ်ကောင်မိတ်ဆက်များနှင့် စိတ်လှုပ်ရှားဖွယ်ရာ ဖန်တီးပါ။ စာတန်းထိုး: {full_text[:15000]}"""
        else:
            prompt = f"""You are a master movie recap script writer. Write a detailed, engaging English movie recap script based on this transcript. Include key scenes, character introductions, and build excitement. Transcript: {full_text[:15000]}"""
        
        response_text = call_gemini_api(prompt, key, lang)
        
        if "❌" in response_text:
            if "Invalid/Expired" in response_text:
                rotate_key(email, "gemini")
            return response_text
        
        is_vip, _, _ = get_user_vip_info(email)
        if not is_vip:
            increment_usage(email)
        return response_text
    except Exception as e:
        rotate_key(email, "gemini")
        return f"{t('yt_gemini_error', lang)}: {e}"

def polish_script(script, email, lang="my"):
    if not email: 
        return t('not_logged_in', lang)
    if not script or script.strip() == "": 
        return "❌ Please generate a script first."
    key = get_key_with_rotation(email, "gemini", GEMINI_API_KEY)
    if not key: 
        return t('yt_gemini_error', lang)
    try:
        if lang == "my":
            prompt = f"""သင်သည် ကျွမ်းကျင်သော ဇာတ်ညွှန်းတည်းဖြတ်သူတစ်ဦးဖြစ်သည်။ အောက်ပါ မြန်မာလို ရုပ်ရှင်အကျဉ်းချုပ် ဇာတ်ညွှန်းကို ရုပ်ရှင်ဆန်ဆန်၊ ဆွဲဆောင်မှုရှိရှိနှင့် သဒ္ဒါချို့ယွင်းချက်မရှိအောင် ပြန်လည်ရေးသားပါ။ ဇာတ်လမ်းအူတိုင်ကို ထိန်းသိမ်းပြီး စာသားအရည်အသွေးကို မြှင့်တင်ပါ။ မူရင်းဇာတ်ညွှန်း: {script[:15000]}"""
        else:
            prompt = f"""You are a professional script editor. Rewrite the following English movie recap script to make it cinematic, highly engaging, and grammatically flawless. Maintain the core story but improve pacing and vocabulary.
        Original Script: {script[:15000]}"""
        
        response_text = call_gemini_api(prompt, key, lang)
        
        if "❌" in response_text and "Invalid/Expired" in response_text:
            rotate_key(email, "gemini")
        return response_text
    except Exception as e:
        rotate_key(email, "gemini")
        return f"{t('yt_gemini_error', lang)}: {e}"

def generate_post(script, email, lang="my"):
    if not email: 
        return t('not_logged_in', lang)
    if not script or script.strip() == "": 
        return "❌ Please generate a script first."
    key = get_key_with_rotation(email, "gemini", GEMINI_API_KEY)
    if not key: 
        return t('yt_gemini_error', lang)
    try:
        if lang == "my":
            prompt = f"""သင်သည် ဆိုရှယ်မီဒီယာ ကြီးထွားရေး ကျွမ်းကျင်သူတစ်ဦးဖြစ်သည်။ အောက်ပါ ရုပ်ရှင်အကျဉ်းချုပ် ဇာတ်ညွှန်းကို အခြေခံ၍ YouTube/TikTok အတွက် ဆွဲဆောင်မှုရှိသော မြန်မာလို ဗိုင်ရယ်ပို့စ်တစ်ခု ရေးသားပါ။
        အောက်ပါအတိုင်း ဖော်ပြပါ:
        1. ဆွဲဆောင်မှုရှိသော ခေါင်းစဉ် (စာလုံး ၆၀ အတွင်း)
        2. အတိုချုံးဖော်ပြချက် (စာလုံး ၂၀၀ အတွင်း)
        3. ဆက်စပ်သော ဟက်ရှ်တဂ် ၁၀ ခု
        အတိအကျ ဖော်မတ်:
        **ခေါင်းစဉ်:** ...
        **ဖော်ပြချက်:** ...
        **ဟက်ရှ်တဂ်များ:** ...
        ဇာတ်ညွှန်း: {script[:15000]}"""
        else:
            prompt = f"""You are a social media growth expert. Based on the following movie recap script, generate a catchy, viral post for YouTube/TikTok in English.
        Provide:
        1. A compelling Title (Max 60 chars)
        2. A short description (Max 200 chars)
        3. 10 relevant hashtags
        Format exactly like this:
        **Title:** ...
        **Description:** ...
        **Hashtags:** ..."""
        
        response_text = call_gemini_api(prompt, key, lang)
        
        if "❌" in response_text and "Invalid/Expired" in response_text:
            rotate_key(email, "gemini")
        return response_text
    except Exception as e:
        rotate_key(email, "gemini")
        return f"{t('yt_gemini_error', lang)}: {e}"

# ==========================================
# DNS HELPER FUNCTIONS
# ==========================================
def check_dns_resolution():
    hosts_to_check = [
        "api-inference.huggingface.co",
        "huggingface.co",
        "api.huggingface.co",
        "8.8.8.8",
        "1.1.1.1"
    ]
    results = {}
    for host in hosts_to_check:
        try:
            ip = socket.gethostbyname(host)
            results[host] = {"resolved": True, "ip": ip}
            print(f"✅ {host} -> {ip}")
        except socket.gaierror:
            results[host] = {"resolved": False, "ip": None}
            print(f"❌ Cannot resolve {host}")
        except Exception as e:
            results[host] = {"resolved": False, "error": str(e)}
            print(f"⚠️ Error resolving {host}: {e}")
    return results

def get_dns_servers():
    dns_servers = []
    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                if line.startswith("nameserver"):
                    parts = line.split()
                    if len(parts) >= 2:
                        dns_servers.append(parts[1])
    except:
        pass
    common_dns = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "9.9.9.9"]
    for dns in common_dns:
        if dns not in dns_servers:
            dns_servers.append(dns)
    return dns_servers

# ==========================================
# WHISPER TRANSCRIPTION
# ==========================================
def transcribe_audio_file(audio_path, email, lang="my"):
    if not audio_path:
        return None, "❌ No audio file provided"
    token = get_key_with_rotation(email, "hf", HF_TOKEN)
    if not token:
        return None, "❌ Please provide Hugging Face Token"
    try:
        print("🔍 Checking DNS resolution...")
        try:
            dns_servers = [
                ("api-inference.huggingface.co", 443),
                ("huggingface.co", 443),
                ("api.huggingface.co", 443)
            ]
            resolved = False
            for host, port in dns_servers:
                try:
                    ip = socket.gethostbyname(host)
                    print(f"✅ Resolved {host} -> {ip}")
                    resolved = True
                    break
                except socket.gaierror:
                    print(f"❌ Cannot resolve {host}")
                    continue
            if not resolved:
                try:
                    import subprocess
                    result = subprocess.run(
                        ["nslookup", "api-inference.huggingface.co", "8.8.8.8"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if "Address:" in result.stdout:
                        print(f"✅ DNS resolved using Google DNS: {result.stdout}")
                        resolved = True
                except:
                    pass
            if not resolved:
                return None, "❌ DNS resolution failed. Please check your internet connection and DNS settings."
        except Exception as e:
            print(f"⚠️ DNS check error: {e}")
        print("📂 Reading audio file...")
        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            print(f"✅ Audio file size: {len(audio_data)} bytes")
        except Exception as e:
            return None, f"❌ Failed to read audio file: {e}"
        endpoints = [
            "https://api-inference.huggingface.co/models/openai/whisper-large-v3",
            "https://huggingface.co/api/models/openai/whisper-large-v3",
            "https://api-inference.huggingface.co/models/openai/whisper-large-v2",
            "https://api.huggingface.co/models/openai/whisper-large-v3"
        ]
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": audio_b64,
            "parameters": {
                "language": lang if lang != "auto" else None,
                "return_timestamps": False
            }
        }
        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1.5,
            status_forcelist=[500, 502, 503, 504, 429],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('https://', adapter)
        print("🔄 Trying API endpoints...")
        last_error = None
        for endpoint in endpoints:
            try:
                print(f"⏳ Trying: {endpoint}")
                response = session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=300,
                    verify=True
                )
                print(f"📊 Response status: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, dict) and "text" in result:
                        transcript = result["text"].strip()
                    elif isinstance(result, list) and len(result) > 0:
                        transcript = " ".join([seg.get("text", "") for seg in result]).strip()
                    else:
                        transcript = str(result).strip()
                    if not transcript:
                        return None, "❌ No text returned from API"
                    is_vip, _, _ = get_user_vip_info(email)
                    if not is_vip:
                        increment_usage(email)
                    return transcript, f"✅ Transcription successful! (via {endpoint})"
                elif response.status_code == 401 or response.status_code == 403:
                    print(f"⚠️ Invalid token, rotating...")
                    rotate_key(email, "hf")
                    return None, "❌ Invalid API token. Rotating to next key..."
                elif response.status_code == 429 or response.status_code == 503:
                    print(f"⏳ Rate limited on {endpoint}, trying next...")
                    time.sleep(2)
                    continue
                else:
                    print(f"⚠️ Error {response.status_code} on {endpoint}: {response.text[:100]}")
                    last_error = f"API error: {response.status_code} - {response.text[:200]}"
                    continue
            except requests.exceptions.ConnectionError as e:
                print(f"❌ Connection error on {endpoint}: {e}")
                last_error = f"Connection error: {str(e)}"
                continue
            except requests.exceptions.Timeout as e:
                print(f"⏳ Timeout on {endpoint}: {e}")
                last_error = f"Timeout: {str(e)}"
                continue
            except requests.exceptions.SSLError as e:
                print(f"🔒 SSL error on {endpoint}: {e}")
                last_error = f"SSL error: {str(e)}"
                continue
            except Exception as e:
                print(f"⚠️ Unexpected error on {endpoint}: {e}")
                last_error = f"Error: {str(e)}"
                continue
        print("❌ All API endpoints failed")
        try:
            print("⏳ Trying fallback with longer timeout...")
            response = requests.post(
                endpoints[0],
                headers=headers,
                json=payload,
                timeout=600,
                verify=False
            )
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, dict) and "text" in result:
                    transcript = result["text"].strip()
                elif isinstance(result, list) and len(result) > 0:
                    transcript = " ".join([seg.get("text", "") for seg in result]).strip()
                else:
                    transcript = str(result).strip()
                if transcript:
                    return transcript, "✅ Transcription successful! (Fallback)"
        except:
            pass
        if last_error:
            return None, f"❌ Transcription failed after multiple attempts. Last error: {last_error}"
        else:
            return None, "❌ Transcription failed. Please try again later."
    except Exception as e:
        print(f"❌ Fatal error in transcribe_audio_file: {e}")
        return None, f"❌ Transcription error: {str(e)}"

def transcribe_audio(file_path, language="auto", email=None, lang="my", progress=gr.Progress()):
    if not email: 
        return t('not_logged_in', lang)
    can_access, msg = check_tool_access(email, lang)
    if not can_access: 
        return f"❌ {msg}"
    if not file_path: 
        return t('trans_upload', lang)
    if not os.path.exists(file_path):
        return f"❌ File not found: {file_path}"
    progress(0.1, desc="⏳ Preparing audio file...")
    try:
        import subprocess
        result = subprocess.run(
            ["ping", "-c", "1", "8.8.8.8"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return "❌ No internet connection. Please check your network."
    except:
        pass
    progress(0.3, desc="⏳ Connecting to Hugging Face API...")
    max_retries = 2
    for attempt in range(max_retries):
        try:
            transcript, status = transcribe_audio_file(file_path, email, language)
            if transcript:
                progress(1.0, desc="✅ Transcription complete!")
                return transcript
            else:
                if "Invalid API" in status or "403" in status:
                    rotate_key(email, "hf")
                    if attempt < max_retries - 1:
                        print(f"🔄 Retry {attempt + 1} with new key...")
                        continue
                return status
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                progress(1.0, desc="❌ Transcription failed!")
                return f"❌ Transcription failed after {max_retries} attempts: {str(e)}"
            time.sleep(2)
    progress(1.0, desc="❌ Transcription failed!")
    return "❌ Transcription failed. Please try again later."

# ==========================================
# AI THUMBNAIL
# ==========================================
def generate_thumbnail(prompt, email, lang="my"):
    if not email: 
        return None, t('not_logged_in', lang)
    can_access, msg = check_tool_access(email, lang)
    if not can_access: 
        return None, f"❌ {msg}"
    if not prompt or prompt.strip() == "": 
        return None, t('thumb_prompt', lang)
    token = get_key_with_rotation(email, "hf", HF_TOKEN)
    if not token: 
        return None, t('thumb_no_token', lang)
    try:
        url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"inputs": prompt}
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        if response.status_code != 200:
            rotate_key(email, "hf")
            return None, f"❌ Image API error: {response.status_code} - {response.text}"
        img_path = "generated_thumbnail.png"
        with open(img_path, "wb") as f:
            f.write(response.content)
        is_vip, _, _ = get_user_vip_info(email)
        if not is_vip:
            increment_usage(email)
        return img_path, t('thumb_success', lang)
    except Exception as e:
        rotate_key(email, "hf")
        return None, f"❌ Image generation failed: {e}"

# ==========================================
# VOICE CLONING
# ==========================================
def clone_voice_with_gtts(email, text, voice_speed=1.0, lang="my"):
    if not email:
        return None, t('not_logged_in', lang)
    can_access, msg = check_tool_access(email, lang)
    if not can_access:
        return None, f"❌ {msg}"
    if not text or text.strip() == "":
        return None, t('clone_text', lang)
    try:
        tts_lang = 'my'
        if re.search(r'[a-zA-Z]', text) and not re.search(r'[\u1000-\u109F]', text):
            tts_lang = 'en'
        tts = gTTS(text=text, lang=tts_lang, slow=False)
        output_path = "cloned_voice_output.mp3"
        tts.save(output_path)
        
        # ✅ TRACK TTS USAGE FOR gTTS
        try:
            audio = AudioSegment.from_mp3(output_path)
            duration = len(audio) / 1000.0
            track_tts_usage(
                email=email,
                voice="gTTS",
                engine="gtts",
                text_length=len(text),
                duration_seconds=duration
            )
        except:
            pass
        
        try:
            if voice_speed != 1.0:
                audio = AudioSegment.from_mp3(output_path)
                new_audio = audio.speedup(playback_speed=voice_speed)
                new_audio.export(output_path, format="mp3")
        except Exception as e:
            print(f"Speed adjustment error: {e}")
        is_vip, _, _ = get_user_vip_info(email)
        if not is_vip:
            increment_usage(email)
        return output_path, f"{t('clone_gtts', lang)} (Language: {tts_lang.upper()})"
    except Exception as e:
        return None, f"❌ gTTS error: {e}"

def clone_voice_with_edge(email, text, voice="en-US-JennyNeural", speed=1.0, lang="my"):
    if not email:
        return None, t('not_logged_in', lang)
    can_access, msg = check_tool_access(email, lang)
    if not can_access:
        return None, f"❌ {msg}"
    if not text or text.strip() == "":
        return None, t('clone_text', lang)
    try:
        edge_voices = {
            "Jenny (US English)": "en-US-JennyNeural",
            "Guy (US English)": "en-US-GuyNeural",
            "Aria (US English)": "en-US-AriaNeural",
            "Sonia (UK English)": "en-GB-SoniaNeural",
            "Ryan (UK English)": "en-GB-RyanNeural",
            "Nilar (Myanmar)": "my-MM-NilarNeural",
            "Thiha (Myanmar)": "my-MM-ThihaNeural",
        }
        selected_voice = edge_voices.get(voice, "en-US-JennyNeural")
        speed_percent = int((speed - 1.0) * 50)
        speed_rate = f"{'+' if speed_percent >= 0 else ''}{speed_percent}%"
        async def generate():
            comm = edge_tts.Communicate(text=text, voice=selected_voice, rate=speed_rate)
            audio_data = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])
            return audio_data
        audio_bytes = asyncio.run(generate())
        if not audio_bytes:
            return None, "❌ Failed to generate audio."
        output_path = "edge_clone_voice.mp3"
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        
        # ✅ TRACK TTS USAGE FOR Edge TTS
        try:
            audio = AudioSegment.from_mp3(output_path)
            duration = len(audio) / 1000.0
            track_tts_usage(
                email=email,
                voice=voice,
                engine="edge_tts",
                text_length=len(text),
                duration_seconds=duration
            )
        except:
            pass
        
        is_vip, _, _ = get_user_vip_info(email)
        if not is_vip:
            increment_usage(email)
        return output_path, f"{t('clone_edge', lang)} (Voice: {voice})"
    except Exception as e:
        return None, f"❌ Edge TTS error: {e}"

# ==========================================
# VIDEO EXPORT
# ==========================================
def export_video(mp3_path, srt_path, bg_image=None, email=None, lang="my"):
    if not email: 
        return None, t('not_logged_in', lang)
    if not mp3_path: 
        return None, "❌ Please generate MP3 audio first."
    if not srt_path: 
        return None, "❌ Please generate SRT subtitles first."
    try:
        bg_path = bg_image if bg_image else "placeholder_bg.png"
        if not os.path.exists(bg_path) or not bg_image:
            img = Image.new('RGB', (1920, 1080), color=(15, 12, 41))
            img.save("placeholder_bg.png")
            bg_path = "placeholder_bg.png"
        output_path = "final_recap_video.mp4"
        cmd = [
            "ffmpeg",
            "-loop", "1",
            "-i", bg_path,
            "-i", mp3_path,
            "-c:v", "libx264",
            "-t", "10",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-y",
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None, f"❌ FFmpeg error: {result.stderr}"
        return output_path, "✅ Video exported successfully! (10s preview limit applied)"
    except Exception as e:
        return None, f"❌ Video export error: {e}"

# ==========================================
# BACKGROUND REMOVAL
# ==========================================
def remove_bg(image, email, lang="my"):
    if not email: 
        return None, t('not_logged_in', lang)
    can_access, msg = check_tool_access(email, lang)
    if not can_access: 
        return None, f"❌ {msg}"
    if not image: 
        return None, t('bg_upload', lang)
    try:
        input_img = Image.open(image)
        output_img = remove(input_img)
        img_path = "no_bg_image.png"
        output_img.save(img_path)
        return img_path, t('bg_success', lang)
    except Exception as e:
        return None, f"❌ Background removal failed: {e}"

# ==========================================
# SRT TRANSLATION
# ==========================================
def translate_srt_file(srt_file, deepl_api_key, src_lang="auto", tgt_lang="MY", email=None, lang="my"):
    if not email: 
        return None, t('not_logged_in', lang)
    can_access, msg = check_tool_access(email, lang)
    if not can_access: 
        return None, f"❌ {msg}"
    if not srt_file: 
        return None, t('srt_upload', lang)
    key = deepl_api_key or get_key_with_rotation(email, "deepl", "")
    if not key: 
        return None, t('srt_no_key', lang)
    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        blocks = content.strip().split('\n\n')
        translated_blocks = []
        for block in blocks:
            lines = block.split('\n')
            if len(lines) >= 3:
                index = lines[0]
                timestamp = lines[1]
                text_to_translate = " ".join(lines[2:])
                url = "https://api-free.deepl.com/v2/translate"
                headers = {"Authorization": f"DeepL-Auth-Key {key}"}
                data = {
                    "text": [text_to_translate],
                    "target_lang": tgt_lang
                }
                if src_lang != "auto":
                    data["source_lang"] = src_lang
                response = requests.post(url, headers=headers, data=data)
                if response.status_code == 200:
                    translated_text = response.json()["translations"][0]["text"]
                else:
                    translated_text = text_to_translate
                translated_blocks.append(f"{index}\n{timestamp}\n{translated_text}")
            else:
                translated_blocks.append(block)
        output_path = "translated_subtitle.srt"
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            f.write("\n\n".join(translated_blocks))
        return output_path, t('srt_success', lang)
    except Exception as e:
        rotate_key(email, "deepl")
        return None, f"❌ SRT translation failed: {e}"

# ==========================================
# VIP PAYMENT SUBMISSION
# ==========================================
def submit_vip_payment(user_email, phone, plan, amount, payment_method, screenshot_file, transaction_id, lang="my"):
    try:
        if not user_email: 
            return t('payment_email', lang)
        if not phone: 
            return t('payment_phone', lang)
        if not screenshot_file: 
            return t('payment_screenshot', lang)
        if not transaction_id: 
            return t('payment_transaction', lang)
        client = get_mongo_client()
        if not client:
            return "❌ Database connection failed. Please try again later."
        db_mongo = client["vip_database"]
        payment_col = db_mongo["payment_requests"]
        upload_dir = "uploads"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        file_content = None
        file_name = "screenshot.png"
        if isinstance(screenshot_file, str):
            file_path = screenshot_file
            file_name = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                f.write(file_content)
        else:
            file_path = getattr(screenshot_file, 'name', '')
            if file_path:
                file_name = os.path.basename(file_path)
                with open(file_path, "rb") as f:
                    f.write(file_content)
            else:
                return "❌ Invalid screenshot file format."
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{file_name}"
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, "wb") as f:
            f.write(file_content)
        payment_data = {
            "user_email": user_email,
            "phone": phone,
            "plan": plan,
            "amount": amount,
            "payment_method": payment_method,
            "screenshot_path": filepath,
            "transaction_id": transaction_id,
            "status": "pending",
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        payment_col.insert_one(payment_data)
        client.close()
        return f"{t('payment_success', lang)} Transaction ID: {transaction_id}. Please wait for admin approval."
    except Exception as e:
        return f"❌ Payment submission error: {e}"

# ==========================================
# MOVIE RECAP - VIDEO FILE SUPPORT
# ==========================================
def extract_audio_from_video(video_path):
    try:
        audio_path = "extracted_audio.mp3"
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-q:a", "0",
            "-map", "a",
            "-y",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None, f"❌ Audio extraction error: {result.stderr}"
        return audio_path, "✅ Audio extracted successfully!"
    except Exception as e:
        return None, f"❌ Audio extraction error: {str(e)}"

def rewrite_script_from_text(text, email, lang="my"):
    if not text:
        return None, "❌ No text provided"
    key = get_key_with_rotation(email, "gemini", GEMINI_API_KEY)
    if not key:
        return None, "❌ Please provide Gemini API Key"
    try:
        if lang == "my":
            prompt = f"""သင်သည် ရုပ်ရှင်အကျဉ်းချုပ် ဇာတ်ညွှန်းရေးဆရာတစ်ဦးဖြစ်သည်။ 
            အောက်ပါ စာသားကို အခြေခံ၍ ဆွဲဆောင်မှုရှိသော မြန်မာလို ရုပ်ရှင်အကျဉ်းချုပ် 
            ဇာတ်ညွှန်းကို ရေးသားပါ။ 
            အဓိကဇာတ်ဝင်ခန်းများ၊ ဇာတ်ကောင်မိတ်ဆက်များနှင့် စိတ်လှုပ်ရှားဖွယ်ရာ ဖန်တီးပါ။
            စာသား: {text[:15000]}"""
        else:
            prompt = f"""You are a master movie recap script writer. 
            Write a detailed, engaging English movie recap script based on this text. 
            Include key scenes, character introductions, and build excitement.
            Text: {text[:15000]}"""
        
        response_text = call_gemini_api(prompt, key, lang)
        
        if "❌" in response_text and "Invalid/Expired" in response_text:
            rotate_key(email, "gemini")
        return response_text, "✅ Script rewritten successfully!"
    except Exception as e:
        rotate_key(email, "gemini")
        return None, f"❌ AI rewrite error: {str(e)}"

def generate_tts_audio_from_text(text, voice="my-MM-ThihaNeural", filename="movie_recap"):
    if not text:
        return None, "❌ No text provided"
    try:
        sentences = clean_and_split_text(text, max_chars=65)
        if not sentences:
            return None, "❌ No sentences found"
        combined = AudioSegment.empty()
        pause = AudioSegment.silent(duration=200)
        for sentence in sentences:
            try:
                async def generate():
                    comm = edge_tts.Communicate(text=sentence, voice=voice, rate="+0%")
                    audio_data = bytearray()
                    async for chunk in comm.stream():
                        if chunk["type"] == "audio":
                            audio_data.extend(chunk["data"])
                    return audio_data
                audio_bytes = asyncio.run(generate())
                if audio_bytes:
                    temp_file = f"temp_{hash(sentence)}.mp3"
                    with open(temp_file, "wb") as f:
                        f.write(audio_bytes)
                    seg = AudioSegment.from_mp3(temp_file)
                    combined += seg + pause
                    os.remove(temp_file)
            except Exception as e:
                print(f"TTS error: {e}")
                continue
        if len(combined) == 0:
            return None, "❌ Audio generation failed"
        output_path = f"{filename}.mp3"
        combined.export(output_path, format="mp3")
        return output_path, "✅ Audio generated successfully!"
    except Exception as e:
        return None, f"❌ TTS error: {str(e)}"

def generate_movie_thumbnail(prompt, email):
    if not prompt:
        return None, "❌ No prompt provided"
    token = get_key_with_rotation(email, "hf", HF_TOKEN)
    if not token:
        return None, "❌ Please provide Hugging Face Token"
    try:
        url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
        headers = {"Authorization": f"Bearer {token}"}
        is_myanmar = bool(re.search(r'[\u1000-\u109F]', prompt))
        if is_myanmar:
            full_prompt = f"ရုပ်ရှင်ပိုစတာ၊ ဒရာမာကျသော ရုပ်ရှင်ဇာတ်ဝင်ခန်း၊ {prompt}၊ အနက်ရောင်နောက်ခံ၊ ရုပ်ရှင်စတိုင်၊ 4k အရည်အသွေးမြင့်"
        else:
            full_prompt = f"Movie poster, dramatic cinema scene, {prompt}, dark background, cinematic style, 4k, high quality"
        payload = {"inputs": full_prompt}
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        if response.status_code != 200:
            rotate_key(email, "hf")
            return None, f"❌ Image API error: {response.status_code}"
        img_path = "movie_thumbnail.png"
        with open(img_path, "wb") as f:
            f.write(response.content)
        try:
            img = Image.open(img_path)
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 50)
            except:
                font = ImageFont.load_default()
            text = "🎬 MOVIE RECAP" if not is_myanmar else "🎬 ရုပ်ရှင်အကျဉ်းချုပ်"
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            x = (img.width - text_width) // 2
            y = img.height - 100
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle([x-30, y-20, x+text_width+30, y+text_height+20], fill=(0, 0, 0, 200))
            img = Image.alpha_composite(img.convert('RGBA'), overlay)
            draw = ImageDraw.Draw(img)
            draw.text((x, y), text, fill=(255, 215, 0), font=font)
            img.save(img_path)
        except Exception as e:
            print(f"Thumbnail overlay error: {e}")
        return img_path, "✅ Thumbnail generated successfully!"
    except Exception as e:
        rotate_key(email, "hf")
        return None, f"❌ Thumbnail error: {str(e)}"

def generate_movie_subtitles(text, audio_path, filename="movie_recap"):
    if not text or not audio_path:
        return None, "❌ Missing text or audio"
    try:
        sentences = clean_and_split_text(text, max_chars=65)
        if not sentences:
            return None, "❌ No sentences found"
        audio = AudioSegment.from_mp3(audio_path)
        total_duration = len(audio) / 1000.0
        total_chars = sum(len(s) for s in sentences)
        if total_chars == 0:
            return None, "❌ No text characters"
        srt_path = f"{filename}.srt"
        with open(srt_path, "w", encoding="utf-8") as f:
            current_time = 0.0
            for i, sentence in enumerate(sentences, 1):
                char_ratio = len(sentence) / total_chars
                duration = char_ratio * total_duration
                end_time = current_time + duration
                start = format_srt_time(current_time)
                end = format_srt_time(end_time)
                f.write(f"{i}\n{start} --> {end}\n{sentence.strip()}\n\n")
                current_time = end_time
        return srt_path, "✅ Subtitles generated successfully!"
    except Exception as e:
        return None, f"❌ Subtitle error: {str(e)}"

def export_movie_video(audio_path, subtitle_path, thumbnail_path, filename="movie_recap"):
    if not audio_path:
        return None, "❌ No audio file"
    try:
        output_path = f"{filename}.mp4"
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            img = Image.new('RGB', (1920, 1080), color=(15, 12, 41))
            thumbnail_path = "placeholder.png"
            img.save(thumbnail_path)
        if subtitle_path and os.path.exists(subtitle_path):
            cmd = [
                "ffmpeg",
                "-loop", "1",
                "-i", thumbnail_path,
                "-i", audio_path,
                "-vf", f"subtitles={subtitle_path}:force_style='FontSize=28,OutlineColour=&H80000000&,BorderStyle=4,FontName=Arial'",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-y",
                output_path
            ]
        else:
            cmd = [
                "ffmpeg",
                "-loop", "1",
                "-i", thumbnail_path,
                "-i", audio_path,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-y",
                output_path
            ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None, f"❌ FFmpeg error: {result.stderr}"
        return output_path, "✅ Video exported successfully!"
    except Exception as e:
        return None, f"❌ Video export error: {str(e)}"

# ==========================================
# ONE CLICK MOVIE RECAP - MAIN FUNCTION
# ==========================================
def one_click_movie_recap(video_file, youtube_url, email, voice, lang, progress=gr.Progress()):
    results = {
        "source_text": None,
        "transcript": None,
        "script": None,
        "audio": None,
        "thumbnail": None,
        "subtitles": None,
        "video": None,
        "status": []
    }
    if video_file:
        progress(0, desc="🎬 Processing uploaded video...")
        audio_path, status = extract_audio_from_video(video_file)
        results["status"].append(status)
        if not audio_path:
            return None, None, None, None, None, None, "\n".join(results["status"])
        progress(0.15, desc="📝 Transcribing audio...")
        transcript, status = transcribe_audio_file(audio_path, email, lang)
        results["status"].append(status)
        if not transcript:
            return None, None, None, None, None, None, "\n".join(results["status"])
        results["transcript"] = transcript
        results["source_text"] = transcript
    elif youtube_url and youtube_url.strip():
        progress(0, desc="📝 Extracting transcript from YouTube...")
        transcript = analyze_youtube_link(youtube_url, email, lang)
        if "❌" in transcript:
            results["status"].append(transcript)
            return None, None, None, None, None, None, "\n".join(results["status"])
        results["transcript"] = transcript
        results["source_text"] = transcript
    else:
        return None, None, None, None, None, None, "❌ Please provide either a video file or YouTube URL"
    progress(0.25, desc="🤖 Rewriting script with AI...")
    script, status = rewrite_script_from_text(results["source_text"], email, lang)
    results["status"].append(status)
    if not script:
        return None, None, None, None, None, None, "\n".join(results["status"])
    results["script"] = script
    progress(0.45, desc="🎙️ Generating TTS audio...")
    voice_map = {
        "my-MM-ThihaNeural (Myanmar Male)": "my-MM-ThihaNeural",
        "my-MM-NilarNeural (Myanmar Female)": "my-MM-NilarNeural",
        "en-US-JennyNeural (English Female)": "en-US-JennyNeural",
        "en-US-GuyNeural (English Male)": "en-US-GuyNeural"
    }
    selected_voice = voice_map.get(voice, "my-MM-ThihaNeural")
    audio_path, status = generate_tts_audio_from_text(script, selected_voice, "movie_recap")
    results["status"].append(status)
    if not audio_path:
        return None, None, None, None, None, None, "\n".join(results["status"])
    results["audio"] = audio_path
    
    # ✅ TRACK TTS USAGE FOR MOVIE RECAP
    try:
        audio = AudioSegment.from_mp3(audio_path)
        duration = len(audio) / 1000.0
        track_tts_usage(
            email=email,
            voice=selected_voice,
            engine="edge_tts",
            text_length=len(script),
            duration_seconds=duration
        )
    except:
        pass
    
    progress(0.65, desc="🎨 Generating AI thumbnail...")
    thumbnail_path, status = generate_movie_thumbnail(script[:100], email)
    results["status"].append(status)
    results["thumbnail"] = thumbnail_path
    progress(0.8, desc="📝 Generating subtitles...")
    subtitle_path, status = generate_movie_subtitles(script, audio_path, "movie_recap")
    results["status"].append(status)
    results["subtitles"] = subtitle_path
    progress(0.9, desc="🎬 Exporting final video...")
    video_path, status = export_movie_video(audio_path, subtitle_path, thumbnail_path, "movie_recap")
    results["status"].append(status)
    results["video"] = video_path
    return (
        results["transcript"],
        results["script"],
        results["audio"],
        results["thumbnail"],
        results["subtitles"],
        results["video"],
        "\n".join(results["status"])
    )

# ==========================================
# MODERN CSS (NEW UI DESIGN)
# ==========================================
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg-main: #0B0A15;
    --bg-card: rgba(255, 255, 255, 0.03);
    --border-color: rgba(255, 255, 255, 0.08);
    --accent-primary: #8A2BE2;
    --accent-secondary: #00D2FF;
    --text-main: #F3F4F6;
    --text-muted: #9CA3AF;
    --glass-blur: blur(16px);
    --card-radius: 16px;
    --shadow: 0 10px 30px rgba(0,0,0,0.2);
}

* { box-sizing: border-box !important; }
body, .gradio-container {
    background-color: var(--bg-main) !important;
    background-image: 
        radial-gradient(circle at 15% 50%, rgba(138, 43, 226, 0.15), transparent 25%),
        radial-gradient(circle at 85% 30%, rgba(0, 210, 255, 0.15), transparent 25%) !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--text-main) !important;
    min-height: 100vh !important;
    margin: 0 !important;
    padding: 0 !important;
}
footer { display: none !important; }
.gradio-interface { background: transparent !important; }

/* ===== CUSTOM SCROLLBAR ===== */
::-webkit-scrollbar { width: 6px !important; height: 6px !important; }
::-webkit-scrollbar-track { background: transparent !important; }
::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2) !important; border-radius: 4px !important; }
::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.4) !important; }

/* ===== AUTH ===== */
.auth-container {
    max-width: 420px !important;
    margin: 8vh auto !important;
    padding: 48px 40px !important;
    background: rgba(255, 255, 255, 0.02) !important;
    backdrop-filter: var(--glass-blur) !important;
    border-radius: 28px !important;
    border: 1px solid var(--border-color) !important;
    box-shadow: 0 30px 60px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.08) !important;
}
.auth-logo { text-align: center !important; margin-bottom: 32px !important; }
.auth-logo .logo-image { width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 3px solid rgba(138, 43, 226, 0.4); box-shadow: 0 0 30px rgba(138, 43, 226, 0.3); margin-bottom: 16px; }
.auth-logo .logo-image:hover { transform: scale(1.05); box-shadow: 0 0 50px rgba(138, 43, 226, 0.5); }
.auth-logo h1 { font-size: 26px !important; font-weight: 700 !important; color: #FFFFFF !important; margin: 0 0 6px 0 !important; background: none !important; -webkit-text-fill-color: #FFFFFF !important; }
.auth-logo p { color: var(--text-muted) !important; font-size: 14px !important; margin: 0 !important; }
.auth-input input { background: rgba(255, 255, 255, 0.03) !important; border: 1px solid var(--border-color) !important; border-radius: 14px !important; padding: 14px 18px !important; color: var(--text-main) !important; font-size: 15px !important; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1) !important; }
.auth-input input:focus { background: rgba(255, 255, 255, 0.06) !important; border-color: rgba(138, 43, 226, 0.6) !important; box-shadow: 0 0 0 4px rgba(138, 43, 226, 0.15) !important; outline: none !important; }
.auth-input input::placeholder { color: #6B7280 !important; }
.auth-buttons-row { gap: 12px !important; margin-top: 12px !important; }
.auth-btn-primary { background: linear-gradient(135deg, var(--accent-primary), #6a11cb) !important; border: none !important; color: white !important; font-weight: 600 !important; padding: 12px 24px !important; border-radius: 14px !important; box-shadow: 0 8px 16px rgba(138, 43, 226, 0.25) !important; transition: all 0.3s ease !important; }
.auth-btn-primary:hover { transform: translateY(-2px) !important; box-shadow: 0 12px 20px rgba(138, 43, 226, 0.4) !important; }
.auth-btn-secondary { background: rgba(255, 255, 255, 0.03) !important; border: 1px solid var(--border-color) !important; color: #E2E8F0 !important; font-weight: 600 !important; padding: 12px 24px !important; border-radius: 14px !important; transition: all 0.3s ease !important; }
.auth-btn-secondary:hover { background: rgba(255, 255, 255, 0.08) !important; border-color: rgba(255, 255, 255, 0.2) !important; }
.lang-toggle-container { display: flex !important; justify-content: center !important; margin-top: 16px !important; gap: 8px !important; }
.lang-btn { padding: 8px 20px !important; border-radius: 20px !important; border: 1px solid rgba(255,255,255,0.1) !important; background: rgba(255,255,255,0.03) !important; color: var(--text-muted) !important; font-weight: 600 !important; font-size: 13px !important; cursor: pointer !important; transition: all 0.3s ease !important; }
.lang-btn.active { background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)) !important; border-color: transparent !important; color: white !important; box-shadow: 0 4px 15px rgba(138, 43, 226, 0.3) !important; }
.lang-btn:hover:not(.active) { background: rgba(255,255,255,0.08) !important; color: #E2E8F0 !important; }
.admin-link-wrapper { text-align: center; margin-top: 24px; padding-top: 20px; border-top: 1px solid rgba(255, 255, 255, 0.06); }
.admin-link-wrapper a { color: var(--text-muted); font-size: 13px; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; transition: color 0.3s ease; }
.admin-link-wrapper a:hover { color: var(--text-main); }

/* ===== INPUTS ===== */
input[type="text"]:not(.auth-input input), input[type="password"]:not(.auth-input input), textarea, select, .gr-textbox:not(.auth-input), .gr-number {
    background: rgba(0,0,0,0.4) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
    color: var(--text-main) !important;
    font-size: 15px !important;
    transition: all 0.3s ease !important;
    width: 100% !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.2) !important;
}
input:not(.auth-input input):focus, textarea:focus, select:focus {
    border-color: var(--accent-primary) !important;
    box-shadow: 0 0 0 3px rgba(138, 43, 226, 0.2) !important;
    outline: none !important;
}

/* ===== BUTTONS ===== */
button { font-family: 'Inter', sans-serif !important; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important; }
.btn-primary { background: linear-gradient(135deg, var(--accent-primary), #4A00E0) !important; border: none !important; color: white !important; font-weight: 600 !important; padding: 14px 28px !important; border-radius: 12px !important; box-shadow: 0 8px 20px rgba(138, 43, 226, 0.3) !important; font-size: 15px !important; }
.btn-primary:hover { transform: translateY(-2px) !important; box-shadow: 0 12px 25px rgba(138, 43, 226, 0.5) !important; filter: brightness(1.1) !important; }
.btn-secondary { background: rgba(255,255,255,0.05) !important; color: var(--text-main) !important; border: 1px solid var(--border-color) !important; font-weight: 600 !important; border-radius: 12px !important; padding: 14px 28px !important; }
.btn-secondary:hover { background: rgba(255,255,255,0.1) !important; border-color: rgba(255,255,255,0.2) !important; }
.btn-success { background: linear-gradient(135deg, #00b09b, #96c93d) !important; border: none !important; color: white !important; font-weight: 600 !important; border-radius: 12px !important; box-shadow: 0 8px 20px rgba(0, 176, 155, 0.3) !important; }
.btn-success:hover { transform: translateY(-2px) !important; box-shadow: 0 12px 25px rgba(0, 176, 155, 0.5) !important; }

/* ===== APP UI ===== */
.app-container { max-width: 1400px !important; margin: 0 auto !important; padding: 24px !important; }
.app-header { background: var(--bg-card) !important; backdrop-filter: var(--glass-blur) !important; border-radius: 20px !important; padding: 16px 32px !important; border: 1px solid var(--border-color) !important; display: flex !important; align-items: center !important; justify-content: space-between !important; margin-bottom: 32px !important; box-shadow: var(--shadow) !important; }
.app-header .logo { display: flex !important; align-items: center !important; gap: 16px !important; }
.app-header .logo img { height: 48px !important; border-radius: 12px !important; }
.app-header .logo span { font-size: 24px !important; font-weight: 800 !important; background: linear-gradient(135deg, var(--accent-secondary), var(--accent-primary), #ff007f, #00D2FF) !important; background-size: 300% 300% !important; -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; letter-spacing: -0.5px !important; animation: gradientShift 5s ease infinite !important; }
@keyframes gradientShift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
.user-info { display: flex !important; align-items: center !important; gap: 16px !important; justify-content: flex-end !important; }
.profile-html-wrap { display: flex !important; align-items: center !important; position: relative !important; z-index: 50 !important; }
.logout-btn { flex: 0 0 auto !important; height: 42px !important; padding: 0 16px !important; }
.notif-btn { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; font-size: 28px !important; color: #fff !important; margin-right: 0 !important; line-height: 1 !important; min-height: 0 !important; height: auto !important; display: inline-block !important; vertical-align: middle !important; }
.notif-btn:hover { transform: scale(1.1) !important; }
.notif-badge-container { display: inline-block !important; vertical-align: middle !important; margin-right: 12px !important; }

/* ===== PROFILE ===== */
.profile-dropdown-container { position: relative; cursor: pointer; display: inline-block; }
.profile-avatar { width: 42px; height: 42px; border-radius: 50%; overflow: hidden; border: 2px solid var(--accent-primary); box-shadow: 0 0 10px rgba(138, 43, 226, 0.5); transition: transform 0.2s ease, box-shadow 0.2s ease; }
.profile-avatar img { width: 100%; height: 100%; object-fit: cover; }
.profile-dropdown-container:hover .profile-avatar { transform: scale(1.05); box-shadow: 0 0 15px rgba(138, 43, 226, 0.8); }
.profile-dropdown-menu { position: absolute; top: 55px; right: 0; background: rgba(15, 12, 41, 0.95); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 16px; width: 220px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); opacity: 0; visibility: hidden; transform: translateY(-10px); transition: opacity 0.3s ease, transform 0.3s ease, visibility 0.3s ease; display: flex; flex-direction: column; gap: 8px; z-index: 100; }
.profile-dropdown-container.active .profile-dropdown-menu { opacity: 1; visibility: visible; transform: translateY(0); }
.profile-email { font-weight: 600; font-size: 14px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; margin-bottom: 4px; }
.profile-location { font-size: 13px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; }
.profile-status-box { margin-top: 8px; font-size: 13px; font-weight: 600; color: #fff; background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)); padding: 8px 12px; border-radius: 10px; text-align: center; box-shadow: 0 4px 10px rgba(138, 43, 226, 0.3); }

/* ===== BROADCAST ===== */
.broadcast-marquee { background: linear-gradient(90deg, rgba(138,43,226,0.1), rgba(0,210,255,0.1)) !important; border: 1px solid rgba(138,43,226,0.2) !important; border-radius: 12px !important; padding: 12px 24px !important; overflow: hidden !important; white-space: nowrap !important; margin-bottom: 24px !important; box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important; }
@keyframes scrollText { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
.broadcast-marquee-inner { display: inline-block !important; animation: scrollText 25s linear infinite !important; color: #E2E8F0 !important; font-weight: 600 !important; font-size: 15px !important; }

/* ===== TABS ===== */
.tabs > .tab-nav { background: rgba(0,0,0,0.4) !important; border-radius: 16px !important; padding: 8px !important; border: 1px solid var(--border-color) !important; display: flex !important; flex-wrap: nowrap !important; gap: 8px !important; overflow-x: auto !important; margin-bottom: 24px !important; }
.tabs > .tab-nav::-webkit-scrollbar { display: none !important; }
.tabs > .tab-nav button { border-radius: 12px !important; padding: 12px 20px !important; font-weight: 600 !important; font-size: 14px !important; color: var(--text-muted) !important; background: transparent !important; border: none !important; white-space: nowrap !important; transition: all 0.3s ease !important; }
.tabs > .tab-nav button.selected { background: linear-gradient(135deg, rgba(138,43,226,0.2), rgba(0,210,255,0.1)) !important; color: #fff !important; border: 1px solid rgba(138,43,226,0.4) !important; box-shadow: 0 4px 15px rgba(138,43,226,0.15) !important; }
.tabs > .tab-nav button:hover:not(.selected) { background: rgba(255,255,255,0.05) !important; color: #fff !important; }

/* ===== GLASS CARD ===== */
.glass-card { background: var(--bg-card) !important; backdrop-filter: var(--glass-blur) !important; border: 1px solid var(--border-color) !important; border-radius: 24px !important; padding: 32px !important; box-shadow: var(--shadow) !important; margin-bottom: 24px !important; transition: transform 0.3s ease, border-color 0.3s ease !important; }
.glass-card:hover { border-color: rgba(255,255,255,0.15) !important; }

/* ===== KEY MANAGEMENT (MODERN UI) ===== */
.key-manager-container { 
    background: rgba(255,255,255,0.02); 
    border-radius: 16px; 
    padding: 20px; 
    border: 1px solid rgba(255,255,255,0.05); 
}
.status-header { 
    display: flex; 
    justify-content: space-between; 
    align-items: center; 
    border-bottom: 1px solid rgba(255,255,255,0.05); 
    padding-bottom: 12px; 
    margin-bottom: 16px; 
}
.status-title { color: #E2E8F0; font-weight: 600; }
.live-badge { background: #10B981; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.status-card { 
    background: rgba(0,0,0,0.2); 
    border-radius: 12px; 
    padding: 16px; 
    margin-bottom: 12px; 
    border: 1px solid rgba(255,255,255,0.03); 
}
.env-card { border-left: 3px solid #6B7280; }
.key-card { border-left: 3px solid #8A2BE2; }
.empty-card { border-left: 3px solid #4B5563; }
.card-row { display: flex; justify-content: space-between; align-items: center; }
.card-label { color: #E2E8F0; font-weight: 500; font-size: 14px; }
.card-subtext { font-size: 12px; color: #6B7280; margin-top: 4px; }
.status-badge { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 4px; border: 1px solid; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.key-count { font-size: 12px; color: #6B7280; background: rgba(255,255,255,0.05); padding: 2px 8px; border-radius: 12px; }
.key-count.empty { color: #6B7280; }
.key-list { display: flex; flex-direction: column; gap: 4px; }
.key-item { 
    display: flex; 
    justify-content: space-between; 
    align-items: center; 
    padding: 6px 10px; 
    border-bottom: 1px solid rgba(255,255,255,0.03); 
    background: rgba(0,0,0,0.2); 
    border-radius: 6px; 
}
.key-name { font-family: monospace; font-size: 12px; color: #9CA3AF; }
.key-actions { display: flex; align-items: center; gap: 8px; }
.key-status { font-weight: 600; font-size: 12px; }
.delete-btn { 
    background: rgba(239, 68, 68, 0.2); 
    border: 1px solid rgba(239, 68, 68, 0.3); 
    color: #EF4444; 
    padding: 2px 8px; 
    border-radius: 6px; 
    cursor: pointer; 
    font-size: 12px; 
    font-weight: 600; 
    transition: all 0.3s ease; 
}
.delete-btn:hover { background: rgba(239, 68, 68, 0.4); }
.status-footer { 
    display: flex; 
    flex-wrap: wrap; 
    gap: 12px; 
    margin-top: 12px; 
    padding-top: 12px; 
    border-top: 1px solid rgba(255,255,255,0.05); 
    color: #6B7280; 
    font-size: 12px; 
}
.footer-item .highlight { color: #9CA3AF; font-weight: 500; }

/* ===== NOTIFICATION MODAL ===== */
#notif-dialog {
    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(8px); z-index: 9999; display: none !important; justify-content: center; align-items: center;
}
#notif-dialog > div { max-width: 600px; width: 90%; max-height: 450px; overflow-y: auto; background: #0B0A15; border: 1px solid #8A2BE2; border-radius: 24px; padding: 32px; box-shadow: 0 20px 60px rgba(0,0,0,0.8); }
#notif-dialog h2 { margin-top: 0; }
#notif-dialog button { margin-top: 16px; }
#notif-dialog .prose { max-height: 320px; overflow-y: auto; word-break: break-word; }

/* ===== RESPONSIVE ===== */
@media screen and (max-width: 768px) {
    .auth-container { margin: 24px 16px !important; padding: 32px 24px !important; }
    .app-header { flex-direction: column !important; gap: 16px !important; text-align: center !important; padding: 20px !important; }
    .app-header .user-info { justify-content: center !important; width: 100% !important; }
    .glass-card { padding: 20px !important; border-radius: 20px !important; }
    .tabs > .tab-nav { flex-wrap: wrap !important; justify-content: center !important; }
    .tabs > .tab-nav button { flex: 1 1 calc(50% - 8px) !important; padding: 10px !important; font-size: 13px !important; }
    .gradio-container .gr-image, .gradio-container .gr-video { width: 100% !important; height: auto !important; max-height: 85vh !important; border-radius: 12px !important; overflow: hidden !important; }
    .gradio-container .gr-image img, .gradio-container .gr-video video { object-fit: contain !important; max-height: 85vh !important; width: 100% !important; }
    .chat-container { max-height: 250px !important; }
}
"""

# ==========================================
# BUILD APP UI
# ==========================================
with gr.Blocks() as demo:
    current_user_email = gr.State("")
    current_language = gr.State("my")
    chat_history_state = gr.State([])
    current_notif_doc_id_state = gr.State("")
    current_notif_msg_state = gr.State("")
    
    # ===== AUTH PAGE =====
    with gr.Column(visible=True, elem_classes="auth-container") as auth_page:
        auth_title = gr.HTML(f"""
        <div class="auth-logo">
            <img src="https://cdn.phototourl.com/free/2026-07-21-023573ae-5979-4c45-974c-84f2864a959a.png" alt="Logo" class="logo-image" />
            <h1>{t('welcome_title', 'my')}</h1>
            <p>{t('welcome_sub', 'my')}</p>
        </div>
        """)
        
        email_input = gr.Textbox(label="", placeholder=t('email_placeholder', 'my'), elem_classes="auth-input")
        password_input = gr.Textbox(label="", placeholder=t('password_placeholder', 'my'), type="password", elem_classes="auth-input")
        
        with gr.Row(elem_classes="auth-buttons-row"):
            login_btn = gr.Button(t('sign_in', 'my'), elem_classes="auth-btn-primary", scale=2)
            signup_btn = gr.Button(t('sign_up', 'my'), elem_classes="auth-btn-secondary", scale=1)
        
        auth_status = gr.Markdown("", elem_classes="auth-status")
        
        with gr.Row(elem_classes="lang-toggle-container"):
            lang_my_btn = gr.Button("🇲🇲 မြန်မာ", elem_classes="lang-btn active", scale=1)
            lang_en_btn = gr.Button("🇬🇧 English", elem_classes="lang-btn", scale=1)
        
        gr.HTML(f"""
        <div class="admin-link-wrapper">
            <a href="/">{t('admin_dashboard', 'my')}</a>
        </div>
        """)
    
    # ===== APP PAGE =====
    with gr.Column(visible=False, elem_classes="app-container") as app_page:
        
        # Header
        with gr.Row(elem_classes="app-header"):
            with gr.Column(scale=2, min_width=250):
                gr.HTML("""
                <div class="logo">
                    <img src="https://cdn.phototourl.com/free/2026-07-21-023573ae-5979-4c45-974c-84f2864a959a.png" alt="Logo">
                    <span>Recap Creator Studio</span>
                </div>
                """)
            with gr.Column(scale=1, min_width=250):
                with gr.Row(elem_classes="user-info"):
                    profile_html = gr.HTML(update_profile_display(""), elem_classes="profile-html-wrap")
                    notif_icon_btn = gr.Button("🔔", elem_classes="notif-btn", size="sm")
                    notif_badge_html = gr.HTML("", elem_classes="notif-badge-container")
                    logout_btn = gr.Button(t('logout', 'my'), elem_classes="btn-secondary logout-btn")
        
        # Notification Modal
        with gr.Column(visible=False, elem_id="notif-dialog") as notif_dialog:
            with gr.Column():
                gr.Markdown("## 📢 Admin Message")
                notif_message_display = gr.Markdown("")
                with gr.Row():
                    notif_close_btn = gr.Button("✅ ဖတ်ပြီးပါပြီ", elem_classes="btn-primary")
        
        # Broadcast
        broadcast_html = gr.HTML(get_broadcast_html())
        
        # ===== MAIN TABS =====
        with gr.Tabs():
            
            # ---- TAB 1: 💎 Pro Upgrade ----
            with gr.TabItem(t('tab_vip', 'my'), elem_id="vip-tab"):
                with gr.Column(elem_classes="glass-card"):
                    gr.Markdown(f"## {t('upgrade_pro', 'my')}")
                    gr.Markdown(t('unlock_features', 'my'))
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown(f"### {t('account_email', 'my')}")
                            vip_email_input = gr.Textbox(label="", placeholder=t('email_placeholder', 'my'))
                            
                            gr.Markdown(f"### {t('payment_contact', 'my')}")
                            gr.HTML("""
                            <div style="background:linear-gradient(135deg, rgba(138,43,226,0.15), rgba(0,210,255,0.15)); 
                                 border:2px solid rgba(138,43,226,0.3); 
                                 border-radius:16px; 
                                 padding:20px; 
                                 margin-bottom:16px;">
                                <div style="display:flex; flex-direction:column; gap:10px;">
                                    <div style="display:flex; justify-content:space-between; align-items:center; 
                                                 background:rgba(0,0,0,0.3); padding:14px 18px; border-radius:10px;">
                                        <span style="color:#9CA3AF; font-weight:600;">🏦 KPay / Wave</span>
                                        <div style="display:flex; align-items:center; gap:10px;">
                                            <span style="color:#00D2FF; font-weight:700; font-size:22px; letter-spacing:1px;">
                                                09683873353
                                            </span>
                                            <button onclick="navigator.clipboard.writeText('09683873353')" 
                                                    style="background:rgba(138,43,226,0.3); border:1px solid rgba(138,43,226,0.4); 
                                                           color:white; padding:6px 14px; border-radius:8px; 
                                                           cursor:pointer; font-size:12px; font-weight:600;">
                                                📋 Copy
                                            </button>
                                        </div>
                                    </div>
                                    <div style="display:flex; justify-content:space-between; align-items:center; 
                                                 background:rgba(0,0,0,0.3); padding:12px 18px; border-radius:10px;">
                                        <span style="color:#9CA3AF; font-weight:600;">👤 Account Name</span>
                                        <span style="color:#fff; font-weight:700; font-size:18px;">
                                            Myo Win Hlaing
                                        </span>
                                    </div>
                                </div>
                            </div>
                            """)
                            
                            vip_phone_input = gr.Textbox(label="", value="09683873353", visible=False)
                            
                            gr.Markdown(f"### {t('subscription_tier', 'my')}")
                            vip_plan = gr.Dropdown(
                                label="",
                                choices=["Lifetime PRO - 3,000 MMK", "Monthly PRO - 1,500 MMK"],
                                value="Lifetime PRO - 3,000 MMK"
                            )
                            
                        with gr.Column():
                            gr.Markdown(f"### {t('payment_method', 'my')}")
                            vip_method = gr.Radio(label="", choices=["💜 KBZPay", "💙 WaveMoney"], value="💜 KBZPay")
                            
                            gr.Markdown(f"### {t('transaction_ref', 'my')}")
                            vip_transaction_id = gr.Textbox(label="", placeholder="e.g. 0212345678")
                            
                            gr.Markdown(f"### {t('upload_receipt', 'my')}")
                            vip_screenshot = gr.File(label="", file_count="single", file_types=[".png", ".jpg", ".jpeg"])
                    
                    vip_amount = gr.Textbox(label="", value="3,000 MMK", visible=False)
                    
                    submit_payment_btn = gr.Button(t('submit_payment', 'my'), elem_classes="btn-success")
                    vip_payment_status = gr.Markdown("")
                    
                    gr.Markdown("---")
                    gr.Markdown(f"### {t('vip_benefits', 'my')}")
                    gr.Markdown("""
                    - ✅ **အကန့်အသတ်မရှိ** အသံ/ဗီဒီယို ထုတ်လုပ်ခြင်း
                    - ✅ **ဦးစားပေး** လုပ်ဆောင်ခြင်း တန်းစီခြင်း
                    - ✅**ပရီမီယံ** အင်္ဂါရပ်အားလုံးကို ဖွင့်လှစ်လိုက်ပါပြီ
                    - ✅နေ့စဉ်အသုံးပြုမှု **ကန့်သတ်ချက်များ** မရှိပါ
                    - ✅ တိုက်ရိုက် **ဦးစားပေး ပံ့ပိုးမှု**
                    """)
            
            # ---- TAB 2: 🎙️ Text to Audio ----
            with gr.TabItem(t('tab_tts', 'my')):
                with gr.Column(elem_classes="glass-card"):
                    gr.Markdown(f"### {t('input_text', 'my')}")
                    text_input = gr.Textbox(label="", placeholder="Enter your text in Myanmar or English here...", lines=5)
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown(f"### {t('replacement_rules', 'my')}")
                            replacement_rules = gr.Textbox(label="", placeholder="e.g., old=new", lines=1)
                        with gr.Column():
                            gr.Markdown(f"### {t('filename', 'my')}")
                            custom_filename = gr.Textbox(label="", placeholder="MyAudioProject")
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown(f"### {t('voice_selection', 'my')}")
                            voice_choice = gr.Radio(
                                label="",
                                choices=["သီဟ (အမျိုးသား)", "နီလာ (အမျိုးသမီး)"],
                                value="သီဟ (အမျိုးသား)"
                            )
                        with gr.Column():
                            gr.Markdown(f"### {t('subtitle_style', 'my')}")
                            subtitle_style = gr.Radio(
                                label="",
                                choices=["TikTok (35 chars)", "Standard (65 chars)"],
                                value="Standard (65 chars)"
                            )
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown(f"### {t('speed_adjust', 'my')}")
                            speed_slider = gr.Slider(label="", minimum=-50, maximum=50, value=0, step=5)
                        with gr.Column():
                            gr.Markdown(f"### {t('volume_adjust', 'my')}")
                            volume_slider = gr.Slider(label="", minimum=0, maximum=50, value=20, step=5)
                    
                    generate_btn = gr.Button(t('generate_audio', 'my'), elem_classes="btn-primary")
                    status_output = gr.Markdown()
                    
                    with gr.Row():
                        audio_output = gr.Audio(
                            label=t('audio_preview', 'my'), 
                            type="filepath",
                            interactive=False
                        )
                    
                    with gr.Row():
                        download_audio = gr.File(label=t('download_mp3', 'my'))
                        download_srt = gr.File(label=t('download_srt', 'my'))
                    
                    gr.Markdown("---")
                    gr.Markdown(f"### {t('video_export', 'my')}")
                    with gr.Row():
                        bg_image_input = gr.Image(label=t('bg_image', 'my'), type="filepath")
                        export_video_btn = gr.Button(t('video_export', 'my'), elem_classes="btn-primary")
                    video_output = gr.Video(label=t('video_preview', 'my'))
                    video_status = gr.Markdown()
            
            # ---- TAB 3: 🎬 YouTube to Script ----
            with gr.TabItem(t('tab_youtube', 'my')):
                with gr.Column(elem_classes="glass-card"):
                    gr.HTML("<div style='margin-bottom:12px;'><a href='https://aistudio.google.com/app/apikey' target='_blank' style='color:#00D2FF;text-decoration:none;'>🔑 Get your Gemini API Key here</a></div>")
                    with gr.Row():
                        link_input = gr.Textbox(label=t('yt_link', 'my'), placeholder="https://youtube.com/watch?v=...", scale=2)
                    
                    analyze_btn = gr.Button(t('analyze_yt', 'my'), elem_classes="btn-primary")
                    script_output = gr.Textbox(label=t('raw_script', 'my'), lines=12)
                    
                    with gr.Row():
                        polish_btn = gr.Button(t('polish_script', 'my'), elem_classes="btn-secondary")
                        post_btn = gr.Button(t('social_post', 'my'), elem_classes="btn-secondary")
                        send_to_tts_btn = gr.Button(t('send_to_tts', 'my'), elem_classes="btn-success")
                    
                    with gr.Row():
                        polished_output = gr.Textbox(label=t('polished_script', 'my'), lines=10)
                        post_output = gr.Textbox(label=t('social_content', 'my'), lines=10)
            
            # ---- TAB 4: 📝 Speech to Text ----
            with gr.TabItem(t('tab_transcribe', 'my')):
                with gr.Column(elem_classes="glass-card"):
                    gr.HTML("<div style='margin-bottom:12px;'><a href='https://huggingface.co/settings/tokens' target='_blank' style='color:#00D2FF;text-decoration:none;'>🔑 Ensure HF_TOKEN environment variable is set</a></div>")
                    with gr.Row():
                        audio_file = gr.Audio(type="filepath", label=t('upload_audio', 'my'))
                        language = gr.Dropdown(choices=["auto", "my", "en", "zh", "ja", "ko"], value="auto", label=t('detect_lang', 'my'))
                    transcribe_btn = gr.Button(t('transcribe_btn', 'my'), elem_classes="btn-primary")
                    whisper_output = gr.Textbox(label=t('transcript', 'my'), lines=10)
            
            # ---- TAB 5: 🖼️ AI Thumbnail ----
            with gr.TabItem(t('tab_thumbnail', 'my')):
                with gr.Column(elem_classes="glass-card"):
                    gr.Markdown("### Generate stunning thumbnails using FLUX.1-dev")
                    thumb_prompt = gr.Textbox(label=t('image_prompt', 'my'), placeholder="A dramatic cinematic movie poster...", lines=4)
                    thumb_btn = gr.Button(t('gen_thumb', 'my'), elem_classes="btn-primary")
                    
                    with gr.Row():
                        thumb_image = gr.Image(label=t('generated_image', 'my'), type="filepath")
                    thumb_status = gr.Markdown()
            
            # ---- TAB 6: 🎤 Voice Clone ----
            with gr.TabItem(t('tab_voiceclone', 'my')):
                with gr.Column(elem_classes="glass-card"):
                    gr.Markdown("### 🎤 Voice Cloning Studio")
                    gr.Markdown("ဒီနေရာမှာ စာသားကို အသံအဖြစ် ပြောင်းလဲနိုင်ပါတယ်။")
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown(f"### {t('text_to_speak', 'my')}")
                            clone_text_input = gr.Textbox(
                                label="", 
                                placeholder="Enter text in Myanmar or English...", 
                                lines=4
                            )
                            
                            gr.Markdown(f"### {t('voice_engine', 'my')}")
                            clone_engine = gr.Radio(
                                label="",
                                choices=["gTTS (Free, Myanmar/English)", "Edge TTS (High Quality)"],
                                value="gTTS (Free, Myanmar/English)"
                            )
                            
                            gr.Markdown(f"### {t('speed', 'my')}")
                            clone_speed = gr.Slider(
                                label="",
                                minimum=0.5, 
                                maximum=2.0, 
                                value=1.0, 
                                step=0.1
                            )
                            
                            edge_voice_choice = gr.Dropdown(
                                label=t('select_edge_voice', 'my'),
                                choices=[
                                    "Jenny (US English)",
                                    "Guy (US English)", 
                                    "Aria (US English)",
                                    "Sonia (UK English)",
                                    "Ryan (UK English)",
                                    "Nilar (Myanmar)",
                                    "Thiha (Myanmar)"
                                ],
                                value="Jenny (US English)",
                                visible=False
                            )
                            
                            def toggle_edge_voice(engine):
                                return gr.update(visible=engine == "Edge TTS (High Quality)")
                            
                            clone_engine.change(
                                fn=toggle_edge_voice,
                                inputs=clone_engine,
                                outputs=edge_voice_choice
                            )
                        
                        with gr.Column():
                            gr.Markdown(f"### {t('audio_preview_label', 'my')}")
                            clone_audio_output = gr.Audio(label=t('audio_preview_label', 'my'), type="filepath")
                            clone_status = gr.Markdown("")
                    
                    clone_generate_btn = gr.Button(t('gen_voice', 'my'), elem_classes="btn-primary")
                    
                    gr.Markdown("---")
                    gr.Markdown("### 💡 Tips")
                    gr.Markdown("""
                    - **gTTS** က Myanmar နဲ့ English အတွက် အခမဲ့သုံးလို့ရပါတယ်
                    - **Edge TTS** က အရည်အသွေးပိုကောင်းတဲ့ အသံတွေကို ထုတ်ပေးပါတယ်
                    - စာသားကို မြန်မာလို ဖြစ်ဖြစ်၊ အင်္ဂလိပ်လို ဖြစ်ဖြစ် ရေးလို့ရပါတယ်
                    - Speed ကို လိုသလို ချိန်ညှိနိုင်ပါတယ်
                    """)
            
            # ---- TAB 7: ✂️ Background Removal ----
            with gr.TabItem(t('tab_bgremoval', 'my')):
                with gr.Column(elem_classes="glass-card"):
                    gr.Markdown("### Remove backgrounds instantly with AI")
                    with gr.Row():
                        bg_image_input2 = gr.Image(type="filepath", label=t('upload_image', 'my'))
                        bg_output = gr.Image(label=t('transparent_result', 'my'), type="filepath")
                    
                    bg_btn = gr.Button(t('remove_bg_btn', 'my'), elem_classes="btn-primary")
                    bg_status = gr.Markdown()
            
            # ---- TAB 8: 🌍 Subtitle Sync ----
            with gr.TabItem(t('tab_srt', 'my')):
                with gr.Column(elem_classes="glass-card"):
                    gr.HTML("<div style='margin-bottom:12px;'><a href='https://www.deepl.com/pro-api' target='_blank' style='color:#00D2FF;text-decoration:none;'>🔑 Requires DeepL API Key</a></div>")
                    srt_file_input = gr.File(label=t('upload_srt', 'my'), file_count="single", file_types=[".srt"])
                    
                    with gr.Row():
                        src_lang = gr.Dropdown(label=t('source_lang', 'my'), choices=["auto", "EN", "DE", "FR", "ES", "JA", "ZH"], value="auto")
                        tgt_lang = gr.Dropdown(label=t('target_lang', 'my'), choices=["MY", "EN", "DE", "FR", "ES", "JA", "ZH"], value="MY")
                    
                    srt_translate_btn = gr.Button(t('translate_srt_btn', 'my'), elem_classes="btn-primary")
                    srt_output = gr.File(label=t('download_translated', 'my'))
                    srt_status = gr.Markdown()

            # ---- TAB 9: 💬 AI Chat Assistant ----
            with gr.TabItem(t('tab_chat', 'my')):
                with gr.Column(elem_classes="glass-card"):
                    gr.Markdown(f"## {t('chat_title', 'my')}")
                    gr.Markdown(t('chat_sub', 'my'))
                    
                    gr.Markdown("### 💬 Chat")
                    
                    chat_display = gr.Chatbot(
                        label=t('chat_history', 'my'),
                        height=400,
                        elem_classes="chat-container"
                    )
                    
                    with gr.Row():
                        chat_input = gr.Textbox(
                            label="",
                            placeholder=t('chat_placeholder', 'my'),
                            lines=2,
                            scale=4
                        )
                        chat_send_btn = gr.Button(t('chat_ask', 'my'), elem_classes="btn-primary", scale=1)
                    
                    with gr.Row():
                        chat_clear_btn = gr.Button(t('chat_clear', 'my'), elem_classes="btn-secondary", scale=1)
                        chat_status = gr.Markdown("", scale=3)
                    
                    def chat_with_ai_wrapper(message, history, email, lang):
                        if not message or message.strip() == "":
                            return history, history, "⚠️ " + t('enter_text', lang)
                        
                        if not email:
                            return history + [(message, "❌ " + t('not_logged_in', lang))], history + [(message, "❌ " + t('not_logged_in', lang))], "❌ " + t('not_logged_in', lang)
                        
                        key = get_key_with_rotation(email, "gemini", GEMINI_API_KEY)
                        if not key:
                            return history + [(message, "❌ " + t('yt_gemini_error', lang))], history + [(message, "❌ " + t('yt_gemini_error', lang))], "❌ " + t('yt_gemini_error', lang)
                        
                        try:
                            if lang == "my":
                                system_prompt = """သင်သည် Recap Creator Studio ရဲ့ AI စကားဝိုင်းအကူဖြစ်သည်။ 
                                သုံးစွဲသူများကို အကြောင်းအရာဖန်တီးခြင်း၊ ဇာတ်ညွှန်းရေးခြင်း၊ အသံထုတ်လုပ်ခြင်း၊ 
                                ဗီဒီယိုထုတ်လုပ်ခြင်းနှင့် အခြားသော ဖန်တီးမှုဆိုင်ရာ ကိစ္စရပ်များတွင် အကူအညီပေးပါ။
                                မြန်မာလို ဖြေကြားပါ။ ရင်းနှီးပြီး အသုံးဝင်သော အကြံပြုချက်များကို ပေးပါ။"""
                            else:
                                system_prompt = """You are the AI Chat Assistant for Recap Creator Studio.
                                Help users with content creation, script writing, audio production, video production, 
                                and other creative tasks. Respond in English. Provide friendly and useful advice."""
                            
                            full_prompt = f"{system_prompt}\n\nUser: {message}"
                            
                            response_text = call_gemini_api(full_prompt, key, lang)
                            
                            if "❌" in response_text:
                                if "Invalid/Expired" in response_text:
                                    rotate_key(email, "gemini")
                                return history, history, f"❌ {t('chat_error', lang)}: {response_text}"
                            
                            is_vip, _, _ = get_user_vip_info(email)
                            if not is_vip:
                                increment_usage(email)
                            
                            new_history = history + [(message, response_text)]
                            return new_history, new_history, "✅ " + t('chat_success', lang)
                            
                        except Exception as e:
                            rotate_key(email, "gemini")
                            return history, history, f"❌ {t('chat_error', lang)}: {str(e)}"
                    
                    def clear_chat_wrapper():
                        return [], [], "🗑️ " + t('chat_clear', 'my') + " " + t('chat_success', 'my')
                    
                    chat_send_btn.click(
                        fn=chat_with_ai_wrapper,
                        inputs=[chat_input, chat_history_state, current_user_email, current_language],
                        outputs=[chat_display, chat_history_state, chat_status]
                    )
                    
                    chat_input.submit(
                        fn=chat_with_ai_wrapper,
                        inputs=[chat_input, chat_history_state, current_user_email, current_language],
                        outputs=[chat_display, chat_history_state, chat_status]
                    )
                    
                    chat_clear_btn.click(
                        fn=clear_chat_wrapper,
                        inputs=[],
                        outputs=[chat_display, chat_history_state, chat_status]
                    )

            # ---- TAB 10: 🎙️ Podcast Studio ----
            with gr.TabItem(t('tab_podcast', 'my')):
                with gr.Column(elem_classes="glass-card"):
                    gr.Markdown(f"## {t('podcast_title', 'my')}")
                    gr.Markdown(t('podcast_sub', 'my'))
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown(f"### {t('podcast_topic', 'my')}")
                            podcast_topic = gr.Textbox(
                                label="",
                                placeholder=t('podcast_topic_placeholder', 'my'),
                                lines=2
                            )
                            
                            with gr.Row():
                                gr.Markdown(f"### {t('podcast_speakers', 'my')}")
                                podcast_speakers = gr.Slider(
                                    label="",
                                    minimum=1,
                                    maximum=4,
                                    value=2,
                                    step=1
                                )
                            
                            with gr.Row():
                                gr.Markdown(f"### {t('podcast_duration', 'my')}")
                                podcast_duration = gr.Slider(
                                    label="",
                                    minimum=1,
                                    maximum=15,
                                    value=5,
                                    step=1
                                )
                            
                            gr.Markdown(f"### {t('podcast_style', 'my')}")
                            podcast_style = gr.Radio(
                                label="",
                                choices=[
                                    t('podcast_style_casual', 'my'),
                                    t('podcast_style_formal', 'my'),
                                    t('podcast_style_interview', 'my'),
                                    t('podcast_style_story', 'my')
                                ],
                                value=t('podcast_style_casual', 'my')
                            )
                    
                    podcast_generate_btn = gr.Button(t('podcast_generate', 'my'), elem_classes="btn-primary")
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown(f"### {t('podcast_script', 'my')}")
                            podcast_script_output = gr.Textbox(label="", lines=12)
                        
                        with gr.Column():
                            gr.Markdown(f"### {t('podcast_audio', 'my')}")
                            podcast_audio_output = gr.Audio(label="", type="filepath")
                    
                    podcast_status_output = gr.Markdown("")
                    
                    def podcast_wrapper(topic, speakers, duration, style, email, lang):
                        if not email:
                            return None, None, "❌ " + t('not_logged_in', lang)
                        
                        if not topic or topic.strip() == "":
                            return None, None, "❌ " + t('podcast_topic', 'my') + " " + t('enter_text', lang)
                        
                        key = get_key_with_rotation(email, "gemini", GEMINI_API_KEY)
                        if not key:
                            return None, None, "❌ " + t('yt_gemini_error', lang)
                        
                        try:
                            style_map = {
                                "ပေါ့ပေါ့ပါးပါး": "casual, conversational, friendly",
                                "တရားဝင်": "formal, professional, structured",
                                "အင်တာဗျူး": "interview style, question and answer",
                                "ပုံပြင်": "storytelling, narrative, engaging",
                                "Casual": "casual, conversational, friendly",
                                "Formal": "formal, professional, structured",
                                "Interview": "interview style, question and answer",
                                "Storytelling": "storytelling, narrative, engaging"
                            }
                            
                            style_desc = style_map.get(style, "casual, friendly")
                            
                            if lang == "my":
                                prompt = f"""သင်သည် ပေါ့ကတ်စ်ဇာတ်ညွှန်းရေးဆရာတစ်ဦးဖြစ်သည်။ 
                                အောက်ပါအတိုင်း ပေါ့ကတ်စ်ဇာတ်ညွှန်းကို ရေးသားပါ:
                                - အကြောင်းအရာ: {topic}
                                - စကားပြောသူအရေအတွက်: {speakers} ဦး
                                - ကြာချိန်: {duration} မိနစ်
                                - ပုံစံ: {style_desc}
                                
                                ဇာတ်ညွှန်းကို သဘာဝကျကျ စကားပြောသလိုရေးပါ။ 
                                စကားပြောသူတွေကို Speaker 1, Speaker 2, Speaker 3 စသဖြင့် သတ်မှတ်ပါ။"""
                            else:
                                prompt = f"""You are a podcast script writer. Write a podcast script with the following details:
                                - Topic: {topic}
                                - Number of speakers: {speakers}
                                - Duration: {duration} minutes
                                - Style: {style_desc}
                                
                                Write the script in a natural conversational style.
                                Label speakers as Speaker 1, Speaker 2, Speaker 3, etc."""
                            
                            response_text = call_gemini_api(prompt, key, lang)
                            
                            if "❌" in response_text:
                                if "Invalid/Expired" in response_text:
                                    rotate_key(email, "gemini")
                                return None, None, response_text
                            
                            script = response_text
                            
                            audio_path = None
                            combined_audio = AudioSegment.empty()
                            
                            speaker_pattern = r'(Speaker \d+|စကားပြောသူ \d+)'
                            segments = re.split(speaker_pattern, script)
                            segments = [s.strip() for s in segments if s.strip()]
                            
                            voices = ["en-US-JennyNeural", "en-US-GuyNeural", "en-US-AriaNeural", "en-US-GuyNeural"]
                            myanmar_voices = ["my-MM-NilarNeural", "my-MM-ThihaNeural", "my-MM-NilarNeural", "my-MM-ThihaNeural"]
                            is_myanmar = bool(re.search(r'[\u1000-\u109F]', script))
                            
                            for i in range(0, len(segments), 2):
                                if i+1 < len(segments):
                                    text = segments[i+1]
                                    voice = myanmar_voices[i//2 % len(myanmar_voices)] if is_myanmar else voices[i//2 % len(voices)]
                                    
                                    try:
                                        async def generate_segment():
                                            comm = edge_tts.Communicate(text=text, voice=voice, rate="+0%")
                                            audio_data = bytearray()
                                            async for chunk in comm.stream():
                                                if chunk["type"] == "audio":
                                                    audio_data.extend(chunk["data"])
                                            return audio_data
                                        
                                        audio_bytes = asyncio.run(generate_segment())
                                        
                                        if audio_bytes:
                                            temp_file = f"temp_segment_{i}.mp3"
                                            with open(temp_file, "wb") as f:
                                                f.write(audio_bytes)
                                            
                                            seg_audio = AudioSegment.from_mp3(temp_file)
                                            combined_audio += seg_audio + AudioSegment.silent(duration=500)
                                            
                                            if os.path.exists(temp_file):
                                                os.remove(temp_file)
                                    except Exception as e:
                                        print(f"Audio generation error for segment {i}: {e}")
                                        continue
                            
                            if len(combined_audio) > 0:
                                audio_path = "podcast_audio.mp3"
                                combined_audio.export(audio_path, format="mp3")
                            
                            is_vip, _, _ = get_user_vip_info(email)
                            if not is_vip:
                                increment_usage(email)
                            
                            return script, audio_path, t('podcast_success', lang)
                            
                        except Exception as e:
                            rotate_key(email, "gemini")
                            return None, None, f"{t('podcast_error', lang)}: {str(e)}"
                    
                    podcast_generate_btn.click(
                        fn=podcast_wrapper,
                        inputs=[podcast_topic, podcast_speakers, podcast_duration, podcast_style, current_user_email, current_language],
                        outputs=[podcast_script_output, podcast_audio_output, podcast_status_output]
                    )

            # ---- TAB 11: 📝 Content Writer ----
            with gr.TabItem(t('tab_content', 'my')):
                with gr.Column(elem_classes="glass-card"):
                    gr.Markdown(f"## {t('content_title', 'my')}")
                    gr.Markdown(t('content_sub', 'my'))
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown(f"### {t('content_topic', 'my')}")
                            content_topic = gr.Textbox(
                                label="",
                                placeholder=t('content_topic_placeholder', 'my'),
                                lines=2
                            )
                            
                            gr.Markdown(f"### {t('content_type', 'my')}")
                            content_type = gr.Radio(
                                label="",
                                choices=[
                                    t('content_type_blog', 'my'),
                                    t('content_type_article', 'my'),
                                    t('content_type_social', 'my'),
                                    t('content_type_email', 'my'),
                                    t('content_type_story', 'my'),
                                    t('content_type_product', 'my')
                                ],
                                value=t('content_type_blog', 'my')
                            )
                            
                            with gr.Row():
                                gr.Markdown(f"### {t('content_length', 'my')}")
                                content_length = gr.Radio(
                                    label="",
                                    choices=[
                                        t('content_length_short', 'my'),
                                        t('content_length_medium', 'my'),
                                        t('content_length_long', 'my')
                                    ],
                                    value=t('content_length_medium', 'my')
                                )
                            
                            gr.Markdown(f"### {t('content_tone', 'my')}")
                            content_tone = gr.Radio(
                                label="",
                                choices=[
                                    t('content_tone_professional', 'my'),
                                    t('content_tone_casual', 'my'),
                                    t('content_tone_enthusiastic', 'my'),
                                    t('content_tone_informative', 'my'),
                                    t('content_tone_persuasive', 'my')
                                ],
                                value=t('content_tone_professional', 'my')
                            )
                    
                    content_generate_btn = gr.Button(t('content_generate', 'my'), elem_classes="btn-primary")
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown(f"### {t('content_output', 'my')}")
                            content_output = gr.Textbox(label="", lines=12)
                        
                        with gr.Column():
                            gr.Markdown("### 📊 " + t('content_status', 'my'))
                            content_status = gr.Markdown("")
                            
                            with gr.Row():
                                content_copy_btn = gr.Button(t('content_copy', 'my'), elem_classes="btn-secondary", scale=1)
                                content_export_btn = gr.Button(t('content_export', 'my'), elem_classes="btn-secondary", scale=1)
                    
                    def content_wrapper(topic, content_type, length, tone, email, lang):
                        if not email:
                            return None, "❌ " + t('not_logged_in', lang)
                        
                        if not topic or topic.strip() == "":
                            return None, "❌ " + t('content_topic', 'my') + " " + t('enter_text', lang)
                        
                        key = get_key_with_rotation(email, "gemini", GEMINI_API_KEY)
                        if not key:
                            return None, "❌ " + t('yt_gemini_error', lang)
                        
                        try:
                            length_map = {
                                "တိုတို": "short (100-200 words)",
                                "အလယ်အလတ်": "medium (300-500 words)",
                                "ရှည်လျား": "long (800-1200 words)",
                                "Short": "short (100-200 words)",
                                "Medium": "medium (300-500 words)",
                                "Long": "long (800-1200 words)"
                            }
                            
                            type_map = {
                                "ဘလော့ဂ်ပို့စ်": "blog post",
                                "ဆောင်းပါး": "article",
                                "ဆိုရှယ်မီဒီယာပို့စ်": "social media post",
                                "အီးမေးလ်": "email",
                                "ဇာတ်လမ်း": "short story",
                                "ကုန်ပစ္စည်းဖော်ပြချက်": "product description",
                                "Blog Post": "blog post",
                                "Article": "article",
                                "Social Media Post": "social media post",
                                "Email": "email",
                                "Story": "short story",
                                "Product Description": "product description"
                            }
                            
                            tone_map = {
                                "ကျွမ်းကျင်သော": "professional",
                                "ပေါ့ပေါ့ပါးပါး": "casual",
                                "စိတ်လှုပ်ရှားဖွယ်": "enthusiastic",
                                "သတင်းအချက်အလက်": "informative",
                                "ဆွဲဆောင်မှုရှိသော": "persuasive",
                                "Professional": "professional",
                                "Casual": "casual",
                                "Enthusiastic": "enthusiastic",
                                "Informative": "informative",
                                "Persuasive": "persuasive"
                            }
                            
                            content_type_desc = type_map.get(content_type, "content")
                            length_desc = length_map.get(length, "medium length")
                            tone_desc = tone_map.get(tone, "professional")
                            
                            if lang == "my":
                                prompt = f"""သင်သည် ကျွမ်းကျင်သော အကြောင်းအရာရေးဆရာတစ်ဦးဖြစ်သည်။ 
                                အောက်ပါအတိုင်း {content_type_desc} တစ်ခုကို ရေးသားပါ:
                                - အကြောင်းအရာ: {topic}
                                - အရှည်: {length_desc}
                                - ဟန်ပန်: {tone_desc}
                                
                                အကြောင်းအရာကို စိတ်ဝင်စားဖွယ်ရာ၊ ဆွဲဆောင်မှုရှိပြီး အသုံးဝင်အောင် ရေးသားပါ။
                                ခေါင်းစဉ်လည်း ထည့်ပေးပါ။"""
                            else:
                                prompt = f"""You are a professional content writer. Write a {content_type_desc} with the following details:
                                - Topic: {topic}
                                - Length: {length_desc}
                                - Tone: {tone_desc}
                                
                                Make the content engaging, interesting, and useful. Include a compelling title."""
                            
                            response_text = call_gemini_api(prompt, key, lang)
                            
                            if "❌" in response_text:
                                if "Invalid/Expired" in response_text:
                                    rotate_key(email, "gemini")
                                return None, response_text
                            
                            content = response_text
                            
                            is_vip, _, _ = get_user_vip_info(email)
                            if not is_vip:
                                increment_usage(email)
                            
                            return content, t('content_success', lang)
                            
                        except Exception as e:
                            rotate_key(email, "gemini")
                            return None, f"{t('content_error', lang)}: {str(e)}"
                    
                    def copy_content(content):
                        if content:
                            return gr.update(value="📋 " + t('content_success', 'my') + " " + t('content_copy', 'my'))
                        return gr.update(value="⚠️ No content to copy")
                    
                    def export_content(content):
                        if content:
                            filename = f"content_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                            with open(filename, "w", encoding="utf-8") as f:
                                f.write(content)
                            return gr.update(value=filename)
                        return gr.update(value=None)
                    
                    content_generate_btn.click(
                        fn=content_wrapper,
                        inputs=[content_topic, content_type, content_length, content_tone, current_user_email, current_language],
                        outputs=[content_output, content_status]
                    )
                    
                    content_copy_btn.click(
                        fn=copy_content,
                        inputs=[content_output],
                        outputs=[content_status]
                    )
                    
                    content_export_btn.click(
                        fn=export_content,
                        inputs=[content_output],
                        outputs=[content_export_btn]
                    )

            # ---- TAB 12: 🎬 Movie Recap (One Click) ----
            with gr.TabItem(t('tab_movie_recap', 'my')):
                with gr.Column(elem_classes="glass-card"):
                    gr.Markdown(f"## {t('movie_recap_title', 'my')}")
                    gr.Markdown(t('movie_recap_sub', 'my'))
                    
                    gr.Markdown(f"### {t('movie_recap_input_method', 'my')}")
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown(f"**{t('movie_recap_upload', 'my')}**")
                            movie_video_upload = gr.File(
                                label=t('movie_recap_upload_hint', 'my'),
                                file_types=[".mp4", ".mov", ".avi", ".mkv", ".webm"],
                                type="filepath"
                            )
                        
                        with gr.Column(scale=1):
                            gr.Markdown(f"**{t('movie_recap_or', 'my')}**")
                            gr.Markdown(f"**{t('movie_recap_link', 'my')}**")
                            movie_youtube_input = gr.Textbox(
                                label="",
                                placeholder=t('movie_recap_link_placeholder', 'my'),
                                lines=1
                            )
                    
                    gr.Markdown("---")
                    
                    with gr.Row():
                        movie_voice = gr.Dropdown(
                            label=t('movie_recap_voice', 'my'),
                            choices=[
                                "my-MM-ThihaNeural (Myanmar Male)",
                                "my-MM-NilarNeural (Myanmar Female)",
                                "en-US-JennyNeural (English Female)",
                                "en-US-GuyNeural (English Male)"
                            ],
                            value="my-MM-ThihaNeural (Myanmar Male)"
                        )
                        
                        movie_lang = gr.Radio(
                            label=t('movie_recap_lang', 'my'),
                            choices=["မြန်မာ (Myanmar)", "English"],
                            value="မြန်မာ (Myanmar)"
                        )
                    
                    movie_generate_btn = gr.Button(
                        t('movie_recap_generate', 'my'), 
                        elem_classes="btn-primary", 
                        size="lg"
                    )
                    
                    gr.Markdown("---")
                    gr.Markdown(f"### {t('movie_recap_status', 'my')}")
                    movie_status = gr.Markdown("")
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown(f"### {t('movie_recap_transcript', 'my')}")
                            movie_transcript = gr.Textbox(label="", lines=4)
                            
                            gr.Markdown(f"### {t('movie_recap_script', 'my')}")
                            movie_script = gr.Textbox(label="", lines=8)
                            
                            gr.Markdown(f"### {t('movie_recap_thumbnail', 'my')}")
                            movie_thumbnail = gr.Image(label="", type="filepath", height=200)
                        
                        with gr.Column():
                            gr.Markdown(f"### {t('movie_recap_audio', 'my')}")
                            movie_audio = gr.Audio(label="", type="filepath")
                            
                            gr.Markdown(f"### {t('movie_recap_subtitles', 'my')}")
                            movie_subtitles = gr.File(label="")
                            
                            gr.Markdown(f"### {t('movie_recap_video', 'my')}")
                            movie_video = gr.Video(label="")
                    
                    gr.Markdown("---")
                    gr.Markdown(f"### {t('movie_recap_how_it_works', 'my')}")
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown(t('movie_recap_step1', 'my'))
                            gr.Markdown(t('movie_recap_step2', 'my'))
                            gr.Markdown(t('movie_recap_step3', 'my'))
                        with gr.Column():
                            gr.Markdown(t('movie_recap_step4', 'my'))
                            gr.Markdown(t('movie_recap_step5', 'my'))
                            gr.Markdown(t('movie_recap_step6', 'my'))
                    
                    gr.Markdown("""
                    ### ⚡ Supported Formats:
                    - **Video Files:** MP4, MOV, AVI, MKV, WEBM (Max 150MB)
                    - **YouTube:** Any public YouTube video with captions
                    """)
                    
                    def process_movie_recap(video, url, email, voice, lang, progress=gr.Progress()):
                        return one_click_movie_recap(video, url, email, voice, lang, progress)
                    
                    movie_generate_btn.click(
                        fn=process_movie_recap,
                        inputs=[movie_video_upload, movie_youtube_input, current_user_email, movie_voice, movie_lang],
                        outputs=[movie_transcript, movie_script, movie_audio, movie_thumbnail, movie_subtitles, movie_video, movie_status]
                    )

            # ---- TAB 13: 🔑 Key Management (NEW DESIGN) ----
            with gr.TabItem(t('tab_keys', 'my')):
                with gr.Column(elem_classes="glass-card"):
                    gr.HTML("""
                    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 10px;">
                        <span style="font-size: 28px;">🔐</span>
                        <div>
                            <h2 style="margin: 0; color: #fff;">Multi-Keys Manager</h2>
                            <p style="color: #9CA3AF; margin: 4px 0 0 0;">Manage Gemini, DeepL & Hugging Face API keys</p>
                        </div>
                    </div>
                    """)
                    
                    with gr.Row():
                        with gr.Column(scale=2):
                            gr.Markdown("### 🗂️ Key Status")
                            key_status_display = gr.HTML(
                                refresh_keys_display("")
                            )
                            refresh_keys_btn = gr.Button("🔄 Refresh Status", elem_classes="btn-secondary", size="sm")

                        with gr.Column(scale=1):
                            gr.Markdown("### ➕ Add API Keys")
                            
                            gr.HTML("""
                            <div style="background: rgba(15, 12, 41, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 20px;">
                                <p style="color: #9CA3AF; margin: 0 0 16px 0; font-size: 14px;">Add multiple keys separated by commas (,) or new lines.</p>
                            """)
                            
                            key_gemini_input = gr.Textbox(
                                label="🔑 Gemini API Keys",
                                placeholder="AQ.Key1\nAQ.Key2\nAQ.Key3",
                                lines=4
                            )
                            
                            key_deepl_input = gr.Textbox(
                                label="🌐 DeepL API Keys",
                                placeholder="deepl-api-key-1\ndeepl-api-key-2",
                                lines=3,
                                visible=True
                            )
                            
                            key_hf_input = gr.Textbox(
                                label="🤗 Hugging Face Tokens",
                                placeholder="hf_token1\nhf_token2",
                                lines=3,
                                visible=True
                            )
                            
                            gr.HTML("""
                            <div style="margin-top: 8px; color: #6B7280; font-size: 12px;">
                                💡 Keys will auto-rotate when rate limit is reached.
                            </div>
                            """)
                            
                            with gr.Row():
                                save_keys_btn = gr.Button("💾 Save All Keys", elem_classes="btn-primary", scale=2)
                            
                            gr.HTML("</div>")
                            key_save_status = gr.Markdown("")
                            
                            key_other_input = gr.Textbox(label="Other Keys (JSON)", visible=False)
                            key_gmail_input = gr.Textbox(label="Gmail App Passwords", visible=False)

                    def save_keys_wrapper(email, gemini, hf, deepl, gmail, other):
                        if not email:
                            return "❌ Please login first."
                        
                        keys_dict = {}
                        
                        def parse_keys(raw_input):
                            if not raw_input or not raw_input.strip():
                                return []
                            parts = raw_input.replace('\r', '').split('\n')
                            all_keys = []
                            for part in parts:
                                if ',' in part:
                                    all_keys.extend([k.strip() for k in part.split(',') if k.strip()])
                                else:
                                    if part.strip():
                                        all_keys.append(part.strip())
                            return all_keys
                        
                        if gemini and gemini.strip():
                            gemini_keys = parse_keys(gemini)
                            if gemini_keys:
                                keys_dict["gemini"] = gemini_keys
                        
                        if deepl and deepl.strip():
                            deepl_keys = parse_keys(deepl)
                            if deepl_keys:
                                keys_dict["deepl"] = deepl_keys
                        
                        if hf and hf.strip():
                            hf_keys = parse_keys(hf)
                            if hf_keys:
                                keys_dict["hf"] = hf_keys
                        
                        if gmail and gmail.strip():
                            gmail_keys = parse_keys(gmail)
                            if gmail_keys:
                                keys_dict["gmail"] = gmail_keys
                        
                        if other and other.strip():
                            try:
                                other_dict = json.loads(other)
                                for k, v in other_dict.items():
                                    if isinstance(v, list):
                                        keys_dict[k] = [item.strip() for item in v if item and str(item).strip()]
                                    else:
                                        keys_dict[k] = [str(v).strip()]
                            except Exception as e:
                                return f"❌ Invalid JSON format: {str(e)}"
                        
                        if not keys_dict:
                            return "❌ No valid keys to save."
                        
                        success, msg = save_user_keys(email, keys_dict)
                        return msg
                    
                    def refresh_keys_display_wrapper(email):
                        return refresh_keys_display(email)
                    
                    save_keys_btn.click(
                        fn=save_keys_wrapper,
                        inputs=[current_user_email, key_gemini_input, key_hf_input, key_deepl_input, key_gmail_input, key_other_input],
                        outputs=[key_save_status]
                    ).then(
                        fn=refresh_keys_display_wrapper,
                        inputs=[current_user_email],
                        outputs=[key_status_display]
                    )
                    
                    refresh_keys_btn.click(
                        fn=refresh_keys_display_wrapper,
                        inputs=[current_user_email],
                        outputs=[key_status_display]
                    )
        
        # Footer
        gr.HTML(f"""
        <div style="text-align: center; margin-top: 40px; padding-top: 24px; border-top: 1px solid rgba(255,255,255,0.05); color: #9CA3AF; font-size: 14px;">
            <p style="margin-bottom: 8px;"><span style="color: #00D2FF; font-weight: 600;">{t('footer_credit', 'my')}</span></p>
            <div style="display: flex; justify-content: center; gap: 16px;">
                <a href="https://t.me/yufei199" target="_blank" style="color: #8A2BE2; text-decoration: none; font-weight: 500;">📲 {t('telegram', 'my')}</a>
                <span>|</span>
                <a href="https://t.me/yufei199" target="_blank" style="color: #8A2BE2; text-decoration: none; font-weight: 500;">💬 {t('support', 'my')}</a>
            </div>
        </div>
        """)

    # ==========================================
    # EVENT BINDINGS
    # ==========================================
    
    def handle_login(email, password, lang="my"):
        if not email or not password:
            return t('enter_credentials', lang), "", gr.update(visible=True), gr.update(visible=False), update_profile_display(""), get_broadcast_html(), "🔔", "", gr.update(visible=False), "", ""
        
        result, logged_email, success = login_with_email_password(email, password)
        if success and logged_email:
            red_dot_html, doc_id, msg = check_notifications(logged_email)
            return t('login_success', lang), logged_email, gr.update(visible=False), gr.update(visible=True), update_profile_display(logged_email, lang), get_broadcast_html(), "🔔", red_dot_html, gr.update(visible=False), doc_id, msg
        
        return result, "", gr.update(visible=True), gr.update(visible=False), update_profile_display(""), get_broadcast_html(), "🔔", "", gr.update(visible=False), "", ""
    
    def handle_signup(email, password, lang="my"):
        if not email or not password:
            return t('enter_credentials', lang), "", gr.update(visible=True), gr.update(visible=False), update_profile_display(""), get_broadcast_html(), "🔔", "", gr.update(visible=False), "", ""
        
        if len(password) < 6:
            return t('password_short', lang), "", gr.update(visible=True), gr.update(visible=False), update_profile_display(""), get_broadcast_html(), "🔔", "", gr.update(visible=False), "", ""
        
        result, logged_email, success = create_user_with_email(email, password)
        if success and logged_email:
            red_dot_html, doc_id, msg = check_notifications(logged_email)
            return t('signup_success', lang), logged_email, gr.update(visible=False), gr.update(visible=True), update_profile_display(logged_email, lang), get_broadcast_html(), "🔔", red_dot_html, gr.update(visible=False), doc_id, msg
        
        return result, "", gr.update(visible=True), gr.update(visible=False), update_profile_display(""), get_broadcast_html(), "🔔", "", gr.update(visible=False), "", ""
    
    def handle_logout(lang="my"):
        return "", gr.update(visible=True), gr.update(visible=False), update_profile_display(""), get_broadcast_html(), "🔔", "", gr.update(visible=False), "", ""
    
    def switch_language(lang, email):
        auth_title_html = f"""
        <div class="auth-logo">
            <img src="https://cdn.phototourl.com/free/2026-07-21-023573ae-5979-4c45-974c-84f2864a959a.png" alt="Logo" class="logo-image" />
            <h1>{t('welcome_title', lang)}</h1>
            <p>{t('welcome_sub', lang)}</p>
        </div>
        """
        return (
            gr.update(value=auth_title_html),
            gr.update(placeholder=t('email_placeholder', lang)),
            gr.update(placeholder=t('password_placeholder', lang)),
            gr.update(value=t('sign_in', lang)),
            gr.update(value=t('sign_up', lang)),
            gr.update(value=""),
            gr.update(value=t('admin_dashboard', lang)),
            gr.update(value=t('logout', lang)),
            update_profile_display(email, lang),
            lang,
            gr.update(value=t('tab_vip', lang)),
            gr.update(value=t('tab_tts', lang)),
            gr.update(value=t('tab_youtube', lang)),
            gr.update(value=t('tab_transcribe', lang)),
            gr.update(value=t('tab_thumbnail', lang)),
            gr.update(value=t('tab_voiceclone', lang)),
            gr.update(value=t('tab_bgremoval', lang)),
            gr.update(value=t('tab_srt', lang)),
            gr.update(value=t('tab_chat', lang)),
            gr.update(value=t('tab_podcast', lang)),
            gr.update(value=t('tab_content', lang)),
            gr.update(value=t('tab_movie_recap', lang)),
            gr.update(value=t('tab_keys', lang)),
            gr.update(value=t('footer_credit', lang)),
            gr.update(value=t('telegram', lang)),
            gr.update(value=t('support', lang)),
        )
    
    def handle_clone_voice(email, text, engine, speed, edge_voice, lang="my"):
        if engine == "gTTS (Free, Myanmar/English)":
            return clone_voice_with_gtts(email, text, speed, lang)
        else:
            return clone_voice_with_edge(email, text, edge_voice, speed, lang)
    
    # Auth Events
    login_btn.click(
        fn=handle_login, 
        inputs=[email_input, password_input, current_language], 
        outputs=[auth_status, current_user_email, auth_page, app_page, profile_html, broadcast_html, notif_icon_btn, notif_badge_html, notif_dialog, current_notif_doc_id_state, current_notif_msg_state]
    )
    
    signup_btn.click(
        fn=handle_signup, 
        inputs=[email_input, password_input, current_language], 
        outputs=[auth_status, current_user_email, auth_page, app_page, profile_html, broadcast_html, notif_icon_btn, notif_badge_html, notif_dialog, current_notif_doc_id_state, current_notif_msg_state]
    )
    
    logout_btn.click(
        fn=handle_logout, 
        inputs=[current_language], 
        outputs=[current_user_email, auth_page, app_page, profile_html, broadcast_html, notif_icon_btn, notif_badge_html, notif_dialog, current_notif_doc_id_state, current_notif_msg_state]
    )
    
    # Notification
    notif_icon_btn.click(
        fn=open_notification,
        inputs=[current_notif_doc_id_state, current_notif_msg_state],
        outputs=[notif_dialog, notif_message_display]
    )
    
    notif_close_btn.click(
        fn=close_notification,
        inputs=[current_notif_doc_id_state],
        outputs=[notif_dialog, notif_message_display]
    ).then(
        fn=lambda: gr.update(visible=True, elem_styles={"display": "none !important"}),
        outputs=notif_dialog
    )
    
    # Language Switching
    lang_my_btn.click(
        fn=switch_language,
        inputs=[gr.State("my"), current_user_email],
        outputs=[
            auth_title, email_input, password_input, login_btn, signup_btn, 
            auth_status, gr.State(""), logout_btn, profile_html, 
            current_language,
            gr.State(""), gr.State(""), gr.State(""), gr.State(""), 
            gr.State(""), gr.State(""), gr.State(""), gr.State(""),
            gr.State(""), gr.State(""), gr.State(""), gr.State(""),
            gr.State(""), gr.State(""), gr.State("")
        ]
    )
    
    lang_en_btn.click(
        fn=switch_language,
        inputs=[gr.State("en"), current_user_email],
        outputs=[
            auth_title, email_input, password_input, login_btn, signup_btn, 
            auth_status, gr.State(""), logout_btn, profile_html, 
            current_language,
            gr.State(""), gr.State(""), gr.State(""), gr.State(""), 
            gr.State(""), gr.State(""), gr.State(""), gr.State(""),
            gr.State(""), gr.State(""), gr.State(""), gr.State(""),
            gr.State(""), gr.State(""), gr.State("")
        ]
    )
    
    # TTS
    generate_btn.click(
        fn=tts_wrapper, 
        inputs=[current_user_email, text_input, replacement_rules, custom_filename, voice_choice, subtitle_style, speed_slider, volume_slider, current_language], 
        outputs=[audio_output, download_audio, download_srt, status_output]
    )
    
    export_video_btn.click(
        fn=export_video, 
        inputs=[download_audio, download_srt, bg_image_input, current_user_email, current_language], 
        outputs=[video_output, video_status]
    )
    
    # YouTube to Script
    analyze_btn.click(
        fn=analyze_youtube_link, 
        inputs=[link_input, current_user_email, current_language], 
        outputs=script_output
    )
    
    polish_btn.click(
        fn=polish_script, 
        inputs=[script_output, current_user_email, current_language], 
        outputs=polished_output
    )
    
    post_btn.click(
        fn=generate_post, 
        inputs=[script_output, current_user_email, current_language], 
        outputs=post_output
    )
    
    send_to_tts_btn.click(fn=lambda s: s, inputs=script_output, outputs=text_input)
    
    # Transcription
    transcribe_btn.click(
        fn=transcribe_audio, 
        inputs=[audio_file, language, current_user_email, current_language], 
        outputs=whisper_output
    )
    
    # Thumbnail
    thumb_btn.click(
        fn=generate_thumbnail, 
        inputs=[thumb_prompt, current_user_email, current_language], 
        outputs=[thumb_image, thumb_status]
    )
    
    # Voice Clone
    clone_generate_btn.click(
        fn=handle_clone_voice,
        inputs=[current_user_email, clone_text_input, clone_engine, clone_speed, edge_voice_choice, current_language],
        outputs=[clone_audio_output, clone_status]
    )
    
    # Background Removal
    bg_btn.click(
        fn=remove_bg, 
        inputs=[bg_image_input2, current_user_email, current_language], 
        outputs=[bg_output, bg_status]
    )
    
    # SRT Translation
    srt_translate_btn.click(
        fn=translate_srt_file, 
        inputs=[srt_file_input, key_deepl_input, src_lang, tgt_lang, current_user_email, current_language], 
        outputs=[srt_output, srt_status]
    )
    
    # VIP Payment
    vip_plan.change(fn=lambda p: "3,000 MMK" if "3,000" in p else "1,500 MMK", inputs=vip_plan, outputs=vip_amount)
    
    submit_payment_btn.click(
        fn=submit_vip_payment, 
        inputs=[vip_email_input, vip_phone_input, vip_plan, vip_amount, vip_method, vip_screenshot, vip_transaction_id, current_language], 
        outputs=vip_payment_status
    )
    
    # Timer: Check for new notifications every 5 seconds
    notif_timer = gr.Timer(5)
    notif_timer.tick(
        fn=check_notifications,
        inputs=current_user_email,
        outputs=[notif_badge_html, current_notif_doc_id_state, current_notif_msg_state]
    )

# ==========================================
# LAUNCH APP
# ==========================================
if __name__ == "__main__":
    # ✅ Setup TTS TTL index for auto-delete after 2 days
    print("⏳ Setting up TTS TTL index for auto-delete after 2 days...")
    setup_tts_ttl_index()
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)), # ✅ Render port
        theme=gr.themes.Base(),
        css=custom_css,
        auth=None # ✅ Disable built-in auth
    )
