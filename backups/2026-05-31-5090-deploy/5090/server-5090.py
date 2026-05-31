"""
Qwen3.6-35B-A3B API + Web Chat + User System + Points
One file, one port (6008). Everything in one process.

Features:
  - Web Chat UI (dark theme)
  - OpenAI-compatible /v1/chat/completions
  - User registration + API key auth
  - Points system: 50 tokens = 1 point, default 1000 points
  - Zero points → recharge page
  - Recharge code redemption
"""
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx, json, re, uvicorn, hashlib, secrets, sqlite3, os
from datetime import datetime

app = FastAPI(title="Qwen3.6-35B-A3B")
LLAMA_URL = "http://127.0.0.1:8080"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")
TOKENS_PER_POINT = 50  # 50 tokens = 1 point
DEFAULT_POINTS = 1000.0

security = HTTPBearer(auto_error=False)

# ============================================================
# Database
# ============================================================
def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            points REAL DEFAULT 1000.0,
            total_tokens_used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            api_key TEXT,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            points_consumed REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS recharge_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            points INTEGER NOT NULL,
            is_used INTEGER DEFAULT 0,
            used_by INTEGER,
            used_at TEXT
        );
    """)
    db.commit()
    db.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def generate_api_key() -> str:
    return "qwen-" + secrets.token_hex(24)

def get_user_by_api_key(api_key: str) -> dict | None:
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
    db.close()
    return dict(row) if row else None

def get_user_by_username(username: str) -> dict | None:
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    db.close()
    return dict(row) if row else None

def deduct_points(user_id: int, api_key: str, prompt_tokens: int, completion_tokens: int) -> dict:
    """Deduct points based on token usage. Returns {points_consumed, remaining}."""
    total_tokens = prompt_tokens + completion_tokens
    points_consumed = round(total_tokens / TOKENS_PER_POINT, 1)

    db = get_db()
    db.execute(
        "UPDATE users SET points = points - ?, total_tokens_used = total_tokens_used + ? WHERE id = ?",
        (points_consumed, total_tokens, user_id)
    )
    db.execute(
        "INSERT INTO usage_log (user_id, api_key, prompt_tokens, completion_tokens, total_tokens, points_consumed) VALUES (?,?,?,?,?,?)",
        (user_id, api_key, prompt_tokens, completion_tokens, total_tokens, points_consumed)
    )
    db.commit()

    row = db.execute("SELECT points FROM users WHERE id = ?", (user_id,)).fetchone()
    remaining = row["points"] if row else 0
    db.close()

    return {"points_consumed": points_consumed, "remaining": round(remaining, 1)}

# Initialize DB on startup
init_db()

# ============================================================
# HTML: Chat UI (dark theme)
# ============================================================
CHAT_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Qwen3.6 Chat</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f0f23;height:100vh;display:flex;flex-direction:column}
.header{background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;padding:14px 20px;text-align:center;font-size:16px;font-weight:600;display:flex;justify-content:space-between;align-items:center}
.header .points{font-size:13px;background:rgba(255,255,255,.2);padding:4px 12px;border-radius:20px;cursor:pointer}
.chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px}
.msg{max-width:80%;padding:12px 16px;border-radius:12px;line-height:1.6;word-break:break-word;font-size:15px;animation:in .2s ease}
.msg.user{align-self:flex-end;background:#6366f1;color:#fff;border-bottom-right-radius:4px}
.msg.assistant{align-self:flex-start;background:#1e1e3a;color:#e2e8f0;border-bottom-left-radius:4px;border:1px solid #2d2d5a}
.msg.error{align-self:center;background:#fef2f2;color:#dc2626;border:1px solid #fca5a5;font-size:14px}
@keyframes in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.input-bar{background:#1a1a2e;padding:12px 16px;display:flex;gap:10px;border-top:1px solid #2d2d5a}
.input-bar textarea{flex:1;resize:none;background:#0f0f23;color:#e2e8f0;border:1px solid #3f3f6a;border-radius:12px;padding:10px 14px;font-size:15px;outline:none;font-family:inherit;height:44px;max-height:120px;transition:border .2s}
.input-bar textarea:focus{border-color:#6366f1}
.input-bar button{background:#6366f1;color:#fff;border:none;border-radius:12px;padding:0 24px;font-size:15px;font-weight:500;cursor:pointer;white-space:nowrap;transition:background .2s}
.input-bar button:hover{background:#5558e6}
.input-bar button:disabled{background:#4a4a7a;cursor:not-allowed}
.login-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.8);display:flex;align-items:center;justify-content:center;z-index:100}
.login-box{background:#1a1a2e;padding:30px;border-radius:16px;width:360px;border:1px solid #2d2d5a}
.login-box h2{color:#e2e8f0;margin-bottom:20px;text-align:center}
.login-box input{width:100%;padding:12px;margin-bottom:12px;background:#0f0f23;color:#e2e8f0;border:1px solid #3f3f6a;border-radius:8px;font-size:14px;outline:none}
.login-box input:focus{border-color:#6366f1}
.login-box button{width:100%;padding:12px;background:#6366f1;color:#fff;border:none;border-radius:8px;font-size:15px;cursor:pointer;margin-top:8px}
.login-box button:hover{background:#5558e6}
.login-box .switch{text-align:center;margin-top:12px;color:#9ca3af;font-size:13px}
.login-box .switch a{color:#6366f1;cursor:pointer;text-decoration:none}
.typing{align-self:flex-start;padding:12px 16px;display:flex;gap:4px}
.typing span{width:7px;height:7px;background:#6366f1;border-radius:50%;animation:bounce 1.4s infinite}
.typing span:nth-child(2){animation-delay:.2s}
.typing span:nth-child(3){animation-delay:.4s}
@keyframes bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}
</style>
</head>
<body>
<div class="header">
  <span>Qwen3.6-35B-A3B</span>
  <span class="points" id="pointsBar" onclick="openRecharge()">🔑 登录</span>
</div>
<div class="chat" id="chat"></div>
<div class="input-bar">
  <textarea id="input" placeholder="登录后开始聊天..." rows="1" disabled
    onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}"></textarea>
  <button id="sendBtn" onclick="send()" disabled>发送</button>
</div>

<div class="login-overlay" id="loginOverlay">
  <div class="login-box" id="loginBox">
    <h2 id="loginTitle">登录</h2>
    <input type="text" id="loginUser" placeholder="用户名" />
    <input type="password" id="loginPass" placeholder="密码" />
    <button onclick="doLogin()" id="loginBtn">登录</button>
    <div class="switch">
      <a onclick="toggleMode()" id="switchLink">没有账号？注册</a>
    </div>
  </div>
</div>

<script>
let apiKey = localStorage.getItem('qwen_api_key') || '';
let points = parseFloat(localStorage.getItem('qwen_points') || '0');
let isRegister = false;
let messages = [];

const chat=document.getElementById('chat'),
      input=document.getElementById('input'),
      btn=document.getElementById('sendBtn'),
      pointsBar=document.getElementById('pointsBar'),
      loginOverlay=document.getElementById('loginOverlay'),
      loginTitle=document.getElementById('loginTitle'),
      loginBtn=document.getElementById('loginBtn'),
      switchLink=document.getElementById('switchLink'),
      loginUser=document.getElementById('loginUser'),
      loginPass=document.getElementById('loginPass');

function updateUI() {
    if (apiKey) {
        loginOverlay.style.display = 'none';
        input.disabled = false;
        btn.disabled = false;
        input.placeholder = '输入消息...';
        pointsBar.textContent = '💰 ' + points + ' 积分';
        document.getElementById('pointsBar').onclick = openRecharge;
    } else {
        loginOverlay.style.display = 'flex';
        input.disabled = true;
        btn.disabled = true;
        pointsBar.textContent = '🔑 登录';
    }
}

function openRecharge() {
    if (!apiKey) return updateUI();
    // Show recharge UI
    let overlay = document.createElement('div');
    overlay.className = 'login-overlay';
    overlay.innerHTML = '<div class="login-box"><h2>充值</h2>'
        + '<p style="color:#e2e8f0;text-align:center;margin-bottom:12px">当前积分: <b>'+points+'</b></p>'
        + '<input type="text" id="rechargeCode" placeholder="输入充值码" />'
        + '<button onclick="doRecharge()">兑换</button>'
        + '<p style="color:#9ca3af;text-align:center;margin-top:10px;font-size:12px">50 tokens = 1 积分</p>'
        + '<div class="switch"><a onclick="this.closest(\'.login-overlay\').remove()">关闭</a></div>'
        + '</div>';
    document.body.appendChild(overlay);
}

async function doRecharge() {
    let code = document.getElementById('rechargeCode').value.trim();
    if (!code) return alert('请输入充值码');
    try {
        let r = await fetch('/api/recharge', {
            method:'POST',
            headers:{'Content-Type':'application/json','Authorization':'Bearer '+apiKey},
            body:JSON.stringify({code})
        });
        let d = await r.json();
        if (r.ok) {
            points = d.points;
            localStorage.setItem('qwen_points', points);
            alert('充值成功！当前积分: ' + points);
            updateUI();
            document.querySelectorAll('.login-overlay').forEach(e=>e.remove());
        } else {
            alert('充值失败: ' + (d.detail || d.error || '未知错误'));
        }
    } catch(e) { alert('网络错误: '+e.message); }
}

function toggleMode() {
    isRegister = !isRegister;
    if (isRegister) {
        loginTitle.textContent = '注册';
        loginBtn.textContent = '注册';
        switchLink.textContent = '已有账号？登录';
    } else {
        loginTitle.textContent = '登录';
        loginBtn.textContent = '登录';
        switchLink.textContent = '没有账号？注册';
    }
}

async function doLogin() {
    let username = loginUser.value.trim();
    let password = loginPass.value.trim();
    if (!username || !password) return alert('请输入用户名和密码');

    let endpoint = isRegister ? '/api/register' : '/api/login';
    try {
        let r = await fetch(endpoint, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({username, password})
        });
        let d = await r.json();
        if (r.ok) {
            apiKey = d.api_key;
            points = d.points;
            localStorage.setItem('qwen_api_key', apiKey);
            localStorage.setItem('qwen_points', points);
            updateUI();
        } else {
            alert(d.detail || d.error || '操作失败');
        }
    } catch(e) { alert('网络错误: '+e.message); }
}

function addMsg(role, text) {
    let d = document.createElement('div');
    d.className = 'msg ' + role;
    d.textContent = text;
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
}

function showTyping() {
    let d = document.createElement('div');
    d.className = 'typing';
    d.id = 'typing';
    d.innerHTML = '<span></span><span></span><span></span>';
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
}

function hideTyping() {
    let e = document.getElementById('typing');
    if (e) e.remove();
}

async function send() {
    let t = input.value.trim();
    if (!t || !apiKey) return;
    input.value = '';
    btn.disabled = true;
    messages.push({role:'user', content:t});
    addMsg('user', t);
    showTyping();

    try {
        let r = await fetch('/v1/chat/completions', {
            method:'POST',
            headers:{'Content-Type':'application/json','Authorization':'Bearer '+apiKey},
            body:JSON.stringify({messages})
        });
        let d = await r.json();
        hideTyping();

        if (r.status == 402) {
            let msg = '❌ ' + (d.error || '积分不足') + ' — <a href="#" onclick="openRecharge();return false" style="color:#6366f1">立即充值</a>';
            addMsg('error', msg);
        } else if (d.choices && d.choices[0].message.content) {
            messages.push({role:'assistant', content:d.choices[0].message.content});
            addMsg('assistant', d.choices[0].message.content);
            // Update points from header
            let pr = r.headers.get('X-Points-Remaining');
            if (pr !== null && pr !== undefined) {
                points = parseFloat(pr);
                localStorage.setItem('qwen_points', points);
                updateUI();
            }
        } else {
            addMsg('error', '❌ 空回复，请重试');
        }
    } catch(e) {
        hideTyping();
        addMsg('error', '❌ 网络错误: '+e.message);
    }
    btn.disabled = false;
    input.focus();
}

updateUI();
if (apiKey && points > 0) {
    fetch('/api/me', {headers:{'Authorization':'Bearer '+apiKey}})
        .then(r=>r.json())
        .then(d=>{ if(d.points!==undefined){ points=d.points; localStorage.setItem('qwen_points',points); updateUI(); }})
        .catch(()=>{});
}
</script>
</body>
</html>"""

