from pathlib import Path

APP_NAME = "PulsePM AI"
DEFAULT_INPUT_FOLDER = Path("data")
DEFAULT_OUTPUT_FOLDER = Path("output")
RAG_GREEN_THRESHOLD = 90
RAG_AMBER_THRESHOLD = 75

SCORE_WEIGHTS = {
    "schedule": 30,
    "milestones": 20,
    "completion": 15,
    "risks": 15,
    "stakeholder_sentiment": 10,
    "critical_tasks": 10,
}

COMMENT_LABELS = ["Risk", "Issue", "Dependency", "Positive", "Negative", "Neutral", "Blocker"]
