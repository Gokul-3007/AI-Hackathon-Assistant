const navButtons = document.querySelectorAll('.nav-link');
const sections = document.querySelectorAll('.content-section');
const themeToggle = document.getElementById('theme-toggle');
const themeToggleLabel = document.getElementById('theme-toggle-label');

function applyTheme(theme) {
  const selectedTheme = theme === 'dark' ? 'dark' : 'light';
  document.documentElement.dataset.theme = selectedTheme;
  themeToggle.setAttribute('aria-pressed', String(selectedTheme === 'dark'));
  themeToggle.setAttribute(
    'aria-label',
    `Switch to ${selectedTheme === 'dark' ? 'light' : 'dark'} theme`,
  );
  themeToggleLabel.textContent = `${selectedTheme === 'dark' ? 'Light' : 'Dark'} mode`;
  document.querySelector('meta[name="theme-color"]').content =
    selectedTheme === 'dark' ? '#0b1020' : '#f4f7fb';
}

let savedTheme = 'light';
try {
  savedTheme = localStorage.getItem('hackathon-theme') || savedTheme;
} catch (error) {
  console.warn('Could not read the saved theme preference.', error);
}
applyTheme(savedTheme);

themeToggle.addEventListener('click', () => {
  const nextTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  applyTheme(nextTheme);
  try {
    localStorage.setItem('hackathon-theme', nextTheme);
  } catch (error) {
    console.warn('Could not save the theme preference.', error);
  }
});

navButtons.forEach((button) => {
  button.addEventListener('click', () => {
    navButtons.forEach((nav) => nav.classList.remove('active'));
    sections.forEach((section) => section.classList.remove('active'));
    button.classList.add('active');
    const target = document.getElementById(button.dataset.target);
    if (target) target.classList.add('active');
  });
});

function setStatus(message) {
  const box = document.getElementById('status-box');
  if (box) box.textContent = message;
}

function renderMessage(containerId, message, type = 'info') {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = `<div class="alert ${type}">${escapeHtml(message)}</div>`;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[character]);
}

