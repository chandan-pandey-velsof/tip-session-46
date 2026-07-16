import json
import urllib.request
import urllib.parse
import urllib.error

from django.conf import settings
from django.http import HttpResponse, JsonResponse

TIP_API_URL = settings.TIP_API_URL
TIP_API_TOKEN = settings.TIP_API_TOKEN

USER_REQUEST = (
    "Build a TriangleIP Analytics Portal with a top navigation bar containing three tabs: "
    "'Patent Lookup', 'Examiner Analysis', and 'Art Unit Predictor'. Clicking a tab switches "
    "the main content area to that feature without a full page reload. Patent Lookup tab: a "
    "number search box that calls patent-lookup search and shows patent title, status, filing "
    "date, examiner. Examiner Analysis tab: an examiner name search with live suggestions "
    "(min 2 chars) that on select calls the examiner overview API and shows total applications, "
    "grant rate, average pendency. Art Unit Predictor tab: a textarea for an invention "
    "description that calls the predictor API and lists predicted group art units with ratings. "
    "Each tab manages its own state and error handling. Default to the Patent Lookup tab. "
    "Include a Diagnostics panel that reflects whichever tab is active. Use TIP design classes."
)

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TriangleIP Analytics Portal</title>
<link rel='stylesheet' href='/static/tip_design.css'>
<style>
  .tip-tab-bar { display:flex; gap:0; border-bottom:2px solid var(--tip-border, #e2e8f0); margin-bottom:24px; }
  .tip-tab { padding:12px 24px; cursor:pointer; font-weight:600; color:var(--tip-text-secondary, #64748b);
             border-bottom:3px solid transparent; transition:all .2s; user-select:none; }
  .tip-tab:hover { color:var(--tip-primary, #4f46e5); }
  .tip-tab.active { color:var(--tip-primary, #4f46e5); border-bottom-color:var(--tip-primary, #4f46e5); }
  .tab-panel { display:none; }
  .tab-panel.active { display:block; }
  .search-row { display:flex; gap:12px; align-items:flex-start; margin-bottom:20px; }
  .search-row input[type="text"], .search-row textarea { flex:1; padding:10px 14px; border:1px solid var(--tip-border, #e2e8f0);
    border-radius:8px; font-family:inherit; font-size:14px; outline:none; transition:border-color .2s; }
  .search-row input[type="text"]:focus, .search-row textarea:focus { border-color:var(--tip-primary, #4f46e5); }
  .search-row textarea { min-height:120px; resize:vertical; }
  .suggestions-dropdown { position:absolute; top:100%; left:0; right:0; background:#fff; border:1px solid var(--tip-border, #e2e8f0);
    border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,.1); z-index:100; max-height:240px; overflow-y:auto; }
  .suggestion-item { padding:10px 14px; cursor:pointer; font-size:14px; border-bottom:1px solid #f1f5f9; }
  .suggestion-item:hover { background:#f8fafc; }
  .suggestion-item:last-child { border-bottom:none; }
  .suggestion-item .sug-title { font-weight:600; color:var(--tip-text, #1e293b); }
  .suggestion-item .sug-sub { font-size:12px; color:var(--tip-text-secondary, #64748b); margin-top:2px; }
  .search-wrapper { position:relative; flex:1; }
  .tip-stats-row { display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:16px; margin-bottom:24px; }
  .tip-card-value { font-size:28px; font-weight:700; color:var(--tip-primary, #4f46e5); }
  .tip-card-label { font-size:13px; color:var(--tip-text-secondary, #64748b); margin-top:4px; }
  .error-card { background:#fef2f2; border:1px solid #fecaca; border-radius:12px; padding:20px; color:#991b1b; }
  .error-card h3 { margin:0 0 8px; font-size:16px; }
  .error-card p { margin:0; font-size:14px; }
  .gau-list { list-style:none; padding:0; margin:0; }
  .gau-list li { padding:12px 16px; border-bottom:1px solid var(--tip-border, #e2e8f0); display:flex; justify-content:space-between; align-items:center; }
  .gau-list li:last-child { border-bottom:none; }
  .gau-code { font-weight:700; font-size:15px; color:var(--tip-text, #1e293b); }
  .gau-title { font-size:13px; color:var(--tip-text-secondary, #64748b); margin-top:2px; }
  .rating-stars { font-size:18px; color:#f59e0b; }
  .patent-field { margin-bottom:12px; }
  .patent-field-label { font-size:12px; text-transform:uppercase; letter-spacing:.5px; color:var(--tip-text-secondary, #64748b); margin-bottom:2px; }
  .patent-field-value { font-size:15px; color:var(--tip-text, #1e293b); font-weight:500; }
  .loading { text-align:center; padding:40px; color:var(--tip-text-secondary, #64748b); }
  .empty-state { text-align:center; padding:60px 20px; color:var(--tip-text-secondary, #64748b); }
  .empty-state p { font-size:15px; margin:8px 0; }
  .empty-state .empty-icon { font-size:48px; margin-bottom:12px; opacity:.4; }
  details summary { cursor:pointer; font-weight:600; font-size:15px; padding:8px 0; }
  details summary:hover { color:var(--tip-primary, #4f46e5); }
  .diag-table { width:100%; border-collapse:collapse; font-size:13px; }
  .diag-table th { text-align:left; padding:8px 12px; background:#f8fafc; border-bottom:1px solid var(--tip-border, #e2e8f0); font-weight:600; color:var(--tip-text-secondary, #64748b); }
  .diag-table td { padding:8px 12px; border-bottom:1px solid #f1f5f9; color:var(--tip-text, #1e293b); word-break:break-all; }
  .diag-section { margin-top:16px; }
  .diag-section h4 { font-size:14px; margin:0 0 8px; color:var(--tip-text, #1e293b); }
  .allowance-bar { height:8px; border-radius:4px; background:#e2e8f0; overflow:hidden; margin-top:4px; }
  .allowance-bar-fill { height:100%; border-radius:4px; background:var(--tip-primary, #4f46e5); transition:width .4s; }
</style>
</head>
<body>
<div class='tip-page'>
  <nav class='tip-navbar'>
    <a class='tip-navbar-brand' href='/'>TriangleIP Analytics Portal</a>
  </nav>

  <h1 class='tip-page-title'>Analytics Portal</h1>

  <div class='tip-tab-bar'>
    <div class='tip-tab active' data-tab='patent-lookup' onclick='switchTab("patent-lookup")'>Patent Lookup</div>
    <div class='tip-tab' data-tab='examiner-analysis' onclick='switchTab("examiner-analysis")'>Examiner Analysis</div>
    <div class='tip-tab' data-tab='art-unit-predictor' onclick='switchTab("art-unit-predictor")'>Art Unit Predictor</div>
  </div>

  <!-- Patent Lookup Tab -->
  <div id='tab-patent-lookup' class='tab-panel active'>
    <div class='tip-card'>
      <h2 style='margin:0 0 16px;font-size:18px;'>Search Patent</h2>
      <div class='search-row'>
        <div class='search-wrapper'>
          <input type='text' id='patent-input' placeholder='Enter patent or application number (e.g. 16/687,273, US8623891, EP1514569A1)'
                 oninput='onPatentInput(this.value)' onkeydown='patentInputKeydown(event)' autocomplete='off'>
          <div id='patent-suggestions' class='suggestions-dropdown' style='display:none'></div>
        </div>
        <button class='tip-btn tip-btn-primary' onclick='searchPatent()'>Search</button>
      </div>
    </div>
    <div id='patent-results'></div>
  </div>

  <!-- Examiner Analysis Tab -->
  <div id='tab-examiner-analysis' class='tab-panel'>
    <div class='tip-card'>
      <h2 style='margin:0 0 16px;font-size:18px;'>Search Examiner</h2>
      <div class='search-row'>
        <div class='search-wrapper'>
          <input type='text' id='examiner-input' placeholder='Type examiner name (min 2 characters)'
                 oninput='onExaminerInput(this.value)' onkeydown='examinerInputKeydown(event)' autocomplete='off'>
          <div id='examiner-suggestions' class='suggestions-dropdown' style='display:none'></div>
        </div>
        <button class='tip-btn tip-btn-primary' onclick='searchExaminer()'>Analyze</button>
      </div>
    </div>
    <div id='examiner-results'></div>
  </div>

  <!-- Art Unit Predictor Tab -->
  <div id='tab-art-unit-predictor' class='tab-panel'>
    <div class='tip-card'>
      <h2 style='margin:0 0 16px;font-size:18px;'>Predict Group Art Units</h2>
      <div class='search-row' style='flex-direction:column;'>
        <textarea id='predictor-text' placeholder='Describe the invention in at least 50 words...'></textarea>
        <div style='display:flex;gap:12px;'>
          <button class='tip-btn tip-btn-primary' onclick='predictGAU()'>Predict</button>
          <span id='predictor-char-count' style='font-size:13px;color:var(--tip-text-secondary,#64748b);align-self:center;'>0 words</span>
        </div>
      </div>
    </div>
    <div id='predictor-results'></div>
  </div>

  <!-- Diagnostics Panel -->
  <div class='tip-card' style='margin-top:32px;'>
    <details>
      <summary>Diagnostics</summary>
      <div id='diagnostics-content'>
        <div class='empty-state' style='padding:20px;'>
          <p>No API calls made yet. Perform a search to see diagnostics.</p>
        </div>
      </div>
    </details>
  </div>
</div>

<script>
// ── State ──
let activeTab = 'patent-lookup';
let patentDiagnostics = null;
let examinerDiagnostics = null;
let predictorDiagnostics = null;

// ── Tab switching ──
function switchTab(tabId) {
  activeTab = tabId;
  document.querySelectorAll('.tip-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabId));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab-' + tabId));
  updateDiagnostics();
}

// ── Patent Lookup ──
let patentSuggestTimeout = null;
let patentSelectedValue = '';

function onPatentInput(val) {
  patentSelectedValue = '';
  const box = document.getElementById('patent-suggestions');
  if (val.length < 5) { box.style.display = 'none'; return; }
  clearTimeout(patentSuggestTimeout);
  patentSuggestTimeout = setTimeout(() => fetchPatentSuggestions(val), 300);
}

async function fetchPatentSuggestions(q) {
  const box = document.getElementById('patent-suggestions');
  try {
    const resp = await fetch('/tip-api/v1/patent-lookup/suggest?q=' + encodeURIComponent(q) + '&limit=8');
    const json = await resp.json();
    if (json.status && json.data && json.data.results && json.data.results.length > 0) {
      box.innerHTML = json.data.results.map(r =>
        '<div class="suggestion-item" data-value="' + escHtml(r.display) + '" onclick="selectPatentSuggestion(this)">'
        + '<div class="sug-title">' + escHtml(r.display) + '</div>'
        + '<div class="sug-sub">' + escHtml(r.title || '') + '</div></div>'
      ).join('');
      box.style.display = 'block';
    } else {
      box.style.display = 'none';
    }
  } catch(e) { box.style.display = 'none'; }
}

function selectPatentSuggestion(el) {
  const val = el.dataset.value;
  patentSelectedValue = val;
  document.getElementById('patent-input').value = val;
  document.getElementById('patent-suggestions').style.display = 'none';
  searchPatent();
}

function patentInputKeydown(e) {
  if (e.key === 'Enter') { e.preventDefault(); document.getElementById('patent-suggestions').style.display = 'none'; searchPatent(); }
}

async function searchPatent() {
  const input = document.getElementById('patent-input').value.trim();
  const query = patentSelectedValue || input;
  if (!query) return;
  const container = document.getElementById('patent-results');
  container.innerHTML = '<div class="loading">Searching...</div>';
  const startTime = Date.now();
  try {
    const resp = await fetch('/tip-api/v1/patent-lookup/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query })
    });
    const json = await resp.json();
    const elapsed = Date.now() - startTime;
    if (json.status && json.data && json.data.result) {
      const s = json.data.result.summary;
      patentDiagnostics = {
        request: USER_REQUEST,
        apiCalls: [{ method: 'POST', path: '/tip-api/v1/patent-lookup/search' }],
        inputParams: { query: query },
        outputParams: {
          'data.result.summary.title': s.title,
          'data.result.summary.status': s.status,
          'data.result.summary.filing_date': s.filing_date,
          'data.result.summary.examiner_name': s.examiner_name,
          'data.result.summary.patent_number': s.patent_number,
          'data.result.summary.application_type': s.application_type,
          'data.result.summary.group_art_unit': s.group_art_unit,
          'data.result.summary.first_inventor_name': s.first_inventor_name,
          'data.result.summary.first_applicant_name': s.first_applicant_name,
          'data.result.summary.entity_status': s.entity_status,
          'data.result.summary.grant_date': s.grant_date,
          'data.result.summary.earliest_publication_number': s.earliest_publication_number,
          'data.result.summary.earliest_publication_date': s.earliest_publication_date,
          'data.result.summary.class_subclass': s.class_subclass,
          'data.result.summary.application_number': s.application_number,
          'data.result.summary.docket_number': s.docket_number,
          'data.result.summary.confirmation_number': s.confirmation_number,
          'data.result.summary.status_date': s.status_date,
          'data.quota': JSON.stringify(json.data.quota)
        },
        fieldMapping: [
          ['data.result.summary.title', 'Patent Title'],
          ['data.result.summary.status', 'Status badge'],
          ['data.result.summary.filing_date', 'Filing Date'],
          ['data.result.summary.examiner_name', 'Examiner'],
          ['data.result.summary.patent_number', 'Patent Number'],
          ['data.result.summary.application_type', 'Application Type'],
          ['data.result.summary.group_art_unit', 'Group Art Unit'],
          ['data.result.summary.first_inventor_name', 'First Inventor'],
          ['data.result.summary.first_applicant_name', 'First Applicant'],
          ['data.result.summary.entity_status', 'Entity Status'],
          ['data.result.summary.grant_date', 'Grant Date'],
          ['data.result.summary.earliest_publication_number', 'Earliest Publication'],
          ['data.result.summary.earliest_publication_date', 'Publication Date'],
          ['data.result.summary.class_subclass', 'Class/Subclass'],
          ['data.result.summary.application_number', 'Application Number'],
          ['data.result.summary.docket_number', 'Docket Number'],
          ['data.result.summary.confirmation_number', 'Confirmation Number'],
          ['data.result.summary.status_date', 'Status Date'],
          ['data.quota', 'Quota info']
        ],
        responseTime: elapsed + 'ms',
        httpStatus: resp.status
      };
      renderPatentResults(s, json.data.quota);
    } else {
      const msg = json.message || 'Unknown error';
      container.innerHTML = '<div class="error-card"><h3>Search Error</h3><p>' + escHtml(msg) + '</p></div>';
      patentDiagnostics = { request: USER_REQUEST, apiCalls: [{ method:'POST', path:'/tip-api/v1/patent-lookup/search' }],
        inputParams: { query: query }, outputParams: { error: msg }, fieldMapping: [], responseTime: elapsed+'ms', httpStatus: resp.status };
    }
  } catch(e) {
    container.innerHTML = '<div class="error-card"><h3>Network Error</h3><p>' + escHtml(e.message) + '</p></div>';
    patentDiagnostics = { request: USER_REQUEST, apiCalls: [{ method:'POST', path:'/tip-api/v1/patent-lookup/search' }],
      inputParams: { query: query }, outputParams: { error: e.message }, fieldMapping: [], responseTime: (Date.now()-startTime)+'ms', httpStatus: 'N/A' };
  }
  updateDiagnostics();
}

function renderPatentResults(s, quota) {
  const statusTag = getStatusTag(s.status);
  const entityTag = s.entity_status === 'Small' ? 'tip-tag tip-tag-success' : 'tip-tag tip-tag-default';
  let html = '<div class="tip-stats-row">';
  html += '<div class="tip-card"><div class="tip-card-label">Application Number</div><div class="tip-card-value" style="font-size:20px;">' + escHtml(s.application_number || '-') + '</div></div>';
  html += '<div class="tip-card"><div class="tip-card-label">Patent Number</div><div class="tip-card-value" style="font-size:20px;">' + escHtml(s.patent_number || '-') + '</div></div>';
  html += '<div class="tip-card"><div class="tip-card-label">Status</div><div style="margin-top:8px;">' + statusTag + '</div></div>';
  html += '<div class="tip-card"><div class="tip-card-label">Entity Size</div><div style="margin-top:8px;"><span class="' + entityTag + '">' + escHtml(s.entity_status || '-') + '</span></div></div>';
  html += '</div>';

  html += '<div class="tip-card"><h3 style="margin:0 0 16px;font-size:16px;">Patent Details</h3>';
  html += '<div class="patent-field"><div class="patent-field-label">Title</div><div class="patent-field-value">' + escHtml(s.title || '-') + '</div></div>';

  const fields = [
    ['Filing Date', s.filing_date], ['Grant Date', s.grant_date], ['Status Date', s.status_date],
    ['Application Type', s.application_type], ['Examiner', s.examiner_name],
    ['Group Art Unit', s.group_art_unit], ['Class / Subclass', s.class_subclass],
    ['First Inventor', s.first_inventor_name], ['First Applicant', s.first_applicant_name],
    ['Docket Number', s.docket_number], ['Confirmation Number', s.confirmation_number],
    ['Earliest Publication', (s.earliest_publication_number || '-') + (s.earliest_publication_date ? ' (' + s.earliest_publication_date + ')' : '')]
  ];
  html += '<div class="tip-table-wrap"><table class="tip-table"><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>';
  fields.forEach(f => {
    html += '<tr><td>' + escHtml(f[0]) + '</td><td>' + escHtml(f[1] != null ? String(f[1]) : '-') + '</td></tr>';
  });
  html += '</tbody></table></div></div>';

  if (quota) {
    html += '<div class="tip-card" style="margin-top:16px;"><div class="tip-card-label">API Quota</div>';
    html += '<div style="margin-top:8px;font-size:14px;">Used: ' + quota.used + ' / ' + quota.limit + ' (Remaining: ' + quota.remaining + ')</div></div>';
  }
  document.getElementById('patent-results').innerHTML = html;
}

function getStatusTag(status) {
  if (!status) return '<span class="tip-tag tip-tag-default">Unknown</span>';
  const s = status.toLowerCase();
  if (s.includes('patent')) return '<span class="tip-tag tip-tag-success">Patented</span>';
  if (s.includes('pend') || s.includes('non-final') || s.includes('allow')) return '<span class="tip-tag tip-tag-primary">Pending</span>';
  if (s.includes('abandon')) return '<span class="tip-tag tip-tag-error">Abandoned</span>';
  if (s.includes('expir')) return '<span class="tip-tag tip-tag-warning">Expired</span>';
  return '<span class="tip-tag tip-tag-default">' + escHtml(status) + '</span>';
}

// ── Examiner Analysis ──
let examinerSuggestTimeout = null;
let examinerSelectedName = '';

function onExaminerInput(val) {
  examinerSelectedName = '';
  const box = document.getElementById('examiner-suggestions');
  if (val.length < 2) { box.style.display = 'none'; return; }
  clearTimeout(examinerSuggestTimeout);
  examinerSuggestTimeout = setTimeout(() => fetchExaminerSuggestions(val), 300);
}

async function fetchExaminerSuggestions(q) {
  const box = document.getElementById('examiner-suggestions');
  try {
    const resp = await fetch('/tip-api/v1/examiner/suggest?q=' + encodeURIComponent(q));
    const json = await resp.json();
    if (json.status && json.data && json.data.length > 0) {
      box.innerHTML = json.data.map(r =>
        '<div class="suggestion-item" data-value="' + escHtml(r.id) + '" onclick="selectExaminerSuggestion(this)">'
        + '<div class="sug-title">' + escHtml(r.text) + '</div></div>'
      ).join('');
      box.style.display = 'block';
    } else {
      box.style.display = 'none';
    }
  } catch(e) { box.style.display = 'none'; }
}

function selectExaminerSuggestion(el) {
  examinerSelectedName = el.dataset.value;
  document.getElementById('examiner-input').value = el.dataset.value;
  document.getElementById('examiner-suggestions').style.display = 'none';
  searchExaminer();
}

function examinerInputKeydown(e) {
  if (e.key === 'Enter') { e.preventDefault(); document.getElementById('examiner-suggestions').style.display = 'none'; searchExaminer(); }
}

async function searchExaminer() {
  const input = document.getElementById('examiner-input').value.trim();
  const name = examinerSelectedName || input;
  if (!name) return;
  const container = document.getElementById('examiner-results');
  container.innerHTML = '<div class="loading">Analyzing examiner...</div>';
  const startTime = Date.now();
  try {
    const resp = await fetch('/tip-api/v1/examiner/overview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ examiner_name: name })
    });
    const json = await resp.json();
    const elapsed = Date.now() - startTime;
    if (json.status && json.data && json.data.ex_rule) {
      const er = json.data.ex_rule;
      const p = er.profile || {};
      const oa = er.oa || {};
      const pend = er.pendency || {};
      examinerDiagnostics = {
        request: USER_REQUEST,
        apiCalls: [{ method: 'POST', path: '/tip-api/v1/examiner/overview' }],
        inputParams: { examiner_name: name },
        outputParams: {
          'data.ex_rule.profile.name': p.name,
          'data.ex_rule.profile.total': p.total,
          'data.ex_rule.profile.granted': p.granted,
          'data.ex_rule.profile.grant_rate_text': p.grant_rate_text,
          'data.ex_rule.profile.experience': p.experience,
          'data.ex_rule.profile.gau': p.gau,
          'data.ex_rule.profile.app_range': p.app_range,
          'data.ex_rule.oa.average_oa': oa.average_oa,
          'data.ex_rule.oa.least_oa': oa.least_oa,
          'data.ex_rule.oa.most_oa': oa.most_oa,
          'data.ex_rule.pendency.shortest': pend.shortest,
          'data.ex_rule.pendency.average': pend.average,
          'data.ex_rule.pendency.longest': pend.longest
        },
        fieldMapping: [
          ['data.ex_rule.profile.name', 'Examiner Name heading'],
          ['data.ex_rule.profile.total', 'Total Applications card'],
          ['data.ex_rule.profile.granted', 'Granted count'],
          ['data.ex_rule.profile.grant_rate_text', 'Grant Rate card'],
          ['data.ex_rule.profile.experience', 'Experience card'],
          ['data.ex_rule.profile.gau', 'GAU info'],
          ['data.ex_rule.profile.app_range', 'Application Range'],
          ['data.ex_rule.oa.average_oa', 'Avg Office Actions card'],
          ['data.ex_rule.oa.least_oa', 'Least OA'],
          ['data.ex_rule.oa.most_oa', 'Most OA'],
          ['data.ex_rule.pendency.average', 'Avg Pendency card'],
          ['data.ex_rule.pendency.shortest', 'Shortest Pendency'],
          ['data.ex_rule.pendency.longest', 'Longest Pendency']
        ],
        responseTime: elapsed + 'ms',
        httpStatus: resp.status
      };
      renderExaminerResults(p, oa, pend);
    } else {
      const msg = json.message || 'Unknown error';
      container.innerHTML = '<div class="error-card"><h3>Analysis Error</h3><p>' + escHtml(msg) + '</p></div>';
      examinerDiagnostics = { request: USER_REQUEST, apiCalls: [{ method:'POST', path:'/tip-api/v1/examiner/overview' }],
        inputParams: { examiner_name: name }, outputParams: { error: msg }, fieldMapping: [], responseTime: elapsed+'ms', httpStatus: resp.status };
    }
  } catch(e) {
    container.innerHTML = '<div class="error-card"><h3>Network Error</h3><p>' + escHtml(e.message) + '</p></div>';
    examinerDiagnostics = { request: USER_REQUEST, apiCalls: [{ method:'POST', path:'/tip-api/v1/examiner/overview' }],
      inputParams: { examiner_name: name }, outputParams: { error: e.message }, fieldMapping: [], responseTime: (Date.now()-startTime)+'ms', httpStatus: 'N/A' };
  }
  updateDiagnostics();
}

function renderExaminerResults(p, oa, pend) {
  let html = '<div class="tip-card" style="margin-bottom:16px;">';
  html += '<h3 style="margin:0 0 4px;font-size:18px;">' + escHtml(p.name || 'Examiner') + '</h3>';
  html += '<div style="font-size:13px;color:var(--tip-text-secondary,#64748b);">GAU: ' + escHtml(p.gau || '-') + ' &middot; Range: ' + escHtml(p.app_range || '-') + '</div></div>';

  html += '<div class="tip-stats-row">';
  html += '<div class="tip-card"><div class="tip-card-label">Total Applications</div><div class="tip-card-value">' + escHtml(String(p.total || 0)) + '</div></div>';
  html += '<div class="tip-card"><div class="tip-card-label">Grant Rate</div><div class="tip-card-value">' + escHtml(p.grant_rate_text || '0') + '%</div></div>';
  html += '<div class="tip-card"><div class="tip-card-label">Avg Pendency</div><div class="tip-card-value" style="font-size:22px;">' + escHtml(pend.average || '-') + '</div></div>';
  html += '<div class="tip-card"><div class="tip-card-label">Avg Office Actions</div><div class="tip-card-value">' + escHtml(String(oa.average_oa || 0)) + '</div></div>';
  html += '<div class="tip-card"><div class="tip-card-label">Experience</div><div class="tip-card-value">' + escHtml(String(p.experience || 0)) + ' yrs</div></div>';
  html += '<div class="tip-card"><div class="tip-card-label">Granted / Total</div><div class="tip-card-value" style="font-size:20px;">' + escHtml(String(p.granted || 0)) + ' / ' + escHtml(String(p.total || 0)) + '</div></div>';
  html += '</div>';

  html += '<div class="tip-card"><h3 style="margin:0 0 12px;font-size:16px;">Pendency &amp; Office Actions</h3>';
  html += '<div class="tip-table-wrap"><table class="tip-table"><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>';
  const rows = [
    ['Shortest Pendency', pend.shortest], ['Average Pendency', pend.average], ['Longest Pendency', pend.longest],
    ['Least Office Actions', oa.least_oa], ['Average Office Actions', oa.average_oa], ['Most Office Actions', oa.most_oa]
  ];
  rows.forEach(r => { html += '<tr><td>' + escHtml(r[0]) + '</td><td>' + escHtml(r[1] != null ? String(r[1]) : '-') + '</td></tr>'; });
  html += '</tbody></table></div></div>';

  document.getElementById('examiner-results').innerHTML = html;
}

// ── Art Unit Predictor ──
document.addEventListener('DOMContentLoaded', function() {
  const ta = document.getElementById('predictor-text');
  if (ta) {
    ta.addEventListener('input', function() {
      const words = this.value.trim().split(/\\s+/).filter(w => w.length > 0).length;
      document.getElementById('predictor-char-count').textContent = words + ' word' + (words !== 1 ? 's' : '');
    });
  }
});

async function predictGAU() {
  const text = document.getElementById('predictor-text').value.trim();
  if (text.split(/\\s+/).filter(w => w.length > 0).length < 50) {
    document.getElementById('predictor-results').innerHTML = '<div class="error-card"><h3>Input Too Short</h3><p>Please provide at least 50 words describing the invention.</p></div>';
    return;
  }
  const container = document.getElementById('predictor-results');
  container.innerHTML = '<div class="loading">Predicting group art units...</div>';
  const startTime = Date.now();
  try {
    const formData = new FormData();
    formData.append('data_text', text);
    formData.append('type', 'gau');
    const resp = await fetch('/tip-api/v1/predictor/predict', { method: 'POST', body: formData });
    const json = await resp.json();
    const elapsed = Date.now() - startTime;
    if (json.status && json.data) {
      const d = json.data;
      const ratingData = d.rating || [];
      const allowanceData = d.allowance || [];
      const gauTitles = d.gau_titles || {};
      const sigTerms = d.significant_terms || {};
      predictorDiagnostics = {
        request: USER_REQUEST,
        apiCalls: [{ method: 'POST (multipart/form-data)', path: '/tip-api/v1/predictor/predict' }],
        inputParams: { data_text: '(text, ' + text.length + ' chars)', type: 'gau' },
        outputParams: {
          'data.rating': JSON.stringify(ratingData),
          'data.allowance': JSON.stringify(allowanceData),
          'data.gau_titles': JSON.stringify(gauTitles),
          'data.significant_terms.term_gau_map': JSON.stringify(sigTerms.term_gau_map || {}),
          'data.significant_terms.rating': JSON.stringify(sigTerms.rating || {})
        },
        fieldMapping: [
          ['data.rating', 'Predicted GAUs by rating tier'],
          ['data.allowance', 'Allowance rates per GAU'],
          ['data.gau_titles', 'GAU title labels'],
          ['data.significant_terms.term_gau_map', 'Significant terms mapping']
        ],
        responseTime: elapsed + 'ms',
        httpStatus: resp.status
      };
      renderPredictorResults(ratingData, allowanceData, gauTitles, sigTerms);
    } else {
      const msg = json.message || 'Unknown error';
      container.innerHTML = '<div class="error-card"><h3>Prediction Error</h3><p>' + escHtml(msg) + '</p></div>';
      predictorDiagnostics = { request: USER_REQUEST, apiCalls: [{ method:'POST', path:'/tip-api/v1/predictor/predict' }],
        inputParams: { data_text: '(text, ' + text.length + ' chars)', type: 'gau' }, outputParams: { error: msg }, fieldMapping: [], responseTime: elapsed+'ms', httpStatus: resp.status };
    }
  } catch(e) {
    container.innerHTML = '<div class="error-card"><h3>Network Error</h3><p>' + escHtml(e.message) + '</p></div>';
    predictorDiagnostics = { request: USER_REQUEST, apiCalls: [{ method:'POST', path:'/tip-api/v1/predictor/predict' }],
      inputParams: { data_text: '(text, ' + text.length + ' chars)', type: 'gau' }, outputParams: { error: e.message }, fieldMapping: [], responseTime: (Date.now()-startTime)+'ms', httpStatus: 'N/A' };
  }
  updateDiagnostics();
}

function renderPredictorResults(ratingData, allowanceData, gauTitles, sigTerms) {
  let html = '';

  // Rating tiers
  if (ratingData.length > 0) {
    html += '<div class="tip-card" style="margin-bottom:16px;"><h3 style="margin:0 0 12px;font-size:16px;">Predicted Group Art Units</h3>';
    html += '<ul class="gau-list">';
    ratingData.forEach(tier => {
      const gaus = (tier.group_art_units || '').split(',').map(g => g.trim()).filter(g => g);
      const stars = '&#9733;'.repeat(parseInt(tier.rating) || 0) + '&#9734;'.repeat(5 - (parseInt(tier.rating) || 0));
      gaus.forEach(gau => {
        const title = gauTitles[gau] || '';
        html += '<li><div><div class="gau-code">' + escHtml(gau) + '</div>';
        if (title) html += '<div class="gau-title">' + escHtml(title) + '</div>';
        html += '</div><div><span class="rating-stars">' + stars + '</span><div style="font-size:11px;color:var(--tip-text-secondary,#64748b);text-align:right;">Rating ' + escHtml(tier.rating) + '/5</div></div></li>';
      });
    });
    html += '</ul></div>';
  }

  // Allowance rates
  if (allowanceData.length > 0) {
    html += '<div class="tip-card" style="margin-bottom:16px;"><h3 style="margin:0 0 12px;font-size:16px;">Allowance Rates</h3>';
    html += '<div class="tip-table-wrap"><table class="tip-table"><thead><tr><th>GAU</th><th>Class</th><th>Allowance Rate</th><th>Visual</th></tr></thead><tbody>';
    allowanceData.forEach(a => {
      const rate = parseFloat(a.allowance_rate) || 0;
      html += '<tr><td>' + escHtml(a.group_art || '-') + '</td><td>' + escHtml(a.class || '-') + '</td><td>' + rate.toFixed(2) + '%</td>';
      html += '<td style="width:200px;"><div class="allowance-bar"><div class="allowance-bar-fill" style="width:' + Math.min(rate, 100) + '%;"></div></div></td></tr>';
    });
    html += '</tbody></table></div></div>';
  }

  // Significant terms
  if (sigTerms.term_gau_map && Object.keys(sigTerms.term_gau_map).length > 0) {
    html += '<div class="tip-card"><h3 style="margin:0 0 12px;font-size:16px;">Significant Terms</h3>';
    html += '<div class="tip-table-wrap"><table class="tip-table"><thead><tr><th>Term</th><th>Associated GAUs</th></tr></thead><tbody>';
    Object.entries(sigTerms.term_gau_map).forEach(([term, gaus]) => {
      html += '<tr><td><strong>' + escHtml(term) + '</strong></td><td>' + gaus.map(g => {
        const r = (sigTerms.rating || {})[g];
        return escHtml(g) + (r ? ' <span class="tip-tag tip-tag-primary" style="font-size:11px;">' + r + '/5</span>' : '');
      }).join(', ') + '</td></tr>';
    });
    html += '</tbody></table></div></div>';
  }

  if (!html) html = '<div class="tip-card"><div class="empty-state"><p>No prediction results available.</p></div></div>';
  document.getElementById('predictor-results').innerHTML = html;
}

// ── Diagnostics ──
function updateDiagnostics() {
  const container = document.getElementById('diagnostics-content');
  let diag = null;
  if (activeTab === 'patent-lookup') diag = patentDiagnostics;
  else if (activeTab === 'examiner-analysis') diag = examinerDiagnostics;
  else if (activeTab === 'art-unit-predictor') diag = predictorDiagnostics;

  if (!diag) {
    container.innerHTML = '<div class="empty-state" style="padding:20px;"><p>No API calls made yet for the <strong>' + escHtml(activeTab) + '</strong> tab. Perform a search to see diagnostics.</p></div>';
    return;
  }

  let html = '<div class="diag-section"><h4>Active Tab</h4><p style="font-size:14px;margin:0;">' + escHtml(activeTab) + '</p></div>';

  html += '<div class="diag-section"><h4>Request</h4><p style="font-size:13px;margin:0;color:var(--tip-text-secondary,#64748b);">' + escHtml(diag.request) + '</p></div>';

  html += '<div class="diag-section"><h4>API Calls</h4><table class="diag-table"><thead><tr><th>Method</th><th>Path</th><th>Status</th><th>Time</th></tr></thead><tbody>';
  diag.apiCalls.forEach(c => {
    html += '<tr><td>' + escHtml(c.method) + '</td><td>' + escHtml(c.path) + '</td><td>' + escHtml(String(diag.httpStatus)) + '</td><td>' + escHtml(diag.responseTime) + '</td></tr>';
  });
  html += '</tbody></table></div>';

  html += '<div class="diag-section"><h4>Input Parameters</h4><table class="diag-table"><thead><tr><th>Parameter</th><th>Value</th></tr></thead><tbody>';
  Object.entries(diag.inputParams).forEach(([k, v]) => {
    html += '<tr><td>' + escHtml(k) + '</td><td>' + escHtml(String(v)) + '</td></tr>';
  });
  html += '</tbody></table></div>';

  html += '<div class="diag-section"><h4>Output Parameters</h4><table class="diag-table"><thead><tr><th>Field Path</th><th>Value</th></tr></thead><tbody>';
  Object.entries(diag.outputParams).forEach(([k, v]) => {
    const display = String(v).length > 200 ? String(v).substring(0, 200) + '...' : String(v);
    html += '<tr><td style="white-space:nowrap;">' + escHtml(k) + '</td><td>' + escHtml(display) + '</td></tr>';
  });
  html += '</tbody></table></div>';

  if (diag.fieldMapping && diag.fieldMapping.length > 0) {
    html += '<div class="diag-section"><h4>Field Mapping</h4><table class="diag-table"><thead><tr><th>API Field</th><th>UI Element</th></tr></thead><tbody>';
    diag.fieldMapping.forEach(([field, ui]) => {
      html += '<tr><td style="white-space:nowrap;">' + escHtml(field) + '</td><td>' + escHtml(ui) + '</td></tr>';
    });
    html += '</tbody></table></div>';
  }

  container.innerHTML = html;
}

// ── Utilities ──
function escHtml(str) {
  if (str == null) return '';
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(String(str)));
  return div.innerHTML;
}

// Close suggestion dropdowns when clicking outside
document.addEventListener('click', function(e) {
  if (!e.target.closest('#patent-input') && !e.target.closest('#patent-suggestions')) {
    document.getElementById('patent-suggestions').style.display = 'none';
  }
  if (!e.target.closest('#examiner-input') && !e.target.closest('#examiner-suggestions')) {
    document.getElementById('examiner-suggestions').style.display = 'none';
  }
});
</script>
</body>
</html>"""


def index(request):
    """Render the TriangleIP Analytics Portal."""
    return HttpResponse(HTML_PAGE, content_type="text/html")


def tip_api_proxy(request, path):
    """Proxy API requests to the TIP backend, attaching the API key server-side."""
    url = f"{TIP_API_URL.rstrip('/')}/{path}"

    # Forward query string
    qs = request.META.get("QUERY_STRING", "")
    if qs:
        url += f"?{qs}"

    body = request.body if request.body else None

    req = urllib.request.Request(url, data=body, method=request.method)
    req.add_header("x-api-key", TIP_API_TOKEN)

    # Forward content-type for JSON and multipart
    content_type = request.META.get("CONTENT_TYPE", "")
    if content_type:
        req.add_header("Content-Type", content_type)

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            data = resp.read()
            return HttpResponse(data, status=status, content_type="application/json")
    except urllib.error.HTTPError as e:
        return HttpResponse(e.read(), status=e.code, content_type="application/json")
    except urllib.error.URLError as e:
        return JsonResponse(
            {"status": False, "message": f"Upstream connection error: {e.reason}"},
            status=502,
        )
