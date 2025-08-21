// static/app.js - Sam AI dashboard frontend (polished, real-time via polling + optimistic UI)

// -------------------- Helpers --------------------
function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
function qs(id){ return document.getElementById(id); }
function nowMs(){ return Date.now(); }

// small safe JSON parse wrapper
async function safeJson(resp){
  try { return await resp.json(); } catch(e){ return null; }
}

// -------------------- UI state --------------------
let todayXP = 0; // today's earned XP (client-side accumulation)
let POLLING_INTERVAL_MS = 10000; // 10s; change as needed
let POLLER = null;
let CURRENT_STATE = { user:null, stats:{xp:0, level:1}, tasks:[] };

// debounce helper
function debounce(fn, ms=200){
  let t;
  return (...a)=>{ clearTimeout(t); t = setTimeout(()=>fn(...a), ms); };
}

// -------------------- XP & progress UI --------------------
function setTopPoints(x){
  const pointsEl = qs('points');
  if (pointsEl) pointsEl.textContent = String(x || 0);
  // also update profile small xp
  const profXp = qs('profile-xp');
  if (profXp) profXp.textContent = String(x || 0);
  const leaderYou = qs('leader-you');
  if (leaderYou) leaderYou.textContent = String(x || 0);
}

function updateDailyProgressVisual(today){
  // today = numeric XP earned today
  const bar = qs('daily-progress');
  const label = qs('daily-progress-label');
  const percent = Math.min(100, Math.round((Number(today||0) / 100) * 100));
  if (bar) bar.style.width = percent + '%';
  if (label) label.textContent = `${Math.round(today||0)} / 100 XP`;
}

// central updater used for optimistic changes and server sync
function updateXPAndUI(delta){
  delta = Number(delta || 0);
  todayXP = (typeof todayXP === "number") ? todayXP + delta : delta;

  const todayXpEl = qs('today-xp');
  if (todayXpEl) todayXpEl.innerText = String(Math.round(todayXP));

  // adjust top points optimistically; server will later overwrite if it returns authoritative total_xp
  const pointsEl = qs('points');
  if (pointsEl) {
    const cur = parseInt(pointsEl.innerText || "0", 10);
    const newVal = Math.max(0, cur + delta);
    pointsEl.innerText = String(newVal);
  }

  // progress UI
  updateDailyProgressVisual(todayXP);
}

// -------------------- Fetch / State --------------------
async function fetchState(){
  try {
    const resp = await fetch('/api/state', { credentials: 'same-origin' });
    const j = await safeJson(resp);
    if (!j || !j.ok) return null;
    return j;
  } catch(e){
    console.error('fetchState failed', e);
    return null;
  }
}

// Pull authoritative state and update UI. Returns state or null.
async function refreshStateAndUI(){
  const s = await fetchState();
  if (!s) return null;
  CURRENT_STATE = s;
  // top points authoritative
  if (s.stats && typeof s.stats.xp !== 'undefined') setTopPoints(s.stats.xp);
  // username
  if (s.user && s.user.username){
    if (qs('profile-name')) qs('profile-name').textContent = s.user.username;
    if (qs('profile-welcome')) qs('profile-welcome').textContent = s.user.username;
    if (qs('avatar-initials')) qs('avatar-initials').textContent = (s.user.username.slice(0,2) || 'SA').toUpperCase();
  }
  // tasks
  if (Array.isArray(s.tasks)) {
    CURRENT_STATE.tasks = s.tasks;
    renderTasks();
  }
  // academics: we don't have daily aggregation from API here; loadAcademic will fetch sessions
  return s;
}

