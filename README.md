# Redrob AI — Intelligent Candidate Discovery & Ranking System

> A hybrid AI ranking system that goes beyond keyword matching to find candidates who genuinely fit the role. Built for the **India Runs by Redrob AI** Hackathon — Track 1: Data & AI Challenge.

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    TWO-PHASE RANKING PIPELINE                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Phase 1: Pre-computation (embed.py) -- runs once, offline        │
│  ┌─────────────┐    ┌───────────────────┐    ┌────────────────┐  │
│  │ Load 100K   │--->│ Build narrative   │--->│ TF-IDF + SVD   │  │
│  │ candidates  │    │ documents         │    │ (384 dims)     │  │
│  └─────────────┘    └───────────────────┘    └───────┬────────┘  │
│                                                       │           │
│                                              ┌────────v────────┐ │
│                                              │ Save .npy       │ │
│                                              │ embeddings +    │ │
│                                              │ fitted models   │ │
│                                              └─────────────────┘ │
│                                                                    │
│  Phase 2: Ranking (rank.py) -- < 5 min, CPU only, no network     │
│  ┌──────────┐  ┌───────────────────────────────────────────────┐ │
│  │ Encode   │  │         HYBRID SCORING ENGINE                  │ │
│  │ JD text  │  │                                                │ │
│  └────┬─────┘  │  ┌────────────┐ ┌──────────┐ ┌────────────┐  │ │
│       │        │  │ Semantic   │ │Structural│ │ Behavioral │  │ │
│       │        │  │ Score 40%  │ │Score 40% │ │ Score 20%  │  │ │
│       │        │  │ (cosine    │ │(title,   │ │(activity,  │  │ │
│       │        │  │ similarity)│ │exp, skill│ │response    │  │ │
│       │        │  │            │ │career,   │ │rate,       │  │ │
│       └────────┤  │            │ │location) │ │GitHub)     │  │ │
│                │  └─────┬──────┘ └────┬─────┘ └─────┬──────┘  │ │
│                │        └──────┬──────┘──────────────┘         │ │
│                │               v                                │ │
│                │     ┌─────────────────────┐                   │ │
│                │     │  Honeypot Detection  │                   │ │
│                │     │  & Disqualifiers     │                   │ │
│                │     └──────────┬──────────┘                   │ │
│                │               v                                │ │
│                │     ┌─────────────────────┐                   │ │
│                │     │  Top 100 + Reasoning │--> submission.csv │ │
│                │     └─────────────────────┘                   │ │
│                └───────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- ~500 MB disk space (for TF-IDF models + embeddings)

### Setup
```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/redrob.git
cd redrob

# Install dependencies
pip install -r requirements.txt

# Place dataset
# Ensure India_runs_data_and_ai_challenge/candidates.jsonl exists
```

### Run

```bash
# Step 1: Pre-compute embeddings (runs once, ~2 min)
python embed.py

# Step 2: Generate ranked submission (< 5 min on CPU)
python rank.py --out submission.csv

# Step 3: Validate
python India_runs_data_and_ai_challenge/validate_submission.py submission.csv
```

### Single Reproduction Command
```bash
python embed.py && python rank.py --candidates ./India_runs_data_and_ai_challenge/candidates.jsonl --out ./submission.csv
```

## 🧠 Approach — How It Works

### The Core Insight

The JD for "Senior AI Engineer — Founding Team" is deliberately written to trap keyword-matching systems. It explicitly states:
> *"The right answer is not 'find candidates whose skills section contains the most AI keywords.' That's a trap we've explicitly built into the dataset."*

Our system addresses this by combining three complementary scoring approaches:

### 1. Semantic Scoring (40% weight)
- Builds a narrative document for each candidate from their profile summary, career descriptions, and duration-filtered skills
- Uses **TF-IDF vectorization** (30K features, unigrams + bigrams) followed by **Truncated SVD / Latent Semantic Analysis** (384 dimensions) to create dense semantic representations
- Computes cosine similarity between the JD embedding and each candidate embedding
- Captures conceptual alignment — candidates who "talk about" similar problems even without exact keyword overlap
- Skills with `duration_months < 6` are excluded to prevent keyword-stuffing from inflating semantic scores

### 2. Structural Scoring (40% weight)
Rule-based engine evaluating hard JD requirements:

| Component | Weight | Logic |
|---|---|---|
| **Title/Domain Fit** | 25% | Is the candidate's title ML/AI/Engineering? Penalizes HR, Marketing, Sales titles |
| **Skill Match** | 25% | Count of JD-required skills with `duration >= 6 months`, weighted by proficiency |
| **Experience Band** | 20% | Gaussian scoring centered on 6-8 years (JD ideal range) |
| **Career Evidence** | 17.5% | Production ML work at product companies (not consulting-only) |
| **Location** | 7.5% | India preferred; Pune/Noida bonus |
| **Education** | 5% | CS/ML degree + institution tier (minor factor) |

