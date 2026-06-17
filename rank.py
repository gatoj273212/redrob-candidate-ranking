#!/usr/bin/env python3
"""
rank.py — Ranking phase: produce the top-100 ranked CSV from precomputed embeddings.

This is the time-constrained step: must complete in < 5 minutes on CPU, 16 GB RAM, no network.

Usage:
    python rank.py [--candidates ./India_runs_data_and_ai_challenge/candidates.jsonl] [--out submission.csv]
"""

import json
import csv
import argparse
import time
import re
import os
from datetime import datetime, date
from collections import defaultdict
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

CANDIDATES_DEFAULT = os.path.join("India_runs_data_and_ai_challenge", "candidates.jsonl")
PRECOMPUTED_DIR = "precomputed"
OUTPUT_DEFAULT = "submission.csv"
TODAY = date(2026, 6, 17)  # Reference date for recency calculations

# ─── JD-derived configuration ───

# The role: Senior AI Engineer — Founding Team at Redrob AI
JD_TEXT = """
Senior AI Engineer at Redrob AI, a Series A AI-native talent intelligence platform.
Building the intelligence layer: ranking, retrieval, and matching systems for recruiters and candidates.
Need deep technical depth in modern ML systems: embeddings, retrieval, ranking, LLMs, fine-tuning.
Scrappy product-engineering attitude, willing to ship fast.
Must have: production experience with embeddings-based retrieval, vector databases or hybrid search,
strong Python, evaluation frameworks for ranking systems (NDCG, MRR, MAP, A/B testing).
Nice to have: LLM fine-tuning (LoRA, QLoRA, PEFT), learning-to-rank, HR-tech exposure.
Experience: 5-9 years, ideal 6-8 years in applied ML/AI at product companies.
Location: Pune/Noida India (Hybrid). Open to Tier-1 Indian cities.
Must have shipped at least one end-to-end ranking, search, or recommendation system to real users.
"""

# Must-have skills (core JD requirements)
MUST_HAVE_SKILLS = {
    # Embeddings & retrieval
    "embeddings", "sentence embeddings", "vector search", "vector databases",
    "faiss", "pinecone", "weaviate", "qdrant", "milvus", "chromadb",
    "elasticsearch", "opensearch", "information retrieval",
    # ML fundamentals
    "python", "pytorch", "tensorflow", "keras", "scikit-learn",
    "machine learning", "deep learning", "neural networks",
    # NLP & LLMs
    "nlp", "natural language processing", "transformers",
    "bert", "gpt", "llm", "large language models",
    "hugging face", "huggingface",
    # Ranking & search
    "ranking", "learning to rank", "recommendation systems",
    "search", "retrieval",
    # Evaluation
    "a/b testing", "ndcg", "mrr",
    # Production ML
    "mlops", "mlflow", "docker", "kubernetes",
    "flask", "fastapi",
}

# Nice-to-have skills
NICE_TO_HAVE_SKILLS = {
    "fine-tuning", "fine-tuning llms", "lora", "qlora", "peft", "rlhf",
    "rag", "retrieval augmented generation",
    "langchain", "llamaindex",
    "xgboost", "lightgbm", "catboost",
    "spark", "pyspark", "airflow", "kafka",
    "aws", "gcp", "azure",
    "weights & biases", "wandb",
    "bentoml", "triton", "onnx",
    "feature engineering", "data engineering",
    "statistical modeling",
    "sql", "postgresql", "mongodb", "redis",
    "git", "linux", "bash",
}

# AI/ML relevant titles (positive signal)
AI_ML_TITLES = {
    "ai engineer", "senior ai engineer", "lead ai engineer", "principal ai engineer",
    "ml engineer", "machine learning engineer", "senior ml engineer", "senior machine learning engineer",
    "lead ml engineer", "principal ml engineer",
    "data scientist", "senior data scientist", "lead data scientist",
    "nlp engineer", "senior nlp engineer",
    "research engineer", "applied scientist", "applied ml engineer",
    "deep learning engineer", "computer vision engineer",
    "backend engineer", "software engineer", "senior software engineer",
    "full stack engineer", "platform engineer",
    "data engineer", "senior data engineer",
    "mlops engineer", "devops engineer",
    "junior ml engineer", "junior ai engineer",
    "junior data scientist",
}

