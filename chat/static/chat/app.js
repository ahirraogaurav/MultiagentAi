(() => {
  const $ = (id) => document.getElementById(id);
  const onClick = (id, fn) => { const el = $(id); if (el) el.onclick = fn; };
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const app = $('app'), thread = $('thread'), input = $('input'), sendBtn = $('send'), scrollEl = $('scroll'), page = $('page');
  let convId = null, streaming = false, currentProject = null;
  const AGENT = 'auto';

  const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
  const api = (url, opts = {}) => fetch(url, { headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() }, ...opts });
  const getJSON = async (url) => (await api(url)).json();
  const send_ = (url, method, data) => api(url, { method, body: JSON.stringify(data || {}) });

  // ---------- theme ----------
  const setTheme = (t) => { document.documentElement.dataset.theme = t; localStorage.setItem('theme', t); };
  setTheme(localStorage.getItem('theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));

  // ---------- markdown ----------
  const render = (md) => {
    const html = DOMPurify.sanitize(marked.parse(md || '', { breaks: true }));
    const box = document.createElement('div'); box.innerHTML = html;
    box.querySelectorAll('pre').forEach((pre) => {
      const code = pre.querySelector('code'); if (!code) return;
      hljs.highlightElement(code);
      const lang = ([...code.classList].find((c) => c.startsWith('language-')) || '').replace('language-', '') || 'code';
      const bar = document.createElement('div'); bar.className = 'codebar';
      bar.innerHTML = `<span>${esc(lang)}</span><button type="button">Copy</button>`;
      bar.querySelector('button').onclick = (e) => { navigator.clipboard.writeText(code.innerText); e.target.textContent = 'Copied'; setTimeout(() => (e.target.textContent = 'Copy'), 1400); };
      pre.prepend(bar);
    });
    return box.innerHTML;
  };

  // ---------- messages ----------
  const toBottom = () => (scrollEl.scrollTop = scrollEl.scrollHeight);
  const addUser = (text) => { const d = document.createElement('div'); d.className = 'msg user'; const b = document.createElement('div'); b.className = 'bubble'; b.textContent = text; d.append(b); thread.append(d); };
  const stepEl = (s) => { const e = document.createElement('span'); e.className = 'step ' + (s.state === 'done' ? 'done' : ''); e.dataset.agent = s.agent; e.innerHTML = `<i class="dot"></i>${esc(s.name)}${s.detail ? ' → ' + esc(s.detail) : ''}`; return e; };
  const addBot = (text = '', steps = []) => {
    const d = document.createElement('div'); d.className = 'msg bot';
    d.innerHTML = '<div class="steps"></div><div class="body"></div>';
    steps.forEach((s) => d.querySelector('.steps').append(stepEl({ ...s, state: 'done' })));
    if (text) d.querySelector('.body').innerHTML = render(text);
    thread.append(d); return d;
  };
  const setHasMsgs = (v) => document.body.classList.toggle('has-msgs', v);

  // ---------- view switching ----------
  const setActiveNav = (v) => document.querySelectorAll('[data-view]').forEach((b) => b.classList.toggle('active', b.dataset.view === v));
  function showChat() { document.body.classList.remove('page-mode'); setActiveNav(null); }
  function showPage(view, arg) {
    document.body.classList.add('page-mode'); app.classList.remove('open'); setActiveNav(view === 'project' ? 'projects' : view);
    page.scrollTop = 0;
    return ({ search: pageSearch, projects: pageProjects, project: pageProject, artifacts: pageArtifacts, customize: pageCustomize }[view])(arg);
  }

  // ---------- project chip ----------
  function updateChip() {
    const c = $('proj-chip');
    if (!currentProject) { c.hidden = true; return; }
    c.hidden = false; c.innerHTML = `Project: <b>${esc(currentProject.name)}</b>`;
    if (!convId) { const x = document.createElement('button'); x.type = 'button'; x.textContent = '✕'; x.title = 'Remove from project'; x.onclick = () => { currentProject = null; updateChip(); }; c.append(x); }
  }

  // ---------- sidebar: chat list ----------
  let allConvs = [], showAll = false, sortAlpha = false, listOpen = true;
  function renderConvs() {
    const nav = $('convs'); nav.innerHTML = '';
    if (!listOpen) return;
    let items = [...allConvs];
    if (sortAlpha) items.sort((a, b) => a.title.localeCompare(b.title));
    if (!items.length) { nav.innerHTML = '<div class="conv-empty">No chats yet</div>'; return; }
    (showAll ? items : items.slice(0, 10)).forEach((c) => {
      const row = document.createElement('div'); row.className = 'conv' + (c.id === convId ? ' active' : '');
      row.innerHTML = '<span></span><button class="del" title="Delete" aria-label="Delete chat">✕</button>';
      row.querySelector('span').textContent = c.title;
      row.onclick = () => openConv(c.id);
      row.querySelector('.del').onclick = async (ev) => {
        ev.stopPropagation(); await send_(`/api/conversations/${c.id}/`, 'DELETE');
        if (convId === c.id) newChat(); else loadConvs();
      };
      nav.append(row);
    });
    if (!showAll && items.length > 10) {
      const v = document.createElement('button'); v.className = 'view-all'; v.type = 'button'; v.textContent = 'View all';
      v.onclick = () => { showAll = true; renderConvs(); }; nav.append(v);
    }
  }
  async function loadConvs() { allConvs = (await getJSON('/api/conversations/')).conversations; renderConvs(); }

  async function openConv(id) {
    const d = await getJSON(`/api/conversations/${id}/`);
    convId = id; currentProject = d.project; thread.innerHTML = ''; $('chat-title').textContent = d.title;
    d.messages.forEach((m) => (m.role === 'user' ? addUser(m.content) : addBot(m.content, m.steps)));
    setHasMsgs(d.messages.length > 0); showChat(); updateChip(); app.classList.remove('open'); loadConvs(); toBottom();
  }
  function newChat(project = null) {
    convId = null; currentProject = project; thread.innerHTML = ''; $('chat-title').textContent = '';
    setHasMsgs(false); showChat(); updateChip(); app.classList.remove('open'); loadConvs(); input.focus();
  }

  // ---------- send / stream ----------
  const autosize = () => { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 220) + 'px'; };
  async function send() {
    const text = input.value.trim(); if (!text || streaming) return;
    streaming = true; sendBtn.disabled = true; input.value = ''; autosize();
    setHasMsgs(true); addUser(text);
    const bot = addBot(); const body = bot.querySelector('.body'), stepsBox = bot.querySelector('.steps');
    body.classList.add('cursor'); toBottom();
    let acc = '';
    try {
      const res = await send_('/api/chat/', 'POST', { conversation_id: convId, message: text, agent: AGENT, project_id: currentProject && currentProject.id });
      const reader = res.body.getReader(), dec = new TextDecoder(); let buf = '';
      while (true) {
        const { value, done } = await reader.read(); if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split('\n\n'); buf = parts.pop();
        for (const p of parts) {
          if (!p.startsWith('data: ')) continue;
          const ev = JSON.parse(p.slice(6));
          if (ev.type === 'meta') { convId = ev.conversation_id; $('chat-title').textContent = ev.title; updateChip(); }
          else if (ev.type === 'step') { const old = stepsBox.querySelector(`[data-agent="${ev.agent}"]`); const n = stepEl(ev); old ? old.replaceWith(n) : stepsBox.append(n); }
          else if (ev.type === 'delta') { acc += ev.text; body.innerHTML = render(acc); }
          else if (ev.type === 'error') { body.insertAdjacentHTML('beforeend', '<div class="err"></div>'); body.lastChild.textContent = ev.message; }
          toBottom();
        }
      }
    } catch (e) { body.innerHTML = '<div class="err">Couldn\'t reach the server. Check that it is running.</div>'; }
    body.classList.remove('cursor'); streaming = false; sendBtn.disabled = !input.value.trim(); loadConvs();
  }
  input.addEventListener('input', () => { autosize(); sendBtn.disabled = streaming || !input.value.trim(); });
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });
  sendBtn.onclick = send;

  // ---------- modal ----------
  function modal({ title, fields, submit, onSubmit }) {
    const m = $('modal');
    m.innerHTML = `<form><h2>${esc(title)}</h2>${fields.map((f) => `<label>${esc(f.label)}${f.type === 'textarea'
      ? `<textarea class="field" name="${f.name}" rows="${f.rows || 4}" placeholder="${esc(f.placeholder || '')}">${esc(f.value || '')}</textarea>`
      : `<input class="field" name="${f.name}" value="${esc(f.value || '')}" placeholder="${esc(f.placeholder || '')}" ${f.required ? 'required' : ''}>`}</label>`).join('')}
      <div class="modal-actions"><button type="button" class="btn" id="m-cancel">Cancel</button><button class="btn primary">${esc(submit)}</button></div></form>`;
    m.querySelector('#m-cancel').onclick = () => m.close();
    m.querySelector('form').onsubmit = async (e) => { e.preventDefault(); await onSubmit(Object.fromEntries(new FormData(e.target))); m.close(); };
    m.showModal();
  }

  // ---------- PAGE: Search ----------
  async function pageSearch() {
    page.innerHTML = `<div class="page-inner"><h1>Search</h1><input class="big-input" id="pg-q" type="search" placeholder="Search chats and messages…" autocomplete="off"><div class="results" id="pg-res"></div></div>`;
    const q = $('pg-q'), res = $('pg-res'); let t;
    const run = async () => {
      const d = await getJSON('/api/search/?q=' + encodeURIComponent(q.value.trim()));
      res.innerHTML = d.results.length
        ? d.results.map((r) => `<button class="result" data-id="${r.id}"><b>${esc(r.title)}</b>${r.snippet ? `<span>${esc(r.snippet)}</span>` : ''}</button>`).join('')
        : '<p class="muted">No results found.</p>';
      res.querySelectorAll('.result').forEach((b) => (b.onclick = () => openConv(Number(b.dataset.id))));
    };
    q.oninput = () => { clearTimeout(t); t = setTimeout(run, 200); };
    run(); q.focus();
  }

  // ---------- PAGE: Projects ----------
  const projectForm = (p = {}) => [
    { name: 'name', label: 'Name', value: p.name, required: true, placeholder: 'e.g. Marketing plan' },
    { name: 'description', label: 'Description', value: p.description, placeholder: 'What is this project about?' },
    { name: 'instructions', label: 'Instructions for the agents', type: 'textarea', rows: 5, value: p.instructions, placeholder: 'Tone, rules, background info… applied to every chat in this project.' },
  ];
  async function pageProjects() {
    const { projects } = await getJSON('/api/projects/');
    page.innerHTML = `<div class="page-inner"><div class="page-head"><h1>Projects</h1><button class="btn primary" id="np">New project</button></div>
      ${projects.length ? `<div class="grid">${projects.map((p) => `<button class="card" data-id="${p.id}"><b>${esc(p.name)}</b><span>${esc(p.description || 'No description')}</span><small>${p.chat_count} chat${p.chat_count === 1 ? '' : 's'}</small></button>`).join('')}</div>`
        : '<div class="emptybox">Projects keep related chats together and give the agents shared instructions.<br>Create your first project to get started.</div>'}</div>`;
    $('np').onclick = () => modal({ title: 'New project', fields: projectForm(), submit: 'Create project', onSubmit: async (d) => { const r = await (await send_('/api/projects/', 'POST', d)).json(); showPage('project', r.id); } });
    page.querySelectorAll('.card').forEach((c) => (c.onclick = () => showPage('project', Number(c.dataset.id))));
  }
  async function pageProject(id) {
    const p = await getJSON(`/api/projects/${id}/`);
    page.innerHTML = `<div class="page-inner"><button class="link" id="back">← All projects</button>
      <div class="page-head"><h1>${esc(p.name)}</h1><div class="row"><button class="btn" id="edit">Edit</button><button class="btn danger" id="del">Delete</button></div></div>
      <p class="muted">${esc(p.description)}</p>
      <h3>Instructions</h3><pre class="instr">${esc(p.instructions || 'No instructions yet. Click Edit to add some, and every chat in this project will follow them.')}</pre>
      <div class="page-head" style="margin-top:26px"><h3>Chats</h3><button class="btn primary" id="nc">New chat in project</button></div>
      <div class="results">${p.chats.length ? p.chats.map((c) => `<button class="result" data-id="${c.id}"><b>${esc(c.title)}</b></button>`).join('') : '<p class="muted">No chats in this project yet.</p>'}</div></div>`;
    $('back').onclick = () => showPage('projects');
    $('nc').onclick = () => newChat({ id: p.id, name: p.name });
    $('edit').onclick = () => modal({ title: 'Edit project', fields: projectForm(p), submit: 'Save', onSubmit: async (d) => { await send_(`/api/projects/${id}/`, 'PATCH', d); showPage('project', id); } });
    $('del').onclick = async () => { if (confirm(`Delete project "${p.name}"? Its chats will be kept.`)) { await send_(`/api/projects/${id}/`, 'DELETE'); showPage('projects'); } };
    page.querySelectorAll('.result').forEach((b) => (b.onclick = () => openConv(Number(b.dataset.id))));
  }

  // ---------- PAGE: Artifacts ----------
  const EXT = { python: 'py', py: 'py', javascript: 'js', js: 'js', typescript: 'ts', ts: 'ts', html: 'html', css: 'css', json: 'json', bash: 'sh', sh: 'sh', sql: 'sql', java: 'java', cpp: 'cpp', c: 'c', markdown: 'md', svg: 'svg', xml: 'xml', yaml: 'yml' };
  async function pageArtifacts() {
    const { artifacts } = await getJSON('/api/artifacts/');
    page.innerHTML = `<div class="page-inner"><h1>Artifacts</h1>
      ${artifacts.length ? `<div class="grid">${artifacts.map((a, i) => `<button class="card art" data-i="${i}"><div class="art-top"><b>${esc(a.title)}</b><em class="tag">${esc(a.language)}</em></div><pre>${esc(a.code.split('\n').slice(0, 7).join('\n'))}</pre><small>${esc(a.chat)}</small></button>`).join('')}</div>`
        : '<div class="emptybox">Code, pages and files the agents create in your chats will appear here.<br>Ask for a script or an HTML page to see one.</div>'}</div>`;
    page.querySelectorAll('.card').forEach((c) => (c.onclick = () => artifactDetail(artifacts[Number(c.dataset.i)])));
  }
  function artifactDetail(a) {
    const canPreview = ['html', 'svg'].includes(a.language.toLowerCase());
    page.innerHTML = `<div class="page-inner"><button class="link" id="back">← All artifacts</button>
      <div class="page-head"><h1>${esc(a.title)}</h1><div class="row">${canPreview ? '<div class="tabs"><button class="on" id="t-code">Code</button><button id="t-prev">Preview</button></div>' : ''}
      <button class="btn" id="copy">Copy</button><button class="btn" id="dl">Download</button><button class="btn" id="chat">Open chat</button></div></div>
      <p class="muted">${esc(a.language)} · from “${esc(a.chat)}”</p><div id="av"></div></div>`;
    const av = $('av');
    const showCode = () => { av.innerHTML = '<pre class="code-view"><code></code></pre>'; const c = av.querySelector('code'); c.textContent = a.code; if (window.hljs) hljs.highlightElement(c); };
    const showPrev = () => { av.innerHTML = '<iframe class="preview" sandbox=""></iframe>'; av.querySelector('iframe').srcdoc = a.code; };
    showCode();
    if (canPreview) {
      $('t-code').onclick = () => { $('t-code').classList.add('on'); $('t-prev').classList.remove('on'); showCode(); };
      $('t-prev').onclick = () => { $('t-prev').classList.add('on'); $('t-code').classList.remove('on'); showPrev(); };
    }
    $('back').onclick = () => showPage('artifacts');
    $('copy').onclick = () => { navigator.clipboard.writeText(a.code); $('copy').textContent = 'Copied'; setTimeout(() => ($('copy').textContent = 'Copy'), 1400); };
    $('dl').onclick = () => { const l = document.createElement('a'); l.href = URL.createObjectURL(new Blob([a.code], { type: 'text/plain' })); l.download = `artifact.${EXT[a.language.toLowerCase()] || 'txt'}`; l.click(); };
    $('chat').onclick = () => openConv(a.conversation_id);
  }

  // ---------- PAGE: Customize ----------
  const STYLE_INFO = { normal: ['Normal', 'Balanced answers for everyday use'], concise: ['Concise', 'Short and direct, no preamble'], explanatory: ['Explanatory', 'Step-by-step, teaches as it goes'], formal: ['Formal', 'Professional tone'] };
  function applyName(name) {
    if (!name) return;
    const u = document.querySelector('.uname'), a = document.querySelector('.avatar');
    if (u) u.textContent = name; if (a) a.textContent = name.slice(0, 1).toUpperCase();
  }
  async function pageCustomize() {
    const p = await getJSON('/api/profile/');
    page.innerHTML = `<div class="page-inner"><h1>Customize</h1>
      <div class="form-section"><h3>About you</h3><p>What should the agents call you?</p><input class="field" id="c-name" value="${esc(p.display_name)}" placeholder="Your name"></div>
      <div class="form-section"><h3>Custom instructions</h3><p>Added to every chat. Say how you like answers, your background, or things to avoid.</p><textarea class="field" id="c-instr" rows="5" placeholder="e.g. I'm a Django developer. Prefer short code examples.">${esc(p.instructions)}</textarea></div>
      <div class="form-section"><h3>Response style</h3>${p.styles.map((s) => `<label class="opt"><input type="radio" name="style" value="${s}" ${p.style === s ? 'checked' : ''}><span><b>${STYLE_INFO[s][0]}</b><small>${STYLE_INFO[s][1]}</small></span></label>`).join('')}</div>
      <div class="form-section"><h3>Agents</h3><p>The orchestrator only uses the specialists you leave on.</p>${p.agents.map((a) => `<label class="opt"><input type="checkbox" class="ag" value="${a.id}" ${p.disabled_agents.includes(a.id) ? '' : 'checked'}><span><b>${esc(a.name)}</b><small>${esc(a.description)}</small></span></label>`).join('')}</div>
      <button class="btn primary" id="c-save">Save changes</button><span class="saved" id="c-ok"></span></div>`;
    $('c-save').onclick = async () => {
      const body = {
        display_name: $('c-name').value.trim(), instructions: $('c-instr').value,
        style: (page.querySelector('input[name=style]:checked') || {}).value || 'normal',
        disabled_agents: [...page.querySelectorAll('.ag')].filter((x) => !x.checked).map((x) => x.value),
      };
      await send_('/api/profile/', 'PATCH', body); applyName(body.display_name);
      $('c-ok').textContent = 'Saved'; setTimeout(() => ($('c-ok').textContent = ''), 1800);
    };
  }

  // ---------- sidebar wiring ----------
  const isMobile = () => matchMedia('(max-width: 760px)').matches;
  onClick('collapse', () => app.classList.toggle(isMobile() ? 'open' : 'collapsed'));
  onClick('new-chat', () => newChat());
  document.querySelectorAll('[data-view]').forEach((b) => (b.onclick = () => showPage(b.dataset.view)));
  document.querySelectorAll('[data-soon]').forEach((b) => (b.onclick = () => alert(b.dataset.soon + ': coming soon')));
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'k') { e.preventDefault(); app.classList.remove('collapsed'); showPage('search'); }
  });
  onClick('list-toggle', () => { listOpen = !listOpen; renderConvs(); });
  onClick('sort-btn', () => { sortAlpha = !sortAlpha; $('sort-btn').title = sortAlpha ? 'Sorted A–Z (click for Recent)' : 'Sorted by Recent (click for A–Z)'; renderConvs(); });

  // ---------- header: title menu, export, share ----------
  const titleMenu = $('title-menu'), userMenu = $('user-menu');
  onClick('title-btn', (e) => { e.stopPropagation(); userMenu.hidden = true; titleMenu.hidden = !titleMenu.hidden; });
  onClick('rename', async () => {
    const t = prompt('Rename chat', $('chat-title').textContent); if (!t || !convId) return;
    await send_(`/api/conversations/${convId}/`, 'PATCH', { title: t }); $('chat-title').textContent = t; loadConvs();
  });
  onClick('delete-chat', async () => { if (!convId) return; await send_(`/api/conversations/${convId}/`, 'DELETE'); newChat(); });
  onClick('share', async () => {
    if (!convId) return;
    try { await navigator.clipboard.writeText(`${location.origin}/?c=${convId}`); } catch (e) {}
    const s = $('share').querySelector('span'); s.textContent = 'Link copied'; setTimeout(() => (s.textContent = 'Share'), 1500);
  });
  onClick('export', async () => {
    if (!convId) return;
    const d = await getJSON(`/api/conversations/${convId}/`);
    const md = `# ${d.title}\n\n` + d.messages.map((m) => `**${m.role === 'user' ? 'You' : 'Assistant'}:**\n\n${m.content}`).join('\n\n---\n\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([md], { type: 'text/markdown' })); a.download = `${d.title.slice(0, 40)}.md`; a.click();
  });

  // ---------- user menu ----------
  onClick('user-btn', (e) => { e.stopPropagation(); titleMenu.hidden = true; userMenu.hidden = !userMenu.hidden; });
  document.addEventListener('click', () => { titleMenu.hidden = true; userMenu.hidden = true; });
  userMenu.addEventListener('click', (e) => e.stopPropagation());
  onClick('theme', () => { setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'); userMenu.hidden = true; });
  onClick('settings', () => { userMenu.hidden = true; showPage('customize'); });
  onClick('language', () => alert('Language: coming soon'));
  onClick('help', () => window.open('https://docs.djangoproject.com', '_blank'));
  onClick('upgrade', () => alert('Upgrade plan: coming soon'));
  onClick('learn', () => alert('Learn more: coming soon'));
  onClick('logout', () => {
    document.getElementById('logoutForm')?.requestSubmit();
});

  // ---------- start ----------
  getJSON('/api/profile/').then((p) => applyName(p.display_name)).catch(() => {});
  const shared = new URLSearchParams(location.search).get('c');
  if (shared) openConv(Number(shared));
  loadConvs();
})();

/* Voice input: speech-to-text */
(() => {
    const voiceBtn = document.getElementById("voice-btn");
    const input = document.getElementById("input");

    if (!voiceBtn || !input) return;

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        voiceBtn.title =
            "Voice input is not supported in this browser";
        voiceBtn.addEventListener("click", () => {
            alert(
                "Voice input is not supported. Please use Google Chrome or Microsoft Edge."
            );
        });
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = true;

    let listening = false;
    let finalTranscript = "";

    recognition.onstart = () => {
        listening = true;
        finalTranscript = "";
        voiceBtn.classList.add("recording");
        voiceBtn.title = "Listening... click to stop";
    };

    recognition.onresult = (event) => {
        let interimTranscript = "";

        for (let i = event.resultIndex;
             i < event.results.length; i++) {
            const transcript =
                event.results[i][0].transcript;

            if (event.results[i].isFinal) {
                finalTranscript += transcript + " ";
            } else {
                interimTranscript += transcript;
            }
        }

        input.value =
            (finalTranscript + interimTranscript).trim();

        input.dispatchEvent(
            new Event("input", { bubbles: true })
        );
    };

    recognition.onerror = (event) => {
        console.error("Voice recognition error:", event.error);

        if (event.error === "not-allowed") {
            alert("Please allow microphone access in your browser.");
        } else if (event.error === "no-speech") {
            console.log("No speech detected. Please try again.");
        }
    };

    recognition.onend = () => {
        listening = false;
        voiceBtn.classList.remove("recording");
        voiceBtn.title = "Speak your message";
    };

    voiceBtn.addEventListener("click", () => {
        if (listening) {
            recognition.stop();
            return;
        }

        try {
            recognition.start();
        } catch (error) {
            console.error("Could not start voice input:", error);
        }
    });
})();

/* Text-to-speech: read an answer aloud */
function speakAIResponse(text) {
    if (!("speechSynthesis" in window)) {
        alert("Text-to-speech is not supported in this browser.");
        return;
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-IN";
    utterance.rate = 1;
    utterance.pitch = 1;

    window.speechSynthesis.speak(utterance);
}

/* Optional: stop speaking when needed */
function stopAIResponse() {
    if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
    }
}
