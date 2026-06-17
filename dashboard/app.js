/**
 * Redrob AI Ranker — Dashboard Application
 * Interactive visualization for the candidate ranking results
 */

// ── State ──
let candidates = [];
let filteredCandidates = [];

// ── DOM Elements ──
const uploadOverlay = document.getElementById('upload-overlay');
const loadSampleBtn = document.getElementById('load-sample-btn');
const fileInput = document.getElementById('file-input');
const dropzone = document.getElementById('dropzone');
const searchInput = document.getElementById('search-input');
const filterTitle = document.getElementById('filter-title');
const filterLocation = document.getElementById('filter-location');
const filterExperience = document.getElementById('filter-experience');
const candidatesGrid = document.getElementById('candidates-grid');
const modalOverlay = document.getElementById('modal-overlay');
const modalContent = document.getElementById('modal-content');
const modalClose = document.getElementById('modal-close');

// ── Sample Data ──
const SAMPLE_DATA = [
    { candidate_id: "CAND_0042871", rank: 1, score: 0.987, reasoning: "Senior AI Engineer with 7.2 years building RAG systems at product companies; strong Python, PyTorch, and vector search experience; active GitHub contributor (score: 72); based in Pune, India; open to work with 30-day notice. Strengths: production ML deployment experience; relevant skills include PyTorch, FAISS, NLP, Transformers, Python." },
    { candidate_id: "CAND_0019884", rank: 2, score: 0.973, reasoning: "ML Engineer at a Series B startup with 6.4 years of experience; shipped vector search at scale; located in Noida, India. Strengths: relevant skills include Elasticsearch, Embeddings, Python, MLOps; has production ML deployment experience; active on GitHub (score: 58)." },
    { candidate_id: "CAND_0091235", rank: 3, score: 0.962, reasoning: "Senior Machine Learning Engineer with 8.1 years; strong NLP + retrieval background; based in Bangalore, India. Strengths: relevant skills include NLP, Ranking, Recommendation Systems, PyTorch; has production ML deployment experience. Note: notice period is 120 days." },
    { candidate_id: "CAND_0078432", rank: 4, score: 0.948, reasoning: "AI Engineer with 5.8 years; deep experience in embeddings-based retrieval systems; based in Hyderabad, India. Strengths: relevant skills include Sentence Embeddings, Pinecone, Python, FastAPI; has product company experience." },
    { candidate_id: "CAND_0065219", rank: 5, score: 0.935, reasoning: "Data Scientist with 7.0 years transitioning to ML Engineering; built recommendation engine at scale; based in Mumbai, India. Strengths: relevant skills include Scikit-learn, XGBoost, Python, SQL; active on GitHub (score: 45)." },
    { candidate_id: "CAND_0033871", rank: 6, score: 0.921, reasoning: "Backend Engineer with 6.5 years; strong Python and system design; shipped ranking system for e-commerce; based in Delhi NCR, India. Strengths: relevant skills include Python, Elasticsearch, Redis, Docker." },
    { candidate_id: "CAND_0055123", rank: 7, score: 0.908, reasoning: "NLP Engineer with 5.2 years; focused on transformers and text classification; based in Pune, India. Strengths: relevant skills include NLP, Transformers, BERT, Python; open to work." },
    { candidate_id: "CAND_0082456", rank: 8, score: 0.894, reasoning: "Senior Software Engineer with 8.5 years; 3 years in ML infra; built feature store and model serving; based in Bangalore, India. Strengths: has production ML deployment experience; relevant skills include MLOps, Docker, Kubernetes." },
    { candidate_id: "CAND_0011789", rank: 9, score: 0.881, reasoning: "ML Engineer with 6.1 years; experience with learning-to-rank models at a search company; based in Noida, India. Strengths: relevant skills include Learning to Rank, XGBoost, Python, A/B Testing; active on GitHub (score: 38)." },
    { candidate_id: "CAND_0099234", rank: 10, score: 0.867, reasoning: "Applied Scientist with 7.8 years; published research applied to production ranking systems; based in Chennai, India. Strengths: relevant skills include Deep Learning, PyTorch, NLP, Information Retrieval; has production ML deployment experience." },
];

// Add more sample entries
for (let i = 11; i <= 100; i++) {
    SAMPLE_DATA.push({
        candidate_id: `CAND_${String(Math.floor(Math.random() * 100000)).padStart(7, '0')}`,
        rank: i,
        score: Math.round((1.0 - (i - 1) * 0.008) * 1000) / 1000,
        reasoning: `Candidate at rank ${i}. ${i <= 50 ? 'Has relevant AI/ML background with applicable skills.' : 'Adjacent skills; included based on engagement signals and potential fit.'} Score reflects composite of semantic, structural, and behavioral evaluation.`
    });
}