# Non-technical titles (strong negative signal for AI Engineer role)
NON_TECH_TITLES = {
    "hr manager", "human resources", "hr",
    "marketing manager", "marketing",
    "sales executive", "sales manager", "sales",
    "accountant", "accounting",
    "content writer", "copywriter", "content",
    "graphic designer", "designer",
    "operations manager", "operations",
    "customer support", "customer service",
    "project manager", "program manager",
    "business analyst",
    "civil engineer",
    "mechanical engineer",
    "teacher", "professor", "lecturer",
    "receptionist", "administrative",
    "recruiter", "talent acquisition",
}

# Consulting firms (JD explicitly warns against consulting-only careers)
CONSULTING_FIRMS = {
    "tcs", "tata consultancy services",
    "infosys",
    "wipro",
    "accenture",
    "cognizant",
    "capgemini",
    "hcl", "hcl technologies",
    "tech mahindra",
    "mindtree",
    "l&t infotech", "lti",
    "mphasis",
}

# Indian Tier-1 cities (preferred locations from JD)
INDIA_TIER1_CITIES = {
    "pune", "noida", "mumbai", "delhi", "delhi ncr",
    "bangalore", "bengaluru", "hyderabad",
    "gurgaon", "gurugram", "chennai", "kolkata",
    "new delhi", "greater noida", "ghaziabad",
}

# Production keywords to detect in career descriptions
PRODUCTION_KEYWORDS = {
    "production", "deployed", "shipped", "scale", "scaled",
    "real users", "user-facing", "end-to-end", "e2e",
    "latency", "throughput", "availability", "uptime",
    "monitoring", "alerting", "on-call",
    "ci/cd", "pipeline", "infrastructure",
    "a/b test", "experiment", "metrics",
    "api", "microservice", "service",
    "million", "billion", "thousands",
}

# Research-only keywords (not necessarily bad, but need production balance)
RESEARCH_ONLY_KEYWORDS = {
    "academic", "research lab", "phd research", "paper", "publication",
    "thesis", "dissertation",
}


# ─────────────────────────────────────────────────────────────────────────────
# Scoring Functions
# ─────────────────────────────────────────────────────────────────────────────

def compute_semantic_score(jd_embedding, candidate_embedding):
    """Cosine similarity between JD and candidate embeddings (already L2-normalized)."""
    return float(np.dot(jd_embedding, candidate_embedding))


def compute_title_score(candidate):
    """Score based on how well the current title matches the JD role."""
    profile = candidate.get("profile", {})
    current_title = profile.get("current_title", "").lower().strip()

    # Check career history titles too
    career = candidate.get("career_history", [])
    all_titles = [current_title] + [r.get("title", "").lower().strip() for r in career]

    score = 0.0

    # Current title is most important
    if current_title in AI_ML_TITLES or any(t in current_title for t in
        ["ai", "ml", "machine learning", "data scien", "nlp", "deep learning"]):
        score = 1.0
    elif any(t in current_title for t in ["software engineer", "backend", "full stack", "platform"]):
        score = 0.6
    elif any(t in current_title for t in ["data engineer", "devops", "mlops"]):
        score = 0.5
    elif current_title in NON_TECH_TITLES or any(nt in current_title for nt in NON_TECH_TITLES):
        score = 0.05  # Very low but not zero
    else:
        score = 0.2  # Unknown title, neutral

    # Check if any historical title is AI/ML relevant
    has_ml_history = any(
        any(kw in t for kw in ["ai", "ml", "machine learning", "data scien", "nlp", "deep learning"])
        for t in all_titles
    )
    if has_ml_history and score < 0.7:
        score = max(score, 0.5)  # Boost if they have ML history even if current title isn't ML

    return score


def compute_experience_score(candidate):
    """Gaussian-like scoring centered on 6-8 years (JD ideal range)."""
    yoe = candidate.get("profile", {}).get("years_of_experience", 0)

    if 5 <= yoe <= 9:
        # In range: peak score for 6-8
        if 6 <= yoe <= 8:
            return 1.0
        elif 5 <= yoe < 6:
            return 0.85
        else:  # 8 < yoe <= 9
            return 0.85
    elif 4 <= yoe < 5:
        return 0.6
    elif 9 < yoe <= 12:
        return 0.5
    elif 3 <= yoe < 4:
        return 0.35
    elif 12 < yoe <= 15:
        return 0.3
    elif yoe < 3:
        return 0.15
    else:  # > 15
        return 0.2


