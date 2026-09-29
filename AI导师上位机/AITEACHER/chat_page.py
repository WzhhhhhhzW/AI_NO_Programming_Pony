"""对话区的网页外壳：CSS 与 JS。

这里是一张普通网页。之所以不用 Qt 的富文本，是因为它只认 HTML4 子集——
块级元素的背景不渲染、围栏代码块会被拆成一行一个 <pre>、一半 CSS 属性
无效。用 QWebEngineView 之后这些限制全部消失，改样式就是改 CSS。

Python 侧负责把 Markdown 渲染成 HTML（markdown_render.py），这里只管排版
和增量插入，所以页面里不需要任何第三方 JS。
"""

CSS = """
:root {
  --page:#f5f5f7; --fg:#1d1d1f; --muted:#8a8a8f;
  --user:#007aff; --user-fg:#fff;
  --bot:#ffffff; --bot-border:#e5e5ea;
  --card:#f0f6ff; --card-border:#007aff;
  --tool:#ececf0; --tool-fg:#5f6368; --deny:#c0392b;
  --code:#f6f6f8; --code-border:#e5e5ea;
  --tbl:#d8d8dd; --th:#eeeef2;
  --shadow:0 1px 2px rgba(0,0,0,.05), 0 1px 8px rgba(0,0,0,.04);
  --add-bg:#e6ffec; --add-fg:#0a5f2c; --add-sign:#1a7f37;
  --del-bg:#ffebe9; --del-fg:#82061e; --del-sign:#cf222e;
  --diff-hd:#f6f8fa; --gutter:#8c959f; --gutter-bg:#fbfbfd;
  --btn:#007aff; --btn-hover:#0069d9; --btn-fg:#fff;
  --ghost-fg:#3a3a40; --ghost-border:#d3d3d9; --ghost-hover:#ececf0;
  --chip-bg:#ffffff; --chip-border:#dcdce2; --chip-hover:#f0f6ff;
  --ok:#1a7f37; --sb:#c6c6cc; --sb-hover:#a8a8b0;
}
body[data-theme="dark"] {
  --page:#121214; --fg:#e5e5ea; --muted:#8e8e93;
  --user:#0a84ff; --user-fg:#fff;
  --bot:#1c1c20; --bot-border:#2c2c32;
  --card:#16222f; --card-border:#0a84ff;
  --tool:#26262b; --tool-fg:#9aa0a6; --deny:#ff8a80;
  --code:#0d0d10; --code-border:#2a2a30;
  --tbl:#33333a; --th:#26262b;
  --shadow:none;
  --add-bg:#12261c; --add-fg:#7ee787; --add-sign:#3fb950;
  --del-bg:#2d1517; --del-fg:#ffa198; --del-sign:#f85149;
  --diff-hd:#17171b; --gutter:#6e7681; --gutter-bg:#141418;
  --btn:#0a84ff; --btn-hover:#3d9bff; --btn-fg:#fff;
  --ghost-fg:#c8c8ce; --ghost-border:#3a3a42; --ghost-hover:#26262b;
  --chip-bg:#1c1c20; --chip-border:#33333a; --chip-hover:#232a33;
  --ok:#3fb950; --sb:#3a3a42; --sb-hover:#4d4d57;
}

/* Chromium 默认滚动条在暗色下是白的，代码块和 diff 里特别刺眼 */
::-webkit-scrollbar { width:10px; height:10px; }
::-webkit-scrollbar-track,
::-webkit-scrollbar-corner { background:transparent; }
::-webkit-scrollbar-thumb {
  background:var(--sb); border-radius:6px;
  border:2px solid transparent; background-clip:padding-box;
}
::-webkit-scrollbar-thumb:hover {
  background:var(--sb-hover); background-clip:padding-box;
}

* { box-sizing:border-box; }
html,body { margin:0; padding:0; }
body {
  background:var(--page); color:var(--fg);
  font-family:-apple-system,"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif;
  font-size:14px; line-height:1.65;
  padding:14px 16px 24px;
}
#log { display:flex; flex-direction:column; gap:12px; max-width:1000px; margin:0 auto; }

/* ---------- 学生 ---------- */
.user { align-self:flex-end; max-width:78%; }
.user .body {
  background:var(--user); color:var(--user-fg);
  padding:9px 14px; border-radius:16px 16px 4px 16px;
  white-space:pre-wrap; word-break:break-word;
}

/* ---------- 系统提示 ---------- */
.sys { align-self:center; color:var(--muted); font-size:12px; font-style:italic; }

/* ---------- 课程卡片 ---------- */
.lesson {
  background:var(--card); border-left:4px solid var(--card-border);
  border-radius:10px; padding:14px 18px; box-shadow:var(--shadow);
}
.lesson > .hd {
  color:var(--card-border); font-weight:700; font-size:13px;
  letter-spacing:.02em; margin-bottom:8px;
}

/* ---------- AI ---------- */
.bot {
  background:var(--bot); border:1px solid var(--bot-border);
  border-radius:12px; padding:12px 16px 14px; box-shadow:var(--shadow);
}
.bot > .hd {
  color:var(--muted); font-size:12px; margin-bottom:8px;
  display:flex; align-items:center; gap:8px;
}
.bot > .hd .cost { margin-left:auto; font-variant-numeric:tabular-nums; }

/* 一轮回复内部的时间线：文字段和工具调用按到达顺序交替排。
   以前是"所有工具堆顶上、所有文字拼成一坨"，模型每次调工具前说的那半句
   （"编译确认："）就全被粘到一起了。 */
.stream { display:flex; flex-direction:column; align-items:stretch; gap:9px; }

/* 工具调用 */
.tool {
  align-self:flex-start;              /* 不然会被拉成整行宽 */
  display:flex; align-items:center; gap:8px;
  background:var(--tool); color:var(--tool-fg);
  border-radius:7px; padding:5px 10px; font-size:12px;
  max-width:100%;
}
.tool .name { font-weight:600; white-space:nowrap; }
.tool .arg  { font-family:ui-monospace,Menlo,Consolas,monospace; opacity:.85;
              overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.tool.deny { color:var(--deny); }

/* 打字光标：还在跑的时候，缀在时间线最后一个块上 */
.bot.busy .stream > .md:last-child > *:last-child::after {
  content:"▌"; margin-left:2px; opacity:.55;
  animation:blink 1.1s steps(1) infinite;
}
.bot.busy .stream > .tool:last-child::after {
  content:"…"; opacity:.7;
  animation:blink 1.1s steps(1) infinite;
}
/* 刚开一轮时时间线还是空的，上面两条都挂不上——冷启动那几秒不能一片空白 */
.bot.busy .stream:empty::after {
  content:"▌"; opacity:.55;
  animation:blink 1.1s steps(1) infinite;
}
@keyframes blink { 50% { opacity:0; } }

/* ---------- Markdown 正文 ---------- */
.md > *:first-child { margin-top:0; }
.md > *:last-child  { margin-bottom:0; }
.md p { margin:.5em 0; }
.md h1,.md h2,.md h3,.md h4 { margin:1em 0 .4em; line-height:1.35; font-weight:700; }
.md h1 { font-size:1.28em; } .md h2 { font-size:1.16em; }
.md h3 { font-size:1.06em; } .md h4 { font-size:1em; }
.md ul,.md ol { margin:.45em 0; padding-left:1.5em; }
.md li { margin:.2em 0; }
.md hr { border:0; border-top:1px solid var(--bot-border); margin:1em 0; }
.md a { color:var(--user); }
.md blockquote {
  margin:.6em 0; padding:.1em 0 .1em .9em;
  border-left:3px solid var(--tbl); color:var(--muted);
}
.md code {
  font-family:ui-monospace,Menlo,Consolas,monospace; font-size:.9em;
  background:var(--code); border:1px solid var(--code-border);
  border-radius:4px; padding:.1em .35em;
}
.md pre {
  background:var(--code); border:1px solid var(--code-border);
  border-radius:8px; padding:12px 14px; margin:.7em 0;
  overflow-x:auto;
}
.md pre code { background:none; border:0; padding:0; font-size:.88em; line-height:1.55; }
.md table { border-collapse:collapse; margin:.7em 0; font-size:.94em; }
.md th,.md td { border:1px solid var(--tbl); padding:6px 12px; text-align:left; }
.md th { background:var(--th); font-weight:600; }
.md img { max-width:100%; }

/* ==================== 初级模式 ==================== */

/* ---------- 按钮（都是 <a>，靠 horse: 协议回到 Python） ---------- */
.btn {
  display:inline-flex; align-items:center; gap:6px;
  padding:8px 16px; border-radius:9px; font-size:13px; font-weight:600;
  text-decoration:none; cursor:pointer; user-select:none;
  transition:background .13s ease, border-color .13s ease, transform .08s ease;
}
.btn:active { transform:translateY(1px); }
.btn.primary { background:var(--btn); color:var(--btn-fg); }
.btn.primary:hover { background:var(--btn-hover); }
.btn.ghost {
  color:var(--ghost-fg); border:1px solid var(--ghost-border); background:transparent;
}
.btn.ghost:hover { background:var(--ghost-hover); }

/* ---------- 开场：快捷指令 ---------- */
.quick {
  background:var(--bot); border:1px solid var(--bot-border);
  border-radius:14px; padding:16px 18px; box-shadow:var(--shadow);
}
.quick .qhd { display:flex; gap:12px; align-items:flex-start; margin-bottom:14px; }
.quick .qicon {
  font-size:22px; line-height:1.2; flex:none;
  width:38px; height:38px; border-radius:11px; background:var(--card);
  display:flex; align-items:center; justify-content:center;
}
.quick .qtitle { font-weight:700; font-size:15px; }
.quick .qsub { color:var(--muted); font-size:12.5px; margin-top:2px; }
.chips { display:flex; flex-wrap:wrap; gap:8px; }
.chip {
  display:inline-flex; align-items:center; gap:7px;
  background:var(--chip-bg); border:1px solid var(--chip-border);
  border-radius:10px; padding:8px 13px; font-size:13px;
  color:var(--fg); text-decoration:none; cursor:pointer;
  transition:background .13s ease, border-color .13s ease, transform .08s ease;
}
.chip:hover { background:var(--chip-hover); border-color:var(--card-border); }
.chip:active { transform:translateY(1px); }
.chip .k { opacity:.85; }

/* ---------- 改动 diff ---------- */
.diff {
  border:1px solid var(--bot-border); border-radius:12px;
  overflow:hidden; box-shadow:var(--shadow); background:var(--bot);
}
.diff .dhd {
  display:flex; align-items:center; gap:10px; flex-wrap:wrap;
  background:var(--diff-hd); border-bottom:1px solid var(--bot-border);
  padding:9px 14px; font-size:13px;
}
.diff .dfile {
  font-family:ui-monospace,Menlo,Consolas,monospace; font-weight:600;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}
.diff .dnote {
  font-size:11px; color:var(--muted); border:1px solid var(--bot-border);
  border-radius:5px; padding:1px 6px;
}
.diff .dstat { display:flex; gap:6px; font-variant-numeric:tabular-nums; font-size:12px; }
.diff .dstat .p { color:var(--add-sign); font-weight:700; }
.diff .dstat .m { color:var(--del-sign); font-weight:700; }
.diff .dopen {
  margin-left:auto; color:var(--btn); text-decoration:none;
  font-size:12px; white-space:nowrap;
}
.diff .dopen:hover { text-decoration:underline; }

.dbody {
  overflow-x:auto; font-family:ui-monospace,Menlo,Consolas,monospace;
  font-size:12.5px; line-height:1.6;
}
/* 只留一列行号（改动后的行号，删掉的行显示原行号）。GitHub 那种新旧
   两列在这个侧栏宽度下会把代码挤没，行号本身也不是重点。 */
.drow { display:grid; grid-template-columns:40px 1fr; min-width:max-content; }
.drow .dn {
  position:sticky; left:0; text-align:right; padding:0 7px;
  color:var(--gutter); background:var(--gutter-bg);
  user-select:none; font-size:11.5px;
  box-shadow:1px 0 0 var(--bot-border);
}
.drow .dc { padding:0 12px 0 10px; white-space:pre; }
.drow .dc::before { content:attr(data-sign); display:inline-block; width:1ch; opacity:.75; }
.drow.add { background:var(--add-bg); }
.drow.add .dc { color:var(--add-fg); }
.drow.del { background:var(--del-bg); }
.drow.del .dc { color:var(--del-fg); }
.drow.gap { background:var(--gutter-bg); color:var(--gutter); }
.drow.gap .dc { padding-left:12px; opacity:.7; }

/* ---------- 改完之后的动作条 ---------- */
.act {
  background:var(--bot); border:1px solid var(--bot-border);
  border-left:4px solid var(--ok);
  border-radius:12px; padding:13px 16px; box-shadow:var(--shadow);
  display:flex; align-items:center; gap:14px; flex-wrap:wrap;
}
.act .atext { font-size:13.5px; }
.act .atext b { color:var(--ok); }
.act .ahint { color:var(--muted); font-size:12px; margin-top:2px; }
.act .btns { margin-left:auto; display:flex; gap:8px; flex-wrap:wrap; }
.act.done { border-left-color:var(--muted); opacity:.72; }
.act.done .btns { display:none; }
"""