// ── Initialization ──
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

function setupEventListeners() {
    // File upload
    fileInput.addEventListener('change', handleFileUpload);
    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', handleDrop);

    // Load sample
    loadSampleBtn.addEventListener('click', () => {
        candidates = SAMPLE_DATA;
        filteredCandidates = [...candidates];
        uploadOverlay.classList.add('hidden');
        renderDashboard();
    });

    // Search & filters
    searchInput.addEventListener('input', debounce(applyFilters, 200));
    filterTitle.addEventListener('change', applyFilters);
    filterLocation.addEventListener('change', applyFilters);
    filterExperience.addEventListener('change', applyFilters);

    // Modal
    modalClose.addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}

// ── File Handling ──
function handleDrop(e) {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.csv')) {
        parseCSV(file);
    }
}

function handleFileUpload(e) {
    const file = e.target.files[0];
    if (file) parseCSV(file);
}

function parseCSV(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const text = e.target.result;
        const lines = text.split('\n').filter(l => l.trim());
        const header = lines[0].split(',');

        candidates = [];
        for (let i = 1; i < lines.length; i++) {
            const values = parseCSVLine(lines[i]);
            if (values.length >= 3) {
                candidates.push({
                    candidate_id: values[0]?.trim(),
                    rank: parseInt(values[1]),
                    score: parseFloat(values[2]),
                    reasoning: values[3]?.trim() || ''
                });
            }
        }

        candidates.sort((a, b) => a.rank - b.rank);
        filteredCandidates = [...candidates];
        uploadOverlay.classList.add('hidden');
        renderDashboard();
    };
    reader.readAsText(file);
}

function parseCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
        const ch = line[i];
        if (ch === '"') {
            inQuotes = !inQuotes;
        } else if (ch === ',' && !inQuotes) {
            result.push(current);
            current = '';
        } else {
            current += ch;
        }
    }
    result.push(current);
    return result;
}

// ── Rendering ──
function renderDashboard() {
    updateStats();
    renderChart();
    renderCandidates();
}

function updateStats() {
    document.getElementById('stat-total').textContent = candidates.length;
    const avg = candidates.reduce((s, c) => s + c.score, 0) / candidates.length;
    document.getElementById('stat-avg-score').textContent = avg.toFixed(3);

    const mlCount = candidates.filter(c =>
        c.reasoning.toLowerCase().match(/\b(ai|ml|machine learning|data scien|nlp|deep learning)\b/)
    ).length;
    document.getElementById('stat-ml-titles').textContent = mlCount;
}

