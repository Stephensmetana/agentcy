
// ─── Tasks Board ─────────────────────────────────────────────────────────────

function StandaloneNav({ children, navigate, lastChannel }) {
  return (
    <div style={{ background:'var(--surface)', borderBottom:'1px solid var(--border)', padding:'0 20px', height:48, display:'flex', alignItems:'center', gap:8, flexShrink:0 }}>
      <span style={{ color:'var(--muted)', fontSize:13, cursor:'pointer' }} onClick={() => navigate('/channel/'+(lastChannel||'general'))}>Agentcy</span>
      <span style={{ color:'var(--border)' }}>›</span>
      {children}
      <div style={{ marginLeft:'auto' }}>
        <button onClick={() => navigate('/channel/'+(lastChannel||'general'))} style={{ background:'var(--surface2)', border:'1px solid var(--border)', color:'var(--muted)', cursor:'pointer', borderRadius:6, padding:'5px 12px', fontSize:12 }}>← Back to channel</button>
      </div>
    </div>
  );
}

function BoardTaskCard({ task, navigate }) {
  return (
    <div onClick={() => navigate('/tasks/'+task.id)}
      style={{ background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'10px', marginBottom:6, cursor:'pointer', transition:'border-color 0.15s' }}
      onMouseEnter={e => e.currentTarget.style.borderColor='var(--accent)'}
      onMouseLeave={e => e.currentTarget.style.borderColor='var(--border)'}
    >
      <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:5 }}>
        <span style={{ fontSize:11, color:'var(--muted)', fontFamily:'monospace' }}>#{task.id}</span>
        <PriorityDot priority={task.priority} />
      </div>
      <div style={{ fontSize:13, fontWeight:600, color:'var(--text)', lineHeight:1.4, marginBottom:6 }}>{task.title}</div>
      {task.labels.length > 0 && (
        <div style={{ display:'flex', flexWrap:'wrap', gap:4, marginBottom:6 }}>
          {task.labels.map(l => <LabelPill key={l} label={l} />)}
        </div>
      )}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginTop:4 }}>
        <span style={{ fontSize:11, color:'var(--muted)' }}>{task.assignee || 'Unassigned'}</span>
        <span onClick={e => { e.stopPropagation(); }} style={{ fontSize:11, color:'var(--accent)', cursor:'default' }}>#{task.channel}</span>
      </div>
    </div>
  );
}

function KanbanColumn({ title, status, tasks, navigate, onNewTask, showNew }) {
  const colors = { todo:'var(--accent)', in_progress:'var(--user)', blocked:'var(--danger)', done:'var(--muted)' };
  return (
    <div style={{ flex:1, minWidth:0, display:'flex', flexDirection:'column' }}>
      <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:10, padding:'0 2px' }}>
        <span style={{ fontSize:12, fontWeight:700, color:'var(--text)', textTransform:'uppercase', letterSpacing:'0.04em' }}>{title}</span>
        <span style={{ background:colors[status]+'22', color:colors[status], border:`1px solid ${colors[status]}44`, borderRadius:10, padding:'1px 8px', fontSize:11, fontWeight:700 }}>{tasks.length}</span>
      </div>
      <div style={{ flex:1, overflowY:'auto', paddingRight:4 }}>
        {tasks.map(t => <BoardTaskCard key={t.id} task={t} navigate={navigate} />)}
      </div>
      {showNew && (
        <button onClick={onNewTask} style={{ width:'100%', background:'none', border:'1px dashed var(--border)', color:'var(--muted)', cursor:'pointer', borderRadius:6, padding:'7px', fontSize:12, marginTop:4, transition:'all 0.15s' }}
          onMouseEnter={e => { e.currentTarget.style.borderColor='var(--accent)'; e.currentTarget.style.color='var(--accent)'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor='var(--border)'; e.currentTarget.style.color='var(--muted)'; }}
        >+ New Task</button>
      )}
    </div>
  );
}

function NewTaskModal({ channels, channelFilter, onSave, onCancel }) {
  const [form, setForm] = React.useState({ title:'', description:'', ac:'', priority:'medium', channel: channelFilter||channels[0]?.id||'', labels:'' });
  const set = (k,v) => setForm(f => ({...f,[k]:v}));
  const valid = form.title.trim() && form.channel;
  return (
    <div style={{ position:'fixed', inset:0, background:'#0009', zIndex:200, display:'flex', alignItems:'center', justifyContent:'center' }} onClick={onCancel}>
      <div style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:10, padding:'24px', width:480, boxShadow:'0 16px 48px #000a' }} onClick={e => e.stopPropagation()}>
        <h2 style={{ margin:'0 0 16px', fontSize:16, color:'var(--text)' }}>New Task</h2>
        {[['Title *', 'title', 'text'],['Labels (comma-separated)', 'labels', 'text']].map(([label, key, type]) => (
          <div key={key} style={{ marginBottom:12 }}>
            <label style={{ fontSize:12, color:'var(--muted)', display:'block', marginBottom:4 }}>{label}</label>
            <input type={type} value={form[key]} onChange={e => set(key, e.target.value)} style={{ width:'100%', background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'7px 10px', color:'var(--text)', fontSize:13, outline:'none', boxSizing:'border-box' }} />
          </div>
        ))}
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginBottom:12 }}>
          <div>
            <label style={{ fontSize:12, color:'var(--muted)', display:'block', marginBottom:4 }}>Priority</label>
            <select value={form.priority} onChange={e => set('priority', e.target.value)} style={{ width:'100%', background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'7px 10px', color:'var(--text)', fontSize:13, outline:'none' }}>
              {['high','medium','low'].map(p => <option key={p} value={p}>{p.charAt(0).toUpperCase()+p.slice(1)}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize:12, color:'var(--muted)', display:'block', marginBottom:4 }}>Channel</label>
            <select value={form.channel} onChange={e => set('channel', e.target.value)} style={{ width:'100%', background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'7px 10px', color:'var(--text)', fontSize:13, outline:'none' }}>
              {channels.map(c => <option key={c.id} value={c.id}>#{c.name}</option>)}
            </select>
          </div>
        </div>
        <div style={{ marginBottom:12 }}>
          <label style={{ fontSize:12, color:'var(--muted)', display:'block', marginBottom:4 }}>Description</label>
          <textarea value={form.description} onChange={e => set('description', e.target.value)} rows={3} style={{ width:'100%', background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'7px 10px', color:'var(--text)', fontSize:13, outline:'none', resize:'vertical', fontFamily:'inherit', boxSizing:'border-box' }} />
        </div>
        <div style={{ display:'flex', gap:8, justifyContent:'flex-end' }}>
          <button onClick={onCancel} style={{ background:'none', border:'1px solid var(--border)', color:'var(--muted)', cursor:'pointer', borderRadius:6, padding:'7px 16px', fontSize:13 }}>Cancel</button>
          <button onClick={() => valid && onSave(form)} disabled={!valid} style={{ background: valid ? 'var(--accent)' : 'var(--surface2)', border:'none', color: valid ? '#fff' : 'var(--muted)', cursor: valid ? 'pointer' : 'default', borderRadius:6, padding:'7px 16px', fontSize:13, fontWeight:600 }}>Create Task</button>
        </div>
      </div>
    </div>
  );
}