JS = """
const log = document.getElementById('log');
const nodes = {};

function nearBottom() {
  return window.innerHeight + window.scrollY >= document.body.scrollHeight - 90;
}
function toBottom(force) {
  if (force || nearBottom()) window.scrollTo({top: document.body.scrollHeight});
}
function el(cls, html) {
  const d = document.createElement('div');
  d.className = cls;
  if (html !== undefined) d.innerHTML = html;
  return d;
}

function addUser(text) {
  const w = el('user');
  const b = el('body');
  b.textContent = text;
  w.appendChild(b); log.appendChild(w); toBottom(true);
}

function addSystem(html) {
  log.appendChild(el('sys', html)); toBottom(true);
}

function addLesson(header, bodyHtml) {
  const w = el('lesson');
  w.appendChild(el('hd', header));
  w.appendChild(el('md', bodyHtml));
  log.appendChild(w); toBottom(true);
}

function beginBot(id, title) {
  const w = el('bot busy');
  w.appendChild(el('hd', '<span>' + title + '</span><span class="cost"></span>'));
  w.appendChild(el('stream'));
  log.appendChild(w);
  nodes[id] = w;
  toBottom(true);
}

function botTool(id, icon, name, arg, deny) {
  const w = nodes[id]; if (!w) return;
  const t = el('tool' + (deny ? ' deny' : ''));
  t.innerHTML = '<span>' + icon + '</span><span class="name">' + name +
                '</span><span class="arg">' + arg + '</span>';
  w.querySelector('.stream').appendChild(t);
  toBottom(false);
}

/* seg 是这段文字在时间线里的序号：同一个序号重复调用就是流式更新，
   新序号就在末尾新起一段。工具调用夹在中间，顺序自然是对的。 */
function botText(id, seg, html) {
  const w = nodes[id]; if (!w) return;
  const stream = w.querySelector('.stream');
  let d = stream.querySelector('[data-seg="' + seg + '"]');
  if (!d) {
    d = el('md');
    d.setAttribute('data-seg', seg);
    stream.appendChild(d);
  }
  d.innerHTML = html;
  toBottom(false);
}

function botFinish(id, cost) {
  const w = nodes[id]; if (!w) return;
  w.classList.remove('busy');
  w.querySelector('.cost').textContent = cost || '';
  toBottom(false);
}

/* ---------- 初级模式 ---------- */

/* 页面回到 Python 的唯一通道：一个自定义协议的链接。
   chat_view.py 里覆盖了 acceptNavigationRequest，拦下 horse: 开头的跳转。
   这样不用引 QtWebChannel，也不用在页面里塞任何第三方 JS。 */
function href(action, params) {
  const q = [];
  for (const k in (params || {})) q.push(k + '=' + encodeURIComponent(params[k]));
  return 'horse:' + action + (q.length ? '?' + q.join('&') : '');
}
function link(cls, action, params, html) {
  const a = document.createElement('a');
  a.className = cls;
  a.setAttribute('href', href(action, params));
  a.innerHTML = html;
  return a;
}

function addQuick(title, sub, items) {
  const w = el('quick');
  const hd = el('qhd');
  hd.appendChild(el('qicon', '🐎'));
  const t = el('');
  t.appendChild(el('qtitle', title));
  t.appendChild(el('qsub', sub));
  hd.appendChild(t);
  w.appendChild(hd);

  const chips = el('chips');
  items.forEach(function (it) {
    chips.appendChild(link('chip', 'send', {text: it.text},
      '<span class="k">' + it.icon + '</span><span>' + it.label + '</span>'));
  });
  w.appendChild(chips);
  log.appendChild(w); toBottom(true);
}

function addDiff(d) {
  const w = el('diff');
  const hd = el('dhd');
  hd.appendChild(el('dfile', '📄 ' + d.path));
  if (d.note) hd.appendChild(el('dnote', d.note));
  const st = el('dstat');
  if (d.added)   st.appendChild(el('p', '+' + d.added));
  if (d.removed) st.appendChild(el('m', '−' + d.removed));
  hd.appendChild(st);
  if (d.abs) hd.appendChild(link('dopen', 'open', {path: d.abs, line: d.line},
                                 '在编辑器中打开 ›'));
  w.appendChild(hd);

  const body = el('dbody');
  d.rows.forEach(function (r) {
    const row = el('drow ' + r.kind);
    const n = el('dn');
    n.textContent = r.new || r.old || '';
    const c = el('dc');
    if (r.kind === 'gap') {
      c.textContent = '⋯';
    } else {
      c.setAttribute('data-sign', r.kind === 'add' ? '+' : (r.kind === 'del' ? '-' : ' '));
      c.textContent = r.text;
    }
    row.appendChild(n); row.appendChild(c);
    body.appendChild(row);
  });
  w.appendChild(body);
  log.appendChild(w); toBottom(true);
}

function addActions(id, text, hint) {
  const w = el('act');
  const t = el('');
  t.appendChild(el('atext', text));
  if (hint) t.appendChild(el('ahint', hint));
  w.appendChild(t);
  const btns = el('btns');
  btns.appendChild(link('btn primary', 'build', {}, '🔨 编译并准备烧录'));
  btns.appendChild(link('btn ghost', 'undo', {id: id}, '↩ 撤销这次修改'));
  w.appendChild(btns);
  log.appendChild(w);
  nodes[id] = w;
  toBottom(true);
}

/* 撤销/编译点过之后就把这张卡片收起来，免得学生反复点同一个撤销 */
function retireActions(id, text) {
  const w = nodes[id]; if (!w) return;
  w.classList.add('done');
  if (text) w.querySelector('.atext').textContent = text;
}

function setTheme(t) { document.body.setAttribute('data-theme', t); }
function clearAll() { log.innerHTML = ''; for (const k in nodes) delete nodes[k]; }
"""


def page_html(theme: str, pygments_css: str) -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<style>{CSS}\n{pygments_css}</style></head>"
        f"<body data-theme='{theme}'><div id='log'></div>"
        f"<script>{JS}</script></body></html>"
    )