def compute_skill_match_score(candidate):
    """
    Score based on how many JD-required skills the candidate has.
    Only counts skills with duration_months >= 6 to filter keyword stuffing.
    """
    skills = candidate.get("skills", [])

    must_have_count = 0
    nice_to_have_count = 0
    total_relevant = 0

    for skill in skills:
        name = skill.get("name", "").lower().strip()
        duration = skill.get("duration_months", 0)
        proficiency = skill.get("proficiency", "beginner")

        # Only count skills with meaningful duration
        if duration < 6:
            continue

        # Proficiency weight
        prof_weight = {"beginner": 0.3, "intermediate": 0.6, "advanced": 0.9, "expert": 1.0}.get(proficiency, 0.3)

        if name in MUST_HAVE_SKILLS or any(mh in name for mh in ["embedding", "retrieval", "ranking", "vector",
                                                                    "nlp", "machine learning", "deep learning",
                                                                    "pytorch", "tensorflow", "python"]):
            must_have_count += prof_weight
            total_relevant += 1
        elif name in NICE_TO_HAVE_SKILLS or any(nth in name for nth in ["fine-tun", "lora", "rag",
                                                                         "langchain", "xgboost", "spark"]):
            nice_to_have_count += prof_weight * 0.5
            total_relevant += 0.5

    # Normalize: aim for a score between 0-1
    # A great candidate might have 6-10 relevant must-have skills
    must_score = min(must_have_count / 5.0, 1.0)
    nice_score = min(nice_to_have_count / 3.0, 1.0)

    return must_score * 0.75 + nice_score * 0.25


def compute_career_evidence_score(candidate):
    """
    Evaluate career history for production ML/AI experience at product companies.
    """
    career = candidate.get("career_history", [])
    if not career:
        return 0.0

    score = 0.0
    has_product_company = False
    has_production_ml = False
    total_ml_months = 0
    consulting_only = True

    for role in career:
        company = role.get("company", "").lower().strip()
        title = role.get("title", "").lower().strip()
        desc = (role.get("description", "") or "").lower()
        industry = role.get("industry", "").lower()
        duration = role.get("duration_months", 0)
        company_size = role.get("company_size", "")

        # Check if this is a consulting firm
        is_consulting = any(cf in company for cf in CONSULTING_FIRMS)
        if not is_consulting:
            consulting_only = False

        # Check for product company experience
        if not is_consulting and industry not in ["consulting", "staffing"]:
            has_product_company = True

        # Check for production ML work in descriptions
        prod_keywords_found = sum(1 for kw in PRODUCTION_KEYWORDS if kw in desc)
        ml_keywords_found = sum(1 for kw in ["ml", "ai", "model", "embedding", "ranking",
                                              "recommendation", "search", "retrieval",
                                              "neural", "training", "inference",
                                              "nlp", "transformer", "vector"]
                                if kw in desc)

        if prod_keywords_found >= 2 and ml_keywords_found >= 1:
            has_production_ml = True
            total_ml_months += duration

        # Title-based ML detection
        if any(kw in title for kw in ["ml", "ai", "machine learning", "data scien",
                                       "nlp", "deep learning"]):
            total_ml_months += duration

    # Score composition
    if has_product_company:
        score += 0.3
    if has_production_ml:
        score += 0.4
    if total_ml_months >= 36:  # 3+ years in ML roles
        score += 0.2
    elif total_ml_months >= 18:
        score += 0.1
    if not consulting_only:
        score += 0.1

    return min(score, 1.0)


def compute_location_score(candidate):
    """Score based on location fit with JD requirements."""
    profile = candidate.get("profile", {})
    location = profile.get("location", "").lower().strip()
    country = profile.get("country", "").lower().strip()
    signals = candidate.get("redrob_signals", {})
    willing_to_relocate = signals.get("willing_to_relocate", False)

    if country == "india":
        # Check for preferred cities
        if any(city in location for city in ["pune", "noida"]):
            return 1.0
        elif any(city in location for city in INDIA_TIER1_CITIES):
            if willing_to_relocate:
                return 0.9
            return 0.8
        else:
            if willing_to_relocate:
                return 0.7
            return 0.5
    else:
        # Outside India
        if willing_to_relocate:
            return 0.3
        return 0.15


