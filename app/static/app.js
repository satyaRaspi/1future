const el = (id) => document.getElementById(id);

const form = el('decoderForm');
const result = el('result');
const loading = el('loading');
const errorBox = el('error');
const metricsEl = el('metrics');
const promptTilesEl = el('promptTiles');

let selectedPrompt = 'life_path';
let geocodeResult = null;
let geocodeTimer = null;
let lastGeocodedPlace = '';
let geocodeInProgress = false;
let lastReportText = '';
let lastFileName = 'life-path-report.txt';
let lastPayload = null;
let csrfToken = '';
let appBaseUrl = '';
let reportSections = [];
let activeSectionIndex = 0;
let appConfig = { features: { demo_data_button: false } };

const promptOptions = {
  life_path: {
    icon: '✦',
    title: 'The Decoder of the Life Path',
    short: 'Deep personality, strengths, weaknesses and destiny map.',
  },
  soul_purpose: {
    icon: '☉',
    title: "The Discoverer of the Soul's Purpose",
    short: 'Central mission, life lessons and contribution to the world.',
  },
  professional_destiny: {
    icon: '◆',
    title: 'The Professional Destiny Detector',
    short: 'Talent pattern, decision style, best careers and one field to avoid.',
  },
  relationships: {
    icon: '♡',
    title: 'The Destiny Map in Relationships',
    short: 'Compatibility, love lessons and ideal partner profile.',
  },
  wealth_abundance: {
    icon: '₹',
    title: 'The Code of Wealth and Abundance',
    short: 'Financial personality, money blockers and wealth strategy.',
  },
  future_timeline: {
    icon: '⌁',
    title: 'The Future Timeline Guide',
    short: 'Past, present and next 5-year roadmap.',
  },
  compatibility: {
    icon: '♡',
    title: 'Partner Compatibility Report',
    short: 'Two-person love, marriage and emotional fit analysis.',
  },
  children_family: {
    icon: '⌂',
    title: 'Children & Family Outlook',
    short: 'Family patterns, children themes and care style.',
  },
  name_suggestion: {
    icon: '✍',
    title: 'Name Correction & Lucky Name',
    short: 'Meaning, spelling options and lucky name signals.',
  },
  business_name: {
    icon: '◈',
    title: 'Business Name Numerology',
    short: 'Brand name fit, trust and number resonance.',
  },
};

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove('hidden');
}

function clearError() {
  errorBox.textContent = '';
  errorBox.classList.add('hidden');
}

function metric(label, value, small = '') {
  return `<div class="metric"><div class="label">${escapeHtml(label)}</div><div class="value">${escapeHtml(String(value))}</div>${small ? `<div class="small">${escapeHtml(small)}</div>` : ''}</div>`;
}

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrfToken,
  };
}


const MONTHS = [
  ['01', 'January'], ['02', 'February'], ['03', 'March'], ['04', 'April'],
  ['05', 'May'], ['06', 'June'], ['07', 'July'], ['08', 'August'],
  ['09', 'September'], ['10', 'October'], ['11', 'November'], ['12', 'December'],
];

