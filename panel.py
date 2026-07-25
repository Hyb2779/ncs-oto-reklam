import functools
import datetime
import json
import os
from flask import Flask, Blueprint, request, session, redirect, url_for, render_template_string
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import db

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

panel_bp = Blueprint('adpanel', __name__, url_prefix='/ilan-panel')

def login_required(f):
    @functools.wraps(f)
    def wrapper(*a, **kw):
        if not session.get('ad_logged_in'):
            return redirect(url_for('adpanel.login'))
        return f(*a, **kw)
    return wrapper

STYLE = """
<style>
* { box-sizing: border-box; }
body { font-family: -apple-system, Segoe UI, sans-serif; background:#0f1620; color:#e6edf3; margin:0; }
.topbar { background:#18222d; padding:16px 24px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #263140; }
.topbar h1 { font-size:18px; margin:0; color:#2481cc; }
.topbar a { color:#8b98a5; text-decoration:none; margin-left:16px; font-size:14px; }
.container { padding:24px; max-width:1100px; margin:0 auto; }
.panel-box { background:#18222d; border:1px solid #263140; border-radius:10px; padding:18px; margin-bottom:24px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th, td { text-align:left; padding:8px 10px; border-bottom:1px solid #263140; vertical-align:top; }
th { color:#8b98a5; font-weight:600; }
input, select, textarea, button { background:#0f1620; border:1px solid #263140; color:#e6edf3; padding:8px 10px; border-radius:6px; font-size:14px; font-family:inherit; }
textarea { width:100%; min-height:80px; }
button { background:#2481cc; border:none; cursor:pointer; }
button.danger { background:#e5484d; }
button.small { padding:4px 8px; font-size:12px; margin-right:4px; }
.form-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.form-grid label { display:block; font-size:12px; color:#8b98a5; margin-bottom:4px; }
.form-grid > div { display:flex; flex-direction:column; }
.badge { padding:2px 8px; border-radius:6px; font-size:12px; }
.badge.on { background:#132d1c; color:#3fb950; }
.badge.off { background:#3d1a1c; color:#e5484d; }
.login-box { max-width:340px; margin:80px auto; background:#18222d; padding:30px; border-radius:12px; border:1px solid #263140; }
.login-box input { width:100%; margin-bottom:12px; }
.login-box button { width:100%; padding:10px; }
</style>
"""

NAV = """
<div class="topbar">
  <h1>NCS <span style="color:#8b98a5;font-weight:400;">| Oto Reklam Paneli</span></h1>
  <div>
    <a href="/ilan-panel/">Ilanlar</a>
    <a href="/ilan-panel/logs">Gonderim Loglari</a>
    <a href="/ilan-panel/logout">Cikis</a>
  </div>
</div>
"""

LOGIN_HTML = STYLE + """
<div class="login-box">
  <h2 style="text-align:center;color:#2481cc;">Oto Reklam Paneli</h2>
  {% if error %}<p style="color:#e5484d;text-align:center;">{{ error }}</p>{% endif %}
  <form method="post">
    <input type="text" name="username" placeholder="Kullanici adi" required>
    <input type="password" name="password" placeholder="Sifre" required>
    <button type="submit">Giris Yap</button>
  </form>
</div>
"""