def compute_education_score(candidate):
    """Score based on education relevance (minor weight)."""
    education = candidate.get("education", [])
    if not education:
        return 0.3  # No education info, neutral

    score = 0.3  # Base
    for edu in education:
        field = edu.get("field_of_study", "").lower()
        degree = edu.get("degree", "").lower()
        tier = edu.get("tier", "unknown")

        # Field relevance
        if any(f in field for f in ["computer science", "machine learning", "artificial intelligence",
                                     "data science", "information technology", "software",
                                     "electronics", "electrical"]):
            score += 0.3
        elif any(f in field for f in ["mathematics", "statistics", "physics"]):
            score += 0.2

        # Degree level
        if "ph.d" in degree or "phd" in degree:
            score += 0.15
        elif "m." in degree or "master" in degree or "msc" in degree or "mtech" in degree:
            score += 0.1

        # Institution tier
        tier_bonus = {"tier_1": 0.2, "tier_2": 0.1, "tier_3": 0.05, "tier_4": 0.0, "unknown": 0.0}
        score += tier_bonus.get(tier, 0.0)

    return min(score, 1.0)


def compute_behavioral_score(candidate):
    """
    Score based on Redrob behavioral signals.
    Returns a multiplier between 0 and 1 that modifies the overall score.
    """
    signals = candidate.get("redrob_signals", {})
    score = 0.0
    weights_sum = 0.0

    # 1. Recency / Activity (high importance)
    last_active = signals.get("last_active_date", "")
    if last_active:
        try:
            last_dt = datetime.strptime(last_active, "%Y-%m-%d").date()
            days_inactive = (TODAY - last_dt).days
            if days_inactive <= 30:
                score += 0.20
            elif days_inactive <= 90:
                score += 0.15
            elif days_inactive <= 180:
                score += 0.08
            else:
                score += 0.02  # Very stale
        except (ValueError, TypeError):
            score += 0.05
    weights_sum += 0.20

    # 2. Recruiter response rate (high importance)
    response_rate = signals.get("recruiter_response_rate", 0)
    if response_rate >= 0.7:
        score += 0.15
    elif response_rate >= 0.4:
        score += 0.10
    elif response_rate >= 0.2:
        score += 0.05
    else:
        score += 0.01  # Very low response — effectively unavailable
    weights_sum += 0.15

    # 3. Open to work flag
    if signals.get("open_to_work_flag", False):
        score += 0.10
    else:
        score += 0.03
    weights_sum += 0.10

    # 4. Interview completion rate
    interview_rate = signals.get("interview_completion_rate", 0)
    if interview_rate >= 0.8:
        score += 0.08
    elif interview_rate >= 0.5:
        score += 0.05
    else:
        score += 0.02
    weights_sum += 0.08

    # 5. Notice period
    notice = signals.get("notice_period_days", 90)
    if notice <= 30:
        score += 0.10
    elif notice <= 60:
        score += 0.07
    elif notice <= 90:
        score += 0.04
    else:
        score += 0.01  # Very long notice period
    weights_sum += 0.10

    # 6. Profile completeness
    completeness = signals.get("profile_completeness_score", 0)
    if completeness >= 80:
        score += 0.05
    elif completeness >= 50:
        score += 0.03
    else:
        score += 0.01
    weights_sum += 0.05

    # 7. GitHub activity (important for AI Engineer role)
    github = signals.get("github_activity_score", -1)
    if github >= 50:
        score += 0.08
    elif github >= 20:
        score += 0.05
    elif github >= 0:
        score += 0.02
    else:  # -1 = no GitHub
        score += 0.01
    weights_sum += 0.08

    # 8. Work mode preference
    preferred = signals.get("preferred_work_mode", "")
    if preferred in ["hybrid", "flexible"]:
        score += 0.04
    elif preferred == "onsite":
        score += 0.03
    elif preferred == "remote":
        score += 0.02
    weights_sum += 0.04

    # 9. Average response time
    avg_response = signals.get("avg_response_time_hours", 100)
    if avg_response <= 24:
        score += 0.05
    elif avg_response <= 48:
        score += 0.04
    elif avg_response <= 72:
        score += 0.03
    else:
        score += 0.01
    weights_sum += 0.05

    # 10. Verification signals
    verified_count = 0
    if signals.get("verified_email", False):
        verified_count += 1
    if signals.get("verified_phone", False):
        verified_count += 1
    if signals.get("linkedin_connected", False):
        verified_count += 1
    score += 0.05 * (verified_count / 3)
    weights_sum += 0.05

    # 11. Market validation — saved by recruiters
    saved = signals.get("saved_by_recruiters_30d", 0)
    if saved >= 10:
        score += 0.05
    elif saved >= 5:
        score += 0.03
    elif saved >= 1:
        score += 0.02
    weights_sum += 0.05

    # 12. Skill assessment scores (Redrob platform assessments)
    assessments = signals.get("skill_assessment_scores", {})
    if assessments:
        avg_assessment = sum(assessments.values()) / len(assessments) if assessments else 0
        if avg_assessment >= 70:
            score += 0.05
        elif avg_assessment >= 50:
            score += 0.03
        elif avg_assessment >= 30:
            score += 0.02
        else:
            score += 0.01
    else:
        score += 0.01
    weights_sum += 0.05

    # Normalize to 0-1
    return score / weights_sum if weights_sum > 0 else 0.5