// start/stop poller
function startPoller(){
  if (POLLER) return;
  POLLER = setInterval(async ()=>{
    try {
      const s = await fetchState();
      if (s && s.ok){
        // update only changed pieces to avoid UI flicker
        if (s.stats && typeof s.stats.xp !== 'undefined') setTopPoints(s.stats.xp);
        if (Array.isArray(s.tasks)) {
          CURRENT_STATE.tasks = s.tasks;
          renderTasks();
        }
      }
    } catch(e){ console.warn('poller error', e); }
  }, POLLING_INTERVAL_MS);
}
function stopPoller(){ if (POLLER){ clearInterval(POLLER); POLLER = null; } }

// -------------------- TASKS --------------------
async function loadTasks(){
  try{
    const resp = await fetch('/api/tasks', { credentials:'same-origin' });
    const data = await safeJson(resp);
    if (data && data.ok){
      CURRENT_STATE.tasks = data.tasks || [];
      renderTasks();
    } else {
      console.warn('loadTasks error', data);
    }
  }catch(e){
    console.error('loadTasks network', e);
  }
}

function renderTasks(){
  const node = qs('tasks-list');
  if (!node) return;
  node.innerHTML = '';
  const tasks = CURRENT_STATE.tasks || [];
  if (!tasks || tasks.length === 0) {
    node.innerHTML = '<p style="color:var(--muted)">No tasks yet. Add one above.</p>';
    return;
  }
  tasks.forEach(t=>{
    const div = document.createElement('div');
    div.className = 'task';
    div.innerHTML = `
      <div>
        <strong>${escapeHtml(t.title || '')}</strong>
        <div style="color:var(--muted)">${escapeHtml(t.description || '')}</div>
      </div>
      <div>
        ${t.is_done ? '<span style="color:#7bd389;">Done</span>' : `<button class="btn ghost" data-taskid="${t.id}">Complete</button>`}
      </div>`;
    node.appendChild(div);
  });

  // (re)bind complete buttons
  node.querySelectorAll('button[data-taskid]').forEach(btn=>{
    // avoid double binding
    if (btn._sami_cb) btn.removeEventListener('click', btn._sami_cb);
    const cb = async (e) => {
      const id = btn.getAttribute('data-taskid');
      btn.disabled = true;
      await completeTask(id);
      btn.disabled = false;
    };
    btn.addEventListener('click', cb);
    btn._sami_cb = cb;
  });
}

async function submitTask(e){
  if (e && e.preventDefault) e.preventDefault();
  const title = (qs('task-title')?.value || '').trim();
  const desc  = (qs('task-desc')?.value || '').trim();
  if (!title) return alert('Please enter a title');

  // disable form while working
  const form = qs('task-form');
  if (form) form.classList.add('loading');

  try{
    const resp = await fetch('/api/tasks', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      credentials: 'same-origin',
      body: JSON.stringify({ title, description: desc })
    });
    const data = await safeJson(resp);

    if (data && data.ok){
      // server may have returned awarded_xp or total_xp
      if (typeof data.total_xp === 'number') {
        setTopPoints(data.total_xp);
      } else if (typeof data.awarded_xp === 'number') {
        // add awarded_xp to UI (and today)
        updateXPAndUI(Number(data.awarded_xp));
      } else {
        // backup: refresh state
        await refreshStateAndUI();
      }
      if (qs('task-title')) qs('task-title').value = '';
      if (qs('task-desc')) qs('task-desc').value = '';
      await loadTasks();
    } else {
      alert('Failed to add task: ' + (data && data.error || 'unknown'));
    }
  }catch(err){
    alert('Network error: ' + err.message);
  } finally {
    if (form) form.classList.remove('loading');
  }
}

