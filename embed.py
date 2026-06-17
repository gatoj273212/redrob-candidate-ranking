#!/usr/bin/env python3
"""
embed.py — Pre-computation phase: generate sentence embeddings for all candidates.

Uses Scikit-Learn's TF-IDF Vectorizer + Truncated SVD (Latent Semantic Analysis)
to create dense semantic representations of profiles. This is highly efficient,
requires no deep learning dependencies (such as PyTorch/ONNX) which frequently face
DLL loading compatibility issues on newer Python installations on Windows.

Usage:
    python embed.py [--candidates ./India_runs_data_and_ai_challenge/candidates.jsonl]
"""

import json
import argparse
import time
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import joblib

CANDIDATES_DEFAULT = os.path.join("India_runs_data_and_ai_challenge", "candidates.jsonl")
OUTPUT_DIR = "precomputed"


def build_candidate_document(candidate: dict) -> str:
    """
    Build a text document for embedding from a candidate's profile.
    Only includes skills used for >= 6 months to avoid keyword stuffing.
    """
    parts = []

    profile = candidate.get("profile", {})
    if profile.get("headline"):
        parts.append(profile["headline"])
    if profile.get("summary"):
        parts.append(profile["summary"])

    if profile.get("current_title"):
        parts.append(f"Current role: {profile['current_title']} at {profile.get('current_company', 'Unknown')}")

    career = candidate.get("career_history", [])
    for role in career[:3]:
        title = role.get("title", "")
        company = role.get("company", "")
        desc = role.get("description", "")
        duration = role.get("duration_months", 0)
        if desc:
            parts.append(f"{title} at {company} ({duration} months): {desc}")

    skills = candidate.get("skills", [])
    meaningful_skills = [s["name"] for s in skills if s.get("duration_months", 0) >= 6]
    if meaningful_skills:
        parts.append("Skills: " + ", ".join(meaningful_skills))

    education = candidate.get("education", [])
    for edu in education:
        field = edu.get("field_of_study", "")
        degree = edu.get("degree", "")
        institution = edu.get("institution", "")
        if field:
            parts.append(f"{degree} in {field} from {institution}")

    certs = candidate.get("certifications", [])
    if certs:
        cert_names = [c.get("name", "") for c in certs if c.get("name")]
        if cert_names:
            parts.append("Certifications: " + ", ".join(cert_names))

    return " | ".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Pre-compute candidate embeddings using TF-IDF + SVD")
    parser.add_argument("--candidates", default=CANDIDATES_DEFAULT, help="Path to candidates.jsonl")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"{'='*60}")
    print(f"Redrob Ranker — Embedding Pre-computation (TF-IDF + SVD)")
    print(f"{'='*60}")
    print(f"Candidates file: {args.candidates}")
    print()

    # ── Step 1: Load candidates ──
    print(f"[1/3] Loading candidates from {args.candidates}...")
    t0 = time.time()
    candidate_ids = []
    documents = []

    with open(args.candidates, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            cand = json.loads(line)
            candidate_ids.append(cand["candidate_id"])
            documents.append(build_candidate_document(cand))

            if (i + 1) % 10000 == 0:
                print(f"  Loaded {i + 1} candidates...")

    n = len(candidate_ids)
    print(f"  Loaded {n} candidates in {time.time() - t0:.1f}s")

    # ── Step 2: TF-IDF Vectorization ──
    print(f"\n[2/3] Computing TF-IDF vectorizer...")
    t1 = time.time()
    # Use max_features=30000 to keep the representation rich but memory footprint small
    vectorizer = TfidfVectorizer(max_features=30000, stop_words="english", ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(documents)
    print(f"  TF-IDF matrix computed: shape {tfidf_matrix.shape} in {time.time() - t1:.1f}s")

    # ── Step 3: Latent Semantic Analysis (Truncated SVD) ──
    print(f"\n[3/3] Fitting TruncatedSVD for semantic embeddings (384 dimensions)...")
    t2 = time.time()
    svd = TruncatedSVD(n_components=384, random_state=42)
    embeddings = svd.fit_transform(tfidf_matrix)
    
    # L2 normalize the SVD projections to ensure cosine similarity equals dot product
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.clip(norms, 1e-9, None)
    embeddings = (embeddings / norms).astype(np.float32)
    
    print(f"  TruncatedSVD fitted: shape {embeddings.shape} in {time.time() - t2:.1f}s")

    # ── Save to disk ──
    print(f"\nSaving pre-computed artifacts to {OUTPUT_DIR}/...")

    emb_path = os.path.join(OUTPUT_DIR, "candidate_embeddings.npy")
    np.save(emb_path, embeddings)
    print(f"  Saved embeddings: {emb_path} ({os.path.getsize(emb_path) / 1e6:.1f} MB)")

    ids_path = os.path.join(OUTPUT_DIR, "candidate_ids.json")
    with open(ids_path, "w") as f:
        json.dump(candidate_ids, f)
    print(f"  Saved candidate IDs: {ids_path}")

    # Save fitted models for transform phase in rank.py
    vectorizer_path = os.path.join(OUTPUT_DIR, "tfidf_vectorizer.joblib")
    joblib.dump(vectorizer, vectorizer_path)
    print(f"  Saved TF-IDF Vectorizer: {vectorizer_path}")

    svd_path = os.path.join(OUTPUT_DIR, "svd_model.joblib")
    joblib.dump(svd, svd_path)
    print(f"  Saved TruncatedSVD model: {svd_path}")

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"Pre-computation complete in {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"Embedding dimensions: {embeddings.shape[1]}")
    print(f"Total candidates: {n}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