function appendChatMessage(role, message, options = {}) {
  const chatWindow = document.getElementById('chat-window');
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  let displayMessage = String(message ?? '').replace(/\*\*(.*?)\*\*/g, '$1');
  displayMessage = displayMessage.replace(/^#{1,6}\s+/gm, '').replace(/^\s*[-*]\s+/gm, '• ');
  if (role === 'assistant' && displayMessage.length > 700) {
    displayMessage = `${displayMessage.slice(0, 700).trimEnd()}… (older reply shortened)`;
  }
  bubble.textContent = displayMessage;
  if (options.typing) {
    bubble.classList.add('typing');
    bubble.setAttribute('aria-label', 'Mentor is replying');
  }
  chatWindow.appendChild(bubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return bubble;
}

function showSection(targetId) {
  navButtons.forEach((nav) => {
    const active = nav.dataset.target === targetId;
    nav.classList.toggle('active', active);
  });
  sections.forEach((section) => {
    section.classList.toggle('active', section.id === targetId);
  });
}

let dashboardProject = {};

function updateDashboard(project = {}) {
  dashboardProject = { ...dashboardProject, ...project };
  const stages = {
    problem: Boolean(dashboardProject.selected_problem && Object.keys(dashboardProject.selected_problem).length),
    solution: Boolean(dashboardProject.selected_solution && Object.keys(dashboardProject.selected_solution).length),
    technology: Boolean(dashboardProject.tech_stack && Object.keys(dashboardProject.tech_stack).length),
    pitch: Boolean(dashboardProject.pitch && Array.isArray(dashboardProject.pitch.slides) && dashboardProject.pitch.slides.length),
  };

  Object.entries(stages).forEach(([stage, complete]) => {
    const status = document.querySelector(`[data-stage-status="${stage}"]`);
    const card = status.closest('.stat-card');
    status.textContent = complete ? '✓ Completed' : '○ Pending';
    card.classList.toggle('pending', !complete);
    card.setAttribute(
      'aria-label',
      `${status.previousElementSibling.textContent}: ${complete ? 'Completed' : 'Pending'}`,
    );
  });

  const pitchEnabled = stages.problem;
  document.getElementById('generate-pitch-button').disabled = !pitchEnabled;
  document.getElementById('pitch-prerequisite').textContent = pitchEnabled
    ? 'Choose a pitch duration and generate a presentation for your selected problem.'
    : 'Select a problem statement first to enable pitch generation.';
}

document.querySelectorAll('.stat-card[data-target]').forEach((card) => {
  card.addEventListener('click', () => showSection(card.dataset.target));
});

function renderSelectedProblem(problem) {
  const summary = document.getElementById('selected-problem-summary');
  const generateButton = document.getElementById('generate-solutions');
  if (!problem) {
    summary.textContent = 'Select a problem statement to see it here.';
    generateButton.disabled = true;
    return;
  }

  const fields = problem.source_fields || {};
  const labels = {
    id: 'ID',
    title: 'Title',
    track: 'Track',
    domain: 'Domain',
    theme: 'Theme',
    organization: 'Organization',
    description: 'Description',
    requirements: 'Requirements',
    expected_outcome: 'Expected Outcome',
    constraints: 'Constraints',
  };
  const details = Object.entries(labels)
    .filter(([key]) => fields[key])
    .map(([key, label]) => `<p><strong>${label} (from uploaded file):</strong> ${escapeHtml(fields[key])}</p>`)
    .join('');
  summary.innerHTML = `
    <h4>Selected problem statement</h4>
    ${details || `<p>${escapeHtml(problem.title || 'Selected problem')}</p>`}
  `;
  generateButton.disabled = false;
}

function renderProblemList(items, selectedProblem = null) {
  const container = document.getElementById('problem-results');
  if (!items || !items.length) {
    container.innerHTML = '<p>No problem statements were generated.</p>';
    return;
  }

  const sourceLabels = {
    id: 'Problem Statement ID',
    title: 'Title',
    track: 'Track',
    organization: 'Organization',
    domain: 'Domain',
    theme: 'Theme',
    description: 'Description',
    requirements: 'Requirements',
    expected_outcome: 'Expected Outcome',
    constraints: 'Constraints',
    additional_information: 'Additional Information',
  };

  container.innerHTML = items.map((item) => {
    const fields = item.source_fields || {};
    const sourceDetails = Object.entries(sourceLabels)
      .filter(([key]) => fields[key])
      .map(([key, label]) => `<p><strong>${label} (from file):</strong> ${escapeHtml(fields[key])}</p>`)
      .join('');
    const title = fields.title || 'Title not found in uploaded file';
    const identity = fields.id ? `<span>ID: ${escapeHtml(fields.id)}</span>` : '';
    const domain = fields.theme
      ? `<span>Theme: ${escapeHtml(fields.theme)}</span>`
      : fields.domain ? `<span>Domain: ${escapeHtml(fields.domain)}</span>` : '';
    return `
      <div class="problem-item">
        <h4>${escapeHtml(title)}</h4>
        <div class="meta">
          ${identity}
          ${domain}
          <span>Team fit: ${escapeHtml(item.compatibility)} (${escapeHtml(item.score)}/100)</span>
        </div>
        <h5>Details extracted from the uploaded file</h5>
        ${sourceDetails || '<p>No labeled details were extracted from this statement.</p>'}
        <h5>Team-fit assessment (recommendation)</h5>
        <p><strong>Reasoning:</strong> ${escapeHtml(item.reasoning)}</p>
        <p><strong>AI/ML evidence:</strong> ${escapeHtml(item.ai_scope)}</p>
        <button class="select-button" data-selection-key="${escapeHtml(item.selection_key || fields.id || '')}">
          ${selectedProblem && (selectedProblem.selection_key === item.selection_key || selectedProblem.id === item.id) ? 'Selected' : 'Select this problem'}
        </button>
      </div>
    `;
  }).join('');

  container.querySelectorAll('[data-selection-key]').forEach((button) => {
    button.addEventListener('click', async () => {
      const formData = new FormData();
      formData.append('selection_key', button.dataset.selectionKey);
      button.disabled = true;
      button.textContent = 'Selecting…';
      try {
        const response = await fetch('/api/select-problem', {
          method: 'POST',
          body: formData,
        });
        const result = await response.json();
        if (!response.ok || result.status !== 'success') {
          throw new Error(result.message || 'Problem selection failed.');
        }
        renderSelectedProblem(result.selected_problem);
        ['solution-results', 'tech-results', 'pitch-results'].forEach((id) => {
          document.getElementById(id).replaceChildren();
        });
        renderProblemList(items, result.selected_problem);
        updateDashboard({
          selected_problem: result.selected_problem,
          selected_solution: {},
          tech_stack: {},
          pitch: {},
        });
        setStatus('Problem selected. Continue to Solution Generator.');
        showSection('solution-generator');
      } catch (error) {
        button.disabled = false;
        button.textContent = 'Select this problem';
        setStatus('Problem selection failed');
        renderMessage('problem-results', error.message, 'error');
      }
    });
  });
}

function renderSolutions(items, generationMode = 'groq', selectedSolution = {}) {
  const container = document.getElementById('solution-results');
  if (!items || !items.length) {
    container.innerHTML = '<p>No solutions were generated.</p>';
    return;
  }

  const fallbackNotice = generationMode === 'local_fallback'
    ? '<div class="generation-notice"><strong>These are older local drafts, not verified solutions.</strong> They may not match the selected problem. Generate solutions again to get problem-specific options.</div>'
    : '';

  container.innerHTML = `${fallbackNotice}${items.map((item) => `
    <div class="solution-item">
      <h4>${escapeHtml(item.name)}</h4>
      <p><strong>Overview:</strong> ${escapeHtml(item.overview)}</p>
      <p><strong>Source requirement addressed:</strong> ${escapeHtml(item.source_requirement_addressed)}</p>
      <p><strong>Target Users:</strong> ${escapeHtml(item.target_users)}</p>
      <p><strong>Core Functionality:</strong> ${escapeHtml(item.core_functionality)}</p>
      <p><strong>Technologies:</strong> ${escapeHtml(Array.isArray(item.required_technologies) ? item.required_technologies.join(', ') : item.required_technologies)}</p>
      <p><strong>AI/ML Components:</strong> ${escapeHtml(Array.isArray(item.ai_ml_components) ? item.ai_ml_components.join(', ') : item.ai_ml_components)}</p>
      <button class="select-button" data-solution-name="${escapeHtml(item.name)}" ${selectedSolution.name === item.name ? 'disabled' : ''}>
        ${selectedSolution.name === item.name ? 'Selected' : 'Select this solution'}
      </button>
    </div>
  `).join('')}`;

  document.querySelectorAll('[data-solution-name]').forEach((button) => {
    button.addEventListener('click', async () => {
      const formData = new FormData();
      formData.append('solution_name', button.dataset.solutionName);
      button.disabled = true;
      try {
        const response = await fetch('/api/select-solution', {
          method: 'POST',
          body: formData,
        });
        const result = await response.json();
        if (!response.ok || result.status !== 'success') {
          throw new Error(result.message || 'Solution selection failed.');
        }
        document.querySelectorAll('[data-solution-name]').forEach((option) => {
          option.disabled = option === button;
          option.textContent = option === button ? 'Selected' : 'Select this solution';
        });
        document.getElementById('tech-results').replaceChildren();
        document.getElementById('pitch-results').replaceChildren();
        updateDashboard({
          selected_solution: result.selected_solution,
          tech_stack: {},
          pitch: {},
        });
        setStatus(result.message || 'Solution selected');
      } catch (error) {
        button.disabled = false;
        setStatus('Solution selection failed');
        renderMessage('solution-results', error.message, 'error');
      }
    });
  });
}

function renderTech(item) {
  const container = document.getElementById('tech-results');
  if (!item || !Object.keys(item).length) {
    container.innerHTML = '<p>No technology recommendations available yet.</p>';
    return;
  }

  const sections = Object.entries(item).map(([key, value]) => {
    if (Array.isArray(value)) {
      return `<div class="tech-item"><h4>${key}</h4><ul>${value.map((entry) => typeof entry === 'string' ? `<li>${entry}</li>` : `<li>${entry.Technology || key}: ${entry.Why || ''}</li>`).join('')}</ul></div>`;
    }
    return `<div class="tech-item"><h4>${key}</h4><p>${value}</p></div>`;
  }).join('');

  container.innerHTML = sections;
}

function renderPitch(data) {
  const container = document.getElementById('pitch-results');
  if (!data || !data.slides) {
    container.innerHTML = '<p>No pitch deck generated.</p>';
    return;
  }

  container.innerHTML = `
    <h4>${escapeHtml(data.project_name)}</h4>
    <p><strong>Tagline:</strong> ${escapeHtml(data.tagline)}</p>
    ${data.slides.map((slide, index) => `
      <div class="slide-item">
        <h5>Slide ${index + 1}: ${escapeHtml(slide.title)}</h5>
        <p>${escapeHtml(slide.content)}</p>
        <p><em>${escapeHtml(slide.script)}</em></p>
      </div>
    `).join('')}
    ${data.pitch_script ? `<details class="pitch-script"><summary>Full speaker script</summary><p>${escapeHtml(data.pitch_script)}</p></details>` : ''}
  `;
}

async function initialProjectState() {
  const response = await fetch('/api/project-state');
  const data = await response.json();
  const project = data.project || {};
  updateDashboard(project);
  const upload = project.uploaded_documents && project.uploaded_documents[0];
  const analyzeButton = document.getElementById('analyze-problems-button');
  if (upload) {
    const count = upload.problem_statements_detected || 0;
    document.getElementById('upload-result').innerHTML = `
      <p><strong>File:</strong> ${escapeHtml(upload.name)}</p>
      <p><strong>Status:</strong> ${escapeHtml(upload.status)}</p>
      <p><strong>Problem statements detected:</strong> ${escapeHtml(count)}</p>
    `;
    analyzeButton.disabled = count === 0;
  }
  if (project.problem_statements && project.problem_statements.length) {
    renderProblemList(project.problem_statements, project.selected_problem);
  }
  if (project.selected_problem && Object.keys(project.selected_problem).length) {
    renderSelectedProblem(project.selected_problem);
  }
  const selectedKey = project.selected_problem &&
    (project.selected_problem.selection_key || project.selected_problem.id);
  if (
    project.solutions &&
    project.solutions.length &&
    project.solutions_for_selection_key &&
    project.solutions_for_selection_key === selectedKey
  ) {
    if (project.solution_generation_mode === 'local_fallback') {
      document.getElementById('solution-results').innerHTML =
        '<div class="generation-notice"><strong>Older local draft suggestions were hidden because they may not match this problem.</strong> Generate solutions again for problem-specific options.</div>';
    } else {
    renderSolutions(project.solutions, project.solution_generation_mode, project.selected_solution);
    }
  }
  if (project.tech_stack && Object.keys(project.tech_stack).length) {
    renderTech(project.tech_stack);
  }
  if (project.pitch && project.pitch.slides) {
    renderPitch(project.pitch);
  }
  if (project.chat_history && project.chat_history.length) {
    const chatWindow = document.getElementById('chat-window');
    chatWindow.replaceChildren();
    project.chat_history.slice(-12).forEach((entry) => {
      appendChatMessage(entry.role === 'user' ? 'user' : 'assistant', entry.message);
    });
  }
}

window.addEventListener('DOMContentLoaded', initialProjectState);

function clearAnalysisResults() {
  ['problem-results', 'solution-results', 'tech-results', 'pitch-results'].forEach((id) => {
    const container = document.getElementById(id);
    if (container) container.replaceChildren();
  });
}

const fileInput = document.querySelector('#upload-form input[type="file"]');
const uploadResult = document.getElementById('upload-result');
const analyzeProblemsButton = document.getElementById('analyze-problems-button');

fileInput.addEventListener('change', () => {
  if (!fileInput.files.length) return;
  clearAnalysisResults();
  uploadResult.replaceChildren();
  analyzeProblemsButton.disabled = true;
  setStatus('Upload the selected document to analyze it');
});

document.getElementById('upload-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  clearAnalysisResults();
  analyzeProblemsButton.disabled = true;
  uploadResult.textContent = 'Uploading and extracting document text…';
  setStatus('Uploading document…');
  const formData = new FormData(event.target);
  try {
    const response = await fetch('/api/upload-document', { method: 'POST', body: formData });
    const result = await response.json();
    const status = result.documents && result.documents.length ? result.documents[0].status : '';
    const count = result.problem_count === undefined ? '' : `<p><strong>Problem statements detected:</strong> ${escapeHtml(result.problem_count)}</p>`;
    uploadResult.innerHTML = `<p>${escapeHtml(result.message || 'Upload failed')}</p>${status ? `<p><strong>Status:</strong> ${escapeHtml(status)}</p>` : ''}${count}`;
    analyzeProblemsButton.disabled = result.status !== 'success' || !result.problem_count;
    if (result.status === 'success') {
      updateDashboard({
        selected_problem: {},
        selected_solution: {},
        tech_stack: {},
        pitch: {},
      });
    }
    setStatus(result.message || 'Upload failed');
  } catch (error) {
    uploadResult.textContent = `Upload failed: ${error.message}. Check the connection and try again.`;
    setStatus('Document upload failed');
  }
});

document.getElementById('problem-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const container = document.getElementById('problem-results');
  container.textContent = 'Analyzing the uploaded document…';
  try {
    const response = await fetch('/api/analyze-problem-statements', { method: 'POST', body: formData });
    const result = await response.json();
    if (result.status === 'success') {
      renderProblemList(result.problem_statements);
    } else {
      renderMessage('problem-results', result.message || 'Problem analysis failed', 'error');
    }
    setStatus(result.message || 'Problem analysis complete');
  } catch (error) {
    renderMessage('problem-results', `Analysis failed: ${error.message}. Check the connection and try again.`, 'error');
    setStatus('Problem analysis failed');
  }
});

