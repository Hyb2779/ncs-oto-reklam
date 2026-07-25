import sys
from werkzeug.security import generate_password_hash
import db

if len(sys.argv) != 3:
    print("Kullanim: python3 create_admin.py <kullanici_adi> <sifre>")
    sys.exit(1)

username, password = sys.argv[1], sys.argv[2]
db.init_db()
with db.get_conn() as conn:
    conn.execute('INSERT OR REPLACE INTO admins (username, password_hash) VALUES (?, ?)',
                 (username, generate_password_hash(password)))
print(f"Admin '{username}' olusturuldu.")