### 3. Behavioral Scoring (20% weight)
Platform signals that indicate hiring feasibility:
- **Activity recency**: When did they last log in? >180 days = effectively unavailable
- **Response rate**: Will they respond to recruiter outreach?
- **Interview completion**: Do they follow through on interview processes?
- **Notice period**: Can they actually start within a reasonable timeframe?
- **GitHub activity**: Active developer signal (especially relevant for AI Engineering roles)
- **Open to work**: Are they actively job-seeking?

### 4. Honeypot Detection
Identifies candidates with impossible or contradictory profiles:
- Expert in 10+ skills with 0 months of usage
- Non-technical titles (Marketing Manager) with excessive AI/ML expert skills
- Skills in profile that completely contradict career history descriptions
- Impossibly long tenures at tiny companies
- Detected honeypots are multiplied by 0.01 (effectively eliminated)

### 5. Disqualifier Penalties
JD-explicit disqualifiers applied as score multipliers:
- Entire career at consulting firms (TCS, Infosys, Wipro, etc.)
- Non-technical title with no ML career history
- Primary expertise in CV/speech/robotics without NLP/IR
- Insufficient experience (<2 years)

## 📊 Scoring Formula

```
raw_score = semantic_score x 0.40 + structural_score x 0.40 + behavioral_score x 0.20

final_score = raw_score x disqualifier_penalty x honeypot_penalty
```

Where:
- `disqualifier_penalty` in [0.08, 1.0] based on JD-explicit disqualifiers
- `honeypot_penalty` = 0.01 if honeypot detected, else 1.0

## 🔍 Design Decisions

### Why TF-IDF + SVD instead of a neural model?
The compute constraints (5 min, CPU only, no network) combined with Python 3.14 DLL compatibility issues for PyTorch/ONNX on Windows made neural sentence transformers impractical. TF-IDF + Truncated SVD (Latent Semantic Analysis) provides a robust, dependency-light semantic representation that captures topic-level meaning without any deep learning runtime. The 384-dimensional SVD space captures latent semantic topics that go well beyond keyword matching.

### Why filter skills by duration?
The dataset contains keyword-stuffing traps: candidates with 20+ AI skills listed but 0 months of actual usage. Filtering by `duration_months >= 6` eliminates these false positives while keeping genuinely experienced candidates.

### Why pre-filter to 3000 before structural scoring?
Semantic scoring runs in O(n) via a single matrix multiplication. Structural scoring requires parsing JSON per candidate. Pre-filtering to the top 3000 by semantic score keeps the ranking step well under 5 minutes.

### Why consulting-only is penalized?
The JD explicitly states: *"People who have only worked at consulting firms (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, etc.) in their entire career. We've had bad fit experiences."* However, candidates with mixed experience (consulting + product) are not penalized.

## 📁 Repository Structure

```
redrob/
├── embed.py                     # Phase 1: Pre-compute TF-IDF + SVD embeddings
├── rank.py                      # Phase 2: Generate ranked submission
├── requirements.txt             # Python dependencies (numpy, scikit-learn, joblib, pyyaml)
├── README.md                    # This file
├── submission.csv               # Generated submission
├── submission_metadata.yaml     # Submission metadata
├── precomputed/                 # Cached embeddings (generated by embed.py)
│   ├── candidate_embeddings.npy # 100K x 384 dense vectors
│   ├── candidate_ids.json       # Candidate ID -> index mapping
│   ├── tfidf_vectorizer.joblib  # Fitted TF-IDF vectorizer
│   └── svd_model.joblib         # Fitted TruncatedSVD model
├── dashboard/                   # Interactive web dashboard (bonus)
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── India_runs_data_and_ai_challenge/  # Dataset (not in repo)
    ├── candidates.jsonl
    ├── job_description.docx
    └── ...
```

## ⚡ Performance

- **Pre-computation**: ~2 min (one-time, generates TF-IDF + SVD embeddings for 100K candidates)
- **Ranking**: ~5 seconds on CPU (well within 5-minute constraint)
- **Memory**: < 4 GB RAM during ranking
- **No GPU required** — all inference runs on CPU
- **No network calls** — fully offline

## 🛠️ Tech Stack

- **Semantic Model**: TF-IDF (30K features) + TruncatedSVD (384 dimensions) — Latent Semantic Analysis
- **Vector Operations**: NumPy (CPU-optimized BLAS operations)
- **Language**: Python 3.11+
- **Dependencies**: numpy, scikit-learn, joblib, PyYAML (no PyTorch/TensorFlow/ONNX required)

## 📝 AI Tools Declaration

- **Gemini (Antigravity IDE)**: Architecture design, code generation, debugging
- **No AI tools used for actual candidate evaluation** — the ranking is deterministic and based on the scoring pipeline described above

## License

MIT