function TasksBoard({ tasks, channels, navigate, lastChannel, channelFilter, onNewTask }) {
  const [showNew, setShowNew] = React.useState(false);
  const [filter, setFilter] = React.useState(channelFilter || 'all');
  const statuses = ['todo','in_progress','blocked','done'];
  const labels = { todo:'Todo', in_progress:'In Progress', blocked:'Blocked', done:'Done' };

  const filtered = filter === 'all' ? tasks : tasks.filter(t => t.channel === filter);
  const sorted = (arr) => arr.sort((a,b) => { const p={high:0,medium:1,low:2}; return (p[a.priority]||1)-(p[b.priority]||1) || a.id-b.id; });

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', overflow:'hidden' }}>
      <StandaloneNav navigate={navigate} lastChannel={lastChannel}>
        <span style={{ fontSize:13, color:'var(--text)', fontWeight:600 }}>Tasks</span>
      </StandaloneNav>
      <div style={{ padding:'12px 20px', borderBottom:'1px solid var(--border)', display:'flex', alignItems:'center', gap:10, flexShrink:0 }}>
        <label style={{ fontSize:12, color:'var(--muted)' }}>Channel:</label>
        <select value={filter} onChange={e => setFilter(e.target.value)} style={{ background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'5px 10px', color:'var(--text)', fontSize:13, outline:'none' }}>
          <option value="all">All Channels</option>
          {channels.map(c => <option key={c.id} value={c.id}>#{c.name}</option>)}
        </select>
        <span style={{ fontSize:12, color:'var(--muted)', marginLeft:4 }}>{filtered.length} tasks</span>
      </div>
      <div style={{ flex:1, overflow:'hidden', padding:'16px 20px' }}>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:16, height:'100%' }}>
          {statuses.map(s => (
            <KanbanColumn key={s} title={labels[s]} status={s} tasks={sorted(filtered.filter(t => t.status===s))} navigate={navigate} showNew={s==='todo'} onNewTask={() => setShowNew(true)} />
          ))}
        </div>
      </div>
      {showNew && <NewTaskModal channels={channels} channelFilter={filter!=='all'?filter:null} onSave={(form) => { onNewTask(form); setShowNew(false); }} onCancel={() => setShowNew(false)} />}
    </div>
  );
}

// ─── Task Detail ─────────────────────────────────────────────────────────────

