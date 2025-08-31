const cfg = { dailyNewLimit: 0, hideAnswer: true };
function esc(s) { return (s || '').replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" }[c])); }
function humanNext(next) { if (!next) return '未安排'; const t = new Date(); t.setHours(0, 0, 0, 0); const n = new Date(next + 'T00:00:00'); const diff = Math.round((n - t) / 86400000); if (diff === 0) return '今天'; if (diff === 1) return '明天'; if (diff < 0) return `已过 ${-diff} 天`; return `${diff} 天后`; }

async function getCfg() { const r = await fetch('/api/cfg'); const j = await r.json(); cfg.dailyNewLimit = j.dailyNewLimit; cfg.hideAnswer = j.hideAnswer; document.getElementById('learn-quota').textContent = j.dailyNewLimit; }

let ALL = [];
async function loadCards() { const r = await fetch('/api/cards'); ALL = await r.json(); renderLibrary(); renderReview(); renderLearn(); }

// enrich
let EDIT_ID = null;
const add_word = document.getElementById('add-word');
const add_translation = document.getElementById('add-translation');
const add_example = document.getElementById('add-example');
const add_phonetic = document.getElementById('add-phonetic');
const add_audio = document.getElementById('add-audio');
const add_image = document.getElementById('add-image');

document.getElementById('btn-enrich').addEventListener('click', async () => {
  const w = add_word.value.trim(); if (!w) { alert('先输入单词'); return; }
  const r = await fetch('/api/enrich?word=' + encodeURIComponent(w)); const j = await r.json(); if (!j.ok) { alert(j.error || '获取失败'); return; }
  if (j.data.translation) add_translation.value = j.data.translation;
  if (j.data.example) add_example.value = j.data.example;
  if (j.data.phonetic) add_phonetic.value = j.data.phonetic;
  if (j.data.audioUrl) add_audio.value = j.data.audioUrl;
  if (j.data.imageUrl) add_image.value = j.data.imageUrl;
});

document.getElementById('add-form').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const payload = {
    id: EDIT_ID,
    word: add_word.value.trim(),
    translation: add_translation.value.trim(),
    example: add_example.value.trim(),
    phonetic: add_phonetic.value.trim(),
    audioUrl: add_audio.value.trim(),
    imageUrl: add_image.value.trim()
  };
  const url = EDIT_ID ? '/api/update' : '/api/add';
  const r = await fetch(url, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  if(!r.ok){
    const j = await r.json();
    alert(j.error || '保存失败');
    return;
  }
  EDIT_ID = null;
  e.target.reset();
  await loadCards();
});


function renderLibrary() { const q = (document.getElementById('search-input').value || '').toLowerCase().trim(); const f = document.getElementById('filter-status').value; const t = new Date(); t.setHours(0, 0, 0, 0); const body = document.getElementById('lib-body'); body.innerHTML = ''; let list = [...ALL]; if (q) { list = list.filter(c => (c.word || '').toLowerCase().includes(q) || (c.translation || '').toLowerCase().includes(q)); } if (f !== 'all') { if (f === 'overdue') { list = list.filter(c => c.nextReview && new Date(c.nextReview) < t); } else { list = list.filter(c => (c.status || 'new') === f); } } list.sort((a, b) => (a.word || '').localeCompare(b.word || '')); for (const c of list) { const tr = document.createElement('tr'); tr.className = 'border-b'; tr.innerHTML = `
  <td class='py-2 pr-2 font-medium'>${esc(c.word)}</td>
  <td class='py-2 pr-2'>${esc(c.translation)}</td>
  <td class='py-2 pr-2'>${esc(c.nextReview?humanNext(c.nextReview):'未安排')}</td>
  <td class='py-2 pr-2'>${esc(c.status||'new')}</td>
  <td class='py-2 pr-2 whitespace-nowrap'>
    <button class='text-blue-600 hover:underline mr-2' onclick='quickReviewById(${c.id})'>复习</button>
    <button class='text-gray-700 hover:underline mr-2' onclick='editCardById(${c.id})'>编辑</button>
    <button class='text-red-600 hover:underline' onclick='deleteCardById(${c.id})'>删除</button>
  </td>`;
; body.appendChild(tr); } }
document.getElementById('filter-status').addEventListener('change', renderLibrary);
document.getElementById('search-input').addEventListener('input', renderLibrary);

// Review
function editCardById(id){
  const c = ALL.find(x=>x.id===id);
  if(!c) return;
  EDIT_ID = id;
  add_word.value = c.word || '';
  add_translation.value = c.translation || '';
  add_example.value = c.example || '';
  add_phonetic.value = c.phonetic || '';
  add_audio.value = c.audioUrl || '';
  add_image.value = c.imageUrl || '';
  window.scrollTo({top: 0, behavior: 'smooth'});
}


let QUEUE = [], CUR = null, ANSWER = false;
function dueList(){
  const t = new Date(); t.setHours(0,0,0,0); // 本地当天 00:00
  return ALL
    .filter(c => c.nextReview && new Date(c.nextReview + 'T00:00:00') <= t)
    .sort((a,b)=> (a.nextReview > b.nextReview ? 1 : -1));
}

