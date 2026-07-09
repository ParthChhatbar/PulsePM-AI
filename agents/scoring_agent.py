from __future__ import annotations

from utils.constants import RAG_AMBER_THRESHOLD, RAG_GREEN_THRESHOLD, SCORE_WEIGHTS
from utils.schemas import HealthScore, ProjectFeatures


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


class ScoringAgent:
    """Deterministic RAG scoring. No LLM is used here."""

    def run(self, features: ProjectFeatures) -> HealthScore:
        if features.total_tasks == 0:
            return HealthScore(
                score=0.0,
                confidence=25.0,
                rag="Red",
                category_scores={
                    "schedule": 0.0,
                    "milestones": 0.0,
                    "completion": 0.0,
                    "risks": 0.0,
                    "stakeholder_sentiment": 0.0,
                    "critical_tasks": 0.0,
                },
                rationale=["No task rows were available for deterministic scoring."],
            )
        total = max(features.total_tasks, 1)
        schedule = _clamp(100 - ((features.late_tasks / total) * 100))
        milestones = _clamp(100 - ((features.delayed_milestones / total) * 120))
        completion = _clamp(features.completion_percent)
        risks = _clamp(100 - ((features.open_risks / total) * 100))
        critical = _clamp(100 - ((features.critical_tasks + features.blocked_tasks) / total * 100))

        positive = features.comment_sentiment_distribution.get("Positive", 0)
        negative = sum(features.comment_sentiment_distribution.get(k, 0) for k in ["Risk", "Issue", "Negative", "Blocker"])
        sentiment_total = max(positive + negative, 1)
        stakeholder = _clamp(70 + ((positive - negative) / sentiment_total) * 30)

        category_scores = {
            "schedule": schedule,
            "milestones": milestones,
            "completion": completion,
            "risks": risks,
            "stakeholder_sentiment": stakeholder,
            "critical_tasks": critical,
        }
        score = round(
            sum(category_scores[key] * weight for key, weight in SCORE_WEIGHTS.items()) / sum(SCORE_WEIGHTS.values()),
            2,
        )
        rag = "Green" if score >= RAG_GREEN_THRESHOLD else "Amber" if score >= RAG_AMBER_THRESHOLD else "Red"
        confidence = _clamp((features.data_completeness_score * 0.75) + 20 - (len(features.missing_data) * 2))
        rationale = [
            f"{features.late_tasks} late tasks out of {features.total_tasks} task rows.",
            f"{features.open_risks} open schedule-risk indicators and {features.blocked_tasks} blocked/on-hold tasks.",
            f"Reported completion is {features.completion_percent}% from {features.completion_source}.",
            features.confidence_explanation,
        ]
        return HealthScore(score=score, confidence=confidence, rag=rag, category_scores=category_scores, rationale=rationale)