def detect_honeypot(candidate):
    """
    Detect honeypot candidates with subtly impossible profiles.
    Returns True if the candidate is likely a honeypot.
    """
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    signals = candidate.get("redrob_signals", {})

    red_flags = 0

    # Flag 1: Expert in many skills with 0 duration
    zero_duration_experts = sum(
        1 for s in skills
        if s.get("proficiency") == "expert" and s.get("duration_months", 0) == 0
    )
    if zero_duration_experts >= 3:
        red_flags += 2

    # Flag 2: Very high endorsements but beginner proficiency across many skills
    high_endorse_beginners = sum(
        1 for s in skills
        if s.get("proficiency") == "beginner" and s.get("endorsements", 0) >= 40
    )
    if high_endorse_beginners >= 3:
        red_flags += 1

    # Flag 3: Years of experience vastly exceeds career history duration
    yoe = profile.get("years_of_experience", 0)
    total_career_months = sum(r.get("duration_months", 0) for r in career)
    if yoe > 0 and total_career_months > 0:
        career_years = total_career_months / 12
        if yoe > career_years * 2.5 and yoe > 5:
            red_flags += 1

    # Flag 4: Non-technical title with excessive AI/ML skills at expert level
    current_title = profile.get("current_title", "").lower()
    is_non_tech = any(nt in current_title for nt in NON_TECH_TITLES)
    ai_expert_skills = sum(
        1 for s in skills
        if s.get("proficiency") in ["expert", "advanced"]
        and any(kw in s.get("name", "").lower() for kw in
                ["ml", "ai", "deep learning", "neural", "nlp", "pytorch",
                 "tensorflow", "embedding", "transformer", "llm", "fine-tun",
                 "rag", "vector", "gan", "reinforcement"])
    )
    if is_non_tech and ai_expert_skills >= 5:
        red_flags += 2

    # Flag 5: Skills list contradicts career descriptions
    all_descriptions = " ".join(r.get("description", "") or "" for r in career).lower()
    ai_skills_in_profile = [
        s["name"] for s in skills
        if any(kw in s.get("name", "").lower() for kw in
               ["ml", "ai", "deep learning", "neural", "nlp", "pytorch",
                "tensorflow", "embedding", "transformer"])
        and s.get("proficiency") in ["expert", "advanced"]
        and s.get("duration_months", 0) >= 24
    ]
    ai_in_descriptions = any(
        kw in all_descriptions for kw in
        ["ml", "ai", "machine learning", "model", "neural", "embedding",
         "ranking", "recommendation", "nlp", "transformer"]
    )
    if len(ai_skills_in_profile) >= 4 and not ai_in_descriptions:
        red_flags += 2

    # Flag 6: Impossibly long tenure at small/new companies
    for role in career:
        company_size = role.get("company_size", "")
        duration = role.get("duration_months", 0)
        if company_size in ["1-10", "11-50"] and duration > 120:  # 10+ years at tiny company
            red_flags += 1

    # Flag 7: Multiple career history entries with identical descriptions
    descriptions = [r.get("description", "").strip() for r in career if r.get("description", "").strip()]
    if len(descriptions) >= 3:
        unique_descs = set(descriptions)
        if len(unique_descs) == 1:  # All descriptions are identical
            red_flags += 1

    # Flag 8: Huge number of skills (20+) with most being advanced/expert
    if len(skills) >= 20:
        high_prof = sum(1 for s in skills if s.get("proficiency") in ["expert", "advanced"])
        if high_prof / len(skills) > 0.7:
            red_flags += 2

    return red_flags >= 3