function fillSelect(selectEl, placeholder, values) {
  selectEl.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>` + values.map(([value, label]) =>
    `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`
  ).join('');
}

function setupDateParts(prefix, options = {}) {
  const dayEl = el(`${prefix}Day`);
  const monthEl = el(`${prefix}Month`);
  const yearEl = el(`${prefix}Year`);
  if (!dayEl || !monthEl || !yearEl) return;

  const dayValues = Array.from({ length: 31 }, (_, i) => {
    const value = String(i + 1).padStart(2, '0');
    return [value, value];
  });
  const currentYear = new Date().getFullYear();
  const startYear = Number.isFinite(options.startYear) ? options.startYear : currentYear;
  const endYear = Number.isFinite(options.endYear) ? options.endYear : 1900;
  const step = startYear >= endYear ? -1 : 1;
  const yearValues = [];
  for (let year = startYear; step < 0 ? year >= endYear : year <= endYear; year += step) {
    yearValues.push([String(year), String(year)]);
  }

  fillSelect(dayEl, 'Day', dayValues);
  fillSelect(monthEl, 'Month', MONTHS);
  fillSelect(yearEl, 'Year', yearValues);
}

function dateParts(prefix) {
  return {
    day: el(`${prefix}Day`)?.value || '',
    month: el(`${prefix}Month`)?.value || '',
    year: el(`${prefix}Year`)?.value || '',
  };
}

function updateDateFromParts(prefix, targetId, helperId, { required = false, allowFuture = false } = {}) {
  const target = el(targetId);
  const helper = el(helperId);
  const { day, month, year } = dateParts(prefix);
  const hasAny = Boolean(day || month || year);

  if (!hasAny) {
    target.value = '';
    if (helper) {
      helper.textContent = required ? 'Select day, month and year.' : 'Optional. Select only when required.';
      helper.classList.remove('field-helper-error');
    }
    return { valid: !required, value: '', complete: false };
  }

  if (!day || !month || !year) {
    target.value = '';
    if (helper) {
      helper.textContent = 'Complete the date by selecting day, month and year.';
      helper.classList.add('field-helper-error');
    }
    return { valid: false, value: '', complete: false };
  }

  const composed = `${year}-${month}-${day}`;
  const parsed = new Date(`${composed}T00:00:00`);
  const isRealDate = parsed.getFullYear() === Number(year) && String(parsed.getMonth() + 1).padStart(2, '0') === month && String(parsed.getDate()).padStart(2, '0') === day;
  const today = new Date();
  today.setHours(23, 59, 59, 999);

  if (!isRealDate) {
    target.value = '';
    if (helper) {
      helper.textContent = 'This date does not exist. Please check the day and month.';
      helper.classList.add('field-helper-error');
    }
    return { valid: false, value: '', complete: true };
  }

  if (!allowFuture && parsed > today) {
    target.value = '';
    if (helper) {
      helper.textContent = 'Date of birth cannot be in the future.';
      helper.classList.add('field-helper-error');
    }
    return { valid: false, value: '', complete: true };
  }

  target.value = composed;
  if (helper) {
    helper.textContent = parsed.toLocaleDateString(undefined, { day: '2-digit', month: 'long', year: 'numeric' });
    helper.classList.remove('field-helper-error');
  }
  return { valid: true, value: composed, complete: true };
}

function setFriendlyDate(prefix, isoDate) {
  const dayEl = el(`${prefix}Day`);
  const monthEl = el(`${prefix}Month`);
  const yearEl = el(`${prefix}Year`);
  if (!dayEl || !monthEl || !yearEl) return;
  const parts = String(isoDate || '').split('-');
  if (parts.length !== 3) return;
  yearEl.value = parts[0];
  monthEl.value = parts[1];
  dayEl.value = parts[2];
}

function resetFriendlyDate(prefix, targetId, helperId, required = false) {
  [`${prefix}Day`, `${prefix}Month`, `${prefix}Year`].forEach((id) => { if (el(id)) el(id).value = ''; });
  if (el(targetId)) el(targetId).value = '';
  if (el(helperId)) {
    el(helperId).textContent = required ? 'Select day, month and year.' : 'Optional. Select only when required.';
    el(helperId).classList.remove('field-helper-error');
  }
}

function validateAllDates() {
  const primary = updateDateFromParts('dob', 'dob', 'dobHelper', { required: true });
  const partner = updateDateFromParts('partnerDob', 'partnerDob', 'partnerDobHelper', { required: false });
  const prediction = updateDateFromParts('predictionDate', 'predictionDate', 'predictionDateHelper', { required: false, allowFuture: true });
  return { primary, partner, prediction };
}

function initialiseFriendlyDateControls() {
  setupDateParts('dob');
  setupDateParts('partnerDob');
  const currentYear = new Date().getFullYear();
  setupDateParts('predictionDate', { startYear: currentYear + 30, endYear: currentYear - 20 });
  ['dobDay', 'dobMonth', 'dobYear'].forEach((id) => el(id)?.addEventListener('change', () => updateDateFromParts('dob', 'dob', 'dobHelper', { required: true })));
  ['partnerDobDay', 'partnerDobMonth', 'partnerDobYear'].forEach((id) => el(id)?.addEventListener('change', () => updateDateFromParts('partnerDob', 'partnerDob', 'partnerDobHelper', { required: false })));
  ['predictionDateDay', 'predictionDateMonth', 'predictionDateYear'].forEach((id) => el(id)?.addEventListener('change', () => updateDateFromParts('predictionDate', 'predictionDate', 'predictionDateHelper', { required: false, allowFuture: true })));
}

function setSelectedPrompt(key) {
  selectedPrompt = key;
  const option = promptOptions[key];
  el('selectedBadge').textContent = option.title;
  document.querySelectorAll('.prompt-tile').forEach((tile) => {
    tile.classList.toggle('active', tile.dataset.key === key);
  });
}

function renderPromptTiles() {
  promptTilesEl.innerHTML = Object.entries(promptOptions).map(([key, item]) => `
    <button class="prompt-tile ${key === selectedPrompt ? 'active' : ''}" type="button" data-key="${key}">
      <span class="tile-icon">${escapeHtml(item.icon)}</span>
      <strong>${escapeHtml(item.title)}</strong>
      <span>${escapeHtml(item.short)}</span>
    </button>
  `).join('');

  document.querySelectorAll('.prompt-tile').forEach((tile) => {
    tile.addEventListener('click', () => setSelectedPrompt(tile.dataset.key));
  });
  setSelectedPrompt(selectedPrompt);
}

function sectionPreview(section) {
  if (section.body) return section.body;
  if (section.bullets && section.bullets.length) return section.bullets[0];
  if (section.table && section.table.length) {
    const firstRow = section.table[0];
    return Object.values(firstRow).slice(0, 2).join(' · ');
  }
  return 'Click to open full section details.';
}

function renderSectionContent(section) {
  const body = document.createElement('div');
  body.className = 'section-detail-content';

  if (section.body) {
    const p = document.createElement('p');
    p.textContent = section.body;
    body.appendChild(p);
  }

  if (section.bullets && section.bullets.length) {
    const ul = document.createElement('ul');
    section.bullets.forEach((item) => {
      const li = document.createElement('li');
      li.textContent = item;
      ul.appendChild(li);
    });
    body.appendChild(ul);
  }

  if (section.table && section.table.length) {
    const table = document.createElement('table');
    const keys = Object.keys(section.table[0]);
    table.innerHTML = `<thead><tr>${keys.map((k) => `<th>${escapeHtml(k.replaceAll('_', ' '))}</th>`).join('')}</tr></thead>`;
    const tbody = document.createElement('tbody');
    section.table.forEach((row) => {
      const tr = document.createElement('tr');
      keys.forEach((key) => {
        const td = document.createElement('td');
        td.textContent = row[key];
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    body.appendChild(table);
  }

  return body;
}

function setActiveSectionTile(index) {
  activeSectionIndex = index;
  document.querySelectorAll('.section-tile').forEach((tile) => {
    tile.classList.toggle('active', Number(tile.dataset.index) === index);
  });
}

function openSectionDetails(index) {
  const section = reportSections[index];
  if (!section) return;
  setActiveSectionTile(index);

  el('sectionModalCount').textContent = `Section ${index + 1} of ${reportSections.length}`;
  el('sectionModalTitle').textContent = section.title;
  const modalBody = el('sectionModalBody');
  modalBody.innerHTML = '';
  modalBody.appendChild(renderSectionContent(section));

  el('sectionPrevBtn').disabled = index <= 0;
  el('sectionNextBtn').disabled = index >= reportSections.length - 1;
  el('sectionModal').classList.remove('hidden');
  document.body.classList.add('modal-open');
  el('sectionModalClose').focus();
}

function closeSectionDetails() {
  el('sectionModal').classList.add('hidden');
  document.body.classList.remove('modal-open');
}

function renderSection(section, index = 0) {
  const article = document.createElement('article');
  article.className = 'card report-card section-tile';
  article.dataset.index = String(index);

  const button = document.createElement('button');
  button.className = 'section-tile-button';
  button.type = 'button';
  button.setAttribute('aria-label', `Open ${section.title}`);

  const header = document.createElement('div');
  header.className = 'section-tile-header';

  const count = document.createElement('span');
  count.className = 'section-count';
  count.textContent = `Section ${index + 1}`;
  header.appendChild(count);

  const icon = document.createElement('span');
  icon.className = 'section-open-icon';
  icon.textContent = '↗';
  header.appendChild(icon);

  const title = document.createElement('h3');
  title.className = 'section-tile-title';
  title.textContent = section.title;

  const preview = document.createElement('p');
  preview.className = 'section-tile-preview';
  preview.textContent = sectionPreview(section);

  const cta = document.createElement('div');
  cta.className = 'section-tile-cta';
  cta.textContent = 'Open details';

  button.appendChild(header);
  button.appendChild(title);
  button.appendChild(preview);
  button.appendChild(cta);
  button.addEventListener('click', () => openSectionDetails(index));

  article.appendChild(button);

  const printContent = document.createElement('div');
  printContent.className = 'section-print-content';
  printContent.appendChild(renderSectionContent(section));
  article.appendChild(printContent);

  return article;
}
function resetShareUi() {
  el('sharePanel').classList.add('hidden');
  el('facebookBtn').classList.add('hidden');
  el('whatsappBtn').classList.add('hidden');
  el('instagramBtn').classList.add('hidden');
  el('storyBtn').classList.add('hidden');
  el('socialCardsBtn').classList.add('hidden');
  el('shareUrl').value = '';
  el('shareNote').textContent = '';
}

function fallbackReportSummary(data) {
  const c = data.calculations || {};
  const r = data.report || {};
  const input = data.input || {};
  return {
    title: 'Report Summary',
    body: `${input.name || 'This profile'} is anchored by Life Path ${c.life_path || '-'} — ${c.life_path_title || 'core pattern'}. This summary combines the key numerology, name, lucky-signal and South Indian-style astrology markers before the detailed section tiles.`,
    bullets: [
      `Core numbers: Life Path ${c.life_path || '-'}, Name Expression ${c.name_expression || '-'}, Soul Urge ${c.soul_urge || '-'}, Birth Day ${c.birth_day || '-'}`,
      `South Indian layer: Nakshatra ${c.nakshatra || '-'}, Moon Rashi ${c.moon_rashi || '-'}, Tithi ${c.tithi || '-'}`,
      `Name insight: ${c.name_meaning || '-'}; commonness: ${c.name_commonness || '-'}`,
      `Lucky signals: ${c.lucky_color || '-'} color, ${c.lucky_fruit || '-'} fruit, ${c.lucky_day || '-'} day, number ${c.lucky_number || '-'}`,
      'Click the tiles below to open the detailed interpretation.'
    ]
  };
}

function renderReportSummary(summary) {
  const box = el('reportSummary');
  if (!box) return;
  const safeSummary = summary && typeof summary === 'object' ? summary : null;
  if (!safeSummary) {
    box.classList.add('hidden');
    box.innerHTML = '';
    return;
  }
  const bullets = Array.isArray(safeSummary.bullets) ? safeSummary.bullets : [];
  box.classList.remove('hidden');
  box.innerHTML = `
    <div class="summary-eyebrow">At a glance</div>
    <h3>${escapeHtml(safeSummary.title || 'Report Summary')}</h3>
    <p>${escapeHtml(safeSummary.body || '')}</p>
    ${bullets.length ? `<ul>${bullets.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : ''}
  `;
}

function renderReport(data) {
  const c = data.calculations;
  const r = data.report;
  const input = data.input;
  lastReportText = r.full_text;
  lastFileName = `${input.name.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'life-path'}-${input.analysis_type || 'report'}.txt`;

  const dobText = new Date(input.dob + 'T00:00:00').toLocaleDateString(undefined, { day: '2-digit', month: 'long', year: 'numeric' });
  const timeText = input.birth_time ? ` · Time: ${input.birth_time}` : '';
  const placeText = input.birth_place ? ` · Birth Place: ${input.birth_place}` : '';
  const geoText = input.latitude !== null && input.longitude !== null ? ` · ${Number(input.latitude).toFixed(6)}, ${Number(input.longitude).toFixed(6)}` : '';

  el('resultTitle').textContent = `${input.name} — ${r.title}`;
  el('resultSub').textContent = `DOB: ${dobText}${timeText} · Age: ${c.age}${placeText}${geoText}`;

  const todayPrediction = r.today_prediction || {};
  const givenPrediction = r.given_date_prediction || {};
  metricsEl.innerHTML = [
    metric('Life Path', c.life_path, c.life_path_title),
    metric('Birth Day', c.birth_day, 'Natural talent pattern'),
    metric('Name Expression', c.name_expression, 'Outer operating style'),
    metric('Personal Year', c.personal_year, c.personal_year_theme),
    metric('Attitude', c.attitude, 'First response style'),
    metric('Soul Urge', c.soul_urge, 'Private motivation'),
    metric('Lucky Color', c.lucky_color || '-', c.lucky_day ? `Day: ${c.lucky_day}` : ''),
    metric('Lucky Fruit', c.lucky_fruit || '-', c.lucky_number ? `Lucky No: ${c.lucky_number}` : ''),
    metric('Nakshatra', c.nakshatra || '-', c.moon_rashi || 'Moon sign'),
    metric('Tithi', c.tithi || '-', c.sun_sign || 'Sun sign'),
    metric('Today Location', todayPrediction.location_label || '-', todayPrediction.weekday_ruler ? `Ruler: ${todayPrediction.weekday_ruler}` : 'IP-based'),
    metric('Prediction Date', givenPrediction.date_label || '-', givenPrediction.weekday_ruler ? `Ruler: ${givenPrediction.weekday_ruler}` : 'Optional'),
    metric('Personality', c.personality, 'First impression'),
    metric('Report Tile', data.prompt.title.replace('The ', ''), 'Selected mode'),
  ].join('');

  renderReportSummary(r.quick_summary || fallbackReportSummary(data));

  const container = el('dynamicSections');
  container.innerHTML = '';
  reportSections = r.sections || [];
  reportSections.forEach((section, index) => container.appendChild(renderSection(section, index)));
  setActiveSectionTile(0);

  resetShareUi();
  result.classList.remove('hidden');
  result.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function geocodePlace({ showErrors = false, force = false } = {}) {
  if (geocodeInProgress) return geocodeResult;
  clearError();
  const birthPlace = el('birthPlace').value.trim();

  if (!birthPlace) {
    geocodeResult = null;
    lastGeocodedPlace = '';
    el('latitude').value = '';
    el('longitude').value = '';
    el('geoStatus').textContent = 'Enter birth place to auto-resolve latitude and longitude.';
    return null;
  }

  if (birthPlace.length < 3) {
    el('geoStatus').textContent = 'Keep typing the birth place...';
    return null;
  }

  if (!force && birthPlace === lastGeocodedPlace && el('latitude').value && el('longitude').value) {
    return geocodeResult;
  }

  geocodeInProgress = true;
  el('geoStatus').textContent = 'Auto-resolving latitude and longitude...';
  geocodeResult = null;
  el('latitude').value = '';
  el('longitude').value = '';

  try {
    const res = await fetch('/api/geocode', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ birth_place: birthPlace }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Unable to find latitude and longitude.');
    geocodeResult = data;
    lastGeocodedPlace = birthPlace;
    if (data.resolved) {
      el('latitude').value = data.latitude;
      el('longitude').value = data.longitude;
      el('geoStatus').textContent = `Resolved automatically: ${data.display_name} → ${Number(data.latitude).toFixed(6)}, ${Number(data.longitude).toFixed(6)} (${data.source})`;
    } else {
      el('geoStatus').textContent = `Auto-resolve incomplete: ${data.source}`;
    }
    return data;
  } catch (err) {
    el('geoStatus').textContent = 'Could not auto-resolve. Check spelling or use a larger city/state/country.';
    if (showErrors) showError(err.message || 'Unable to find latitude and longitude.');
    return null;
  } finally {
    geocodeInProgress = false;
  }
}

function scheduleAutoGeocode() {
  const birthPlace = el('birthPlace').value.trim();
  clearTimeout(geocodeTimer);
  geocodeResult = null;
  el('latitude').value = '';
  el('longitude').value = '';

  if (!birthPlace) {
    lastGeocodedPlace = '';
    el('geoStatus').textContent = 'Enter birth place to auto-resolve latitude and longitude.';
    return;
  }

  if (birthPlace.length < 3) {
    el('geoStatus').textContent = 'Keep typing the birth place...';
    return;
  }

  el('geoStatus').textContent = 'Auto-resolve will run after you pause typing...';
  geocodeTimer = setTimeout(() => geocodePlace({ showErrors: false }), 850);
}

function resetFormAfterSuccessfulReport() {
  // Keep the generated report/share payload available, but clear all visible inputs
  // and geocode state so the next report cannot accidentally reuse prior data.
  clearTimeout(geocodeTimer);
  form.reset();
  resetFriendlyDate('dob', 'dob', 'dobHelper', true);
  resetFriendlyDate('partnerDob', 'partnerDob', 'partnerDobHelper', false);
  resetFriendlyDate('predictionDate', 'predictionDate', 'predictionDateHelper', false);
  el('latitude').value = '';
  el('longitude').value = '';
  el('geoStatus').textContent = 'Form cleared after report generation. Enter birth place to auto-resolve latitude and longitude.';
  geocodeResult = null;
  lastGeocodedPlace = '';
  geocodeInProgress = false;
  setSelectedPrompt('life_path');
}


async function analyze(payload) {
  clearError();
  result.classList.add('hidden');
  loading.classList.remove('hidden');
  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Unable to generate report.');
    lastPayload = { ...payload };
    renderReport(data);
    resetFormAfterSuccessfulReport();
  } catch (err) {
    showError(err.message || 'Something went wrong.');
  } finally {
    loading.classList.add('hidden');
  }
}

async function createShare() {
  clearError();
  if (!lastPayload) {
    showError('Generate a report first, then create a public share link.');
    return;
  }
  const btn = el('createShareBtn');
  btn.disabled = true;
  btn.textContent = 'Creating...';
  try {
    const res = await fetch('/api/share', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ ...lastPayload, allow_public_share: true }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Unable to create share link.');
    el('shareUrl').value = data.share_url;
    el('facebookBtn').href = data.facebook_share_url;
    el('whatsappBtn').href = data.whatsapp_share_url || '#';
    el('instagramBtn').href = data.instagram_cards_url;
    el('storyBtn').href = data.instagram_story_url || '#';
    el('socialCardsBtn').href = data.social_cards_url || '#';
    el('sharePanel').classList.remove('hidden');
    el('facebookBtn').classList.remove('hidden');
    el('whatsappBtn').classList.remove('hidden');
    el('instagramBtn').classList.remove('hidden');
    el('storyBtn').classList.remove('hidden');
    el('socialCardsBtn').classList.remove('hidden');
    const isLocal = data.share_url.includes('127.0.0.1') || data.share_url.includes('localhost');
    el('shareNote').textContent = isLocal
      ? 'This is a local URL. It will work only on this machine. Deploy the app and set APP_BASE_URL to create a true public internet URL for Facebook sharing.'
      : `Public link expires on ${new Date(data.expires_at).toLocaleString()}. Anyone with the link can view the shared report.`;
  } catch (err) {
    showError(err.message || 'Unable to create public share link.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Create Public Share Link';
  }
}

async function downloadPdf() {
  clearError();
  if (!lastPayload) {
    showError('Generate a report first, then download the PDF.');
    return;
  }
  const btn = el('pdfBtn');
  btn.disabled = true;
  btn.textContent = 'Preparing PDF...';
  try {
    const res = await fetch('/api/report.pdf', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(lastPayload),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || 'Unable to create PDF.');
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = lastFileName.replace('.txt', '.pdf');
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    showError(err.message || 'Unable to download PDF.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Download PDF';
  }
}

async function loadHistory() {
  clearError();
  const panel = el('historyPanel');
  panel.textContent = 'Loading history...';
  try {
    const res = await fetch('/api/reports', { headers: { 'Accept': 'application/json', 'X-CSRF-Token': csrfToken } });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Unable to load history.');
    const reports = data.reports || [];
    if (!reports.length) {
      panel.textContent = 'No saved reports yet. Use No Storage Mode for reports you do not want saved.';
      return;
    }
    panel.innerHTML = reports.map((r) => `<div class="history-row"><strong>${escapeHtml(r.name)}</strong><span>${escapeHtml(r.analysis_type)} · ${new Date(r.created_at).toLocaleString()}</span><button type="button" class="ghost history-delete" data-id="${r.id}">Delete</button></div>`).join('');
    document.querySelectorAll('.history-delete').forEach((btn) => btn.addEventListener('click', async () => {
      await deleteHistoryItem(btn.dataset.id);
      loadHistory();
    }));
  } catch (err) {
    panel.textContent = err.message || 'Unable to load history.';
  }
}

async function deleteHistoryItem(id) {
  await fetch(`/api/reports/${id}`, { method: 'DELETE', headers: { 'X-CSRF-Token': csrfToken } });
}

async function clearHistory() {
  clearError();
  if (!confirm('Clear all saved local report history?')) return;
  const res = await fetch('/api/reports', { method: 'DELETE', headers: { 'X-CSRF-Token': csrfToken } });
  const data = await res.json().catch(() => ({}));
  el('historyPanel').textContent = data.deleted !== undefined ? `Deleted ${data.deleted} saved report(s).` : 'History cleared.';
}

function openAdminLoginDialog() {
  const modal = el('adminLoginModal');
  el('adminLoginError').textContent = '';
  el('adminLoginError').classList.add('hidden');
  el('adminLoginId').value = '';
  el('adminLoginPassword').value = '';
  modal.classList.remove('hidden');
  document.body.classList.add('modal-open');
  setTimeout(() => el('adminLoginId').focus(), 50);
}

function closeAdminLoginDialog() {
  el('adminLoginModal').classList.add('hidden');
  document.body.classList.remove('modal-open');
}

function showAdminLoginError(message) {
  el('adminLoginError').textContent = message;
  el('adminLoginError').classList.remove('hidden');
}

async function submitAdminLogin() {
  const admin_id = el('adminLoginId').value.trim();
  const password = el('adminLoginPassword').value;
  if (!admin_id || !password) {
    showAdminLoginError('Please enter admin ID and password.');
    return;
  }
  const btn = el('adminLoginSubmit');
  btn.disabled = true;
  btn.textContent = 'Checking...';
  try {
    const res = await fetch('/api/admin/login', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ admin_id, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'Invalid admin ID or password.');
    closeAdminLoginDialog();
    window.open('/admin', '_blank', 'noopener,noreferrer');
  } catch (err) {
    showAdminLoginError(err.message || 'Unable to login as admin.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Open Admin Settings';
  }
}


async function loadPublicConfig() {
  try {
    const res = await fetch('/api/public-config', { headers: { 'Accept': 'application/json' } });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return;
    appConfig = data || appConfig;
    const demoBtn = el('demoDataBtn');
    if (demoBtn) {
      const showDemo = Boolean(appConfig.features?.demo_data_button);
      demoBtn.classList.toggle('hidden', !showDemo);
      demoBtn.disabled = !showDemo;
      demoBtn.title = showDemo ? 'Create sample reports in local history' : 'Demo data is disabled by admin configuration';
    }
    const tagline = appConfig.brand_tagline;
    const eyebrow = document.querySelector('.brand-copy .eyebrow');
    if (tagline && eyebrow) eyebrow.textContent = tagline;
  } catch (err) {
    // Public config is optional; keep defaults if it fails.
  }
}

async function refreshLocalSession() {
  const res = await fetch('/api/me', {
    credentials: 'same-origin',
    headers: { 'Accept': 'application/json' },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data.csrf_token) {
    throw new Error(data.detail || 'Unable to refresh local session. Please reload the page.');
  }
  csrfToken = data.csrf_token;
  appBaseUrl = data.app_base_url || appBaseUrl || '';
  return data;
}

function setDemoDataStatus(message, isError = false) {
  const panel = el('historyPanel');
  if (panel) panel.textContent = message;
  if (isError) showError(message);
}

async function postDemoDataOnce() {
  return fetch('/api/demo-data', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      ...authHeaders(),
      'Accept': 'application/json',
    },
    body: JSON.stringify({}),
  });
}

async function createDemoData(event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  clearError();
  const btn = el('demoDataBtn');
  if (!btn || btn.classList.contains('hidden')) return;
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Creating...';
  setDemoDataStatus('Creating demo reports...');
  try {
    // Refresh CSRF first; this avoids failures after a long idle session or page cache restore.
    await refreshLocalSession();
    let res = await postDemoDataOnce();

    // Retry once if the session token was stale.
    if (res.status === 403) {
      await refreshLocalSession();
      res = await postDemoDataOnce();
    }

    const raw = await res.text();
    let data = {};
    try {
      data = raw ? JSON.parse(raw) : {};
    } catch (_) {
      data = { detail: raw };
    }

    if (!res.ok) {
      throw new Error(data.detail || `Unable to create demo data. Server returned ${res.status}.`);
    }

    const created = Number(data.created_count || 0);
    const errorNote = Array.isArray(data.errors) && data.errors.length ? ` Some samples had warnings: ${data.errors.slice(0, 2).join('; ')}` : '';
    setDemoDataStatus(`Created ${created} demo report(s).${errorNote} Loading history...`);
    await loadHistory();
  } catch (err) {
    setDemoDataStatus(err.message || 'Unable to create demo data.', true);
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}

async function copyShareUrl() {
  const value = el('shareUrl').value;
  if (!value) return;
  await navigator.clipboard.writeText(value);
  el('copyShareBtn').textContent = 'Copied';
  setTimeout(() => (el('copyShareBtn').textContent = 'Copy Public URL'), 1400);
}

async function submitCurrentForm() {
  const dates = validateAllDates();
  const name = el('name').value.trim();
  const date_of_birth = dates.primary.value;
  const birth_place = el('birthPlace').value.trim();
  const birth_time = el('birthTime').value;
  const prediction_date = dates.prediction.value;
  const partner_name = el('partnerName').value.trim();
  const partner_date_of_birth = dates.partner.value;
  const partner_birth_time = el('partnerBirthTime').value;
  const partner_birth_place = el('partnerBirthPlace').value.trim();

  if (!name || !date_of_birth) {
    showError('Please enter name and a complete date of birth.');
    return;
  }

  if (!dates.primary.valid || !dates.partner.valid || !dates.prediction.valid) {
    showError('Please check the date fields before generating the report.');
    return;
  }

  if (birth_place && (!el('latitude').value || !el('longitude').value)) {
    await geocodePlace({ showErrors: true, force: true });
  }

  const payload = {
    name,
    date_of_birth,
    birth_time: birth_time || null,
    birth_place: birth_place || null,
    latitude: el('latitude').value ? Number(el('latitude').value) : null,
    longitude: el('longitude').value ? Number(el('longitude').value) : null,
    analysis_type: selectedPrompt,
    report_length: el('reportLength').value,
    tone: el('tone').value,
    output_language: el('outputLanguage').value,
    brutal_mode: el('tone').value === 'brutally_honest',
    no_storage: el('noStorage').checked,
    prediction_date: prediction_date || null,
    partner_name: partner_name || null,
    partner_date_of_birth: partner_date_of_birth || null,
    partner_birth_time: partner_birth_time || null,
    partner_birth_place: partner_birth_place || null,
  };
  analyze(payload);
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  submitCurrentForm();
});

el('birthPlace').addEventListener('input', scheduleAutoGeocode);
el('birthPlace').addEventListener('blur', () => geocodePlace({ showErrors: false, force: true }));

const demoButton = el('demoDataBtn');
if (demoButton) demoButton.onclick = createDemoData;

el('sampleBtn').addEventListener('click', async () => {
  el('name').value = 'Aarav Sharma';
  setFriendlyDate('dob', '1988-07-13');
  updateDateFromParts('dob', 'dob', 'dobHelper', { required: true });
  el('birthTime').value = '09:30';
  el('birthPlace').value = 'Bengaluru, Karnataka, India';
  el('reportLength').value = 'detailed';
  el('tone').value = 'balanced';
  el('outputLanguage').value = 'english';
  el('noStorage').checked = false;
  const samplePrediction = new Date();
  samplePrediction.setDate(samplePrediction.getDate() + 30);
  setFriendlyDate('predictionDate', samplePrediction.toISOString().slice(0, 10));
  updateDateFromParts('predictionDate', 'predictionDate', 'predictionDateHelper', { required: false, allowFuture: true });
  el('partnerName').value = 'Ananya Rao';
  setFriendlyDate('partnerDob', '1990-02-21');
  updateDateFromParts('partnerDob', 'partnerDob', 'partnerDobHelper', { required: false });
  el('partnerBirthTime').value = '18:15';
  el('partnerBirthPlace').value = 'Mysuru, Karnataka, India';
  setSelectedPrompt('compatibility');
  await geocodePlace({ showErrors: false, force: true });
  submitCurrentForm();
});

el('clearBtn').addEventListener('click', () => {
  clearTimeout(geocodeTimer);
  form.reset();
  resetFriendlyDate('dob', 'dob', 'dobHelper', true);
  resetFriendlyDate('partnerDob', 'partnerDob', 'partnerDobHelper', false);
  resetFriendlyDate('predictionDate', 'predictionDate', 'predictionDateHelper', false);
  result.classList.add('hidden');
  el('latitude').value = '';
  el('longitude').value = '';
  el('geoStatus').textContent = 'Enter birth place to auto-resolve latitude and longitude.';
  geocodeResult = null;
  lastGeocodedPlace = '';
  geocodeInProgress = false;
  lastPayload = null;
  reportSections = [];
  clearError();
  resetShareUi();
  setSelectedPrompt('life_path');
});

el('copyBtn').addEventListener('click', async () => {
  if (!lastReportText) return;
  await navigator.clipboard.writeText(lastReportText);
  el('copyBtn').textContent = 'Copied';
  setTimeout(() => (el('copyBtn').textContent = 'Copy Report'), 1400);
});

el('downloadBtn').addEventListener('click', () => {
  if (!lastReportText) return;
  const blob = new Blob([lastReportText], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = lastFileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});

el('printBtn').addEventListener('click', () => window.print());
el('pdfBtn').addEventListener('click', downloadPdf);
el('createShareBtn').addEventListener('click', createShare);
el('copyShareBtn').addEventListener('click', copyShareUrl);
el('loadHistoryBtn').addEventListener('click', loadHistory);
el('clearHistoryBtn').addEventListener('click', clearHistory);
['adminSettingsBtn', 'adminFooterLoginBtn'].forEach((id) => {
  const btn = el(id);
  if (btn) btn.addEventListener('click', (event) => { event.preventDefault(); openAdminLoginDialog(); });
});
el('adminLoginSubmit').addEventListener('click', submitAdminLogin);
el('adminLoginCancel').addEventListener('click', closeAdminLoginDialog);
el('adminLoginClose').addEventListener('click', closeAdminLoginDialog);
el('adminLoginBackdrop').addEventListener('click', closeAdminLoginDialog);
el('adminLoginPassword').addEventListener('keydown', (event) => { if (event.key === 'Enter') submitAdminLogin(); });
el('sectionModalClose').addEventListener('click', closeSectionDetails);
el('sectionModalBackdrop').addEventListener('click', closeSectionDetails);
el('sectionPrevBtn').addEventListener('click', () => openSectionDetails(Math.max(0, activeSectionIndex - 1)));
el('sectionNextBtn').addEventListener('click', () => openSectionDetails(Math.min(reportSections.length - 1, activeSectionIndex + 1)));
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !el('sectionModal').classList.contains('hidden')) closeSectionDetails();
  if (event.key === 'Escape' && !el('adminLoginModal').classList.contains('hidden')) closeAdminLoginDialog();
});


function showApp(me) {
  csrfToken = me.csrf_token;
  appBaseUrl = me.app_base_url || '';
  el('appScreen').classList.remove('hidden');
}

async function init() {
  renderPromptTiles();
  initialiseFriendlyDateControls();
  try {
    const res = await fetch('/api/me', { headers: { 'Accept': 'application/json' } });
    const me = await res.json();
    if (!res.ok || !me.csrf_token) throw new Error(me.detail || 'Unable to initialise local session.');
    showApp(me);
    await loadPublicConfig();
  } catch (err) {
    showError('Unable to start local session. Please restart the app.');
  }
}

init();