LIST_HTML = STYLE + NAV + """
<div class="container">
  <div class="panel-box">
    <h3 style="margin-top:0;">Yeni Ilan Olustur</h3>
    <form method="post" action="/ilan-panel/create" enctype="multipart/form-data">
      <div class="form-grid">
        <div><label>Baslik</label><input type="text" name="title" required></div>
        <div><label>Gorsel (opsiyonel)</label><input type="file" name="image"></div>
        <div style="grid-column:1/3;"><label>Metin</label><textarea name="text" required></textarea></div>
        <div><label>Buton Metni (opsiyonel)</label><input type="text" name="button_text"></div>
        <div><label>Buton Linki (opsiyonel)</label><input type="text" name="button_url"></div>
        <div style="grid-column:1/3;"><label>Hedef Grup ID'leri (virgulle ayirin, orn: -1001234,-1005678)</label><input type="text" name="target_chat_ids" value="-1003768511628" required></div>
        <div><label>Baslangic Tarihi</label><input type="date" name="start_date" required></div>
        <div><label>Bitis Tarihi (opsiyonel)</label><input type="date" name="end_date"></div>
        <div><label>Ilk Gonderim Saati (SS:DD)</label><input type="text" name="send_time" placeholder="09:00" required></div>
        <div><label>Kac Saatte Bir Tekrarlansin</label><input type="number" step="0.5" name="repeat_hours" placeholder="4" required></div>
        <div><label>Toplam Kac Kez Gonderilsin (bos=sinirsiz)</label><input type="number" name="total_limit" placeholder="bos birakilabilir"></div>
      </div>
      <br>
      <button type="submit">Ilani Kaydet</button>
    </form>
  </div>

  <div class="panel-box">
    <h3 style="margin-top:0;">Ilanlar ({{ ads|length }})</h3>
    <table>
      <tr><th>Baslik</th><th>Hedef</th><th>Zaman/Tekrar</th><th>Gonderim</th><th>Durum</th><th>Islem</th></tr>
      {% for ad in ads %}
      <tr>
        <td>{{ ad.title }}</td>
        <td style="font-size:11px;">{{ ad.target_chat_ids }}</td>
        <td>{{ ad.send_time }} / her {{ ad.repeat_hours }}sa</td>
        <td>{{ ad.sent_count }}{% if ad.total_limit %} / {{ ad.total_limit }}{% endif %}</td>
        <td><span class="badge {{ 'on' if ad.is_active else 'off' }}">{{ 'Aktif' if ad.is_active else 'Pasif' }}</span></td>
        <td>
          <a href="/ilan-panel/edit/{{ ad.id }}"><button class="small" type="button">Duzenle</button></a>
          <form method="post" action="/ilan-panel/toggle/{{ ad.id }}" style="display:inline;"><button class="small" type="submit">Ac/Kapat</button></form>
          <form method="post" action="/ilan-panel/send-now/{{ ad.id }}" style="display:inline;"><button class="small" type="submit">Simdi Gonder</button></form>
          <form method="post" action="/ilan-panel/delete/{{ ad.id }}" style="display:inline;" onsubmit="return confirm('Silinsin mi?');"><button class="small danger" type="submit">Sil</button></form>
        </td>
      </tr>
      {% endfor %}
    </table>
  </div>
  <div style="text-align:center;padding:20px;color:#4a5568;font-size:12px;">NCS Oto Reklam Paneli &copy; 2026 &mdash; Nitro Core Systems</div>
</div>
"""

LOGS_HTML = STYLE + NAV + """
<div class="container">
  <div class="panel-box">
    <table>
      <tr><th>Zaman</th><th>Ilan</th><th>Hedef</th><th>Sonuc</th><th>Hata</th></tr>
      {% for l in logs %}
      <tr>
        <td>{{ l.time_str }}</td>
        <td>{{ l.title or '-' }}</td>
        <td>{{ l.chat_id }}</td>
        <td><span class="badge {{ 'on' if l.success else 'off' }}">{{ 'basarili' if l.success else 'hata' }}</span></td>
        <td style="font-size:11px;max-width:300px;overflow:hidden;text-overflow:ellipsis;">{{ l.error or '-' }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  <div style="text-align:center;padding:20px;color:#4a5568;font-size:12px;">NCS Oto Reklam Paneli &copy; 2026 &mdash; Nitro Core Systems</div>
</div>
"""


EDIT_HTML = STYLE + NAV + """
<div class="container">
  <div class="panel-box">
    <h3 style="margin-top:0;">Ilani Duzenle: {{ ad.title }}</h3>
    <form method="post" action="/ilan-panel/edit/{{ ad.id }}" enctype="multipart/form-data">
      <div class="form-grid">
        <div><label>Baslik</label><input type="text" name="title" value="{{ ad.title }}" required></div>
        <div><label>Yeni Gorsel/Video Yukle (bos birakilirsa mevcut kalir)</label><input type="file" name="image"></div>
        <div style="grid-column:1/3;"><label>Metin</label><textarea name="text" required>{{ ad.text }}</textarea></div>
        <div><label>Buton Metni (opsiyonel)</label><input type="text" name="button_text" value="{{ ad.button_text or '' }}"></div>
        <div><label>Buton Linki (opsiyonel)</label><input type="text" name="button_url" value="{{ ad.button_url or '' }}"></div>
        <div style="grid-column:1/3;"><label>Hedef Grup ID'leri (virgulle ayirin)</label><input type="text" name="target_chat_ids" value="{{ target_ids_str }}" required></div>
        <div><label>Baslangic Tarihi</label><input type="date" name="start_date" value="{{ ad.start_date }}" required></div>
        <div><label>Bitis Tarihi (opsiyonel)</label><input type="date" name="end_date" value="{{ ad.end_date or '' }}"></div>
        <div><label>Ilk Gonderim Saati (SS:DD)</label><input type="text" name="send_time" value="{{ ad.send_time }}" required></div>
        <div><label>Kac Saatte Bir Tekrarlansin</label><input type="number" step="0.5" name="repeat_hours" value="{{ ad.repeat_hours }}" required></div>
        <div><label>Toplam Kac Kez Gonderilsin (bos=sinirsiz)</label><input type="number" name="total_limit" value="{{ ad.total_limit or '' }}"></div>
      </div>
      <br>
      <button type="submit">Degisiklikleri Kaydet</button>
      <a href="/ilan-panel/"><button type="button" style="background:#263140;">Iptal</button></a>
    </form>
  </div>
</div>
"""

