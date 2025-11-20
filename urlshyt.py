from flask import Flask, request, redirect, render_template_string, g, url_for, flash
import sqlite3
import secrets
import string
import os
from datetime import datetime

DB_FILE = "url_shortener.db"
CODE_LEN = 6
ALPHABET = string.ascii_letters + string.digits

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

def open_db():
    conn = getattr(g, "_conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        g._conn = conn
    return conn

@app.teardown_appcontext
def close_db(err):
    conn = getattr(g, "_conn", None)
    if conn is not None:
        conn.close()

def create_db_if_missing():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("""
          CREATE TABLE urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            visits INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
          )
        """)
        conn.commit()
        conn.close()

def rand_code(n=CODE_LEN):
    return ''.join(secrets.choice(ALPHABET) for _ in range(n))

def make_code_unique():
    db = open_db()
    cur = db.cursor()
    for _ in range(30):
        c = rand_code()
        cur.execute("SELECT 1 FROM urls WHERE short_code = ?", (c,))
        if cur.fetchone() is None:
            return c
    while True:
        c = rand_code()
        cur.execute("SELECT 1 FROM urls WHERE short_code = ?", (c,))
        if cur.fetchone() is None:
            return c
        
INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Shortly — URL Shortener</title>
  <style>
    :root{
      --bg: #fbfbfc;
      --card: #ffffff;
      --muted: #6b7280;
      --accent: #2b6cb0;
      --accent-2: #2dd4bf;
      --shadow: 0 6px 18px rgba(15,23,42,0.06);
    }
    body{
      font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
      background: linear-gradient(180deg,#f6fbff 0%,var(--bg) 60%);
      color:#0f172a;
      margin:0;
      padding:2rem;
      display:flex;
      justify-content:center;
    }
    .wrap{
      width:100%;
      max-width:900px;
      background:transparent;
    }
    header{
      display:flex;
      align-items:center;
      gap:0.75rem;
      margin-bottom:1rem;
    }
    .logo{
      width:52px;height:52px;border-radius:10px;
      display:flex;align-items:center;justify-content:center;
      background:linear-gradient(135deg,var(--accent),var(--accent-2));
      color:white;font-weight:700;box-shadow:var(--shadow);
      font-size:20px;
    }
    h1{margin:0;font-size:1.25rem}
    p.lead{margin:0;color:var(--muted);font-size:0.95rem}

    .card{
      background:var(--card);
      border-radius:12px;
      box-shadow:var(--shadow);
      padding:1rem;
      margin-top:1rem;
    }

    form{display:flex;gap:0.5rem;align-items:center;flex-wrap:wrap}
    input[name="url"]{
      flex:1;
      min-width:220px;
      padding:0.7rem 0.9rem;
      border-radius:8px;
      border:1px solid #e6e9ef;
      outline:none;
      box-shadow:inset 0 1px 0 rgba(16,24,40,0.02);
      font-size:0.95rem;
    }
    button{
      background:linear-gradient(180deg,var(--accent),#1e40af);
      color:white;border:none;padding:0.62rem 0.95rem;border-radius:8px;
      cursor:pointer;font-weight:600;
      box-shadow:0 6px 12px rgba(43,108,176,0.12);
    }
    .note{color:var(--muted);font-size:0.9rem;margin-top:0.6rem}

    .result{
      margin-top:0.9rem;padding:0.6rem;border-radius:8px;
      background:linear-gradient(90deg, rgba(45,212,191,0.06), rgba(43,108,176,0.04));
      border:1px solid rgba(43,108,176,0.06);
      display:flex;gap:0.6rem;align-items:center;flex-wrap:wrap;
    }
    .result a{color:var(--accent);font-weight:600;text-decoration:none}

    table{width:100%;border-collapse:collapse;margin-top:1rem}
    thead th{font-size:0.85rem;color:var(--muted);text-align:left;padding:0.6rem 0.4rem;border-bottom:1px dashed #eef2f7}
    tbody tr{transition:background .12s ease}
    tbody tr:hover{background:#fbfdff}
    td{padding:0.65rem 0.4rem;border-bottom:1px solid #f3f5f8;font-size:0.95rem}
    .short-badge{
      display:inline-block;padding:0.28rem 0.5rem;border-radius:6px;
      background:#eef7ff;border:1px solid #e1f0ff;color:var(--accent);font-weight:600;font-size:0.9rem
    }
    .muted{color:var(--muted);font-size:0.9rem}
    @media (max-width:640px){
      input[name="url"]{width:100%}
      header{flex-direction:row;align-items:center}
      .logo{width:44px;height:44px}
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="logo">S</div>
      <div>
        <h1>Shortly</h1>
        <p class="lead">Make long links tiny and shareable — fast and private.</p>
      </div>
    </header>

    <div class="card">
      {% with msgs = get_flashed_messages() %}
        {% if msgs %}
          <div style="color:#b91c1c;margin-bottom:0.6rem;">
            {% for m in msgs %}• {{ m }}<br>{% endfor %}
          </div>
        {% endif %}
      {% endwith %}

      <form method="post" action="{{ url_for('shorten') }}">
        <input name="url" placeholder="Paste a full URL (include http:// or https://)" required>
        <button type="submit">Shorten 🔗</button>
      </form>
      <div class="note">Tip: paste URLs from any site. This tool stores short codes on your machine (SQLite).</div>

      {% if short_url %}
        <div class="result">
          <strong>Short URL:</strong>
          <a href="{{ short_url }}" target="_blank" rel="noopener">{{ short_url }}</a>
          <span class="muted"> — copy and share</span>
        </div>
      {% endif %}
    </div>

    <div class="card" style="margin-top:1rem">
      <h3 style="margin:0 0 0.5rem 0">Recent links</h3>
      <table>
        <thead>
          <tr><th>Short</th><th>Original</th><th>Visits</th><th>Created</th></tr>
        </thead>
        <tbody>
          {% for r in recent %}
            <tr>
              <td><span class="short-badge">{{ request.url_root }}{{ r['short_code'] }}</span></td>
              <td><a href="{{ r['original_url'] }}" target="_blank" rel="noopener">{{ r['original_url'] }}</a></td>
              <td class="muted">{{ r['visits'] }}</td>
              <td class="muted">{{ r['created_at'] }}</td>
            </tr>
          {% endfor %}
          {% if recent|length == 0 %}
            <tr><td colspan="4" class="muted">No links yet — shorten one above!</td></tr>
          {% endif %}
        </tbody>
      </table>
    </div>

    <p style="text-align:center;color:var(--muted);font-size:0.85rem;margin-top:1rem">
      Made with ❤️ — runs locally on your machine.
    </p>
  </div>
</body>
</html>
"""

STATS_HTML = """
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Link Stats</title>
  <style>
    body{font-family:Inter, Arial, sans-serif;background:#fbfbfc;color:#0f172a;margin:0;padding:2rem;display:flex;justify-content:center}
    .card{background:white;padding:1rem;border-radius:12px;box-shadow:0 10px 30px rgba(15,23,42,0.06);max-width:700px;width:100%}
    h1{margin:0 0 0.25rem 0;font-size:1.1rem}
    .meta{color:#6b7280;margin-bottom:0.9rem}
    ul{margin:0.6rem 0 0 1.1rem;color:#111827}
    a.back{display:inline-block;margin-top:0.9rem;color:#2563eb;text-decoration:none}
    .stat{display:flex;gap:1rem;align-items:center;margin-top:0.9rem}
    .count{background:linear-gradient(180deg,#eef2ff,#ffffff);padding:0.6rem 0.8rem;border-radius:10px;font-weight:700;color:#1e40af}
  </style>
</head>
<body>
  <div class="card">
    <h1>Stats for <span style="color:#0f172a">{{ code }}</span></h1>
    <div class="meta">Original link: <a href="{{ row['original_url'] }}" target="_blank" rel="noopener">{{ row['original_url'] }}</a></div>

    <div class="stat">
      <div class="count">{{ row['visits'] }}</div>
      <div class="muted">visits</div>
    </div>

    <ul>
      <li><strong>Created at:</strong> {{ row['created_at'] }}</li>
      <li><strong>Short link:</strong> <a href="{{ request.url_root }}{{ row['short_code'] }}">{{ request.url_root }}{{ row['short_code'] }}</a></li>
    </ul>

    <a class="back" href="{{ url_for('index') }}">← Back to home</a>
  </div>
</body>
</html>
"""


@app.route("/")
def index():
    db = open_db()
    cur = db.cursor()
    cur.execute("SELECT short_code, original_url, visits, created_at FROM urls ORDER BY id DESC LIMIT 20")
    recent = cur.fetchall()
    return render_template_string(INDEX_HTML, recent=recent, short_url=None)

@app.route("/shorten", methods=["POST"])
def shorten():
    original = request.form.get("url", "").strip()

    if not original:
        flash("Please enter a URL.")
        return redirect(url_for("index"))

    if not (original.startswith("http://") or original.startswith("https://")):
        flash("Please include http:// or https:// at the start.")
        return redirect(url_for("index"))

    db = open_db()
    cur = db.cursor()

    cur.execute("SELECT short_code FROM urls WHERE original_url = ?", (original,))
    found = cur.fetchone()
    if found:
        code = found["short_code"]
    else:
        code = make_code_unique()
        cur.execute(
            "INSERT INTO urls (short_code, original_url, created_at) VALUES (?, ?, ?)",
            (code, original, datetime.utcnow().isoformat())
        )
        db.commit()

    short_url = request.url_root.rstrip("/") + "/" + code
    cur.execute("SELECT short_code, original_url, visits, created_at FROM urls ORDER BY id DESC LIMIT 20")
    recent = cur.fetchall()
    return render_template_string(INDEX_HTML, recent=recent, short_url=short_url)

@app.route("/<code>")
def go(code):
    db = open_db()
    cur = db.cursor()
    cur.execute("SELECT original_url, visits FROM urls WHERE short_code = ?", (code,))
    row = cur.fetchone()
    if not row:
        return "Short URL not found", 404

    new_visits = row["visits"] + 1
    cur.execute("UPDATE urls SET visits = ? WHERE short_code = ?", (new_visits, code))
    db.commit()

    return redirect(row["original_url"])

@app.route("/stats/<code>")
def stats(code):
    db = open_db()
    cur = db.cursor()
    cur.execute("SELECT short_code, original_url, visits, created_at FROM urls WHERE short_code = ?", (code,))
    row = cur.fetchone()
    if not row:
        return "Not found", 404
    return render_template_string(STATS_HTML, code=code, row=row)

if __name__ == "__main__":
    create_db_if_missing()
    print("Server running on all device in the network...")
    app.run(host="0.0.0.0",port=5000, debug=True)
