const apiKeyInput = document.getElementById('apiKey');
const fileInput = document.getElementById('fileInput');
const jsonInput = document.getElementById('jsonInput');
const output = document.getElementById('output');
const historyList = document.getElementById('historyList');
const measureButton = document.getElementById('measureButton');
const sampleButton = document.getElementById('sampleButton');
const historyButton = document.getElementById('historyButton');
const uploadSection = document.getElementById('uploadSection');
const jsonSection = document.getElementById('jsonSection');
const buttons = document.querySelectorAll('[data-mode]');

const sampleGeojson = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { name: 'Sample parcel' },
      geometry: {
        type: 'Polygon',
        coordinates: [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
      },
    },
    {
      type: 'Feature',
      properties: { name: 'Sample road' },
      geometry: {
        type: 'LineString',
        coordinates: [[0, 0], [0.5, 0.5], [1, 1]],
      },
    },
  ],
};

function getHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  const key = apiKeyInput.value.trim();
  if (key) headers['X-API-Key'] = key;
  return headers;
}

function setMode(mode) {
  const uploadActive = mode === 'upload';
  uploadSection.classList.toggle('hidden', !uploadActive);
  jsonSection.classList.toggle('hidden', uploadActive);
  buttons.forEach((button) => {
    button.classList.toggle('active', button.dataset.mode === mode);
  });
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.detail || data.message || `Request failed with ${response.status}`);
  }
  return data;
}

async function measure() {
  try {
    output.textContent = 'Measuring…';
    const mode = document.querySelector('[data-mode].active').dataset.mode;
    let payload;

    if (mode === 'upload' && fileInput.files && fileInput.files[0]) {
      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch('/measure', {
        method: 'POST',
        headers: apiKeyInput.value ? { 'X-API-Key': apiKeyInput.value } : {},
        body: formData,
      });
      const text = await response.text();
      const data = text ? JSON.parse(text) : {};
      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed');
      }
      output.textContent = JSON.stringify(data, null, 2);
      return;
    }

    payload = jsonInput.value.trim();
    if (!payload) {
      throw new Error('Please provide GeoJSON or select a file.');
    }

    const result = await fetchJson('/measure', {
      method: 'POST',
      headers: getHeaders(),
      body: payload,
    });
    output.textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    output.textContent = `Error: ${error.message}`;
  }
}

async function loadHistory() {
  try {
    const data = await fetchJson('/history', {
      headers: getHeaders(),
    });

    if (!data.items || data.items.length === 0) {
      historyList.textContent = 'No measurements yet.';
      return;
    }

    historyList.innerHTML = data.items
      .slice(0, 5)
      .map((item) => `
        <div class="history-item">
          <div><strong>#${item.id}</strong> · ${item.created_at}</div>
          <div>${JSON.stringify(item.payload).slice(0, 90)}...</div>
        </div>
      `)
      .join('');
  } catch (error) {
    historyList.textContent = `Unable to load history: ${error.message}`;
  }
}

buttons.forEach((button) => {
  button.addEventListener('click', () => setMode(button.dataset.mode));
});

measureButton.addEventListener('click', measure);
historyButton.addEventListener('click', loadHistory);
sampleButton.addEventListener('click', () => {
  jsonInput.value = JSON.stringify(sampleGeojson, null, 2);
  setMode('json');
});

jsonInput.value = JSON.stringify(sampleGeojson, null, 2);
loadHistory();