def _fmt(rows, key='created_at'):
    for r in rows:
        r['time_str'] = datetime.datetime.fromtimestamp(r[key]).strftime('%d.%m %H:%M:%S')
    return rows

@panel_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        u, p = request.form.get('username', ''), request.form.get('password', '')
        with db.get_conn() as conn:
            row = conn.execute('SELECT * FROM admins WHERE username = ?', (u,)).fetchone()
        if row and check_password_hash(row['password_hash'], p):
            session['ad_logged_in'] = True
            return redirect(url_for('adpanel.ad_list'))
        error = 'Kullanici adi veya sifre hatali.'
    return render_template_string(LOGIN_HTML, error=error)

@panel_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('adpanel.login'))

@panel_bp.route('/')
@login_required
def ad_list():
    return render_template_string(LIST_HTML, ads=db.get_all_ads())

@panel_bp.route('/logs')
@login_required
def logs():
    return render_template_string(LOGS_HTML, logs=_fmt(db.get_logs(200), key='sent_at'))

@panel_bp.route('/create', methods=['POST'])
@login_required
def create():
    f = request.form
    image_path = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename:
            filename = secure_filename(file.filename)
            image_path = os.path.join(UPLOAD_DIR, f"{int(datetime.datetime.now().timestamp())}_{filename}")
            file.save(image_path)

    target_ids = [x.strip() for x in f.get('target_chat_ids', '').split(',') if x.strip()]

    db.create_ad({
        'title': f.get('title'),
        'image_path': image_path,
        'text': f.get('text'),
        'button_text': f.get('button_text') or None,
        'button_url': f.get('button_url') or None,
        'target_chat_ids': json.dumps(target_ids),
        'start_date': f.get('start_date'),
        'end_date': f.get('end_date') or None,
        'send_time': f.get('send_time'),
        'repeat_hours': float(f.get('repeat_hours')) if f.get('repeat_hours') else 24,
        'total_limit': int(f.get('total_limit')) if f.get('total_limit') else None,
    })
    return redirect(url_for('adpanel.ad_list'))

@panel_bp.route('/edit/<int:ad_id>', methods=['GET', 'POST'])
@login_required
def edit(ad_id):
    ad = db.get_ad(ad_id)
    if not ad:
        return redirect(url_for('adpanel.ad_list'))

    if request.method == 'POST':
        f = request.form
        image_path = ad.get('image_path')
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                image_path = os.path.join(UPLOAD_DIR, f"{int(datetime.datetime.now().timestamp())}_{filename}")
                file.save(image_path)

        target_ids = [x.strip() for x in f.get('target_chat_ids', '').split(',') if x.strip()]

        db.update_ad(ad_id, {
            'title': f.get('title'),
            'image_path': image_path,
            'text': f.get('text'),
            'button_text': f.get('button_text') or None,
            'button_url': f.get('button_url') or None,
            'target_chat_ids': json.dumps(target_ids),
            'start_date': f.get('start_date'),
            'end_date': f.get('end_date') or None,
            'send_time': f.get('send_time'),
            'repeat_hours': float(f.get('repeat_hours')) if f.get('repeat_hours') else 24,
            'total_limit': int(f.get('total_limit')) if f.get('total_limit') else None,
        })
        return redirect(url_for('adpanel.ad_list'))

    try:
        target_ids = json.loads(ad['target_chat_ids'])
        target_ids_str = ','.join(target_ids)
    except Exception:
        target_ids_str = ad['target_chat_ids']

    return render_template_string(EDIT_HTML, ad=ad, target_ids_str=target_ids_str)

@panel_bp.route('/toggle/<int:ad_id>', methods=['POST'])
@login_required
def toggle(ad_id):
    db.toggle_ad(ad_id)
    return redirect(url_for('adpanel.ad_list'))

@panel_bp.route('/delete/<int:ad_id>', methods=['POST'])
@login_required
def delete(ad_id):
    db.delete_ad(ad_id)
    return redirect(url_for('adpanel.ad_list'))

@panel_bp.route('/send-now/<int:ad_id>', methods=['POST'])
@login_required
def send_now(ad_id):
    import tg_ad_actions
    ad = db.get_ad(ad_id)
    if ad:
        try:
            target_ids = json.loads(ad['target_chat_ids'])
        except Exception:
            target_ids = []
        for chat_id in target_ids:
            ok, result = tg_ad_actions.send_ad(
                chat_id=chat_id, text=ad['text'], image_path=ad.get('image_path'),
                button_text=ad.get('button_text'), button_url=ad.get('button_url')
            )
            db.mark_sent(ad_id, chat_id, ok, None if ok else str(result))
    return redirect(url_for('adpanel.ad_list'))

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'oto-reklam-key')
db.init_db()
app.register_blueprint(panel_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
