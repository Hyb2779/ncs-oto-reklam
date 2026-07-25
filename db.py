import sqlite3
import os
import time
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ads.db')

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            image_path TEXT,
            text TEXT,
            button_text TEXT,
            button_url TEXT,
            target_chat_ids TEXT,
            start_date TEXT,
            end_date TEXT,
            send_time TEXT,
            repeat_hours REAL,
            total_limit INTEGER,
            sent_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            last_sent_at REAL,
            created_at REAL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS ad_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_id INTEGER,
            chat_id TEXT,
            sent_at REAL,
            success INTEGER,
            error TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY, password_hash TEXT)''')

def create_ad(data):
    with get_conn() as conn:
        cur = conn.execute('''INSERT INTO ads
            (title, image_path, text, button_text, button_url, target_chat_ids,
             start_date, end_date, send_time, repeat_hours, total_limit, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (data['title'], data.get('image_path'), data['text'], data.get('button_text'),
             data.get('button_url'), data['target_chat_ids'], data['start_date'], data.get('end_date'),
             data['send_time'], data.get('repeat_hours'), data.get('total_limit'), 1, time.time()))
        return cur.lastrowid

def update_ad(ad_id, data):
    with get_conn() as conn:
        fields = []
        values = []
        for key in ['title', 'image_path', 'text', 'button_text', 'button_url', 'target_chat_ids',
                     'start_date', 'end_date', 'send_time', 'repeat_hours', 'total_limit']:
            if key in data:
                fields.append(f'{key} = ?')
                values.append(data[key])
        values.append(ad_id)
        conn.execute(f'UPDATE ads SET {", ".join(fields)} WHERE id = ?', values)

def get_ad(ad_id):
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM ads WHERE id = ?', (ad_id,)).fetchone()
        return dict(row) if row else None

def get_all_ads():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM ads ORDER BY created_at DESC').fetchall()]

def get_active_ads():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM ads WHERE is_active = 1').fetchall()]

def toggle_ad(ad_id):
    with get_conn() as conn:
        row = conn.execute('SELECT is_active FROM ads WHERE id = ?', (ad_id,)).fetchone()
        new_val = 0 if row['is_active'] else 1
        conn.execute('UPDATE ads SET is_active = ? WHERE id = ?', (new_val, ad_id))
        return new_val

def delete_ad(ad_id):
    with get_conn() as conn:
        conn.execute('DELETE FROM ads WHERE id = ?', (ad_id,))
        conn.execute('DELETE FROM ad_logs WHERE ad_id = ?', (ad_id,))

def mark_sent(ad_id, chat_id, success, error=None):
    with get_conn() as conn:
        conn.execute('INSERT INTO ad_logs (ad_id, chat_id, sent_at, success, error) VALUES (?, ?, ?, ?, ?)',
                      (ad_id, chat_id, time.time(), 1 if success else 0, error))
        if success:
            conn.execute('UPDATE ads SET sent_count = sent_count + 1, last_sent_at = ? WHERE id = ?',
                          (time.time(), ad_id))

def get_logs(limit=100):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute('''
            SELECT ad_logs.*, ads.title FROM ad_logs
            LEFT JOIN ads ON ads.id = ad_logs.ad_id
            ORDER BY sent_at DESC LIMIT ?''', (limit,)).fetchall()]

def deactivate_ad(ad_id):
    with get_conn() as conn:
        conn.execute('UPDATE ads SET is_active = 0 WHERE id = ?', (ad_id,))
