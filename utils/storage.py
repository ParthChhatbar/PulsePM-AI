from __future__ import annotations

from datetime import datetime
from pathlib import Path

from utils.schemas import MonthlySynthesis, WeeklyReport


def _legacy_safe_report(report: WeeklyReport, fallback_week: int) -> WeeklyReport:
    if not getattr(report, "week_number", 0):
        report.week_number = fallback_week
    return report


def ensure_output_dirs(base: str | Path = "output") -> Path:
    root = Path(base)
    for child in ["weekly", "monthly", "ppt"]:
        (root / child).mkdir(parents=True, exist_ok=True)
    return root


def weekly_markdown(report: WeeklyReport) -> str:
    features = report.features
    scoring = report.scoring
    reasoning = report.reasoning
    project = report.project
    risks = "\n".join(f"- {risk}" for risk in reasoning.top_risks) or "- None identified"
    recs = "\n".join(f"- {rec}" for rec in reasoning.recommendations)
    missing = "\n".join(f"- {item}" for item in reasoning.missing_information) or "- None"
    positives = "\n".join(f"- {item}" for item in features.positive_signals) or "- None captured"
    findings = "\n".join(f"- {item}" for item in reasoning.key_findings) or "- No findings available"
    roots = "\n".join(f"- {item}" for item in reasoning.root_cause_analysis) or "- No root cause evidence available"
    impacts = "\n".join(f"- {item}" for item in features.business_impacts) or f"- {reasoning.business_impact}"
    upcoming = "\n".join(
        f"- {item['phase']}: {item['task']} ({item['status']}, due {item.get('end_date') or 'not dated'})"
        for item in features.upcoming_milestones
    ) or "- No upcoming milestones identified"
    trend = "\n".join(f"- {item}" for item in (report.trend.insights if report.trend else [])) or "- Insufficient trend history"
    return f"""# Weekly Executive Project Health Report: {project.project_name}

Generated: {report.generated_at:%Y-%m-%d %H:%M}
Week Number: {report.week_number}

## Overview
Project Manager: {project.project_manager or "Unknown"}
Project Stage: {features.project_stage or "Not specified"}
Source: {report.source_file}

## RAG
{scoring.rag} ({scoring.score}/100, confidence {scoring.confidence}%)

Data Completeness: {features.data_completeness_score}% ({features.confidence_level})

## Executive Summary
{reasoning.executive_summary}

## Key Findings
{findings}

## Root Cause Analysis
{roots}

## Business Impact
{impacts}

## Top Risks
{risks}

## Positive Signals
{positives}

## Recommendations
{recs}

## Upcoming Milestones
{upcoming}

## Trend Analysis
{trend}

## Missing Data
{missing}

## Supporting Metrics
- Reported completion: {features.completion_percent}% ({features.completion_source})
- Summary task counts: {features.summary_task_counts}
- Late tasks: {features.late_tasks}
- Delayed milestones: {features.delayed_milestones}
- Open risks: {features.open_risks}
- Critical tasks: {features.critical_tasks}
- Dependencies: {features.dependency_count}
"""


def save_weekly_report(report: WeeklyReport, output_root: str | Path = "output") -> WeeklyReport:
    root = ensure_output_dirs(output_root)
    safe_project = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in report.project.project_name)[:80]
    stamp = report.generated_at.strftime("%Y%m%d_%H%M%S")
    json_path = root / "weekly" / f"{stamp}_{safe_project}.json"
    md_path = root / "weekly" / f"{stamp}_{safe_project}.md"
    report.markdown_path = str(md_path)
    report.json_path = str(json_path)
    json_path.write_text(
        report.model_dump_json(indent=2, exclude={"project": {"tasks": {"__all__": {"raw"}}}}),
        encoding="utf-8",
    )
    md_path.write_text(weekly_markdown(report), encoding="utf-8")
    return report


def load_weekly_reports(output_root: str | Path = "output") -> list[WeeklyReport]:
    weekly_dir = Path(output_root) / "weekly"
    reports: list[WeeklyReport] = []
    for index, path in enumerate(sorted(weekly_dir.glob("*.json")), start=1):
        try:
            reports.append(_legacy_safe_report(WeeklyReport.model_validate_json(path.read_text(encoding="utf-8")), index))
        except Exception:
            continue
    return reports


def save_monthly_synthesis(synthesis: MonthlySynthesis, output_root: str | Path = "output") -> MonthlySynthesis:
    root = ensure_output_dirs(output_root)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = root / "monthly" / f"{stamp}_monthly_synthesis.json"
    synthesis.json_path = str(path)
    path.write_text(synthesis.model_dump_json(indent=2), encoding="utf-8")
    return synthesis
