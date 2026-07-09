from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

warnings.simplefilter("ignore", FutureWarning)

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from utils.schemas import ExecutiveReasoning, HealthScore, ParsedProject, ProjectFeatures


class ReasoningAgent:
    """Uses Gemini only for executive reasoning over deterministic inputs."""

    def __init__(self, prompt_path: str | Path = "prompts/weekly_prompt.txt") -> None:
        self.prompt_path = Path(prompt_path)

    def _summary(self, parsed: ParsedProject, features: ProjectFeatures, score: HealthScore) -> str:
        concern = features.root_causes[0] if features.root_causes else "The main concern is limited qualitative evidence."
        action = features.evidence_based_recommendations[0]["recommendation"] if features.evidence_based_recommendations else "Confirm ownership for the highest-risk workstream."
        return (
            f"{parsed.project_name} is {score.rag} with a deterministic health score of {score.score}, while reported completion stands at {features.completion_percent}%. "
            f"The project remains in {features.project_stage or 'the current delivery stage'} with {features.open_risks} schedule-risk indicators and {features.blocked_tasks} blocked or on-hold tasks. "
            f"{concern} "
            f"The business risk is that unresolved dependencies may compress validation, cutover, or hypercare readiness. "
            f"Leadership should {action[0].lower() + action[1:]}"
        )

    def _fallback(self, parsed: ParsedProject, features: ProjectFeatures, score: HealthScore) -> ExecutiveReasoning:
        recommendations = [
            f"{item['recommendation']} Evidence: {item['evidence']}"
            for item in features.evidence_based_recommendations[:5]
        ]
        risks = [
            f"{item['risk']} Impact: {item['business_impact']}"
            for item in features.risk_register[:5]
        ] or features.risk_comments[:5] or score.rationale
        impact = " ".join(features.business_impacts[:3]) or "Leadership should review delivery exposure before confirming commitments."
        return ExecutiveReasoning(
            executive_summary=self._summary(parsed, features, score),
            key_findings=features.key_findings[:8],
            root_cause_analysis=features.root_causes,
            why=features.root_causes,
            evidence=[item.get("insight", "") for item in features.interpreted_comments[:6] if item.get("insight")],
            business_impact=impact,
            top_risks=risks[:5],
            recommendations=recommendations[:5],
            missing_information=features.missing_data + [issue.message for issue in parsed.issues],
            data_quality_note=features.confidence_explanation,
            confidence=score.confidence,
        )

    def run(self, parsed: ParsedProject, features: ProjectFeatures, score: HealthScore) -> ExecutiveReasoning:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or genai is None:
            return self._fallback(parsed, features, score)

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-flash-lite-latest")
        prompt = self.prompt_path.read_text(encoding="utf-8")
        payload = {
            "project": parsed.model_dump(mode="json", exclude={"tasks": {"__all__": {"raw"}}}),
            "features": features.model_dump(mode="json"),
            "scoring": score.model_dump(mode="json"),
        }
        try:
            response = model.generate_content(f"{prompt}\n\nDATA:\n{json.dumps(payload, ensure_ascii=False)}")
            text = response.text.strip().strip("`").replace("json\n", "")
            return ExecutiveReasoning.model_validate_json(text)
        except Exception:
            return self._fallback(parsed, features, score)