async function completeTask(id){
  // optimistic: find task locally and award xp immediately
  const idx = (CURRENT_STATE.tasks || []).findIndex(t=>String(t.id) === String(id));
  const removed = idx >= 0 ? (CURRENT_STATE.tasks.splice(idx,1)[0]) : null;
  const optimisticXP = removed ? Number(removed.xp || 10) : 10;
  if (removed){
    updateXPAndUI(optimisticXP);
    renderTasks();
  }

  try{
    const resp = await fetch(`/api/tasks/${encodeURIComponent(id)}/complete`, {
      method: 'POST',
      credentials: 'same-origin'
    });
    const data = await safeJson(resp);
    if (data && data.ok){
      if (typeof data.total_xp === 'number') setTopPoints(data.total_xp);
      else if (typeof data.awarded_xp === 'number') {
        const diff = Number(data.awarded_xp) - optimisticXP;
        if (diff !== 0) updateXPAndUI(diff);
      } else {
        await refreshStateAndUI();
      }
      await loadTasks();
    } else {
      // rollback optimistic
      if (removed) CURRENT_STATE.tasks.splice(idx,0,removed);
      updateXPAndUI(-optimisticXP);
      renderTasks();
      alert('Server error completing task: ' + (data && data.error || 'unknown'));
    }
  }catch(err){
    if (removed) CURRENT_STATE.tasks.splice(idx,0,removed);
    updateXPAndUI(-optimisticXP);
    renderTasks();
    alert('Network error completing task: ' + err.message);
  }
}

// -------------------- ACADEMIC --------------------
async function loadAcademic(){
  try{
    const resp = await fetch('/api/academic', { credentials:'same-origin' });
    const data = await safeJson(resp);
    if (data && data.ok){
      const node = qs('study-list');
      if (!node) return;
      node.innerHTML = '';
      const sessions = data.sessions || [];
      if (sessions.length === 0) node.innerHTML = '<p style="color:var(--muted)">No study sessions logged yet.</p>';
      sessions.forEach(s=>{
        const el = document.createElement('div');
        el.className = 'task';
        el.innerHTML = `<div><strong>${escapeHtml(s.subject)}</strong><div style="color:var(--muted)">${s.hours} hours — ${s.date ? new Date(s.date).toLocaleString() : ''}</div></div>`;
        node.appendChild(el);
      });
      // update top points if returned
      if (typeof data.total_xp === 'number') setTopPoints(data.total_xp);
    } else {
      console.warn('loadAcademic returned error', data);
    }
  }catch(e){
    console.error('loadAcademic failed', e);
  }
}

async function submitAcademic(e){
  if (e && e.preventDefault) e.preventDefault();
  const subject = (qs('subject')?.value || '').trim();
  const hours = Number(qs('hours')?.value || 0);
  if (!subject || !hours || hours <= 0) return alert('Enter subject and hours');

  const optimisticXP = Math.round(hours * 5);
  // optimistic feedback
  updateXPAndUI(optimisticXP);

  const form = qs('academic-form');
  if (form) form.classList.add('loading');

  try{
    const resp = await fetch('/api/academic', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      credentials: 'same-origin',
      body: JSON.stringify({ subject, hours })
    });
    const data = await safeJson(resp);
    if (!data || !data.ok){
      updateXPAndUI(-optimisticXP);
      return alert('Server error: ' + (data && data.error || 'unknown'));
    }
    // server returns awarded and/or total_xp
    if (typeof data.total_xp === 'number') {
      setTopPoints(data.total_xp);
    } else if (typeof data.awarded_xp === 'number') {
      // if awarded differs from optimistic, adjust
      const diff = Number(data.awarded_xp) - optimisticXP;
      if (diff !== 0) updateXPAndUI(diff);
    } else {
      // fallback re-sync
      await refreshStateAndUI();
    }

    // reload sessions (authoritative)
    await loadAcademic();
    // clear inputs
    if (qs('subject')) qs('subject').value = '';
    if (qs('hours')) qs('hours').value = '';
  }catch(err){
    updateXPAndUI(-optimisticXP);
    alert('Network error: ' + err.message);
  } finally {
    if (form) form.classList.remove('loading');
  }
}