def check_disqualifiers(candidate):
    """
    Check for JD-explicit disqualifiers.
    Returns a penalty multiplier (0.0 to 1.0).
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])

    penalty = 1.0

    # Disqualifier 1: Entire career at consulting firms
    if career:
        all_consulting = all(
            any(cf in r.get("company", "").lower() for cf in CONSULTING_FIRMS)
            for r in career
        )
        if all_consulting:
            penalty *= 0.15

    # Disqualifier 2: Non-technical title with no ML career history
    current_title = profile.get("current_title", "").lower()
    has_any_ml_role = any(
        any(kw in r.get("title", "").lower() for kw in
            ["ai", "ml", "machine learning", "data scien", "nlp", "software",
             "backend", "full stack", "platform", "devops"])
        for r in career
    )

    is_clearly_non_tech = any(nt in current_title for nt in
        ["hr manager", "accountant", "sales executive", "marketing manager",
         "graphic designer", "content writer", "operations manager",
         "customer support", "civil engineer", "mechanical engineer"])

    if is_clearly_non_tech and not has_any_ml_role:
        penalty *= 0.08

    # Disqualifier 3: Insufficient experience (< 2 years)
    yoe = profile.get("years_of_experience", 0)
    if yoe < 2:
        penalty *= 0.3

    # Disqualifier 4: Primary expertise is CV/speech/robotics without NLP/IR
    all_skills_lower = [s.get("name", "").lower() for s in skills]
    cv_speech_skills = sum(1 for s in all_skills_lower
                           if any(kw in s for kw in ["computer vision", "image", "object detection",
                                                      "speech", "tts", "asr", "robotics"]))
    nlp_ir_skills = sum(1 for s in all_skills_lower
                         if any(kw in s for kw in ["nlp", "natural language", "information retrieval",
                                                    "search", "ranking", "retrieval", "embedding"]))
    if cv_speech_skills >= 3 and nlp_ir_skills == 0:
        penalty *= 0.4

    return penalty


# ─────────────────────────────────────────────────────────────────────────────
# Reasoning Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_reasoning(candidate, scores, rank):
    """Generate a specific, factual 1-2 sentence reasoning for this candidate's ranking."""
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])

    title = profile.get("current_title", "Unknown")
    company = profile.get("current_company", "Unknown")
    yoe = profile.get("years_of_experience", 0)
    location = profile.get("location", "Unknown")
    country = profile.get("country", "Unknown")

    # Count relevant skills (duration >= 6 months)
    relevant_skills = [s["name"] for s in skills
                       if s.get("duration_months", 0) >= 6
                       and (s["name"].lower() in MUST_HAVE_SKILLS
                            or s["name"].lower() in NICE_TO_HAVE_SKILLS
                            or any(kw in s["name"].lower() for kw in
                                   ["ml", "ai", "python", "embedding", "nlp", "pytorch",
                                    "tensorflow", "ranking", "retrieval", "vector"]))]

    # Key behavioral signals
    response_rate = signals.get("recruiter_response_rate", 0)
    github = signals.get("github_activity_score", -1)
    last_active = signals.get("last_active_date", "Unknown")
    open_to_work = signals.get("open_to_work_flag", False)
    notice_days = signals.get("notice_period_days", 0)

    # Build reasoning
    parts = []

    # Identity
    parts.append(f"{title} at {company} with {yoe:.1f} years of experience")

    # Location
    if country.lower() == "india":
        parts.append(f"based in {location}")
    else:
        parts.append(f"located in {location}, {country}")

    # Strengths
    strengths = []
    concerns = []

    if relevant_skills:
        top_skills = relevant_skills[:5]
        strengths.append(f"relevant skills include {', '.join(top_skills)}")

    if scores.get("career_evidence", 0) >= 0.6:
        strengths.append("has production ML deployment experience")
    elif scores.get("career_evidence", 0) >= 0.3:
        strengths.append("has some product company experience")

    if github >= 30:
        strengths.append(f"active on GitHub (score: {github:.0f})")

    # Concerns
    if response_rate < 0.2:
        concerns.append(f"very low recruiter response rate ({response_rate:.0%})")
    elif response_rate < 0.4:
        concerns.append(f"below-average response rate ({response_rate:.0%})")

    if notice_days > 90:
        concerns.append(f"long notice period ({notice_days} days)")

    if not open_to_work:
        concerns.append("not currently marked as open to work")

    if scores.get("title_fit", 0) < 0.3:
        concerns.append(f"current title ({title}) is not directly AI/ML related")

    if yoe < 5:
        concerns.append(f"below the preferred 5-9 year experience band")
    elif yoe > 9:
        concerns.append(f"above the preferred experience band at {yoe:.1f} years")

    if country.lower() != "india":
        concerns.append("located outside India")

    # Compose
    reasoning = "; ".join(parts) + ". "
    if strengths:
        reasoning += "Strengths: " + "; ".join(strengths) + ". "
    if concerns and rank > 20:  # Only mention concerns for lower-ranked candidates
        reasoning += "Concerns: " + "; ".join(concerns[:2]) + "."
    elif concerns and rank > 5:
        reasoning += "Note: " + concerns[0] + "."

    return reasoning.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Main Ranking Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Rank candidates for the JD")
    parser.add_argument("--candidates", default=CANDIDATES_DEFAULT,
                        help="Path to candidates.jsonl")
    parser.add_argument("--out", default=OUTPUT_DEFAULT,
                        help="Output CSV path")
    parser.add_argument("--top-n", type=int, default=100,
                        help="Number of candidates to rank")
    args = parser.parse_args()

    t_start = time.time()
    print(f"{'='*60}")
    print(f"Redrob Ranker — Ranking Pipeline")
    print(f"{'='*60}")

    # ── Step 1: Load precomputed embeddings ──
    print("\n[1/6] Loading precomputed embeddings...")
    embeddings_path = os.path.join(PRECOMPUTED_DIR, "candidate_embeddings.npy")
    ids_path = os.path.join(PRECOMPUTED_DIR, "candidate_ids.json")

    if not os.path.exists(embeddings_path):
        print("ERROR: Pre-computed embeddings not found. Run embed.py first.")
        return

    embeddings = np.load(embeddings_path)
    with open(ids_path) as f:
        candidate_ids = json.load(f)

    id_to_idx = {cid: i for i, cid in enumerate(candidate_ids)}
    print(f"  Loaded {len(candidate_ids)} embeddings, shape {embeddings.shape}")

    # ── Step 2: Encode the JD using TF-IDF + SVD ──
    print("\n[2/6] Encoding job description (TF-IDF + SVD)...")
    import joblib

    vectorizer_path = os.path.join(PRECOMPUTED_DIR, "tfidf_vectorizer.joblib")
    svd_path = os.path.join(PRECOMPUTED_DIR, "svd_model.joblib")

    if not os.path.exists(vectorizer_path) or not os.path.exists(svd_path):
        print("  ERROR: Pre-computed vectorizer/SVD model not found. Run embed.py first.")
        return

    vectorizer = joblib.load(vectorizer_path)
    svd = joblib.load(svd_path)

    # Encode JD using the same TF-IDF space and project to SVD dimensions
    jd_tfidf = vectorizer.transform([JD_TEXT])
    jd_embedding = svd.transform(jd_tfidf)[0]

    # L2 normalize the JD embedding
    jd_embedding = jd_embedding / np.clip(np.linalg.norm(jd_embedding), 1e-9, None)

    print(f"  JD embedded -> dim {jd_embedding.shape[0]}")

    # ── Step 3: Compute semantic scores (batch) ──
    print("\n[3/6] Computing semantic scores for all candidates...")
    semantic_scores = embeddings @ jd_embedding  # dot product = cosine sim (normalized)
    print(f"  Semantic scores range: [{semantic_scores.min():.4f}, {semantic_scores.max():.4f}]")

    # ── Step 4: Pre-filter top candidates ──
    # To save time, we only do expensive structural scoring on top ~2000 candidates
    # based on semantic score
    PREFILTER_N = 3000
    top_indices = np.argsort(semantic_scores)[::-1][:PREFILTER_N]
    print(f"\n[4/6] Pre-filtered top {PREFILTER_N} candidates by semantic score")

    # ── Step 5: Full scoring on pre-filtered candidates ──
    print(f"\n[5/6] Computing structural + behavioral scores for top {PREFILTER_N}...")

    scored_candidates = []
    honeypot_count = 0

    # Load candidates from file (streaming to save memory)
    # First, build a set of candidate IDs we need
    needed_ids = set(candidate_ids[i] for i in top_indices)

    # Load only needed candidates
    candidates_map = {}
    with open(args.candidates, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cand = json.loads(line)
            if cand["candidate_id"] in needed_ids:
                candidates_map[cand["candidate_id"]] = cand
            if len(candidates_map) >= PREFILTER_N:
                break

    for i, idx in enumerate(top_indices):
        cid = candidate_ids[idx]
        if cid not in candidates_map:
            continue

        candidate = candidates_map[cid]
        sem_score = float(semantic_scores[idx])

        # Structural scores
        title_score = compute_title_score(candidate)
        exp_score = compute_experience_score(candidate)
        skill_score = compute_skill_match_score(candidate)
        career_score = compute_career_evidence_score(candidate)
        location_score = compute_location_score(candidate)
        education_score = compute_education_score(candidate)

        # Weighted structural score
        structural_score = (
            title_score * 0.25 +
            exp_score * 0.20 +
            skill_score * 0.25 +
            career_score * 0.175 +
            location_score * 0.075 +
            education_score * 0.05
        )

        # Behavioral score
        behavioral_score = compute_behavioral_score(candidate)

        # Honeypot detection
        is_honeypot = detect_honeypot(candidate)
        if is_honeypot:
            honeypot_count += 1

        # Disqualifier check
        disq_penalty = check_disqualifiers(candidate)

        # Final composite score
        raw_score = (
            sem_score * 0.40 +
            structural_score * 0.40 +
            behavioral_score * 0.20
        )

        # Apply penalties
        if is_honeypot:
            final_score = raw_score * 0.01  # Effectively eliminate
        else:
            final_score = raw_score * disq_penalty

        scores_detail = {
            "semantic": sem_score,
            "structural": structural_score,
            "behavioral": behavioral_score,
            "title_fit": title_score,
            "experience": exp_score,
            "skill_match": skill_score,
            "career_evidence": career_score,
            "location": location_score,
            "education": education_score,
            "disqualifier_penalty": disq_penalty,
            "is_honeypot": is_honeypot,
        }

        scored_candidates.append((cid, final_score, candidate, scores_detail))

        if (i + 1) % 500 == 0:
            print(f"  Scored {i + 1}/{PREFILTER_N} candidates...")

    print(f"  Detected {honeypot_count} potential honeypots in top {PREFILTER_N}")

    # ── Step 6: Sort and output ──
    print(f"\n[6/6] Generating output CSV...")

    # Sort by final score descending
    scored_candidates.sort(key=lambda x: (-x[1], x[0]))  # Ties broken by candidate_id ascending

    # Take top 100
    top100 = scored_candidates[:args.top_n]

    # Normalize scores to 0-1 range for the output
    max_score = top100[0][1] if top100 else 1.0
    min_score = top100[-1][1] if top100 else 0.0
    score_range = max_score - min_score if max_score > min_score else 1.0

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for rank, (cid, score, candidate, scores_detail) in enumerate(top100, start=1):
            # Normalize score to a nice 0-1 range
            normalized_score = 0.2 + 0.8 * (score - min_score) / score_range if score_range > 0 else 0.5
            normalized_score = round(normalized_score, 4)

            reasoning = generate_reasoning(candidate, scores_detail, rank)

            writer.writerow([cid, rank, normalized_score, reasoning])

    elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"Ranking complete!")
    print(f"{'='*60}")
    print(f"  Output: {args.out}")
    print(f"  Top 100 candidates ranked")
    print(f"  Time elapsed: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  Honeypots detected and deprioritized: {honeypot_count}")
    print()

    # Print top 10 summary
    print("Top 10 candidates:")
    print("-" * 80)
    for rank, (cid, score, candidate, scores_detail) in enumerate(top100[:10], start=1):
        profile = candidate.get("profile", {})
        title = profile.get("current_title", "?")
        yoe = profile.get("years_of_experience", 0)
        company = profile.get("current_company", "?")
        sem = scores_detail["semantic"]
        struct = scores_detail["structural"]
        behav = scores_detail["behavioral"]
        print(f"  #{rank:2d} {cid} | {title:30s} | {yoe:4.1f}yr | {company:20s} | "
              f"sem={sem:.3f} str={struct:.3f} beh={behav:.3f} | final={score:.4f}")

    print()
    print(f"Remember to validate: python India_runs_data_and_ai_challenge/validate_submission.py {args.out}")


if __name__ == "__main__":
    main()
