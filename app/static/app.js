const form = document.querySelector('#agent-form');
const requestField = document.querySelector('#request');
const characterCount = document.querySelector('#character-count');
const runButton = document.querySelector('#run-button');
const activity = document.querySelector('#activity');
const results = document.querySelector('#results');
const errorMessage = document.querySelector('#error-message');
const progressBar = document.querySelector('#progress-bar');
const activityTitle = document.querySelector('#activity-title');
const escapeHtml = (value = '') => String(value).replace(/[&<>'"]/g, char => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', "'":'&#039;', '"':'&quot;' })[char]);

requestField.addEventListener('input', () => { characterCount.textContent = `${requestField.value.length} / 1500`; });

function setStage(stageName, percent, message) {
  const current = ['plan', 'compose', 'review', 'deliver'].indexOf(stageName);
  document.querySelectorAll('.stage').forEach((stage, index) => {
    stage.classList.toggle('active', index === current);
    stage.classList.toggle('done', index < current);
  });
  progressBar.style.width = `${percent}%`;
  activityTitle.textContent = message;
}

function showWorkingState() {
  activity.classList.remove('hidden');
  results.classList.add('hidden');
  errorMessage.classList.add('hidden');
  document.querySelector('.spinner').classList.remove('hidden');
  setStage('plan', 12, 'Creating a focused execution plan');
  const stages = [['compose', 44, 'Composing your document sections'], ['review', 72, 'Reviewing content for clarity and quality']];
  let step = 0;
  return window.setInterval(() => { if (step < stages.length) setStage(...stages[step++]); }, 4200);
}

function displayResult(data) {
  const plan = data.execution_plan || {};
  const tasks = Array.isArray(plan.tasks) ? plan.tasks : [];
  const documentSections = data.generated_document || {};
  document.querySelector('#document-title').textContent = plan.document_type || 'Your document is ready';
  document.querySelector('#result-summary').textContent = `${tasks.length} completed section${tasks.length === 1 ? '' : 's'} · reviewed and ready to share`;
  document.querySelector('#plan-goal').textContent = plan.goal || data.request || 'Your requested document.';
  const assumptions = Array.isArray(plan.assumptions) ? plan.assumptions : [];
  document.querySelector('#assumptions').innerHTML = assumptions.length ? `<div class="assumption-label">Working assumptions</div>${assumptions.map(escapeHtml).join('<br />')}` : '';
  document.querySelector('#task-list').innerHTML = tasks.map((task, index) => `<article class="task"><span class="task-icon">✓</span><div><b>${escapeHtml(task.title || `Section ${index + 1}`)}</b><span>${escapeHtml(task.description || 'Completed')}</span></div></article>`).join('');
  const sections = Object.entries(documentSections);
  document.querySelector('#section-count').textContent = `${sections.length} section${sections.length === 1 ? '' : 's'}`;
  document.querySelector('#document-preview').innerHTML = sections.map(([title, content]) => `<article class="section"><h4>${escapeHtml(title)}</h4><p>${escapeHtml(content)}</p></article>`).join('') || '<p>No preview was returned.</p>';
  const filename = String(data.document_path || '').split(/[\\/]/).pop();
  const download = document.querySelector('#download-link');
  if (filename) {
    download.href = `/documents/${encodeURIComponent(filename)}`;
    download.setAttribute('download', filename);
    download.classList.remove('hidden');
  } else download.classList.add('hidden');
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const request = requestField.value.trim();
  if (!request) return;
  runButton.disabled = true;
  runButton.querySelector('span').textContent = 'Agent is working';
  const animation = showWorkingState();
  activity.scrollIntoView({ behavior: 'smooth', block: 'center' });
  try {
    const response = await fetch('/agent', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ request }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'The agent could not complete this request.');
    window.clearInterval(animation);
    setStage('deliver', 100, 'Your document is ready to download');
    document.querySelector('.spinner').classList.add('hidden');
    displayResult(data);
    results.classList.remove('hidden');
    window.setTimeout(() => results.scrollIntoView({ behavior: 'smooth', block: 'start' }), 250);
  } catch (error) {
    window.clearInterval(animation);
    activity.classList.add('hidden');
    errorMessage.textContent = error.message || 'Something went wrong. Please check Ollama and try again.';
    errorMessage.classList.remove('hidden');
  } finally {
    runButton.disabled = false;
    runButton.querySelector('span').textContent = 'Start building';
  }
});
