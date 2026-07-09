from __future__ import annotations

import json
import os
import warnings
from collections import Counter
from datetime import datetime
from pathlib import Path

warnings.simplefilter("ignore", FutureWarning)

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from utils.schemas import MonthlySynthesis, WeeklyReport
from utils.trends import trends_by_project


class MonthlySynthesisAgent:
    def __init__(self, prompt_path: str | Path = "prompts/monthly_prompt.txt") -> None:
        self.prompt_path = Path(prompt_path)

    def _fallback(self, reports: list[WeeklyReport]) -> MonthlySynthesis:
        valid = [report for report in reports if report.project.project_name != "Unknown Project"]
        trends = trends_by_project(valid)
        latest_by_project: dict[str, WeeklyReport] = {}
        for report in sorted(valid, key=lambda r: r.generated_at):
            latest_by_project[report.project.project_name] = report
        latest = list(latest_by_project.values())
        red = [r.project.project_name for r in latest if r.scoring.rag == "Red"]
        amber = [r.project.project_name for r in latest if r.scoring.rag == "Amber"]
        green = [r.project.project_name for r in latest if r.scoring.rag == "Green"]

        theme_counter: Counter[str] = Counter()
        dependency_counter: Counter[str] = Counter()
        emerging: list[str] = []
        for report in latest:
            for item in report.features.interpreted_comments:
                theme = item.get("theme") or "General"
                theme_counter[theme] += 1
                if theme in {"Customer Dependency", "Integration Dependency", "Governance Cadence"}:
                    dependency_counter[item.get("insight") or theme] += 1
            emerging.extend(report.reasoning.top_risks[:3])

        improving = [name for name, trend in trends.items() if trend.status == "Improving"]
        deteriorating = [name for name, trend in trends.items() if trend.status == "Deteriorating"]
        positive = []
        for report in latest:
            positive.extend(report.features.positive_signals)

        snapshots = [
            {
                "project_name": report.project.project_name,
                "week_number": report.week_number,
                "date": report.generated_at.date().isoformat(),
                "rag": report.scoring.rag,
                "health_score": report.scoring.score,
                "completion": report.features.completion_percent,
                "confidence": report.scoring.confidence,
            }
            for report in latest
        ]
        overview = [
            f"Portfolio contains {len(latest)} active project(s): {len(green)} Green, {len(amber)} Amber, {len(red)} Red.",
            "Leadership attention should focus on projects with Amber/Red health, deteriorating trend, or recurring customer/integration dependencies.",
        ]
        portfolio_trends = []
        for trend in trends.values():
            portfolio_trends.extend([f"{trend.project_name}: {insight}" for insight in trend.insights[:2]])
        return MonthlySynthesis(
            generated_at=datetime.now(),
            reports_analyzed=len(valid),
            portfolio_overview=overview,
            portfolio_trends=portfolio_trends or ["Insufficient weekly history for multi-week portfolio trends."],
            projects_improving=improving,
            projects_deteriorating=deteriorating,
            projects_declining=deteriorating,
            risk_themes=[f"{theme}: {count} signal(s)" for theme, count in theme_counter.most_common(6)],
            common_dependencies=[item for item, _ in dependency_counter.most_common(5)],
            emerging_risks=emerging[:8],
            positive_trends=positive[:5],
            sentiment_trends=[
                "Comment themes indicate delivery exposure is concentrated in customer inputs, integration mapping and governance cadence."
                if dependency_counter
                else "Commentary depth is limited; sentiment trend confidence is constrained."
            ],
            executive_recommendations=[
                "Create a portfolio dependency war room for customer inputs, integration mapping and governance calendar closure.",
                "Require each Amber/Red project to publish a dated recovery plan with executive owner, decision date and success measure.",
                "Track confidence alongside RAG so incomplete baseline and variance data does not create false precision.",
            ],
            strategic_recommendations=[
                "Standardize weekly PMO evidence capture across Summary, Comments, milestones, baseline dates and variance.",
                "Use recurring dependency themes to drive leadership decisions rather than reviewing each project in isolation.",
            ],
            leadership_attention=red + amber + deteriorating,
            project_snapshots=snapshots,
            confidence=round(sum(r.scoring.confidence for r in latest) / len(latest), 2) if latest else 0,
        )

    def run(self, reports: list[WeeklyReport]) -> MonthlySynthesis:
        valid = [report for report in reports if report.project.project_name != "Unknown Project"]
        if not valid:
            return self._fallback(valid)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or genai is None:
            return self._fallback(valid)
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-flash-lite-latest")
        prompt = self.prompt_path.read_text(encoding="utf-8")
        payload = [r.model_dump(mode="json", exclude={"project": {"tasks": {"__all__": {"raw"}}}}) for r in valid]
        try:
            response = model.generate_content(f"{prompt}\n\nWEEKLY_REPORTS:\n{json.dumps(payload, ensure_ascii=False)}")
            text = response.text.strip().strip("`").replace("json\n", "")
            data = json.loads(text)
            return MonthlySynthesis(generated_at=datetime.now(), reports_analyzed=len(valid), **data)
        except Exception:
            return self._fallback(valid)