// -------------------- QUESTS --------------------
async function completeQuest(title){
  const optimistic = title.includes('3 tasks') ? 30 : 10;
  updateXPAndUI(optimistic);

  try{
    const resp = await fetch('/api/complete_quest', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      credentials: 'same-origin',
      body: JSON.stringify({ title })
    });
    const data = await safeJson(resp);
    if (data && data.ok){
      if (typeof data.total_xp === 'number') setTopPoints(data.total_xp);
      else if (typeof data.awarded_xp === 'number'){
        const diff = Number(data.awarded_xp) - optimistic;
        if (diff !== 0) updateXPAndUI(diff);
      }
      alert('Quest accepted. +' + (data.awarded_xp || optimistic) + ' XP');
    } else {
      updateXPAndUI(-optimistic);
      alert('Quest error: ' + (data && data.error || 'unknown'));
    }
  }catch(err){
    updateXPAndUI(-optimistic);
    alert('Network error: ' + err.message);
  }
}

// -------------------- Init / Wiring --------------------
async function initDashboard(){
  // If server embedded initial state exists, use it immediately for snappy UI
  const initial = window.__INITIAL_STATE__ ?? null;
  if (initial && initial.user){
    CURRENT_STATE = initial;
    if (qs('profile-name')) qs('profile-name').textContent = initial.user.username || '';
    if (qs('profile-welcome')) qs('profile-welcome').textContent = initial.user.username || '';
    if (qs('avatar-initials')) qs('avatar-initials').textContent = (initial.user.username.slice(0,2) || 'SA').toUpperCase();
    if (qs('points')) setTopPoints((initial.stats && initial.stats.xp) ? initial.stats.xp : 0);
  }

  // Wire forms and controls (avoid double binding by removing previous handlers)
  const tf = qs('task-form');
  if (tf) {
    tf.removeEventListener('submit', submitTask);
    tf.addEventListener('submit', submitTask);
  }
  const af = qs('academic-form');
  if (af) {
    af.removeEventListener('submit', submitAcademic);
    af.addEventListener('submit', submitAcademic);
  }
  const quick = qs('quick-task-form');
  if (quick) {
    quick.removeEventListener('submit', submitQuickTask);
    quick.addEventListener('submit', submitQuickTask);
  }

  // wire quick add handler
  function submitQuickTask(e){
    if (e) e.preventDefault();
    const v = qs('quick-title');
    if (!v || !v.value.trim()) return;
    if (qs('task-title')) qs('task-title').value = v.value.trim();
    v.value = '';
    // small timeout so UI updates from assignment before form submit handler reads values
    setTimeout(()=>submitTask(), 50);
  }

  // wire quest accept buttons (delegation)
  document.querySelectorAll('button[data-quest]').forEach(btn=>{
    if (btn._sami_qcb) btn.removeEventListener('click', btn._sami_qcb);
    const cb = ()=>completeQuest(btn.getAttribute('data-quest'));
    btn.addEventListener('click', cb);
    btn._sami_qcb = cb;
  });

  // wire export fallback if present
  const exp = qs('export-btn');
  if (exp) {
    exp.removeEventListener('click', exportCSV);
    exp.addEventListener('click', exportCSV);
  }

  function exportCSV(){
    // try use authoritative lists if present, else fallback to CURRENT_STATE
    const tasks = CURRENT_STATE.tasks || [];
    // academics list not stored globally here: fetch `/api/academic` if needed (skip for perf)
    const rows = [['Type','Title/Subject','Value','Date']];
    tasks.forEach(t=>rows.push(['task', t.title||'', t.description||'', '']));
    // offer download
    const csv = rows.map(r=>r.map(c=>'"'+String(c).replace(/"/g,'""')+'"').join(',')).join('\n');
    const blob = new Blob([csv], {type:'text/csv'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download='sam-ai-data.csv'; a.click();
    URL.revokeObjectURL(url);
  }

  // initial load
  await refreshStateAndUI();
  await loadTasks();
  await loadAcademic();

  // start poller for near-real-time updates (adjust interval above)
  startPoller();
}

document.addEventListener('DOMContentLoaded', initDashboard);
