
// ─── API Client ───────────────────────────────────────────────────────────────

const API = {
  async get(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(path, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async patch(path, body) {
    const r = await fetch(path, { method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async put(path, body) {
    const r = await fetch(path, { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async del(path) {
    const r = await fetch(path, { method:'DELETE' });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
};

// ─── Data Normalizers ─────────────────────────────────────────────────────────
// Transform API shapes → React UI shapes.

const norm = {
  // Channel: use name as routing ID; keep numeric _numId for PATCH/DELETE calls.
  channel(c) {
    return { id: c.name, _numId: c.id, name: c.name, description: '' };
  },

  // Message: API uses sender/content/timestamp; React uses author/body/ts.
  msg(m) {
    const d = new Date(m.timestamp);
    return {
      id: m.id,
      author: m.sender,
      role: m.role || 'user',
      body: m.content,
      ts: d.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' }),
      isSystemMsg: m.role === 'system',
    };
  },

  // Agent: map API status strings; use internal name as id for API calls.
  agent(a) {
    const statusMap = { active:'active', stopped:'offline', idle:'idle' };
    return {
      id: a.name,
      name: a.display_name || a.name,
      model: a.model || '—',
      role: a.role || 'developer',
      channel: a.channel || 'general',
      status: statusMap[a.status] || 'idle',
      lastSeen: a.last_seen ? new Date(a.last_seen).getTime() : Date.now(),
      color: a.color || '#58a6ff',
      pid: a.pid || null,
    };
  },

  // Task: API only has title/description/status/channel; extra fields default.
  task(t) {
    return {
      id: t.id,
      title: t.title,
      description: t.description || '',
      ac: '',
      priority: 'medium',
      status: (t.status || 'todo').replace(/-/g, '_'),
      assignee: null,
      reporter: 'user',
      channel: t.channel || 'general',
      labels: [],
      channelHistory: [t.channel || 'general'],
      createdAt: t.created_at ? new Date(t.created_at).getTime() : Date.now(),
      comments: [],
    };
  },

  // Role: API rules is string[]; React expects newline-joined string.
  role(r) {
    const rulesArr = Array.isArray(r.rules) ? r.rules : [];
    return {
      id: String(r.id || r.name),
      name: r.name,
      description: r.description || '',
      rules: rulesArr.join('\n'),
      maxActive: 4,
      current: 0,
    };
  },
};

// ─── Avatar helpers ────────────────────────────────────────────────────────────

const AVATAR_COLORS = ['#388bfd','#3fb950','#ffa657','#f85149','#bc8cff','#58a6ff','#ff7b72','#a371f7'];
function avatarColor(name) {
  let h = 0;
  for (let c of name) h = (h * 31 + c.charCodeAt(0)) % 8;
  return AVATAR_COLORS[h];
}
function initials(name) {
  return name.replace('-', ' ').split(' ').map(w => w[0]).join('').toUpperCase().slice(0,2);
}

// ─── Time helpers ─────────────────────────────────────────────────────────────

const ts = (offset) => {
  const d = new Date(Date.now() - offset);
  return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
};
const fullTs = (ms) => {
  const d = new Date(ms);
  return d.toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'});
};
const relativeTime = (ms) => {
  const diff = Date.now() - ms;
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff/60000)} min ago`;
  if (diff < 86400000) return `${Math.floor(diff/3600000)}h ago`;
  return `${Math.floor(diff/86400000)}d ago`;
};

// ─── Initial state (empty — loaded from API on boot) ─────────────────────────

const initialChannels = [];
const initialAgents   = [];
const initialRoles    = [];
const initialTasks    = [];
const initialMessages = {};

// ─── Shared Components ────────────────────────────────────────────────────────

const ROLE_COLORS = {
  developer: '#58a6ff',
  designer:  '#a371f7',
  qa:        '#ffa657',
  pm:        '#3fb950',
  user:      '#3fb950',
};

function Avatar({ name, size = 32, isUser = false }) {
  const bg = isUser ? '#3fb950' : avatarColor(name);
  const label = isUser ? 'U' : initials(name);
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: bg, display: 'flex', alignItems: 'center',
      justifyContent: 'center', flexShrink: 0,
      fontSize: size * 0.38, fontWeight: 700, color: '#fff',
      userSelect: 'none',
    }}>{label}</div>
  );
}

function RoleBadge({ role }) {
  const color = ROLE_COLORS[role] || '#8b949e';
  return (
    <span style={{
      background: color + '22', color, border: `1px solid ${color}44`,
      borderRadius: 4, padding: '1px 6px', fontSize: 11, fontWeight: 600,
      letterSpacing: '0.02em',
    }}>{role}</span>
  );
}

function StatusBadge({ status }) {
  const map = {
    todo:        { bg: '#58a6ff22', color: '#58a6ff', label: 'Todo' },
    in_progress: { bg: '#3fb95022', color: '#3fb950', label: 'In Progress' },
    blocked:     { bg: '#f8514922', color: '#f85149', label: 'Blocked' },
    done:        { bg: '#8b949e22', color: '#8b949e', label: 'Done' },
  };
  const s = map[status] || map.todo;
  return (
    <span style={{
      background: s.bg, color: s.color, border: `1px solid ${s.color}44`,
      borderRadius: 4, padding: '1px 7px', fontSize: 11, fontWeight: 600,
    }}>{s.label}</span>
  );
}

function PriorityDot({ priority }) {
  const map = { high: '#f85149', medium: '#ffa657', low: '#8b949e' };
  return <span style={{ display:'inline-block', width:8, height:8, borderRadius:'50%', background: map[priority]||'#8b949e', flexShrink:0 }} />;
}

function PriorityBadge({ priority }) {
  const map = { high: '#f85149', medium: '#ffa657', low: '#8b949e' };
  return (
    <span style={{ display:'flex', alignItems:'center', gap:4, fontSize:11, color: map[priority]||'#8b949e', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.04em' }}>
      <PriorityDot priority={priority} />{priority}
    </span>
  );
}

function LabelPill({ label }) {
  return (
    <span style={{
      background: '#30363d', color: '#8b949e', border: '1px solid #30363d',
      borderRadius: 4, padding: '1px 6px', fontSize: 11,
    }}>{label}</span>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = React.useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text).catch(()=>{});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button onClick={copy} title="Copy" style={{
      background: copied ? '#3fb95033' : 'transparent', border: 'none',
      color: copied ? '#3fb950' : '#8b949e', cursor: 'pointer',
      padding: '3px 6px', borderRadius: 4, fontSize: 11,
      transition: 'all 0.15s',
    }}>
      {copied ? '✓ Copied!' : (
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
          <path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 0 1 0 1.5h-1.5a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-1.5a.75.75 0 0 1 1.5 0v1.5A1.75 1.75 0 0 1 9.25 16h-7.5A1.75 1.75 0 0 1 0 14.25Z"/>
          <path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0 1 14.25 11h-7.5A1.75 1.75 0 0 1 5 9.25Zm1.75-.25a.25.25 0 0 0-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 0 0 .25-.25v-7.5a.25.25 0 0 0-.25-.25Z"/>
        </svg>
      )}
    </button>
  );
}

function AgentStatusDot({ status }) {
  const map = { active: '#3fb950', idle: '#8b949e', offline: '#f85149' };
  return <span style={{ display:'inline-block', width:8, height:8, borderRadius:'50%', background: map[status]||'#8b949e', boxShadow: status==='active' ? `0 0 6px ${map.active}` : 'none' }} />;
}

// Export everything
Object.assign(window, {
  API, norm,
  avatarColor, initials, relativeTime, fullTs, ts,
  ROLE_COLORS, AVATAR_COLORS,
  initialChannels, initialAgents, initialRoles, initialMessages, initialTasks,
  Avatar, RoleBadge, StatusBadge, PriorityDot, PriorityBadge, LabelPill, CopyButton, AgentStatusDot,
});