function setText(id, v) { document.getElementById(id).textContent = v; }
function show(id, yes) { document.getElementById(id).classList.toggle('hidden', !yes); }
function mediaHTML(c) { let html = ''; if (c.audioUrl) { html += `<audio controls src='${esc(c.audioUrl)}' preload='none'></audio>`; } if (c.imageUrl) { html += `<img class='mt-2 h-24 rounded' src='${esc(c.imageUrl)}'/>`; } return html; }

function renderReview() { QUEUE = dueList(); setText('review-remaining', QUEUE.length); show('review-empty', QUEUE.length === 0); show('review-card', QUEUE.length > 0); if (QUEUE.length > 0) nextReview(); }
function nextReview() { CUR = QUEUE.shift(); ANSWER = !cfg.hideAnswer; setText('review-word', CUR.word); setText('review-translation', CUR.translation || ''); setText('review-example', CUR.example || ''); setText('review-reps', CUR.repetitions || 0); setText('review-ef', (CUR.ease || 2.5).toFixed(2)); document.getElementById('review-media').innerHTML = mediaHTML(CUR); document.getElementById('btn-toggle-answer').textContent = ANSWER ? '隐藏释义（空格）' : '显示释义（空格）'; show('review-translation', ANSWER); show('review-example', ANSWER && !!CUR.example); show('grade-row', ANSWER); setText('review-next', CUR.nextReview ? humanNext(CUR.nextReview) : '未安排'); setText('review-remaining', QUEUE.length + 1); }
function toggleAnswer() { ANSWER = !ANSWER; show('review-translation', ANSWER); show('review-example', ANSWER && !!CUR.example); show('grade-row', ANSWER); document.getElementById('btn-toggle-answer').textContent = ANSWER ? '隐藏释义（空格）' : '显示释义（空格）'; }
async function grade(q) { await fetch('/api/review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: CUR.id, q }) }); await loadCards(); }

document.getElementById('btn-toggle-answer').addEventListener('click', toggleAnswer);
document.getElementById('btn-skip').addEventListener('click', () => { if (QUEUE.length > 0) nextReview(); else renderReview(); });
document.querySelectorAll('#grade-row [data-q]').forEach(btn => btn.addEventListener('click', () => grade(parseInt(btn.dataset.q))));
function quickReviewById(id) {
  const card = ALL.find(c => c.id === id);
  if (!card) return;
  // 将该卡片放到复习队列首位；不修改 nextReview
  QUEUE = [card, ...dueList().filter(c => c.id !== id)];
  setText('review-remaining', QUEUE.length);
  show('review-empty', false);
  show('review-card', true);
  nextReview();
}


// Learn
let LQ = [], LCUR = null, LANS = false;
function newList() { return ALL.filter(c => (c.status || 'new') === 'new'); }
function renderLearn() { LQ = newList(); document.getElementById('learn-total').textContent = LQ.length; document.getElementById('learn-index').textContent = '0'; show('learn-empty', LQ.length === 0); show('learn-card', LQ.length > 0); if (LQ.length > 0) nextLearn(); }
function nextLearn() { LCUR = LQ.shift(); LANS = false; setText('learn-index', ((parseInt(document.getElementById('learn-total').textContent) || 0) - LQ.length)); setText('learn-word', LCUR.word); setText('learn-translation', LCUR.translation || ''); setText('learn-example', LCUR.example || ''); document.getElementById('learn-media').innerHTML = mediaHTML(LCUR); show('learn-translation', false); show('learn-example', !!LCUR.example && false); show('learn-actions', false); document.getElementById('btn-learn-toggle').textContent = '显示释义'; }
function learnToggle() { LANS = !LANS; show('learn-translation', LANS); show('learn-example', LANS && !!LCUR.example); show('learn-actions', LANS); document.getElementById('btn-learn-toggle').textContent = LANS ? '隐藏释义' : '显示释义'; }
async function learnIntroduce(mode) { const r = await fetch('/api/introduce', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: LCUR.id, mode }) }); if (!r.ok) { const j = await r.json(); alert(j.error || '失败'); return; } await loadCards(); }

document.getElementById('btn-learn-toggle').addEventListener('click', learnToggle);
document.getElementById('btn-learn-skip').addEventListener('click', () => { if (LQ.length > 0) nextLearn(); else renderLearn(); });
document.getElementById('btn-learn-introduce').addEventListener('click', () => learnIntroduce('tomorrow'));
document.getElementById('btn-learn-hard').addEventListener('click', () => learnIntroduce('short'));

// Hotkeys
document.addEventListener('keydown', (e) => { if (e.code === 'Space') { const reviewVisible = !document.getElementById('review-card').classList.contains('hidden'); const learnVisible = !document.getElementById('learn-card').classList.contains('hidden'); if (reviewVisible) { e.preventDefault(); toggleAnswer(); } else if (learnVisible) { e.preventDefault(); learnToggle(); } } if (/^[0-5]$/.test(e.key)) { const reviewVisible = !document.getElementById('review-card').classList.contains('hidden'); if (reviewVisible && ANSWER) { grade(parseInt(e.key)); } } });

(async function () { await getCfg(); await loadCards(); })();

async function deleteCardById(id) {
  if (!confirm('确认删除该单词？不可恢复')) return;
  const r = await fetch('/api/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id })
  });
  if (!r.ok) {
    const j = await r.json();
    alert(j.error || '删除失败');
    return;
  }
  await loadCards();
}
