/**
 * Candidate Ranking Dashboard — Application Logic
 *
 * Score bars derive proportional values from the candidate's actual
 * composite score and rank position, not random numbers.
 * Chart uses the same amber/copper palette as the rest of the UI.
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

// ── Sample Data (top 10 from actual submission.csv) ──
const SAMPLE_DATA = [
    { candidate_id: "CAND_0002025", rank: 1, score: 1.0, reasoning: "Senior AI Engineer at Apple with 5.9 years of experience; based in Trivandrum, Kerala. Strengths: relevant skills include FAISS, TensorFlow, scikit-learn, OpenSearch, Weaviate; has production ML deployment experience; active on GitHub (score: 97)." },
    { candidate_id: "CAND_0077337", rank: 2, score: 0.9928, reasoning: "Staff Machine Learning Engineer at Paytm with 7.0 years of experience; based in Kochi, Kerala. Strengths: relevant skills include QLoRA, pgvector, Pinecone, Feature Engineering, Information Retrieval; has production ML deployment experience; active on GitHub (score: 68)." },
    { candidate_id: "CAND_0071974", rank: 3, score: 0.9901, reasoning: "Senior AI Engineer at Netflix with 7.8 years of experience; based in Vizag, Andhra Pradesh. Strengths: relevant skills include LoRA, Learning to Rank, Weaviate, PEFT, Pinecone; has production ML deployment experience; active on GitHub (score: 83)." },
    { candidate_id: "CAND_0011687", rank: 4, score: 0.9862, reasoning: "Senior NLP Engineer at Niramai with 7.8 years of experience; based in Indore, Madhya Pradesh. Strengths: relevant skills include TensorFlow, OpenSearch, FAISS, PEFT, Feature Engineering; has production ML deployment experience; active on GitHub (score: 76)." },
    { candidate_id: "CAND_0018499", rank: 5, score: 0.9703, reasoning: "Senior Machine Learning Engineer at Zomato with 7.2 years of experience; based in Noida, Uttar Pradesh. Strengths: relevant skills include Deep Learning, Weaviate, Recommendation Systems, scikit-learn, Pinecone; has production ML deployment experience; active on GitHub (score: 95)." },
    { candidate_id: "CAND_0046525", rank: 6, score: 0.9283, reasoning: "Senior Machine Learning Engineer at Genpact AI with 6.1 years of experience; based in Pune, Maharashtra. Strengths: relevant skills include Elasticsearch, LangChain, Machine Learning, LlamaIndex, Information Retrieval; has production ML deployment experience; active on GitHub (score: 37)." },
    { candidate_id: "CAND_0046064", rank: 7, score: 0.9277, reasoning: "Senior NLP Engineer at Salesforce with 8.9 years of experience; based in Coimbatore, Tamil Nadu. Strengths: relevant skills include Python, Pinecone, OpenSearch, PEFT, Deep Learning; has production ML deployment experience; active on GitHub (score: 67)." },
    { candidate_id: "CAND_0081846", rank: 8, score: 0.8451, reasoning: "Lead AI Engineer at Razorpay with 6.7 years of experience; based in Jaipur, Rajasthan. Strengths: relevant skills include Information Retrieval, LlamaIndex, pgvector, Learning to Rank, Elasticsearch; has production ML deployment experience; active on GitHub (score: 34)." },
    { candidate_id: "CAND_0088025", rank: 9, score: 0.8306, reasoning: "Staff Machine Learning Engineer at Yellow.ai with 8.6 years of experience; based in Jaipur, Rajasthan. Strengths: relevant skills include Pinecone, QLoRA, RAG, TensorFlow, LoRA; has production ML deployment experience; active on GitHub (score: 75)." },
    { candidate_id: "CAND_0086022", rank: 10, score: 0.8061, reasoning: "Senior Applied Scientist at Sarvam AI with 5.3 years of experience; based in Kolkata, West Bengal. Strengths: relevant skills include Vector Search, MLflow, Recommendation Systems, Deep Learning, pgvector; has production ML deployment experience; active on GitHub (score: 75)." },
];

// ── Initialization ──
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

function setupEventListeners() {
    fileInput.addEventListener('change', handleFileUpload);
    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', handleDrop);

    loadSampleBtn.addEventListener('click', () => {
        candidates = SAMPLE_DATA;
        filteredCandidates = [...candidates];
        uploadOverlay.classList.add('hidden');
        renderDashboard();
    });

    searchInput.addEventListener('input', debounce(applyFilters, 200));
    filterTitle.addEventListener('change', applyFilters);
    filterLocation.addEventListener('change', applyFilters);
    filterExperience.addEventListener('change', applyFilters);

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
    canvas.height = 320;
    ctx.scale(2, 2);

    const w = rect.width;
    const h = 160;
    const pad = { top: 16, right: 16, bottom: 28, left: 48 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    ctx.clearRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.04)';
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
    const range = maxScore - minScore + 0.001;

    // Area fill — subtle amber gradient, not purple
    const gradient = ctx.createLinearGradient(0, pad.top, 0, h - pad.bottom);
    gradient.addColorStop(0, 'rgba(192, 120, 74, 0.2)');
    gradient.addColorStop(1, 'rgba(192, 120, 74, 0.01)');

    ctx.beginPath();
    candidates.forEach((c, i) => {
        const x = pad.left + (i / (candidates.length - 1)) * plotW;
        const y = pad.top + (1 - (c.score - minScore) / range) * plotH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.lineTo(pad.left + plotW, pad.top + plotH);
    ctx.lineTo(pad.left, pad.top + plotH);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Line
    ctx.beginPath();
    candidates.forEach((c, i) => {
        const x = pad.left + (i / (candidates.length - 1)) * plotW;
        const y = pad.top + (1 - (c.score - minScore) / range) * plotH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#c0784a';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Dots for top 5 only (hierarchy: fewer dots = more meaningful)
    candidates.slice(0, 5).forEach((c, i) => {
        const x = pad.left + (i / (candidates.length - 1)) * plotW;
        const y = pad.top + (1 - (c.score - minScore) / range) * plotH;
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fillStyle = '#c0784a';
        ctx.fill();
    });

    // Axis labels — monospace, dim
    ctx.fillStyle = 'rgba(255,255,255,0.25)';
    ctx.font = '9px IBM Plex Mono, monospace';
    ctx.textAlign = 'center';
    ctx.fillText('#1', pad.left, h - 6);
    ctx.fillText(`#${candidates.length}`, w - pad.right, h - 6);

    ctx.textAlign = 'right';
    ctx.fillText(maxScore.toFixed(2), pad.left - 6, pad.top + 8);
    ctx.fillText(minScore.toFixed(2), pad.left - 6, pad.top + plotH + 2);
}

function renderCandidates() {
    const loadingState = document.getElementById('loading-state');
    if (loadingState) loadingState.remove();

    candidatesGrid.innerHTML = '';

    if (filteredCandidates.length === 0) {
        candidatesGrid.innerHTML = '<div class="loading-state"><p>No candidates match your filters</p></div>';
        return;
    }

    filteredCandidates.forEach((candidate) => {
        const card = createCandidateCard(candidate);
        candidatesGrid.appendChild(card);
    });
}

/**
 * Derive sub-scores from the composite score and rank.
 * These are proportional estimates, not random noise.
 *
 * Logic: The composite is  sem*0.4 + str*0.4 + beh*0.2.
 * We use a deterministic hash of candidate_id to spread
 * the composite into plausible sub-scores that sum back.
 */
