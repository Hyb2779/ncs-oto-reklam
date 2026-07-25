import os
import json
import requests
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.environ.get('TG_AD_BOT_TOKEN')
API_BASE = f'https://api.telegram.org/bot{BOT_TOKEN}'

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

def send_ad(chat_id, text, image_path=None, button_text=None, button_url=None):
    reply_markup = None
    if button_text and button_url:
        reply_markup = {'inline_keyboard': [[{'text': button_text, 'url': button_url}]]}

    try:
        if image_path and os.path.exists(image_path):
            ext = os.path.splitext(image_path)[1].lower()

            if ext in VIDEO_EXTENSIONS:
                endpoint = 'sendVideo'
                file_field = 'video'
            else:
                endpoint = 'sendPhoto'
                file_field = 'photo'

            with open(image_path, 'rb') as media_file:
                payload = {'chat_id': chat_id, 'caption': text}
                if reply_markup:
                    payload['reply_markup'] = json.dumps(reply_markup)
                r = requests.post(f'{API_BASE}/{endpoint}', data=payload,
                                   files={file_field: media_file}, timeout=60)
        else:
            payload = {'chat_id': chat_id, 'text': text}
            if reply_markup:
                payload['reply_markup'] = reply_markup
            r = requests.post(f'{API_BASE}/sendMessage', json=payload, timeout=15)

        d = r.json()
        return d.get('ok', False), d
    except Exception as e:
        return False, str(e)