# ============================================================
# HTML: Recharge page (standalone)
# ============================================================
RECHARGE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>充值 - Qwen3.6 Chat</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f0f23;color:#e2e8f0;min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:#1a1a2e;padding:40px;border-radius:16px;width:400px;border:1px solid #2d2d5a;text-align:center}
.card h2{margin-bottom:8px}
.card .bal{font-size:48px;font-weight:700;color:#6366f1;margin:16px 0}
.card .sub{color:#9ca3af;font-size:14px;margin-bottom:24px}
.card input{width:100%;padding:14px;background:#0f0f23;color:#e2e8f0;border:1px solid #3f3f6a;border-radius:8px;font-size:16px;outline:none;text-align:center;letter-spacing:2px}
.card input:focus{border-color:#6366f1}
.card button{width:100%;padding:14px;background:#6366f1;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer;margin-top:12px;font-weight:600}
.card button:hover{background:#5558e6}
.card .info{color:#9ca3af;font-size:13px;margin-top:16px}
.card .back{margin-top:16px}.card .back a{color:#6366f1;text-decoration:none;font-size:14px}
</style>
</head>
<body>
<div class="card">
  <h2>⚡ 积分充值</h2>
  <div class="bal" id="balance">--</div>
  <div class="sub">当前积分余额</div>
  <input type="text" id="codeInput" placeholder="输入充值码" />
  <button onclick="redeem()">兑换</button>
  <div class="info">50 tokens = 1 积分 | 默认赠送 1000 积分</div>
  <div class="back"><a href="/">← 返回聊天</a></div>
</div>
<script>
let apiKey = localStorage.getItem('qwen_api_key') || '';
async function load() {
    if (!apiKey) { location.href='/'; return; }
    try {
        let r = await fetch('/api/me', {headers:{'Authorization':'Bearer '+apiKey}});
        let d = await r.json();
        document.getElementById('balance').textContent = d.points !== undefined ? d.points : '--';
    } catch(e) { document.getElementById('balance').textContent = '加载失败'; }
}
async function redeem() {
    let code = document.getElementById('codeInput').value.trim();
    if (!code) return alert('请输入充值码');
    try {
        let r = await fetch('/api/recharge', {
            method:'POST',
            headers:{'Content-Type':'application/json','Authorization':'Bearer '+apiKey},
            body:JSON.stringify({code})
        });
        let d = await r.json();
        if (r.ok) {
            alert('充值成功！+'+d.added+' 积分');
            localStorage.setItem('qwen_points', d.points);
            document.getElementById('balance').textContent = d.points;
            document.getElementById('codeInput').value = '';
        } else {
            alert('充值失败: ' + (d.detail || d.error));
        }
    } catch(e) { alert('网络错误: '+e.message); }
}
load();
</script>
</body>
</html>"""

# ============================================================
# Auth helpers
# ============================================================
async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict | None:
    """Extract user from Bearer token. Returns None if no valid token."""
    if not credentials:
        return None
    return get_user_by_api_key(credentials.credentials)

async def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    """Require valid Bearer token. Raises 401 if missing/invalid."""
    if not credentials:
        raise HTTPException(status_code=401, detail="请提供 API Key (Authorization: Bearer <key>)")
    user = get_user_by_api_key(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="无效的 API Key")
    if user["points"] <= 0:
        raise HTTPException(status_code=402, detail="积分不足，请充值")
    return user

# ============================================================
# Routes: Auth
# ============================================================
@app.post("/api/register")
async def register(req: dict):
    username = (req.get("username") or "").strip()
    password = (req.get("password") or "").strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(username) < 2 or len(username) > 32:
        raise HTTPException(status_code=400, detail="用户名长度 2-32 字符")
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="密码至少 4 个字符")

    if get_user_by_username(username):
        raise HTTPException(status_code=409, detail="用户名已存在")

    api_key = generate_api_key()
    pw_hash = hash_password(password)

    db = get_db()
    db.execute(
        "INSERT INTO users (username, password_hash, api_key, points) VALUES (?,?,?,?)",
        (username, pw_hash, api_key, DEFAULT_POINTS)
    )
    db.commit()
    db.close()

    return {
        "username": username,
        "api_key": api_key,
        "points": DEFAULT_POINTS,
        "message": "注册成功！请保存好你的 API Key"
    }

@app.post("/api/login")
async def login(req: dict):
    username = (req.get("username") or "").strip()
    password = (req.get("password") or "").strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    user = get_user_by_username(username)
    if not user or user["password_hash"] != hash_password(password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    return {
        "username": user["username"],
        "api_key": user["api_key"],
        "points": user["points"],
        "message": "登录成功"
    }

@app.get("/api/me")
async def me(user: dict = Depends(require_user)):
    return {
        "username": user["username"],
        "points": user["points"],
        "total_tokens_used": user["total_tokens_used"],
        "created_at": user["created_at"]
    }

@app.post("/api/recharge")
async def recharge(req: dict, user: dict = Depends(require_user)):
    code = (req.get("code") or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="请输入充值码")

    db = get_db()
    row = db.execute(
        "SELECT * FROM recharge_codes WHERE code = ? AND is_used = 0",
        (code,)
    ).fetchone()

    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="充值码无效或已使用")

    points_to_add = row["points"]
    db.execute(
        "UPDATE recharge_codes SET is_used = 1, used_by = ?, used_at = datetime('now') WHERE id = ?",
        (user["id"], row["id"])
    )
    db.execute(
        "UPDATE users SET points = points + ? WHERE id = ?",
        (points_to_add, user["id"])
    )
    db.commit()

    new_points = db.execute("SELECT points FROM users WHERE id = ?", (user["id"],)).fetchone()["points"]
    db.close()

    return {
        "added": points_to_add,
        "points": round(new_points, 1),
        "message": f"充值成功！获得 {points_to_add} 积分"
    }

@app.get("/api/usage")
async def usage(user: dict = Depends(require_user)):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM usage_log WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        (user["id"],)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]

# ============================================================
# Routes: Pages
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def index():
    return CHAT_HTML

@app.get("/recharge", response_class=HTMLResponse)
async def recharge_page():
    return RECHARGE_HTML

@app.get("/health")
async def health():
    return {"status": "ok", "db": os.path.exists(DB_PATH)}

# ============================================================
# Routes: Chat API (with points)
# ============================================================
SYSTEM_DEFAULT = "You are Qwen, a helpful assistant created by Alibaba. Answer directly without any thinking process, analysis, or reasoning. Output ONLY the final answer."

@app.post("/v1/chat/completions")
async def chat_completions(req: dict, user: dict = Depends(require_user)):
    messages = list(req.get("messages", []))
    max_tokens = req.get("max_tokens", 4096)
    temperature = req.get("temperature", 0.7)

    # Check points before processing
    if user["points"] <= 0:
        return JSONResponse(
            status_code=402,
            content={
                "error": "积分不足，请充值",
                "recharge_url": "/recharge",
                "points": user["points"]
            }
        )

    has_system = any(m["role"] == "system" for m in messages)
    if not has_system:
        messages = [{"role": "system", "content": SYSTEM_DEFAULT}] + messages

    # Proxy to llama-server
    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.post(
            f"{LLAMA_URL}/v1/chat/completions",
            json={
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 0.95,
            },
            headers={"Content-Type": "application/json"}
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"llama error: {resp.status_code}")

        result = resp.json()
        choice = result.get("choices", [{}])[0]
        msg = choice.get("message", {})

        content = msg.get("content", "")

        # Fallback for empty content (thinking consumed all tokens)
        if not content or len(content.strip()) < 2:
            reasoning = msg.get("reasoning_content", "")
            if reasoning:
                final_match = re.search(
                    r'(?i)final\s+(?:selection|output|answer)[^:\n]*:\s*(.+?)(?:\n|$)',
                    reasoning
                )
                if final_match:
                    content = final_match.group(1).strip().strip('"')
                elif len(reasoning) > 0:
                    content = "[Thinking only, increase max_tokens]"

        # Deduct points based on token usage
        usage_info = result.get("usage", {})
        prompt_tokens = usage_info.get("prompt_tokens", 0)
        completion_tokens = usage_info.get("completion_tokens", 0)

        deduction = deduct_points(
            user["id"],
            user["api_key"],
            prompt_tokens,
            completion_tokens
        )

        response = JSONResponse(content={
            "id": "chatcmpl-local",
            "object": "chat.completion",
            "created": 0,
            "model": "Qwen3.6-35B-A3B-Uncensored",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content.strip()},
                "finish_reason": choice.get("finish_reason", "stop")
            }],
            "usage": usage_info,
            "points_consumed": deduction["points_consumed"],
            "points_remaining": deduction["remaining"],
        })

        response.headers["X-Points-Remaining"] = str(deduction["remaining"])
        response.headers["X-Points-Consumed"] = str(deduction["points_consumed"])
        return response

# ============================================================
# Admin: generate recharge codes (CLI only)
# ============================================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "gencode":
        points = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        db = get_db()
        codes = []
        for _ in range(count):
            code = "RCH-" + secrets.token_hex(8).upper()
            db.execute("INSERT INTO recharge_codes (code, points) VALUES (?,?)", (code, points))
            codes.append(code)
        db.commit()
        db.close()
        print(f"Generated {count} recharge code(s) worth {points} points each:")
        for c in codes:
            print(f"  {c}")
    else:
        print("Starting server on port 6008...")
        uvicorn.run(app, host="0.0.0.0", port=6008)