document.getElementById('generate-solutions').addEventListener('click', async () => {
  const button = document.getElementById('generate-solutions');
  const resultContainer = document.getElementById('solution-results');
  button.disabled = true;
  resultContainer.textContent = 'Generating solutions for the selected problem…';
  try {
    const response = await fetch('/api/generate-solutions', { method: 'POST' });
    const result = await response.json();
    if (!response.ok || result.status !== 'success') {
      throw new Error(result.message || 'Solution generation failed.');
    }
    document.getElementById('tech-results').replaceChildren();
    document.getElementById('pitch-results').replaceChildren();
    updateDashboard({ selected_solution: {}, tech_stack: {}, pitch: {} });
    renderSolutions(result.solutions, result.generation_mode);
    setStatus(result.message || 'Solutions generated');
  } catch (error) {
    renderMessage('solution-results', error.message, 'error');
    setStatus('Solution generation failed');
  } finally {
    button.disabled = !document.getElementById('selected-problem-summary').querySelector('h4');
  }
});

document.getElementById('tech-stack-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  try {
    const response = await fetch('/api/generate-tech-stack', { method: 'POST', body: formData });
    const result = await response.json();
    if (!response.ok || result.status !== 'success') {
      throw new Error(result.message || 'Technology stack generation failed.');
    }
    document.getElementById('pitch-results').replaceChildren();
    renderTech(result.tech_stack);
    updateDashboard({ tech_stack: result.tech_stack, pitch: {} });
    setStatus(result.message || 'Technology stack generated');
  } catch (error) {
    renderMessage('tech-results', error.message || 'Technology stack generation failed.', 'error');
    setStatus('Technology stack generation failed');
  }
});

