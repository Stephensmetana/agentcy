
// ─── Chat View ────────────────────────────────────────────────────────────────

function LeftSidebar({ channels, activeChannel, onSelectChannel, onAddChannel, onRenameChannel, onDeleteChannel, navigate }) {
  const [adding, setAdding] = React.useState(false);
  const [newName, setNewName] = React.useState('');
  const [hoveredChannel, setHoveredChannel] = React.useState(null);
  const [menuOpen, setMenuOpen] = React.useState(null);
  const [renaming, setRenaming] = React.useState(null);
  const [renameVal, setRenameVal] = React.useState('');
  const [deleteConfirm, setDeleteConfirm] = React.useState(null);
  const inputRef = React.useRef(null);
  const renameRef = React.useRef(null);

  React.useEffect(() => { if (adding && inputRef.current) inputRef.current.focus(); }, [adding]);
  React.useEffect(() => { if (renaming && renameRef.current) renameRef.current.focus(); }, [renaming]);

  const startAdd = () => { setAdding(true); setNewName(''); };
  const confirmAdd = () => {
    const n = newName.trim().toLowerCase().replace(/\s+/g,'-');
    if (n) onAddChannel(n);
    setAdding(false); setNewName('');
  };
  const confirmRename = (id) => {
    const n = renameVal.trim().toLowerCase().replace(/\s+/g,'-');
    if (n) onRenameChannel(id, n);
    setRenaming(null);
  };

  return (
    <div style={{ width:220, minWidth:220, background:'var(--surface)', borderRight:'1px solid var(--border)', display:'flex', flexDirection:'column', height:'100%', flexShrink:0 }}>
      {/* Workspace header */}
      <div style={{ padding:'14px 16px', borderBottom:'1px solid var(--border)' }}>
        <div style={{ fontWeight:700, fontSize:15, color:'var(--text)', letterSpacing:'-0.01em' }}>Agentcy</div>
      </div>

      {/* Channels */}
      <div style={{ flex:1, overflowY:'auto', padding:'8px 0' }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'6px 16px 4px', marginTop:4 }}>
          <span style={{ fontSize:11, fontWeight:600, color:'var(--muted)', textTransform:'uppercase', letterSpacing:'0.06em' }}>Channels</span>
          <button onClick={startAdd} style={{ background:'none', border:'none', color:'var(--muted)', cursor:'pointer', fontSize:16, lineHeight:1, padding:'0 2px', borderRadius:3 }} title="Add channel">+</button>
        </div>

        {channels.map(ch => (
          <div key={ch.id}>
            {renaming === ch.id ? (
              <div style={{ padding:'2px 12px' }}>
                <input
                  ref={renameRef}
                  value={renameVal}
                  onChange={e => setRenameVal(e.target.value)}
                  onKeyDown={e => { if (e.key==='Enter') confirmRename(ch.id); if (e.key==='Escape') setRenaming(null); }}
                  onBlur={() => confirmRename(ch.id)}
                  style={{ width:'100%', background:'var(--surface2)', border:'1px solid var(--accent)', borderRadius:4, padding:'3px 7px', color:'var(--text)', fontSize:13, outline:'none', boxSizing:'border-box' }}
                />
              </div>
            ) : deleteConfirm === ch.id ? (
              <div style={{ margin:'2px 8px', background:'#f8514922', border:'1px solid #f8514944', borderRadius:6, padding:'8px 10px', fontSize:12 }}>
                <div style={{ color:'var(--text)', marginBottom:6 }}>Delete <strong>#{ch.name}</strong>? All messages will be lost.</div>
                <div style={{ display:'flex', gap:6 }}>
                  <button onClick={() => { onDeleteChannel(ch.id); setDeleteConfirm(null); }} style={{ background:'var(--danger)', border:'none', color:'#fff', borderRadius:4, padding:'3px 10px', cursor:'pointer', fontSize:12 }}>Confirm</button>
                  <button onClick={() => setDeleteConfirm(null)} style={{ background:'var(--surface2)', border:'1px solid var(--border)', color:'var(--muted)', borderRadius:4, padding:'3px 10px', cursor:'pointer', fontSize:12 }}>Cancel</button>
                </div>
              </div>
            ) : (
              <div
                onMouseEnter={() => setHoveredChannel(ch.id)}
                onMouseLeave={() => { setHoveredChannel(null); setMenuOpen(null); }}
                onClick={() => onSelectChannel(ch.id)}
                style={{
                  display:'flex', alignItems:'center', padding:'5px 16px', cursor:'pointer', position:'relative',
                  background: activeChannel===ch.id ? 'rgba(88,166,255,.15)' : hoveredChannel===ch.id ? 'rgba(255,255,255,.04)' : 'transparent',
                  borderRadius:0,
                }}
              >
                <span style={{ color:'var(--muted)', marginRight:6, fontSize:14 }}>#</span>
                <span style={{ flex:1, fontSize:13, color:'var(--text)', fontWeight: activeChannel===ch.id ? 600 : 400, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{ch.name}</span>
                {hoveredChannel===ch.id && (
                  <button
                    onClick={e => { e.stopPropagation(); setMenuOpen(menuOpen===ch.id ? null : ch.id); }}
                    style={{ background:'none', border:'none', color:'var(--muted)', cursor:'pointer', padding:'2px 4px', borderRadius:3, fontSize:14, lineHeight:1 }}
                  >⋯</button>
                )}
                {menuOpen===ch.id && (
                  <div style={{ position:'absolute', right:8, top:28, background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, zIndex:100, minWidth:110, boxShadow:'0 4px 16px #0008', overflow:'hidden' }}>
                    <button onClick={e => { e.stopPropagation(); setRenaming(ch.id); setRenameVal(ch.name); setMenuOpen(null); }} style={{ display:'block', width:'100%', textAlign:'left', background:'none', border:'none', color:'var(--text)', cursor:'pointer', padding:'8px 14px', fontSize:13 }}>Rename</button>
                    <button onClick={e => { e.stopPropagation(); setDeleteConfirm(ch.id); setMenuOpen(null); }} style={{ display:'block', width:'100%', textAlign:'left', background:'none', border:'none', color:'var(--danger)', cursor:'pointer', padding:'8px 14px', fontSize:13 }}>Delete</button>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {adding && (
          <div style={{ padding:'4px 12px' }}>
            <input
              ref={inputRef}
              value={newName}
              placeholder="new-channel"
              onChange={e => setNewName(e.target.value)}
              onKeyDown={e => { if (e.key==='Enter') confirmAdd(); if (e.key==='Escape') setAdding(false); }}
              onBlur={() => { if (newName.trim()) confirmAdd(); else setAdding(false); }}
              style={{ width:'100%', background:'var(--surface2)', border:'1px solid var(--accent)', borderRadius:4, padding:'4px 8px', color:'var(--text)', fontSize:13, outline:'none', boxSizing:'border-box' }}
            />
            <div style={{ fontSize:11, color:'var(--muted)', marginTop:3 }}>Enter to confirm · Esc to cancel</div>
          </div>
        )}
      </div>

      {/* Bottom nav */}
      <div style={{ borderTop:'1px solid var(--border)', padding:'8px 0' }}>
        {[['⚙', 'Settings', '/settings'],['📋', 'Tasks', '/tasks']].map(([icon, label, path]) => (
          <button key={path} onClick={() => navigate(path)} style={{ display:'flex', alignItems:'center', gap:8, width:'100%', background:'none', border:'none', color:'var(--muted)', cursor:'pointer', padding:'7px 16px', fontSize:13, textAlign:'left' }}>
            <span>{icon}</span><span>{label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function ChannelHeader({ channel, agents, navigate }) {
  const [exportOpen, setExportOpen] = React.useState(false);
  const agentCount = agents.filter(a => a.channel === channel.id && a.status !== 'offline').length;
  const ref = React.useRef(null);

  React.useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setExportOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div style={{ height:50, minHeight:50, background:'var(--surface)', borderBottom:'1px solid var(--border)', display:'flex', alignItems:'center', padding:'0 16px', gap:12, flexShrink:0 }}>
      <div style={{ flex:1 }}>
        <div style={{ fontWeight:700, fontSize:15, color:'var(--text)' }}>#{channel.name}</div>
        {channel.description && <div style={{ fontSize:12, color:'var(--muted)', marginTop:1 }}>{channel.description}</div>}
      </div>
      <div style={{ display:'flex', alignItems:'center', gap:10 }}>
        <div style={{ display:'flex', alignItems:'center', gap:5, background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'3px 10px', fontSize:12, color:'var(--muted)' }}>
          <span style={{ width:7, height:7, borderRadius:'50%', background:'#3fb950', display:'inline-block', boxShadow:'0 0 5px #3fb950' }}></span>
          {agentCount} agent{agentCount!==1?'s':''}
        </div>
        <div ref={ref} style={{ position:'relative' }}>
          <button onClick={() => setExportOpen(!exportOpen)} style={{ background:'var(--surface2)', border:'1px solid var(--border)', color:'var(--text)', cursor:'pointer', borderRadius:6, padding:'5px 12px', fontSize:12, display:'flex', alignItems:'center', gap:5 }}>
            Export <span style={{ color:'var(--muted)' }}>▾</span>
          </button>
          {exportOpen && (
            <div style={{ position:'absolute', right:0, top:'110%', background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, minWidth:180, zIndex:100, boxShadow:'0 4px 16px #0008', overflow:'hidden' }}>
              <a href={`/api/export?channel=${encodeURIComponent(channel.name)}`} onClick={() => setExportOpen(false)} style={{ display:'block', textAlign:'left', color:'var(--text)', padding:'9px 14px', fontSize:13, textDecoration:'none' }}>Export this channel</a>
              <a href="/api/export/all" onClick={() => setExportOpen(false)} style={{ display:'block', textAlign:'left', color:'var(--text)', padding:'9px 14px', fontSize:13, textDecoration:'none', borderTop:'1px solid var(--border)' }}>Export all channels</a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user';
  const isSystem = msg.isSystemMsg;
  const copyText = `[${msg.author}] (${msg.role}) — ${msg.ts}\n${msg.body}`;
  return (
    <div style={{ display:'flex', gap:10, padding:'6px 16px', position:'relative', background: isUser ? 'rgba(63,185,80,.04)' : 'transparent', borderLeft: isUser ? '2px solid var(--user)' : '2px solid transparent' }}>
      <div style={{ paddingTop:2 }}>
        <Avatar name={msg.author} size={32} isUser={isUser} />
      </div>
      <div style={{ flex:1, minWidth:0 }}>
        <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:2, flexWrap:'wrap' }}>
          <span style={{ fontWeight:700, fontSize:13, color: isUser ? 'var(--user)' : 'var(--text)' }}>{msg.author}</span>
          <RoleBadge role={msg.role} />
          <span style={{ fontSize:11, color:'var(--muted)', marginLeft:'auto' }}>{msg.ts}</span>
          <CopyButton text={copyText} />
        </div>
        <div style={{ fontSize:13, color: isSystem ? 'var(--muted)' : 'var(--text)', fontStyle: isSystem ? 'italic' : 'normal', lineHeight:1.55 }}>{msg.body}</div>
      </div>
    </div>
  );
}

function PinnedHumanStrip({ msg, onScrollTo }) {
  if (!msg) return null;
  return (
    <div onClick={onScrollTo} style={{ background:'rgba(63,185,80,.08)', borderLeft:'3px solid var(--user)', padding:'6px 14px', cursor:'pointer', display:'flex', alignItems:'center', gap:8, flexShrink:0 }}>
      <span style={{ fontSize:11, fontWeight:700, color:'var(--user)' }}>📌 {msg.author}</span>
      <span style={{ fontSize:12, color:'var(--muted)', flex:1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{msg.body}</span>
    </div>
  );
}

function TasksPanel({ tasks, channelId, navigate }) {
  const channelTasks = tasks.filter(t => t.channel === channelId && t.status !== 'done' && t.status !== 'blocked');
  const inProgress = channelTasks.filter(t => t.status === 'in_progress').sort((a,b) => {
    const p = {high:0,medium:1,low:2};
    return (p[a.priority]||1) - (p[b.priority]||1);
  });
  const todo = channelTasks.filter(t => t.status === 'todo').sort((a,b) => {
    const p = {high:0,medium:1,low:2};
    return (p[a.priority]||1) - (p[b.priority]||1);
  });
  const displayed = [...inProgress, ...todo].slice(0, 8);
  return (
    <React.Fragment>
      <div style={{ flex:1, overflowY:'auto', padding:'8px' }}>
        {displayed.length === 0 && (
          <div style={{ color:'var(--muted)', fontSize:12, textAlign:'center', padding:'20px 0' }}>No active tasks</div>
        )}
        {displayed.map(task => (
          <div key={task.id} onClick={() => navigate('/tasks/'+task.id)} style={{ background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'9px 10px', marginBottom:6, cursor:'pointer', transition:'border-color 0.15s' }}
            onMouseEnter={e => e.currentTarget.style.borderColor='var(--accent)'}
            onMouseLeave={e => e.currentTarget.style.borderColor='var(--border)'}
          >
            <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:4 }}>
              <PriorityDot priority={task.priority} />
              <span style={{ fontSize:12, color:'var(--muted)', fontFamily:'monospace' }}>#{task.id}</span>
              <StatusBadge status={task.status} />
            </div>
            <div style={{ fontSize:13, fontWeight:600, color:'var(--text)', lineHeight:1.4, marginBottom:4, display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical', overflow:'hidden' }}>{task.title}</div>
            <div style={{ fontSize:11, color:'var(--muted)' }}>{task.assignee || 'Unassigned'}</div>
          </div>
        ))}
      </div>
      <div style={{ borderTop:'1px solid var(--border)', padding:'8px', flexShrink:0 }}>
        <button onClick={() => navigate('/tasks?channel='+channelId)} style={{ width:'100%', background:'none', border:'1px solid var(--border)', color:'var(--muted)', cursor:'pointer', borderRadius:6, padding:'6px', fontSize:12 }}>View all tasks →</button>
      </div>
    </React.Fragment>
  );
}

function NotesPanel({ channelId }) {
  const [noteId, setNoteId] = React.useState(null);
  const [notes, setNotes]   = React.useState('');
  const [saved, setSaved]   = React.useState(true);
  const timerRef = React.useRef(null);

  // Load the most recent note for this channel from the API.
  React.useEffect(() => {
    setNoteId(null);
    setNotes('');
    setSaved(true);
    API.get(`/api/notes?channel=${encodeURIComponent(channelId)}`)
      .then(data => {
        if (data.length > 0) {
          const latest = data[data.length - 1];
          setNoteId(latest.id);
          setNotes(latest.content);
        }
      })
      .catch(() => {});
  }, [channelId]);

  const handleChange = (val) => {
    setNotes(val);
    setSaved(false);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      try {
        if (!val.trim()) {
          if (noteId) { await API.del(`/api/notes/${noteId}`); setNoteId(null); }
        } else if (noteId) {
          await API.patch(`/api/notes/${noteId}`, { content: val });
        } else {
          const n = await API.post('/api/notes', { channel: channelId, content: val });
          setNoteId(n.id);
        }
        setSaved(true);
      } catch { setSaved(false); }
    }, 800);
  };

  return (
    <React.Fragment>
      <div style={{ flex:1, display:'flex', flexDirection:'column', padding:'8px', gap:0, overflow:'hidden' }}>
        <div style={{ fontSize:11, color:'var(--muted)', marginBottom:6, lineHeight:1.4 }}>
          Notes are injected into agent context on every chat read. Use this to share persistent instructions, project context, or reference data with all agents in this channel.
        </div>
        <textarea
          value={notes}
          onChange={e => handleChange(e.target.value)}
          placeholder={`Channel-wide context for #${channelId}\n\ne.g. "This channel is for the Civitai redesign sprint. Always use Tailwind CSS. Design tokens are in /tokens/design.ts."`}
          style={{
            flex:1, background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6,
            padding:'9px 10px', color:'var(--text)', fontSize:12, lineHeight:1.6,
            resize:'none', outline:'none', fontFamily:'inherit',
          }}
          onFocus={e => e.target.style.borderColor='var(--accent)'}
          onBlur={e => e.target.style.borderColor='var(--border)'}
        />
      </div>
      <div style={{ padding:'6px 10px', borderTop:'1px solid var(--border)', display:'flex', alignItems:'center', gap:6, flexShrink:0 }}>
        <span style={{ fontSize:11, color: saved ? 'var(--user)' : 'var(--muted)' }}>
          {saved ? '✓ Saved' : '● Saving…'}
        </span>
        <span style={{ flex:1 }} />
        <span style={{ fontSize:11, color:'var(--muted)' }}>injected on read</span>
      </div>
    </React.Fragment>
  );
}

function TaskRail({ tasks, channelId, navigate }) {
  const [tab, setTab] = React.useState('tasks');

  const tabBtn = (id, label) => (
    <button
      onClick={() => setTab(id)}
      style={{
        flex:1, background:'none', border:'none',
        borderBottom: tab===id ? '2px solid var(--accent)' : '2px solid transparent',
        color: tab===id ? 'var(--accent)' : 'var(--muted)',
        cursor:'pointer', padding:'8px 0', fontSize:12,
        fontWeight: tab===id ? 600 : 400,
        transition:'all 0.15s',
      }}
    >{label}</button>
  );

  return (
    <div style={{ width:280, minWidth:280, background:'var(--surface)', borderLeft:'1px solid var(--border)', display:'flex', flexDirection:'column', height:'100%', flexShrink:0 }}>
      {/* Tab bar */}
      <div style={{ display:'flex', borderBottom:'1px solid var(--border)', flexShrink:0 }}>
        {tabBtn('tasks', 'Tasks')}
        {tabBtn('notes', 'Notes')}
        {tab === 'tasks' && (
          <button onClick={() => navigate('/tasks?channel='+channelId)} style={{ background:'none', border:'none', borderBottom:'2px solid transparent', color:'var(--accent)', cursor:'pointer', padding:'8px 10px', fontSize:12 }} title="Open board">→</button>
        )}
      </div>

      {tab === 'tasks'
        ? <TasksPanel tasks={tasks} channelId={channelId} navigate={navigate} />
        : <NotesPanel channelId={channelId} />
      }
    </div>
  );
}

function ComposeBar({ channelName, onSend }) {
  const [val, setVal] = React.useState('');
  const textRef = React.useRef(null);
  const send = () => {
    if (!val.trim()) return;
    onSend(val.trim());
    setVal('');
  };
  return (
    <div style={{ padding:'10px 14px', borderTop:'1px solid var(--border)', background:'var(--surface)', flexShrink:0 }}>
      <div style={{ display:'flex', gap:8, alignItems:'flex-end', background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:8, padding:'6px 10px' }}>
        <textarea
          ref={textRef}
          value={val}
          onChange={e => { setVal(e.target.value); e.target.style.height='auto'; e.target.style.height=Math.min(e.target.scrollHeight,110)+'px'; }}
          onKeyDown={e => { if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
          placeholder={`Message #${channelName}`}
          rows={1}
          style={{ flex:1, background:'transparent', border:'none', outline:'none', color:'var(--text)', fontSize:13, resize:'none', lineHeight:1.5, fontFamily:'inherit', minHeight:22, maxHeight:110 }}
        />
        <button onClick={send} disabled={!val.trim()} style={{ background: val.trim() ? 'var(--accent)' : 'var(--surface)', border:'1px solid '+(val.trim() ? 'var(--accent)' : 'var(--border)'), color: val.trim() ? '#fff' : 'var(--muted)', cursor: val.trim() ? 'pointer' : 'default', borderRadius:6, padding:'5px 14px', fontSize:13, fontWeight:600, transition:'all 0.15s', flexShrink:0 }}>Send</button>
      </div>
    </div>
  );
}

function SeenBy({ agents, channelId }) {
  const seenAgents = agents.filter(a => a.channel === channelId && a.status !== 'offline');
  if (seenAgents.length === 0) return null;
  return (
    <div style={{ display:'flex', alignItems:'center', gap:8, padding:'5px 14px', borderTop:'1px solid var(--border)', background:'var(--surface)', flexShrink:0 }}>
      <svg width="13" height="13" viewBox="0 0 16 16" fill="var(--muted)" style={{flexShrink:0}}>
        <path d="M8 2C4.5 2 1.5 4.5 0 8c1.5 3.5 4.5 6 8 6s6.5-2.5 8-6C14.5 4.5 11.5 2 8 2zm0 10a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm0-6a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"/>
      </svg>
      <span style={{ fontSize:11, color:'var(--muted)', flexShrink:0 }}>seen by</span>
      <div style={{ display:'flex', gap:5, flexWrap:'wrap' }}>
        {seenAgents.map(a => (
          <span key={a.id} style={{
            display:'inline-flex', alignItems:'center', gap:4,
            background: avatarColor(a.name) + '22',
            border: `1px solid ${avatarColor(a.name)}55`,
            color: avatarColor(a.name),
            borderRadius:10, padding:'1px 8px', fontSize:11, fontWeight:600,
          }}>
            <span style={{ width:6, height:6, borderRadius:'50%', background:avatarColor(a.name), display:'inline-block', flexShrink:0 }} />
            {a.name}
          </span>
        ))}
      </div>
    </div>
  );
}

function ChatView({ channels, activeChannelId, messages, tasks, agents, onSend, onAddChannel, onRenameChannel, onDeleteChannel, onSelectChannel, navigate }) {
  const channel = channels.find(c => c.id === activeChannelId || String(c._numId) === activeChannelId) || channels[0];
  const listRef = React.useRef(null);
  const msgs = channel ? (messages[channel.id] || []) : [];
  const pinnedMsg = msgs.filter(m => m.role === 'user').slice(-1)[0] || null;

  React.useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [msgs.length, channel?.id]);

  if (!channel) return (
    <div style={{ display:'flex', height:'100%', alignItems:'center', justifyContent:'center', color:'var(--muted)', fontSize:13 }}>
      Loading…
    </div>
  );

  return (
    <div style={{ display:'flex', height:'100%', overflow:'hidden' }}>
      <LeftSidebar channels={channels} activeChannel={channel.id} onSelectChannel={onSelectChannel} onAddChannel={onAddChannel} onRenameChannel={onRenameChannel} onDeleteChannel={onDeleteChannel} navigate={navigate} />
      <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
        <ChannelHeader channel={channel} agents={agents} navigate={navigate} />
        <PinnedHumanStrip msg={pinnedMsg} onScrollTo={() => { if(listRef.current) listRef.current.scrollTop=listRef.current.scrollHeight; }} />
        <div ref={listRef} style={{ flex:1, overflowY:'auto', padding:'8px 0' }}>
          {msgs.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
          {msgs.length === 0 && <div style={{ textAlign:'center', color:'var(--muted)', fontSize:13, padding:'40px 0' }}>No messages yet. Start the conversation!</div>}
        </div>
        <SeenBy agents={agents} channelId={channel.id} />
        <ComposeBar channelName={channel.name} onSend={onSend} />
      </div>
      <TaskRail tasks={tasks} channelId={channel.id} navigate={navigate} />
    </div>
  );
}

Object.assign(window, { ChatView });