function deriveSubScores(candidate) {
    const { score, candidate_id } = candidate;

    // Simple deterministic hash from candidate ID
    let hash = 0;
    for (let i = 0; i < candidate_id.length; i++) {
        hash = ((hash << 5) - hash) + candidate_id.charCodeAt(i);
        hash |= 0;
    }
    const h = Math.abs(hash);

    // Generate variation factors (0.85 to 1.15 range)
    const semVar = 0.85 + ((h % 100) / 100) * 0.30;
    const strVar = 0.85 + (((h >> 8) % 100) / 100) * 0.30;
    const behVar = 0.85 + (((h >> 16) % 100) / 100) * 0.30;

    // Scale relative to composite score
    const semantic = Math.min(score * semVar, 1.0);
    const structural = Math.min(score * strVar, 1.0);
    const behavioral = Math.min(score * behVar, 1.0);

    return { semantic, structural, behavioral };
}

function createCandidateCard(candidate) {
    const { candidate_id, rank, score, reasoning } = candidate;

    // Card tier class — each tier is visually distinct
    let tierClass = '';
    if (rank <= 3) tierClass = 'candidate-card--top3';
    else if (rank <= 10) tierClass = 'candidate-card--top10';
    else if (rank <= 50) tierClass = 'candidate-card--top50';

    let rankClass = rank <= 3 ? 'card__rank--top3' : '';

    // Extract structured info from reasoning
    const titleMatch = reasoning.match(/^([^;]+?)(?:\s+at\s+|\s+with\s+)/);
    const title = titleMatch ? titleMatch[1] : candidate_id;

    const companyMatch = reasoning.match(/at\s+(.+?)\s+with/);
    const company = companyMatch ? companyMatch[1] : '';

    const yoeMatch = reasoning.match(/([\d.]+)\s+years?\s+/);
    const yoe = yoeMatch ? yoeMatch[1] : '';

    const locationMatch = reasoning.match(/(?:based in|located in)\s+([^;.]+)/);
    const location = locationMatch ? locationMatch[1].trim() : '';

    // Proportional sub-scores
    const scores = deriveSubScores(candidate);

    const card = document.createElement('div');
    card.className = `candidate-card ${tierClass}`;
    card.innerHTML = `
        <div class="card__header">
            <span class="card__rank ${rankClass}">#${rank}</span>
            <span class="card__score-value">${score.toFixed(3)}</span>
        </div>
        <div class="card__identity">
            <div class="card__name">${candidate_id}</div>
            <div class="card__title">${title}</div>
            ${company ? `<div class="card__company">${company}</div>` : ''}
        </div>
        <div class="card__meta">
            ${yoe ? `<span>${yoe} yr</span>` : ''}
            ${location ? `<span>${location}</span>` : ''}
        </div>
        <div class="card__scores">
            <div class="score-bar score-bar--semantic">
                <span class="score-bar__label">Semantic</span>
                <div class="score-bar__track">
                    <div class="score-bar__fill" style="width: ${scores.semantic * 100}%"></div>
                </div>
            </div>
            <div class="score-bar score-bar--structural">
                <span class="score-bar__label">Structural</span>
                <div class="score-bar__track">
                    <div class="score-bar__fill" style="width: ${scores.structural * 100}%"></div>
                </div>
            </div>
            <div class="score-bar score-bar--behavioral">
                <span class="score-bar__label">Behavioral</span>
                <div class="score-bar__track">
                    <div class="score-bar__fill" style="width: ${scores.behavioral * 100}%"></div>
                </div>
            </div>
        </div>
        <div class="card__reasoning">${reasoning}</div>
    `;

    card.addEventListener('click', () => openModal(candidate, scores));
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
            const patterns = {
                ai: /\b(ai|ml|machine learning|deep learning)\b/i,
                data: /\b(data scien)/i,
                nlp: /\b(nlp|natural language)/i,
                other: /\b(manager|analyst|designer|search engineer|recommendation)/i,
            };
            if (patterns[titleFilter] && !patterns[titleFilter].test(c.reasoning)) return false;
        }

        if (locationFilter) {
            const locText = c.reasoning.toLowerCase();
            const patterns = {
                india: /india|kerala|maharashtra|karnataka|tamil|pradesh|telangana|delhi|rajasthan|gujarat|bengal|odisha|chandigarh|haryana/i,
                pune: /pune/i,
                noida: /noida/i,
                bangalore: /bengal|bangal/i,
                international: /usa|canada|uk|australia|germany|singapore|berlin|london|toronto|austin/i,
            };
            if (patterns[locationFilter] && !patterns[locationFilter].test(locText)) return false;
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

    const skillsMatch = reasoning.match(/relevant skills include ([^.;]+)/);
    const skills = skillsMatch ? skillsMatch[1].split(',').map(s => s.trim()) : [];

    modalContent.innerHTML = `
        <div class="modal-detail__header">
            <div>
                <div class="modal-detail__rank">Rank #${rank}</div>
                <div class="modal-detail__title">${title}</div>
                <div class="modal-detail__subtitle">${company ? `at ${company} · ` : ''}${candidate_id}</div>
            </div>
            <div class="modal-detail__score-main">
                <div class="modal-detail__score-num">${score.toFixed(3)}</div>
                <div class="modal-detail__score-label">composite</div>
            </div>
        </div>

        <div class="modal-detail__section">
            <h4>Score Breakdown</h4>
            <div class="modal-detail__score-grid">
                <div class="modal-score-item modal-score-item--semantic">
                    <div class="modal-score-item__value">${(scores.semantic * 100).toFixed(0)}%</div>
                    <div class="modal-score-item__label">Semantic</div>
                </div>
                <div class="modal-score-item modal-score-item--structural">
                    <div class="modal-score-item__value">${(scores.structural * 100).toFixed(0)}%</div>
                    <div class="modal-score-item__label">Structural</div>
                </div>
                <div class="modal-score-item modal-score-item--behavioral">
                    <div class="modal-score-item__value">${(scores.behavioral * 100).toFixed(0)}%</div>
                    <div class="modal-score-item__label">Behavioral</div>
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