document.getElementById('pitch-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = document.getElementById('generate-pitch-button');
  const results = document.getElementById('pitch-results');
  if (!dashboardProject.selected_problem || !Object.keys(dashboardProject.selected_problem).length) {
    renderMessage('pitch-results', 'Select a problem statement before generating a pitch.', 'error');
    return;
  }

  button.disabled = true;
  button.textContent = 'Generating pitch…';
  results.textContent = 'Building your pitch deck…';
  const formData = new FormData(event.target);
  try {
    const response = await fetch('/api/generate-pitch', { method: 'POST', body: formData });
    const result = await response.json();
    if (!response.ok || result.status !== 'success') {
      throw new Error(result.message || 'Pitch generation failed.');
    }
    renderPitch(result.pitch);
    updateDashboard({ pitch: result.pitch });
    setStatus(result.message || 'Pitch deck generated');
  } catch (error) {
    renderMessage('pitch-results', error.message || 'Pitch generation failed. Check the connection and try again.', 'error');
    setStatus('Pitch generation failed');
  } finally {
    button.textContent = 'Generate Pitch';
    button.disabled = !dashboardProject.selected_problem || !Object.keys(dashboardProject.selected_problem).length;
  }
});

document.getElementById('chat-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;

  const sendButton = document.getElementById('chat-send-button');
  appendChatMessage('user', message);
  input.value = '';
  input.disabled = true;
  sendButton.disabled = true;
  const typingBubble = appendChatMessage('assistant', 'Thinking…', { typing: true });

  try {
    const formData = new FormData();
    formData.append('message', message);
    const response = await fetch('/api/chat', { method: 'POST', body: formData });
    const result = await response.json();
    if (!response.ok || result.status !== 'success') {
      throw new Error(result.message || 'I could not send that message. Please try again.');
    }
    typingBubble.remove();
    appendChatMessage('assistant', result.answer);
    setStatus('Chat response ready');
  } catch (error) {
    typingBubble.remove();
    appendChatMessage('assistant', error.message || 'I could not connect just now. Please try again.');
    setStatus('Chat unavailable');
  } finally {
    input.disabled = false;
    sendButton.disabled = false;
    input.focus();
  }
});

document.querySelectorAll('.chat-suggestion').forEach((button) => {
  button.addEventListener('click', () => {
    const input = document.getElementById('chat-input');
    input.value = button.dataset.message;
    document.getElementById('chat-form').requestSubmit();
  });
});