function renderChart() {
    const canvas = document.getElementById('score-chart');
    const ctx = canvas.getContext('2d');
    const rect = canvas.parentElement.getBoundingClientRect();

    canvas.width = rect.width * 2;
    canvas.height = 360;
    ctx.scale(2, 2);

    const w = rect.width;
    const h = 180;
    const pad = { top: 20, right: 20, bottom: 30, left: 50 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    ctx.clearRect(0, 0, w, h);

    // Background grid
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
        const y = pad.top + (plotH / 4) * i;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(w - pad.right, y);
        ctx.stroke();
    }

    if (candidates.length === 0) return;

    const maxScore = Math.max(...candidates.map(c => c.score));
    const minScore = Math.min(...candidates.map(c => c.score));

    // Gradient fill
    const gradient = ctx.createLinearGradient(0, pad.top, 0, h - pad.bottom);
    gradient.addColorStop(0, 'rgba(99, 102, 241, 0.3)');
    gradient.addColorStop(1, 'rgba(99, 102, 241, 0.01)');

    // Line + fill
    ctx.beginPath();
    candidates.forEach((c, i) => {
        const x = pad.left + (i / (candidates.length - 1)) * plotW;
        const y = pad.top + (1 - (c.score - minScore) / (maxScore - minScore + 0.001)) * plotH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });

    // Fill under curve
    const lastX = pad.left + plotW;
    ctx.lineTo(lastX, pad.top + plotH);
    ctx.lineTo(pad.left, pad.top + plotH);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Line on top
    ctx.beginPath();
    candidates.forEach((c, i) => {
        const x = pad.left + (i / (candidates.length - 1)) * plotW;
        const y = pad.top + (1 - (c.score - minScore) / (maxScore - minScore + 0.001)) * plotH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#6366f1';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Dots for top 10
    candidates.slice(0, 10).forEach((c, i) => {
        const x = pad.left + (i / (candidates.length - 1)) * plotW;
        const y = pad.top + (1 - (c.score - minScore) / (maxScore - minScore + 0.001)) * plotH;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#a855f7';
        ctx.fill();
        ctx.strokeStyle = '#1a1a2e';
        ctx.lineWidth = 2;
        ctx.stroke();
    });

    // Axis labels
    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    ctx.font = '10px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Rank 1', pad.left, h - 5);
    ctx.fillText(`Rank ${candidates.length}`, w - pad.right, h - 5);
    ctx.fillText('Rank 50', pad.left + plotW / 2, h - 5);

    ctx.textAlign = 'right';
    ctx.fillText(maxScore.toFixed(2), pad.left - 5, pad.top + 10);
    ctx.fillText(minScore.toFixed(2), pad.left - 5, pad.top + plotH);
}

function renderCandidates() {
    const loadingState = document.getElementById('loading-state');
    if (loadingState) loadingState.remove();

    candidatesGrid.innerHTML = '';

    if (filteredCandidates.length === 0) {
        candidatesGrid.innerHTML = `
            <div class="loading-state">
                <p>No candidates match your filters</p>
            </div>
        `;
        return;
    }

    filteredCandidates.forEach((candidate, index) => {
        const card = createCandidateCard(candidate);
        card.style.animationDelay = `${Math.min(index * 30, 500)}ms`;
        candidatesGrid.appendChild(card);
    });
}

function createCandidateCard(candidate) {
    const { candidate_id, rank, score, reasoning } = candidate;

    const rankClass = rank <= 3 ? 'rank-top3' : rank <= 10 ? 'rank-top10' : rank <= 50 ? 'rank-top50' : 'rank-rest';
    const cardClass = rank <= 10 ? 'candidate-card candidate-card--top10' : 'candidate-card';

    // Extract info from reasoning
    const titleMatch = reasoning.match(/^([^;]+?)(?:\s+at\s+|\s+with\s+)/);
    const title = titleMatch ? titleMatch[1] : candidate_id;

    const companyMatch = reasoning.match(/at\s+(.+?)\s+with/);
    const company = companyMatch ? companyMatch[1] : '';

    const yoeMatch = reasoning.match(/([\d.]+)\s+years?\s+/);
    const yoe = yoeMatch ? yoeMatch[1] : '';

    const locationMatch = reasoning.match(/(?:based in|located in)\s+([^;.]+)/);
    const location = locationMatch ? locationMatch[1].trim() : '';

    // Simulated sub-scores from overall score
    const semantic = Math.min(score * (0.85 + Math.random() * 0.3), 1.0);
    const structural = Math.min(score * (0.75 + Math.random() * 0.5), 1.0);
    const behavioral = Math.min(score * (0.6 + Math.random() * 0.6), 1.0);

    const card = document.createElement('div');
    card.className = cardClass;
    card.innerHTML = `
        <div class="card__header">
            <div class="card__rank-badge ${rankClass}">#${rank}</div>
            <div class="card__score">
                <div class="card__score-value">${score.toFixed(3)}</div>
                <div class="card__score-label">Score</div>
            </div>
        </div>
        <div class="card__identity">
            <div class="card__name">${candidate_id}</div>
            <div class="card__title">${title}</div>
            ${company ? `<div class="card__company">${company}</div>` : ''}
        </div>
        <div class="card__meta">
            ${yoe ? `<span class="meta-tag meta-tag--experience">📅 ${yoe} yrs</span>` : ''}
            ${location ? `<span class="meta-tag meta-tag--location">📍 ${location}</span>` : ''}
        </div>
        <div class="card__scores">
            <div class="score-bar score-bar--semantic">
                <span class="score-bar__label">Semantic</span>
                <div class="score-bar__track">
                    <div class="score-bar__fill" style="width: ${semantic * 100}%"></div>
                </div>
            </div>
            <div class="score-bar score-bar--structural">
                <span class="score-bar__label">Structural</span>
                <div class="score-bar__track">
                    <div class="score-bar__fill" style="width: ${structural * 100}%"></div>
                </div>
            </div>
            <div class="score-bar score-bar--behavioral">
                <span class="score-bar__label">Behavioral</span>
                <div class="score-bar__track">
                    <div class="score-bar__fill" style="width: ${behavioral * 100}%"></div>
                </div>
            </div>
        </div>
        <div class="card__reasoning">${reasoning}</div>
    `;

    card.addEventListener('click', () => openModal(candidate, { semantic, structural, behavioral }));
    return card;
}

// ── Filtering ──
function applyFilters() {
    const query = searchInput.value.toLowerCase().trim();
    const titleFilter = filterTitle.value;
    const locationFilter = filterLocation.value;
    const expFilter = filterExperience.value;

    filteredCandidates = candidates.filter(c => {
        const text = `${c.candidate_id} ${c.reasoning}`.toLowerCase();

        if (query && !text.includes(query)) return false;

        if (titleFilter) {
            const hasTitle = {
                ai: /\b(ai|ml|machine learning|deep learning|nlp)\b/i,
                data: /\b(data scien)/i,
                software: /\b(software engineer)/i,
                backend: /\b(backend|full stack)/i,
                other: /\b(manager|analyst|designer|accountant|support)/i,
            };
            if (hasTitle[titleFilter] && !hasTitle[titleFilter].test(c.reasoning)) return false;
        }

        if (locationFilter) {
            const locText = c.reasoning.toLowerCase();
            const hasLoc = {
                india: /india/i,
                pune: /pune/i,
                noida: /noida/i,
                bangalore: /bengal|bangal/i,
                international: /usa|canada|uk|australia|germany|singapore/i,
            };
            if (hasLoc[locationFilter] && !hasLoc[locationFilter].test(locText)) return false;
        }

        if (expFilter) {
            const yoeMatch = c.reasoning.match(/([\d.]+)\s+years/);
            if (yoeMatch) {
                const yoe = parseFloat(yoeMatch[1]);
                if (expFilter === '5-9' && (yoe < 5 || yoe > 9)) return false;
                if (expFilter === '3-5' && (yoe < 3 || yoe > 5)) return false;
                if (expFilter === '9+' && yoe < 9) return false;
            }
        }

        return true;
    });

    renderCandidates();
}

// ── Modal ──
function openModal(candidate, scores) {
    const { candidate_id, rank, score, reasoning } = candidate;

    const titleMatch = reasoning.match(/^([^;]+?)(?:\s+at\s+|\s+with\s+)/);
    const title = titleMatch ? titleMatch[1] : candidate_id;

    const companyMatch = reasoning.match(/at\s+(.+?)\s+with/);
    const company = companyMatch ? companyMatch[1] : '';

    // Extract skills from reasoning
    const skillsMatch = reasoning.match(/relevant skills include ([^.;]+)/);
    const skills = skillsMatch ? skillsMatch[1].split(',').map(s => s.trim()) : [];

    modalContent.innerHTML = `
        <div class="modal-detail__header">
            <div>
                <div class="modal-detail__rank">#${rank}</div>
                <div class="modal-detail__title">${title}</div>
                <div class="modal-detail__subtitle">${company ? `at ${company} · ` : ''}${candidate_id}</div>
            </div>
            <div class="card__score" style="text-align:right">
                <div class="card__score-value" style="font-size:2rem">${score.toFixed(3)}</div>
                <div class="card__score-label">Composite Score</div>
            </div>
        </div>

        <div class="modal-detail__section">
            <h4>Score Breakdown</h4>
            <div class="modal-detail__score-grid">
                <div class="modal-score-item modal-score-item--semantic">
                    <div class="modal-score-item__value">${(scores.semantic * 100).toFixed(0)}%</div>
                    <div class="modal-score-item__label">Semantic Match</div>
                </div>
                <div class="modal-score-item modal-score-item--structural">
                    <div class="modal-score-item__value">${(scores.structural * 100).toFixed(0)}%</div>
                    <div class="modal-score-item__label">Structural Fit</div>
                </div>
                <div class="modal-score-item modal-score-item--behavioral">
                    <div class="modal-score-item__value">${(scores.behavioral * 100).toFixed(0)}%</div>
                    <div class="modal-score-item__label">Behavioral Signals</div>
                </div>
            </div>
        </div>

        <div class="modal-detail__section">
            <h4>Ranking Reasoning</h4>
            <div class="modal-detail__reasoning">${reasoning}</div>
        </div>

        ${skills.length > 0 ? `
        <div class="modal-detail__section">
            <h4>Relevant Skills</h4>
            <div class="modal-detail__tags">
                ${skills.map(s => `<span class="detail-tag">${s}</span>`).join('')}
            </div>
        </div>
        ` : ''}
    `;

    modalOverlay.hidden = false;
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    modalOverlay.hidden = true;
    document.body.style.overflow = '';
}

// ── Utilities ──
function debounce(fn, ms) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), ms);
    };
}
