from __future__ import annotations

from collections import Counter

from utils.schemas import ProjectTrend, TrendPoint, WeeklyReport


def _sentiment_score(report: WeeklyReport) -> float:
    dist = report.features.comment_sentiment_distribution
    positive = dist.get("Positive", 0)
    negative = sum(dist.get(key, 0) for key in ["Risk", "Issue", "Negative", "Blocker", "Dependency"])
    total = max(positive + negative, 1)
    return round((positive - negative) / total * 100, 2)


def make_trend_point(report: WeeklyReport, week_number: int | None = None) -> TrendPoint:
    return TrendPoint(
        report_id=report.report_id,
        generated_at=report.generated_at,
        week_number=week_number if week_number is not None else report.week_number,
        project_name=report.project.project_name,
        rag=report.scoring.rag,
        health_score=report.scoring.score,
        completion_percent=report.features.completion_percent,
        late_tasks=report.features.late_tasks,
        open_risks=report.features.open_risks,
        sentiment_score=_sentiment_score(report),
        critical_tasks=report.features.critical_tasks,
        dependencies=report.features.dependency_count,
        delayed_milestones=report.features.delayed_milestones,
    )


def build_project_trend(project_name: str, reports: list[WeeklyReport]) -> ProjectTrend:
    ordered = sorted(reports, key=lambda r: r.generated_at)
    points = [make_trend_point(report, idx + 1) for idx, report in enumerate(ordered)]
    if len(points) < 2:
        return ProjectTrend(
            project_name=project_name,
            status="Insufficient History",
            points=points,
            insights=["Trend analysis requires at least two weekly reports for this project."],
            recurring_risks=[],
        )

    first, last = points[0], points[-1]
    score_delta = round(last.health_score - first.health_score, 2)
    risk_delta = last.open_risks - first.open_risks
    late_delta = last.late_tasks - first.late_tasks
    completion_delta = round(last.completion_percent - first.completion_percent, 2)
    if score_delta >= 3 and risk_delta <= 0:
        status = "Improving"
    elif score_delta <= -3 or risk_delta > 3 or late_delta > 3:
        status = "Deteriorating"
    elif abs(score_delta) < 1 and abs(completion_delta) < 1:
        status = "Stagnant"
    else:
        status = "Stable"

    insights = [
        f"Health score moved {score_delta:+.2f} points from Week {first.week_number} to Week {last.week_number}.",
        f"Completion moved {completion_delta:+.2f} points over the period.",
        f"Late tasks changed by {late_delta:+d}; open risks changed by {risk_delta:+d}.",
    ]
    if len(points) >= 4 and len({p.rag for p in points[-4:]}) == 1:
        insights.append(f"Health has remained {points[-1].rag} for four consecutive weeks.")
    if status == "Stagnant":
        insights.append("Schedule recovery has stalled; leadership should force a decision on unresolved dependencies.")
    if risk_delta < 0:
        insights.append(f"Risk count decreased by {abs(risk_delta)} item(s), indicating recovery momentum.")
    elif risk_delta > 0:
        insights.append(f"Risk count increased by {risk_delta} item(s), indicating risk acceleration.")

    risk_text: list[str] = []
    for report in ordered:
        risk_text.extend(report.reasoning.top_risks)
    normalized = [risk.split(".")[0][:120] for risk in risk_text if risk]
    recurring = [risk for risk, count in Counter(normalized).items() if count > 1][:5]
    return ProjectTrend(
        project_name=project_name,
        status=status,
        points=points,
        insights=insights,
        recurring_risks=recurring,
        risk_acceleration="Risk acceleration detected" if risk_delta > 0 else "No acceleration detected",
        recovery_signal="Recovery signal detected" if score_delta > 0 and risk_delta <= 0 else "No recovery signal detected",
    )


def trends_by_project(reports: list[WeeklyReport]) -> dict[str, ProjectTrend]:
    grouped: dict[str, list[WeeklyReport]] = {}
    for report in reports:
        if report.project.project_name == "Unknown Project":
            continue
        grouped.setdefault(report.project.project_name, []).append(report)
    return {project: build_project_trend(project, items) for project, items in grouped.items()}