function TaskDetail({ taskId, tasks, channels, navigate, lastChannel, onUpdateTask, onDeleteTask }) {
  const task = tasks.find(t => t.id === parseInt(taskId));
  const [editMode, setEditMode] = React.useState(false);
  const [form, setForm] = React.useState(null);
  const [deleteConfirm, setDeleteConfirm] = React.useState(false);
  const [newComment, setNewComment] = React.useState('');

  React.useEffect(() => {
    if (task) setForm({ ...task, labels: task.labels.join(', ') });
  }, [task?.id]);

  if (!task || !form) return (
    <div style={{ display:'flex', flexDirection:'column', height:'100vh' }}>
      <StandaloneNav navigate={navigate} lastChannel={lastChannel}><span style={{ fontSize:13, color:'var(--text)' }}>Task not found</span></StandaloneNav>
      <div style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center', color:'var(--muted)' }}>Task #{taskId} not found.</div>
    </div>
  );

  const set = (k,v) => setForm(f => ({...f,[k]:v}));
  const save = () => { onUpdateTask({ ...form, labels: form.labels.split(',').map(s=>s.trim()).filter(Boolean) }); setEditMode(false); };
  const cancel = () => { setForm({ ...task, labels: task.labels.join(', ') }); setEditMode(false); };
  const addComment = () => {
    if (!newComment.trim()) return;
    const updated = { ...task, comments: [...task.comments, { id:'c'+Date.now(), author:'user', role:'user', body:newComment.trim(), createdAt:Date.now() }] };
    onUpdateTask(updated);
    setNewComment('');
  };

  const fieldInput = (label, key, multiline=false, readOnly=false) => (
    <div style={{ marginBottom:12 }}>
      <div style={{ fontSize:11, color:'var(--muted)', marginBottom:3, textTransform:'uppercase', letterSpacing:'0.04em' }}>{label}</div>
      {editMode && !readOnly ? (
        multiline
          ? <textarea value={form[key]} onChange={e => set(key,e.target.value)} rows={3} style={{ width:'100%', background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'6px 9px', color:'var(--text)', fontSize:13, outline:'none', resize:'vertical', fontFamily:'inherit', boxSizing:'border-box' }} />
          : <input value={form[key]||''} onChange={e => set(key,e.target.value)} style={{ width:'100%', background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'6px 9px', color:'var(--text)', fontSize:13, outline:'none', boxSizing:'border-box' }} />
      ) : (
        <div style={{ fontSize:13, color: form[key] ? 'var(--text)' : 'var(--muted)', whiteSpace:'pre-wrap' }}>{form[key] || '—'}</div>
      )}
    </div>
  );

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100vh', overflow:'hidden' }}>
      <StandaloneNav navigate={navigate} lastChannel={lastChannel}>
        <span style={{ fontSize:13, color:'var(--muted)', cursor:'pointer' }} onClick={() => navigate('/tasks')}>Tasks</span>
        <span style={{ color:'var(--border)' }}>›</span>
        <span style={{ fontSize:13, color:'var(--text)' }}>#{task.id}</span>
      </StandaloneNav>

      <div style={{ flex:1, overflowY:'auto', padding:'24px' }}>
        {/* Title row */}
        <div style={{ display:'flex', alignItems:'flex-start', gap:12, marginBottom:16 }}>
          <span style={{ fontSize:13, color:'var(--muted)', fontFamily:'monospace', paddingTop:3, flexShrink:0 }}>#{task.id}</span>
          {editMode
            ? <input value={form.title} onChange={e => set('title',e.target.value)} style={{ flex:1, background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'6px 10px', color:'var(--text)', fontSize:20, fontWeight:700, outline:'none' }} />
            : <h1 style={{ margin:0, fontSize:20, fontWeight:700, color:'var(--text)', flex:1 }}>{task.title}</h1>
          }
        </div>

        {/* Status / priority row */}
        <div style={{ display:'flex', gap:12, marginBottom:16, flexWrap:'wrap', alignItems:'center' }}>
          <div style={{ display:'flex', alignItems:'center', gap:6 }}>
            <span style={{ fontSize:12, color:'var(--muted)' }}>Status:</span>
            {editMode ? (
              <select value={form.status} onChange={e => set('status',e.target.value)} style={{ background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'4px 8px', color:'var(--text)', fontSize:12, outline:'none' }}>
                {['todo','in_progress','blocked','done'].map(s => <option key={s} value={s}>{s.replace('_',' ')}</option>)}
              </select>
            ) : <StatusBadge status={task.status} />}
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:6 }}>
            <span style={{ fontSize:12, color:'var(--muted)' }}>Priority:</span>
            {editMode ? (
              <select value={form.priority} onChange={e => set('priority',e.target.value)} style={{ background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'4px 8px', color:'var(--text)', fontSize:12, outline:'none' }}>
                {['high','medium','low'].map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            ) : <PriorityBadge priority={task.priority} />}
          </div>
        </div>

        {/* Meta row */}
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'8px 24px', background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:8, padding:'12px 16px', marginBottom:16, fontSize:12 }}>
          {[['Assignee', editMode ? <input value={form.assignee||''} onChange={e => set('assignee',e.target.value)} placeholder="Unassigned" style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:4, padding:'2px 6px', color:'var(--text)', fontSize:12, outline:'none', width:'100%' }} /> : (task.assignee||'Unassigned')],
            ['Reporter', task.reporter],
            ['Channel', <span style={{ color:'var(--accent)', cursor:'pointer' }} onClick={() => navigate('/channel/'+task.channel)}>#{task.channel}</span>],
            ['Created', fullTs(task.createdAt)],
            ['Labels', editMode ? <input value={form.labels||''} onChange={e => set('labels',e.target.value)} placeholder="label1, label2" style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:4, padding:'2px 6px', color:'var(--text)', fontSize:12, outline:'none', width:'100%' }} /> : (task.labels.length>0 ? task.labels.map((l,i)=><LabelPill key={i} label={l} />) : '—')],
          ].map(([label, val]) => (
            <div key={label}>
              <span style={{ color:'var(--muted)', textTransform:'uppercase', letterSpacing:'0.04em', fontSize:10 }}>{label}</span>
              <div style={{ color:'var(--text)', marginTop:2, display:'flex', gap:4, flexWrap:'wrap', alignItems:'center' }}>{val}</div>
            </div>
          ))}
        </div>

        {/* Description + Comments */}
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:20 }}>
          {/* Left — description */}
          <div>
            {fieldInput('Description', 'description', true)}
            {fieldInput('Acceptance Criteria', 'ac', true)}
          </div>
          {/* Right — comments */}
          <div>
            <div style={{ fontSize:11, color:'var(--muted)', marginBottom:8, textTransform:'uppercase', letterSpacing:'0.04em' }}>Comments</div>
            <div style={{ maxHeight:300, overflowY:'auto', marginBottom:12 }}>
              {task.comments.length === 0 && <div style={{ color:'var(--muted)', fontSize:12 }}>No comments yet.</div>}
              {task.comments.map(c => (
                <div key={c.id} style={{ borderLeft:`2px solid ${c.author==='user'?'var(--user)':'var(--border)'}`, paddingLeft:10, marginBottom:12 }}>
                  <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:3 }}>
                    <Avatar name={c.author} size={20} isUser={c.author==='user'} />
                    <span style={{ fontWeight:600, fontSize:12, color:'var(--text)' }}>{c.author}</span>
                    <RoleBadge role={c.role} />
                    <span style={{ fontSize:11, color:'var(--muted)', marginLeft:'auto' }}>{fullTs(c.createdAt)}</span>
                  </div>
                  <div style={{ fontSize:13, color:'var(--text)', lineHeight:1.5 }}>{c.body}</div>
                </div>
              ))}
            </div>
            <textarea value={newComment} onChange={e => setNewComment(e.target.value)} placeholder="Add a comment…" rows={3} style={{ width:'100%', background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'8px 10px', color:'var(--text)', fontSize:13, outline:'none', resize:'none', fontFamily:'inherit', boxSizing:'border-box', marginBottom:6 }} />
            <button onClick={addComment} disabled={!newComment.trim()} style={{ background:'var(--accent)', border:'none', color:'#fff', cursor:'pointer', borderRadius:6, padding:'6px 14px', fontSize:13, fontWeight:600, opacity: newComment.trim() ? 1 : 0.5 }}>Comment</button>
          </div>
        </div>

        {/* Channel history */}
        {task.channelHistory.length > 1 && (
          <div style={{ marginTop:16, padding:'10px 14px', background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6 }}>
            <span style={{ fontSize:11, color:'var(--muted)', textTransform:'uppercase', letterSpacing:'0.04em' }}>Channel History: </span>
            <span style={{ fontSize:13, color:'var(--text)' }}>{task.channelHistory.map(c=>'#'+c).join(' → ')}</span>
          </div>
        )}

        {/* Footer actions */}
        <div style={{ display:'flex', gap:8, marginTop:16, paddingTop:16, borderTop:'1px solid var(--border)', flexWrap:'wrap', alignItems:'center' }}>
          {editMode ? (
            <>
              <button onClick={save} style={{ background:'var(--accent)', border:'none', color:'#fff', cursor:'pointer', borderRadius:6, padding:'7px 16px', fontSize:13, fontWeight:600 }}>Save</button>
              <button onClick={cancel} style={{ background:'none', border:'1px solid var(--border)', color:'var(--muted)', cursor:'pointer', borderRadius:6, padding:'7px 16px', fontSize:13 }}>Cancel</button>
            </>
          ) : (
            <button onClick={() => setEditMode(true)} style={{ background:'var(--surface2)', border:'1px solid var(--border)', color:'var(--text)', cursor:'pointer', borderRadius:6, padding:'7px 16px', fontSize:13 }}>Edit</button>
          )}
          {deleteConfirm ? (
            <div style={{ display:'flex', alignItems:'center', gap:8, background:'#f8514922', border:'1px solid #f8514944', borderRadius:6, padding:'6px 12px' }}>
              <span style={{ fontSize:12, color:'var(--text)' }}>Delete task #{task.id}? This cannot be undone.</span>
              <button onClick={() => { onDeleteTask(task.id); navigate('/tasks'); }} style={{ background:'var(--danger)', border:'none', color:'#fff', cursor:'pointer', borderRadius:4, padding:'4px 10px', fontSize:12 }}>Confirm</button>
              <button onClick={() => setDeleteConfirm(false)} style={{ background:'none', border:'1px solid var(--border)', color:'var(--muted)', cursor:'pointer', borderRadius:4, padding:'4px 10px', fontSize:12 }}>Cancel</button>
            </div>
          ) : (
            <button onClick={() => setDeleteConfirm(true)} style={{ background:'none', border:'1px solid var(--danger)', color:'var(--danger)', cursor:'pointer', borderRadius:6, padding:'7px 16px', fontSize:13, marginLeft:'auto' }}>Delete</button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Settings Hub ─────────────────────────────────────────────────────────────

function SettingsHub({ navigate, lastChannel }) {
  const cards = [
    { title:'Agents', desc:'Manage running agents, spawn new ones', path:'/settings/agents', icon:'🤖' },
    { title:'Roles', desc:'Define and assign agent roles', path:'/settings/roles', icon:'🏷️' },
    { title:'Export', desc:'Download channel history as Markdown', path:'/settings/export', icon:'📤' },
  ];
  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100vh' }}>
      <StandaloneNav navigate={navigate} lastChannel={lastChannel}>
        <span style={{ fontSize:13, color:'var(--text)', fontWeight:600 }}>Settings</span>
      </StandaloneNav>
      <div style={{ flex:1, padding:'32px 24px' }}>
        <h1 style={{ margin:'0 0 24px', fontSize:22, color:'var(--text)' }}>Settings</h1>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:16, maxWidth:700 }}>
          {cards.map(c => (
            <div key={c.path} onClick={() => navigate(c.path)} style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:10, padding:'20px', cursor:'pointer', transition:'border-color 0.15s' }}
              onMouseEnter={e => e.currentTarget.style.borderColor='var(--accent)'}
              onMouseLeave={e => e.currentTarget.style.borderColor='var(--border)'}
            >
              <div style={{ fontSize:28, marginBottom:10 }}>{c.icon}</div>
              <div style={{ fontWeight:700, fontSize:15, color:'var(--text)', marginBottom:4 }}>{c.title}</div>
              <div style={{ fontSize:12, color:'var(--muted)' }}>{c.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Agent Row (inline-editable role + channel) ───────────────────────────────

function AgentRow({ agent, roles, channels, onUpdate, killConfirm, setKillConfirm, onKill }) {
  const tdStyle = { padding:'10px 12px', borderBottom:'1px solid var(--border)', verticalAlign:'middle' };

  const InlineSelect = ({ value, options, renderValue, onChange }) => {
    const [open, setOpen] = React.useState(false);
    const ref = React.useRef(null);
    React.useEffect(() => {
      if (!open) return;
      const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
      document.addEventListener('mousedown', handler);
      return () => document.removeEventListener('mousedown', handler);
    }, [open]);
    return (
      <div ref={ref} style={{ position:'relative', display:'inline-block' }}>
        <button onClick={() => setOpen(o => !o)} style={{
          background: open ? 'rgba(88,166,255,.12)' : 'transparent',
          border: `1px solid ${open ? 'var(--accent)' : 'transparent'}`,
          borderRadius:5, padding:'3px 7px 3px 5px', cursor:'pointer',
          display:'flex', alignItems:'center', gap:5, transition:'all 0.12s',
        }}
          onMouseEnter={e => { if (!open) e.currentTarget.style.borderColor='var(--border)'; }}
          onMouseLeave={e => { if (!open) e.currentTarget.style.borderColor='transparent'; }}
        >
          {renderValue(value)}
          <svg width="9" height="9" viewBox="0 0 10 10" fill="var(--muted)"><path d="M2 3.5l3 3 3-3"/></svg>
        </button>
        {open && (
          <div style={{ position:'absolute', top:'110%', left:0, background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:7, minWidth:130, zIndex:200, boxShadow:'0 6px 20px #000a', overflow:'hidden' }}>
            {options.map(opt => (
              <button key={opt.value} onClick={() => { onChange(opt.value); setOpen(false); }} style={{
                display:'flex', alignItems:'center', gap:8, width:'100%', background: opt.value===value ? 'rgba(88,166,255,.1)' : 'none',
                border:'none', color: opt.value===value ? 'var(--accent)' : 'var(--text)',
                cursor:'pointer', padding:'8px 12px', fontSize:13, textAlign:'left',
              }}>
                {opt.label}
                {opt.value===value && <span style={{ marginLeft:'auto', color:'var(--accent)', fontSize:11 }}>✓</span>}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  };

  const roleColor = ROLE_COLORS[agent.role] || '#8b949e';

  return (
    <tr style={{ transition:'background 0.1s' }}
      onMouseEnter={e => e.currentTarget.style.background='rgba(255,255,255,.025)'}
      onMouseLeave={e => e.currentTarget.style.background='transparent'}
    >
      <td style={tdStyle}><Avatar name={agent.name} size={28} /></td>
      <td style={tdStyle}><span style={{ fontWeight:600, color:'var(--text)', fontFamily:'monospace', fontSize:13 }}>{agent.name}</span></td>
      <td style={tdStyle}><span style={{ background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:4, padding:'2px 7px', fontSize:11, color:'var(--muted)', fontFamily:'monospace' }}>{agent.model}</span></td>
      <td style={tdStyle}>
        <InlineSelect
          value={agent.role}
          options={roles.map(r => ({ value: r.name, label: r.name }))}
          renderValue={v => (
            <span style={{ background: roleColor+'22', color: roleColor, border:`1px solid ${roleColor}44`, borderRadius:4, padding:'1px 6px', fontSize:11, fontWeight:600 }}>{v}</span>
          )}
          onChange={v => onUpdate({ ...agent, role: v })}
        />
      </td>
      <td style={tdStyle}>
        <InlineSelect
          value={agent.channel}
          options={channels.map(c => ({ value: c.id, label: '#' + c.name }))}
          renderValue={v => <span style={{ color:'var(--muted)', fontSize:12 }}>#{v}</span>}
          onChange={v => onUpdate({ ...agent, channel: v })}
        />
      </td>
      <td style={tdStyle}><span style={{ display:'flex', alignItems:'center', gap:6 }}><AgentStatusDot status={agent.status} /><span style={{ fontSize:12, color:'var(--muted)' }}>{agent.status}</span></span></td>
      <td style={tdStyle}><span style={{ fontSize:12, color:'var(--muted)', whiteSpace:'nowrap' }}>{relativeTime(agent.lastSeen)}</span></td>
      <td style={tdStyle}>
        {killConfirm === agent.id ? (
          <div style={{ display:'flex', gap:4, alignItems:'center' }}>
            <span style={{ fontSize:11, color:'var(--muted)', marginRight:2 }}>Kill?</span>
            <button onClick={() => { onKill(agent.id); setKillConfirm(null); }} style={{ background:'var(--danger)', border:'none', color:'#fff', cursor:'pointer', borderRadius:4, padding:'3px 8px', fontSize:11 }}>Yes</button>
            <button onClick={() => setKillConfirm(null)} style={{ background:'none', border:'1px solid var(--border)', color:'var(--muted)', cursor:'pointer', borderRadius:4, padding:'3px 8px', fontSize:11 }}>✕</button>
          </div>
        ) : (
          <button onClick={() => setKillConfirm(agent.id)} style={{ background:'none', border:'1px solid var(--danger)', color:'var(--danger)', cursor:'pointer', borderRadius:4, padding:'4px 10px', fontSize:11, whiteSpace:'nowrap' }}>Kill</button>
        )}
      </td>
    </tr>
  );
}

// ─── Settings Agents ──────────────────────────────────────────────────────────

function SettingsAgents({ agents, roles, channels, navigate, lastChannel, onKillAgent, onSpawnAgent, onUpdateAgent, onSaveTimeout, heartbeatTimeout }) {
  const [spawnOpen, setSpawnOpen] = React.useState(false);
  const [spawnTab, setSpawnTab] = React.useState(0);
  const [killConfirm, setKillConfirm] = React.useState(null);
  const [timeout, setTimeout2] = React.useState(heartbeatTimeout);
  const [ollamaStatus, setOllamaStatus] = React.useState(null);

  const defClaude = { model:'claude-haiku-4-5-20251001', role: roles[0]?.name||'', channel: channels[0]?.id||'', interval:5 };
  const defOllama = { url:'http://localhost:11434', model:'qwen3:14b', role:roles[0]?.name||'', channel:channels[0]?.id||'', interval:5 };
  const defCustom = { command:'', role:'', channel:channels[0]?.id||'' };
  const [claudeForm, setClaudeForm] = React.useState(defClaude);
  const [ollamaForm, setOllamaForm] = React.useState(defOllama);
  const [customForm, setCustomForm] = React.useState(defCustom);

  const tabs = ['Claude Code', 'Local LLM (Ollama)', 'Custom / Advanced'];

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', overflow:'hidden' }}>
      <StandaloneNav navigate={navigate} lastChannel={lastChannel}>
        <span style={{ fontSize:13, color:'var(--muted)', cursor:'pointer' }} onClick={() => navigate('/settings')}>Settings</span>
        <span style={{ color:'var(--border)' }}>›</span>
        <span style={{ fontSize:13, color:'var(--text)', fontWeight:600 }}>Agents</span>
      </StandaloneNav>
      <div style={{ flex:1, overflowY:'auto', padding:'24px' }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16 }}>
          <h2 style={{ margin:0, fontSize:18, color:'var(--text)' }}>Active Agents</h2>
          <button onClick={() => setSpawnOpen(!spawnOpen)} style={{ background:'var(--accent)', border:'none', color:'#fff', cursor:'pointer', borderRadius:6, padding:'7px 16px', fontSize:13, fontWeight:600 }}>Spawn New Agent</button>
        </div>

        {/* Agents table */}
        <div style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:8, overflow:'hidden', marginBottom:24 }}>
          <table style={{ width:'100%', borderCollapse:'collapse', fontSize:13 }}>
            <thead>
              <tr style={{ borderBottom:'1px solid var(--border)' }}>
                {['','Name','Model','Role','Channel','Status','Last Seen',''].map((h,i) => (
                  <th key={i} style={{ padding:'8px 12px', textAlign:'left', fontSize:11, color:'var(--muted)', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.04em', whiteSpace:'nowrap' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {agents.map(a => (
                <AgentRow key={a.id} agent={a} roles={roles} channels={channels} onUpdate={onUpdateAgent || (() => {})} killConfirm={killConfirm} setKillConfirm={setKillConfirm} onKill={onKillAgent} />
              ))}
              {agents.length === 0 && (
                <tr><td colSpan={8} style={{ padding:'20px', textAlign:'center', color:'var(--muted)' }}>No active agents.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Spawn panel */}
        {spawnOpen && (
          <div style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:8, padding:'20px', marginBottom:24 }}>
            <div style={{ display:'flex', gap:0, marginBottom:20, borderBottom:'1px solid var(--border)' }}>
              {tabs.map((t,i) => (
                <button key={i} onClick={() => setSpawnTab(i)} style={{ background:'none', border:'none', borderBottom: spawnTab===i ? '2px solid var(--accent)' : '2px solid transparent', color: spawnTab===i ? 'var(--accent)' : 'var(--muted)', cursor:'pointer', padding:'8px 14px', fontSize:13, fontWeight: spawnTab===i ? 600 : 400 }}>{t}</button>
              ))}
            </div>
            {spawnTab === 0 && (
              <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:12, alignItems:'end' }}>
                {[['Model', <select value={claudeForm.model} onChange={e => setClaudeForm(f=>({...f,model:e.target.value}))} style={selStyle}>
                  {['claude-haiku-4-5-20251001','claude-sonnet-4-6','claude-opus-4-7'].map(m=><option key={m} value={m}>{m}</option>)}
                </select>],
                ['Role', <select value={claudeForm.role} onChange={e => setClaudeForm(f=>({...f,role:e.target.value}))} style={selStyle}>
                  {roles.map(r=><option key={r.id} value={r.name}>{r.name}</option>)}
                </select>],
                ['Channel', <select value={claudeForm.channel} onChange={e => setClaudeForm(f=>({...f,channel:e.target.value}))} style={selStyle}>
                  {channels.map(c=><option key={c.id} value={c.id}>#{c.name}</option>)}
                </select>],
                ['Polling (s)', <input type="number" value={claudeForm.interval} onChange={e=>setClaudeForm(f=>({...f,interval:+e.target.value}))} style={inputStyle} />]].map(([l,el])=>(
                  <div key={l}><label style={{ fontSize:11, color:'var(--muted)', display:'block', marginBottom:4 }}>{l}</label>{el}</div>
                ))}
                <button onClick={() => { onSpawnAgent({type:'claude',...claudeForm}); setSpawnOpen(false); }} style={{ background:'var(--accent)', border:'none', color:'#fff', cursor:'pointer', borderRadius:6, padding:'8px 16px', fontSize:13, fontWeight:600, gridColumn:'span 1' }}>Spawn</button>
              </div>
            )}
            {spawnTab === 1 && (
              <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:12, alignItems:'end' }}>
                {[['Ollama URL', <div style={{display:'flex',gap:6}}><input value={ollamaForm.url} onChange={e=>setOllamaForm(f=>({...f,url:e.target.value}))} onBlur={()=>setOllamaStatus(Math.random()>.3?'ok':'fail')} style={{...inputStyle,flex:1}} /><span style={{paddingTop:8,fontSize:13}}>{ollamaStatus==='ok'?'✅':ollamaStatus==='fail'?'❌':'⬜'}</span></div>],
                ['Model Name', <input value={ollamaForm.model} onChange={e=>setOllamaForm(f=>({...f,model:e.target.value}))} style={inputStyle} />],
                ['Role', <select value={ollamaForm.role} onChange={e=>setOllamaForm(f=>({...f,role:e.target.value}))} style={selStyle}>{roles.map(r=><option key={r.id} value={r.name}>{r.name}</option>)}</select>],
                ['Channel', <select value={ollamaForm.channel} onChange={e=>setOllamaForm(f=>({...f,channel:e.target.value}))} style={selStyle}>{channels.map(c=><option key={c.id} value={c.id}>#{c.name}</option>)}</select>],
                ['Polling (s)', <input type="number" value={ollamaForm.interval} onChange={e=>setOllamaForm(f=>({...f,interval:+e.target.value}))} style={inputStyle} />],
                ].map(([l,el])=>(
                  <div key={l}><label style={{ fontSize:11, color:'var(--muted)', display:'block', marginBottom:4 }}>{l}</label>{el}</div>
                ))}
                <button onClick={() => { onSpawnAgent({type:'ollama',...ollamaForm}); setSpawnOpen(false); }} style={{ background:'var(--accent)', border:'none', color:'#fff', cursor:'pointer', borderRadius:6, padding:'8px 16px', fontSize:13, fontWeight:600 }}>Spawn</button>
              </div>
            )}
            {spawnTab === 2 && (
              <div style={{ display:'grid', gridTemplateColumns:'2fr 1fr 1fr auto', gap:12, alignItems:'end' }}>
                {[['Command', <textarea value={customForm.command} onChange={e=>setCustomForm(f=>({...f,command:e.target.value}))} rows={2} placeholder="python my_agent.py --channel general" style={{...inputStyle,resize:'none',fontFamily:'monospace'}} />],
                ['Role (optional)', <select value={customForm.role} onChange={e=>setCustomForm(f=>({...f,role:e.target.value}))} style={selStyle}><option value="">None</option>{roles.map(r=><option key={r.id} value={r.name}>{r.name}</option>)}</select>],
                ['Channel', <select value={customForm.channel} onChange={e=>setCustomForm(f=>({...f,channel:e.target.value}))} style={selStyle}>{channels.map(c=><option key={c.id} value={c.id}>#{c.name}</option>)}</select>],
                ].map(([l,el])=>(
                  <div key={l}><label style={{ fontSize:11, color:'var(--muted)', display:'block', marginBottom:4 }}>{l}</label>{el}</div>
                ))}
                <button onClick={() => { onSpawnAgent({type:'custom',...customForm}); setSpawnOpen(false); }} style={{ background:'var(--accent)', border:'none', color:'#fff', cursor:'pointer', borderRadius:6, padding:'8px 16px', fontSize:13, fontWeight:600 }}>Spawn</button>
              </div>
            )}
          </div>
        )}

        {/* System settings */}
        <div style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:8, padding:'16px 20px' }}>
          <h3 style={{ margin:'0 0 14px', fontSize:14, color:'var(--text)' }}>System Settings</h3>
          <div style={{ display:'flex', alignItems:'center', gap:10 }}>
            <label style={{ fontSize:13, color:'var(--text)' }}>Agent heartbeat timeout</label>
            <input type="number" value={timeout} onChange={e=>setTimeout2(+e.target.value)} style={{ ...inputStyle, width:70 }} />
            <span style={{ fontSize:12, color:'var(--muted)' }}>minutes</span>
            <button onClick={() => onSaveTimeout(timeout)} style={{ background:'var(--surface2)', border:'1px solid var(--border)', color:'var(--text)', cursor:'pointer', borderRadius:6, padding:'6px 14px', fontSize:13 }}>Save</button>
          </div>
          <div style={{ fontSize:11, color:'var(--muted)', marginTop:6 }}>Agents inactive longer than this are marked offline and their in-progress tasks revert to todo.</div>
        </div>
      </div>
    </div>
  );
}

const inputStyle = { width:'100%', background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'7px 9px', color:'var(--text)', fontSize:13, outline:'none', boxSizing:'border-box', fontFamily:'inherit' };
const selStyle = { ...inputStyle };

// ─── Settings Roles ───────────────────────────────────────────────────────────

function SettingsRoles({ roles, agents, navigate, lastChannel, onSaveRole, onDeleteRole }) {
  const [editing, setEditing] = React.useState(null);
  const [creating, setCreating] = React.useState(false);
  const emptyForm = { name:'', description:'', rules:'', maxActive:2 };
  const [form, setForm] = React.useState(emptyForm);
  const set = (k,v) => setForm(f=>({...f,[k]:v}));

  const startEdit = (r) => { setEditing(r.id); setCreating(false); setForm({ name:r.name, description:r.description, rules:r.rules, maxActive:r.maxActive }); };
  const startCreate = () => { setCreating(true); setEditing(null); setForm(emptyForm); };

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', overflow:'hidden' }}>
      <StandaloneNav navigate={navigate} lastChannel={lastChannel}>
        <span style={{ fontSize:13, color:'var(--muted)', cursor:'pointer' }} onClick={() => navigate('/settings')}>Settings</span>
        <span style={{ color:'var(--border)' }}>›</span>
        <span style={{ fontSize:13, color:'var(--text)', fontWeight:600 }}>Roles</span>
      </StandaloneNav>
      <div style={{ flex:1, overflowY:'auto', padding:'24px' }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16 }}>
          <h2 style={{ margin:0, fontSize:18, color:'var(--text)' }}>Roles</h2>
          <div style={{ display:'flex', gap:8 }}>
            <button onClick={() => {}} style={{ background:'var(--surface2)', border:'1px solid var(--border)', color:'var(--muted)', cursor:'pointer', borderRadius:6, padding:'6px 14px', fontSize:12 }}>Export roles.json</button>
            <button onClick={startCreate} style={{ background:'var(--accent)', border:'none', color:'#fff', cursor:'pointer', borderRadius:6, padding:'7px 14px', fontSize:13, fontWeight:600 }}>+ New Role</button>
          </div>
        </div>
        <div style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:8, overflow:'hidden' }}>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1.5fr 2fr auto auto auto', gap:0, fontSize:11, color:'var(--muted)', padding:'8px 14px', borderBottom:'1px solid var(--border)', textTransform:'uppercase', letterSpacing:'0.04em' }}>
            {['Name','Description','Rules','Max','Occupancy','Actions'].map(h=><div key={h}>{h}</div>)}
          </div>
          {roles.map(r => {
            const occupied = agents.filter(a => a.role===r.name).length;
            const inUse = occupied > 0;
            return (
              <React.Fragment key={r.id}>
                <div style={{ display:'grid', gridTemplateColumns:'1fr 1.5fr 2fr auto auto auto', gap:8, alignItems:'center', padding:'11px 14px', borderBottom:'1px solid var(--border)', fontSize:13 }}>
                  <span style={{ fontWeight:600, color:'var(--text)' }}>{r.name}</span>
                  <span style={{ color:'var(--muted)', fontSize:12 }}>{r.description}</span>
                  <span style={{ color:'var(--muted)', fontSize:12, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{r.rules.split('\n').join(' · ')}</span>
                  <span style={{ color:'var(--text)', fontSize:13 }}>{r.maxActive}</span>
                  <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                    <span style={{ fontSize:12, color:'var(--muted)' }}>{occupied}/{r.maxActive}</span>
                    <div style={{ width:40, height:5, background:'var(--surface2)', borderRadius:3, overflow:'hidden' }}>
                      <div style={{ width:`${Math.min(occupied/r.maxActive,1)*100}%`, height:'100%', background:'var(--accent)', borderRadius:3 }} />
                    </div>
                  </div>
                  <div style={{ display:'flex', gap:6 }}>
                    <button onClick={() => startEdit(r)} style={{ background:'none', border:'1px solid var(--border)', color:'var(--text)', cursor:'pointer', borderRadius:4, padding:'3px 9px', fontSize:11 }}>Edit</button>
                    <button onClick={() => !inUse && onDeleteRole(r.id)} title={inUse?'Agents are using this role':''} style={{ background:'none', border:`1px solid ${inUse?'var(--border)':'var(--danger)'}`, color: inUse?'var(--muted)':'var(--danger)', cursor:inUse?'not-allowed':'pointer', borderRadius:4, padding:'3px 9px', fontSize:11, opacity:inUse?0.5:1 }}>Delete</button>
                  </div>
                </div>
                {editing === r.id && <RoleForm form={form} set={set} onSave={() => { onSaveRole({...r,...form}); setEditing(null); }} onCancel={() => setEditing(null)} />}
              </React.Fragment>
            );
          })}
        </div>
        {creating && <div style={{ marginTop:12 }}><RoleForm form={form} set={set} onSave={() => { onSaveRole({id:'r'+Date.now(),...form,current:0}); setCreating(false); }} onCancel={() => setCreating(false)} /></div>}
      </div>
    </div>
  );
}

function RoleForm({ form, set, onSave, onCancel }) {
  return (
    <div style={{ background:'var(--surface2)', border:'1px solid var(--accent)', borderRadius:8, padding:'16px', margin:'0 0 4px' }}>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr auto', gap:12, marginBottom:12, alignItems:'start' }}>
        {[['Name','name'],['Description','description']].map(([l,k])=>(
          <div key={k}><label style={{ fontSize:11, color:'var(--muted)', display:'block', marginBottom:4 }}>{l}</label>
          <input value={form[k]} onChange={e=>set(k,e.target.value)} style={inputStyle} /></div>
        ))}
        <div><label style={{ fontSize:11, color:'var(--muted)', display:'block', marginBottom:4 }}>Max Active</label>
        <input type="number" value={form.maxActive} onChange={e=>set('maxActive',+e.target.value)} style={{...inputStyle,width:60}} /></div>
      </div>
      <div style={{ marginBottom:12 }}>
        <label style={{ fontSize:11, color:'var(--muted)', display:'block', marginBottom:4 }}>Rules (one per line)</label>
        <textarea value={form.rules} onChange={e=>set('rules',e.target.value)} rows={3} style={{...inputStyle,resize:'none'}} />
      </div>
      <div style={{ display:'flex', gap:8 }}>
        <button onClick={onSave} style={{ background:'var(--accent)', border:'none', color:'#fff', cursor:'pointer', borderRadius:6, padding:'6px 14px', fontSize:13, fontWeight:600 }}>Save</button>
        <button onClick={onCancel} style={{ background:'none', border:'1px solid var(--border)', color:'var(--muted)', cursor:'pointer', borderRadius:6, padding:'6px 14px', fontSize:13 }}>Cancel</button>
      </div>
    </div>
  );
}

// ─── Settings Export ──────────────────────────────────────────────────────────

function SettingsExport({ channels, messages, navigate, lastChannel }) {
  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', overflow:'hidden' }}>
      <StandaloneNav navigate={navigate} lastChannel={lastChannel}>
        <span style={{ fontSize:13, color:'var(--muted)', cursor:'pointer' }} onClick={() => navigate('/settings')}>Settings</span>
        <span style={{ color:'var(--border)' }}>›</span>
        <span style={{ fontSize:13, color:'var(--text)', fontWeight:600 }}>Export</span>
      </StandaloneNav>
      <div style={{ flex:1, overflowY:'auto', padding:'24px' }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16 }}>
          <h2 style={{ margin:0, fontSize:18, color:'var(--text)' }}>Export</h2>
          <a href="/api/export/all" style={{ background:'var(--accent)', border:'none', color:'#fff', borderRadius:6, padding:'7px 16px', fontSize:13, fontWeight:600, textDecoration:'none' }}>Export All</a>
        </div>
        <div style={{ background:'var(--surface)', border:'1px solid var(--border)', borderRadius:8, overflow:'hidden' }}>
          <div style={{ display:'grid', gridTemplateColumns:'1fr auto auto', gap:0, fontSize:11, color:'var(--muted)', padding:'8px 14px', borderBottom:'1px solid var(--border)', textTransform:'uppercase', letterSpacing:'0.04em' }}>
            {['Channel','Messages','Export'].map(h=><div key={h}>{h}</div>)}
          </div>
          {channels.map(c => {
            const count = (messages[c.id]||[]).length;
            return (
              <div key={c.id} style={{ display:'grid', gridTemplateColumns:'1fr auto auto', gap:16, alignItems:'center', padding:'11px 14px', borderBottom:'1px solid var(--border)', fontSize:13 }}>
                <span style={{ fontWeight:600, color:'var(--text)' }}>#{c.name}</span>
                <span style={{ color:'var(--muted)', fontSize:12 }}>{count} msgs</span>
                <a href={`/api/export?channel=${encodeURIComponent(c.name)}`} style={{ background:'var(--surface2)', border:'1px solid var(--border)', color:'var(--text)', borderRadius:6, padding:'5px 12px', fontSize:12, textDecoration:'none' }}>Download .md</a>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── Logs View ────────────────────────────────────────────────────────────────

function LogsView({ agents, navigate, lastChannel }) {
  const [logs, setLogs]       = React.useState({});
  const [loading, setLoading] = React.useState(true);

  const loadLogs = React.useCallback(async () => {
    setLoading(true);
    const results = {};
    await Promise.all(agents.map(async a => {
      try {
        const r = await fetch(`/api/agents/${encodeURIComponent(a.id)}/logs?tail=200`);
        results[a.id] = await r.text();
      } catch {
        results[a.id] = '(error fetching logs)';
      }
    }));
    setLogs(results);
    setLoading(false);
  }, [agents]);

  React.useEffect(() => { loadLogs(); }, [loadLogs]);

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', overflow:'hidden' }}>
      <StandaloneNav navigate={navigate} lastChannel={lastChannel}>
        <span style={{ fontSize:13, color:'var(--text)', fontWeight:600 }}>Agent Logs</span>
      </StandaloneNav>
      <div style={{ flex:1, overflowY:'auto', padding:'24px' }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:16 }}>
          <h2 style={{ margin:0, fontSize:18, color:'var(--text)' }}>Agent Logs</h2>
          <button onClick={loadLogs} style={{ background:'var(--surface2)', border:'1px solid var(--border)', color:'var(--text)', cursor:'pointer', borderRadius:6, padding:'6px 14px', fontSize:13 }}>↻ Refresh</button>
        </div>
        {agents.length === 0 && (
          <div style={{ color:'var(--muted)', fontSize:13 }}>No agents registered. Spawn an agent from Settings → Agents.</div>
        )}
        {agents.map(a => (
          <div key={a.id} style={{ marginBottom:24 }}>
            <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:6 }}>
              <Avatar name={a.name} size={24} />
              <span style={{ fontWeight:700, fontSize:14, color:'var(--text)' }}>{a.name}</span>
              <AgentStatusDot status={a.status} />
              <span style={{ fontSize:12, color:'var(--muted)' }}>{a.status}</span>
              <span style={{ marginLeft:'auto' }}>
                <CopyButton text={logs[a.id] || ''} />
              </span>
            </div>
            <pre style={{ background:'var(--surface2)', border:'1px solid var(--border)', borderRadius:6, padding:'10px 12px', fontSize:11, lineHeight:1.5, maxHeight:240, overflowY:'auto', whiteSpace:'pre-wrap', wordBreak:'break-all', color:'var(--muted)', margin:0 }}>
              {loading ? 'Loading…' : (logs[a.id]?.trim() || '(no logs)')}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { TasksBoard, TaskDetail, SettingsHub, SettingsAgents, SettingsRoles, SettingsExport, LogsView });
