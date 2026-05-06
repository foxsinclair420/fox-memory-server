import json
import os
import uuid
from datetime import datetime

from flask import Flask, jsonify, request, render_template_string
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            title TEXT,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Memory Bank</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #0f1117; --surface: #1a1d27; --surface2: #22263a;
      --border: #2e3248; --accent: #6c63ff; --accent-hover: #8b85ff;
      --accent-dim: rgba(108,99,255,0.15); --text: #e8eaf0;
      --text-muted: #7a7f9a; --red: #ff5c72; --red-dim: rgba(255,92,114,0.12);
      --green: #3ecf8e; --radius: 12px; --shadow: 0 4px 24px rgba(0,0,0,0.4);
    }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
    header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 24px; display: flex; align-items: center; justify-content: space-between; height: 64px; position: sticky; top: 0; z-index: 10; }
    .logo { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 700; }
    .logo-icon { width: 32px; height: 32px; background: var(--accent); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; }
    .count-badge { background: var(--accent-dim); color: var(--accent); font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 20px; border: 1px solid var(--accent); }
    .main { max-width: 800px; margin: 0 auto; padding: 32px 24px 80px; }
    .toolbar { display: flex; gap: 10px; margin-bottom: 24px; flex-wrap: wrap; }
    input, textarea { background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: var(--radius); padding: 10px 14px; font-size: 14px; font-family: inherit; outline: none; transition: border-color 0.15s; }
    input:focus, textarea:focus { border-color: var(--accent); }
    input::placeholder, textarea::placeholder { color: var(--text-muted); }
    .search-input { flex: 1; min-width: 180px; }
    button { cursor: pointer; border: none; border-radius: var(--radius); font-size: 14px; font-weight: 600; font-family: inherit; padding: 10px 18px; transition: background 0.15s; }
    .btn-primary { background: var(--accent); color: #fff; }
    .btn-primary:hover { background: var(--accent-hover); }
    .btn-ghost { background: var(--surface2); color: var(--text); border: 1px solid var(--border); }
    .btn-ghost:hover { border-color: var(--accent); color: var(--accent); }
    .btn-danger { background: var(--red-dim); color: var(--red); border: 1px solid transparent; }
    .btn-danger:hover { border-color: var(--red); }
    .btn-icon { padding: 6px 10px; font-size: 13px; }
    .new-card { background: var(--surface); border: 1px solid var(--accent); border-radius: var(--radius); padding: 20px; margin-bottom: 24px; display: none; flex-direction: column; gap: 12px; box-shadow: var(--shadow); }
    .new-card.open { display: flex; }
    .new-card input, .new-card textarea { width: 100%; }
    .new-card textarea { resize: vertical; min-height: 90px; }
    .form-row { display: flex; gap: 10px; flex-wrap: wrap; }
    .form-row input { flex: 1; min-width: 140px; }
    .section-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); font-weight: 600; margin-bottom: 12px; }
    .memory-list { display: flex; flex-direction: column; gap: 12px; }
    .memory-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px 20px; transition: border-color 0.15s, box-shadow 0.15s; }
    .memory-card:hover { border-color: var(--accent); box-shadow: 0 2px 16px rgba(108,99,255,0.12); }
    .card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 8px; }
    .card-title { font-size: 15px; font-weight: 600; line-height: 1.4; }
    .card-actions { display: flex; gap: 6px; flex-shrink: 0; opacity: 0; transition: opacity 0.15s; }
    .memory-card:hover .card-actions { opacity: 1; }
    .card-content { font-size: 14px; color: var(--text-muted); line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
    .card-footer { margin-top: 12px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .tag { font-size: 11px; font-weight: 600; background: var(--accent-dim); color: var(--accent); padding: 2px 8px; border-radius: 20px; border: 1px solid var(--accent); cursor: pointer; }
    .card-meta { font-size: 11px; color: var(--text-muted); margin-left: auto; }
    .edit-form { display: none; flex-direction: column; gap: 10px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }
    .edit-form.open { display: flex; }
    .edit-form input, .edit-form textarea { width: 100%; }
    .edit-form textarea { min-height: 80px; resize: vertical; }
    .empty-state { text-align: center; padding: 64px 24px; color: var(--text-muted); }
    .empty-state .icon { font-size: 48px; margin-bottom: 16px; }
    .toast { position: fixed; bottom: 24px; right: 24px; background: var(--surface2); border: 1px solid var(--border); color: var(--text); padding: 12px 18px; border-radius: var(--radius); font-size: 13px; font-weight: 500; box-shadow: var(--shadow); opacity: 0; transform: translateY(8px); transition: opacity 0.2s, transform 0.2s; pointer-events: none; z-index: 100; }
    .toast.show { opacity: 1; transform: translateY(0); }
    .toast.success { border-color: var(--green); color: var(--green); }
    .toast.error { border-color: var(--red); color: var(--red); }
  </style>
</head>
<body>
<header>
  <div class="logo"><div class="logo-icon">🧠</div>Memory Bank</div>
  <span class="count-badge" id="countBadge">0 memories</span>
</header>
<div class="main">
  <div class="toolbar">
    <input class="search-input" type="text" id="searchInput" placeholder="Search memories…" oninput="onSearch()" />
    <input type="text" id="tagFilter" placeholder="Filter by tag…" style="width:140px" oninput="onSearch()" />
    <button class="btn-primary" onclick="toggleNew()">+ New memory</button>
  </div>
  <div class="new-card" id="newCard">
    <input type="text" id="newTitle" placeholder="Title (optional)" />
    <textarea id="newContent" placeholder="What do you want to remember? *"></textarea>
    <div class="form-row">
      <input type="text" id="newTags" placeholder="Tags (comma-separated)" />
      <button class="btn-primary" onclick="createMemory()">Save memory</button>
      <button class="btn-ghost" onclick="toggleNew()">Cancel</button>
    </div>
  </div>
  <div class="section-label" id="listLabel"></div>
  <div class="memory-list" id="memoryList">
    <div class="empty-state"><div class="icon">⏳</div><p>Loading…</p></div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
  let all = [];
  async function load() {
    try {
      const r = await fetch('/memories');
      const d = await r.json();
      all = d.memories || [];
      render(all);
    } catch { toast('Failed to load', 'error'); }
  }
  function onSearch() {
    const q = document.getElementById('searchInput').value.toLowerCase();
    const tag = document.getElementById('tagFilter').value.trim().toLowerCase();
    let f = all;
    if (q) f = f.filter(m => (m.title||'').toLowerCase().includes(q) || m.content.toLowerCase().includes(q));
    if (tag) f = f.filter(m => (m.tags||[]).some(t => t.toLowerCase().includes(tag)));
    render(f);
  }
  function render(list) {
    const el = document.getElementById('memoryList');
    const badge = document.getElementById('countBadge');
    const label = document.getElementById('listLabel');
    badge.textContent = all.length === 1 ? '1 memory' : `${all.length} memories`;
    label.textContent = list.length !== all.length ? `Showing ${list.length} of ${all.length}` : (all.length ? 'All memories' : '');
    if (!list.length) {
      el.innerHTML = `<div class="empty-state"><div class="icon">${!all.length ? '🧠' : '🔍'}</div><p>${!all.length ? 'No memories yet.' : 'No memories match your search.'}</p></div>`;
      return;
    }
    el.innerHTML = list.map(m => `
      <div class="memory-card">
        <div class="card-header">
          <div class="card-title">${esc(m.title || m.content.slice(0,60))}</div>
          <div class="card-actions">
            <button class="btn-ghost btn-icon" onclick="toggleEdit('${m.id}')">✏️ Edit</button>
            <button class="btn-danger btn-icon" onclick="del('${m.id}')">🗑️</button>
          </div>
        </div>
        ${m.title ? `<div class="card-content">${esc(m.content)}</div>` : ''}
        <div class="card-footer">
          ${(m.tags||[]).map(t=>`<span class="tag" onclick="filterTag('${esc(t)}')">${esc(t)}</span>`).join('')}
          <span class="card-meta">${ago(m.updated_at)}</span>
        </div>
        <div class="edit-form" id="edit-${m.id}">
          <input type="text" id="et-${m.id}" value="${esc(m.title||'')}" placeholder="Title (optional)" />
          <textarea id="ec-${m.id}">${esc(m.content)}</textarea>
          <div class="form-row">
            <input type="text" id="eg-${m.id}" value="${esc((m.tags||[]).join(', '))}" placeholder="Tags" />
            <button class="btn-primary btn-icon" onclick="saveEdit('${m.id}')">Save</button>
            <button class="btn-ghost btn-icon" onclick="toggleEdit('${m.id}')">Cancel</button>
          </div>
        </div>
      </div>`).join('');
  }
  function toggleNew() {
    const c = document.getElementById('newCard');
    c.classList.toggle('open');
    if (c.classList.contains('open')) document.getElementById('newContent').focus();
    else { ['newTitle','newContent','newTags'].forEach(id => document.getElementById(id).value=''); }
  }
  async function createMemory() {
    const title = document.getElementById('newTitle').value.trim();
    const content = document.getElementById('newContent').value.trim();
    const tags = document.getElementById('newTags').value.split(',').map(t=>t.trim()).filter(Boolean);
    if (!content) { toast('Content is required','error'); return; }
    try {
      const r = await fetch('/memories', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({title:title||undefined, content, tags}) });
      if (!r.ok) throw new Error();
      toggleNew(); await load(); toast('Memory saved','success');
    } catch { toast('Failed to save','error'); }
  }
  function toggleEdit(id) { document.getElementById(`edit-${id}`).classList.toggle('open'); }
  async function saveEdit(id) {
    const title = document.getElementById(`et-${id}`).value.trim();
    const content = document.getElementById(`ec-${id}`).value.trim();
    const tags = document.getElementById(`eg-${id}`).value.split(',').map(t=>t.trim()).filter(Boolean);
    if (!content) { toast('Content cannot be empty','error'); return; }
    try {
      const r = await fetch(`/memories/${id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({title:title||null, content, tags}) });
      if (!r.ok) throw new Error();
      await load(); toast('Updated','success');
    } catch { toast('Failed to update','error'); }
  }
  async function del(id) {
    if (!confirm('Delete this memory?')) return;
    try {
      await fetch(`/memories/${id}`, { method:'DELETE' });
      await load(); toast('Deleted');
    } catch { toast('Failed to delete','error'); }
  }
  function filterTag(tag) { document.getElementById('tagFilter').value=tag; onSearch(); }
  function ago(iso) {
    if (!iso) return '';
    const d = Math.floor((Date.now()-new Date(iso))/1000);
    if (d<60) return 'just now';
    if (d<3600) return `${Math.floor(d/60)}m ago`;
    if (d<86400) return `${Math.floor(d/3600)}h ago`;
    return new Date(iso).toLocaleDateString();
  }
  function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }
  let tt;
  function toast(msg, type='') {
    const el = document.getElementById('toast');
    el.textContent=msg; el.className=`toast show ${type}`;
    clearTimeout(tt); tt=setTimeout(()=>el.classList.remove('show'),2500);
  }
  load();
</script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/memories", methods=["GET"])
def list_memories():
    conn = get_db()
    cur = conn.cursor()
    tag = request.args.get("tag")
    search = request.args.get("search", "").lower()
    query = "SELECT * FROM memories"
    conditions = []
    params = []
    if search:
        conditions.append("(LOWER(content) ILIKE %s OR LOWER(title) ILIKE %s)")
        params += [f"%{search}%", f"%{search}%"]
    if tag:
        conditions.append("tags ILIKE %s")
        params.append(f"%{tag}%")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    items = []
    for row in rows:
        row = dict(row)
        row["tags"] = json.loads(row["tags"]) if row["tags"] else []
        row["metadata"] = json.loads(row["metadata"]) if row["metadata"] else {}
        # Truncate and clean content for LSL compatibility
        if row.get("content"):
            c = row["content"].encode("ascii", "ignore").decode("ascii")
            if len(c) > 400:
                c = c[:400] + "..."
            row["content"] = c
        items.append(row)
    return jsonify({"count": len(items), "memories": items})

@app.route("/memories", methods=["POST"])
def create_memory():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "'content' is required"}), 400
    memory_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"
    tags = json.dumps(data.get("tags", []))
    metadata = json.dumps(data.get("metadata", {}))
    title = (data.get("title") or "").strip() or None
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO memories (id, title, content, tags, metadata, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (memory_id, title, content, tags, metadata, now, now)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"id": memory_id, "title": title, "content": content, "tags": data.get("tags", []), "metadata": data.get("metadata", {}), "created_at": now, "updated_at": now}), 201

@app.route("/memories/<memory_id>", methods=["GET"])
def get_memory(memory_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM memories WHERE id = %s", (memory_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return jsonify({"error": "Memory not found"}), 404
    row = dict(row)
    row["tags"] = json.loads(row["tags"]) if row["tags"] else []
    row["metadata"] = json.loads(row["metadata"]) if row["metadata"] else {}
    return jsonify(row)

@app.route("/memories/<memory_id>", methods=["PUT"])
def update_memory(memory_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM memories WHERE id = %s", (memory_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return jsonify({"error": "Memory not found"}), 404
    data = request.get_json(silent=True)
    if not data:
        cur.close()
        conn.close()
        return jsonify({"error": "Request body must be valid JSON"}), 400
    row = dict(row)
    if "content" in data:
        row["content"] = (data["content"] or "").strip()
    if "title" in data:
        row["title"] = (data["title"] or "").strip() or None
    if "tags" in data:
        row["tags_list"] = data["tags"]
    else:
        row["tags_list"] = json.loads(row["tags"]) if row["tags"] else []
    now = datetime.utcnow().isoformat() + "Z"
    cur.execute(
        "UPDATE memories SET title=%s, content=%s, tags=%s, updated_at=%s WHERE id=%s",
        (row["title"], row["content"], json.dumps(row["tags_list"]), now, memory_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"id": memory_id, "title": row["title"], "content": row["content"], "tags": row["tags_list"], "updated_at": now})

@app.route("/memories/<memory_id>", methods=["DELETE"])
def delete_memory(memory_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM memories WHERE id = %s", (memory_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return jsonify({"error": "Memory not found"}), 404
    cur.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Memory deleted"})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Route not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False)
