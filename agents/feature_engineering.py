from __future__ import annotations

import json
import os
import warnings
from collections import Counter
from datetime import datetime
from typing import Any

warnings.simplefilter("ignore", FutureWarning)

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from utils.constants import COMMENT_LABELS
from utils.evidence import build_evidence
from utils.schemas import ParsedProject, ProjectComment, ProjectFeatures, ProjectTask


def _clean_health(value: str) -> str:
    text = (value or "").strip().lower()
    if text in {"green", "g"}:
        return "Green"
    if text in {"yellow", "amber", "a"}:
        return "Amber"
    if text in {"red", "r"}:
        return "Red"
    return "Unknown"


def _status_bucket(value: str) -> str:
    text = (value or "").strip()
    return text or "Unknown"


def _safe_percent(value: float | None) -> float | None:
    if value is None:
        return None
    if value <= 1:
        return round(value * 100, 2)
    return round(value, 2)


class FeatureEngineeringAgent:
    """Computes PMO features and interprets comments as business evidence."""

    def classify_comments(self, parsed: ParsedProject) -> None:
        comments = [comment.text for comment in parsed.comments if comment.text.strip()]
        if not comments:
            return
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or genai is None:
            for comment in parsed.comments:
                self._classify_comment_heuristically(comment)
            return

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-flash-lite-latest")
        prompt = (
            "Classify each project comment as exactly one of: "
            f"{', '.join(COMMENT_LABELS)}. Return only JSON list of labels in order.\n"
            f"Comments:\n{json.dumps(comments, ensure_ascii=False)}"
        )
        try:
            response = model.generate_content(prompt)
            labels = json.loads(response.text.strip().strip("`").replace("json\n", ""))
        except Exception:
            labels = []

        for comment, label in zip(parsed.comments, labels or []):
            comment.classification = label if label in COMMENT_LABELS else "Neutral"
            self._interpret_comment(comment)
        for comment in parsed.comments:
            if not comment.interpreted_insight:
                self._classify_comment_heuristically(comment)

    def _classify_comment_heuristically(self, comment: ProjectComment) -> None:
        text = comment.text.lower()
        if any(term in text for term in ["impacted", "pending", "remain", "need", "changed", "repeating"]):
            comment.classification = "Issue"
        if any(term in text for term in ["provide", "customer", "otk", "titan", "sample", "mapping"]):
            comment.classification = "Dependency"
        if any(term in text for term in ["covered all sessions", "coverd all sessions", "scheduled agenda"]):
            comment.classification = "Positive"
        self._interpret_comment(comment)

    def _interpret_comment(self, comment: ProjectComment) -> None:
        text = comment.text.lower()
        if "parallel" in text and "workshop" in text:
            comment.evidence_theme = "Schedule Constraint"
            comment.interpreted_insight = (
                "Workshop timing pressure appears driven by concurrent Phase 1 activities rather than a single task execution issue."
            )
        elif "sample" in text or "master data" in text or "provide" in text:
            comment.evidence_theme = "Customer Dependency"
            comment.interpreted_insight = (
                "Delivery progress depends on timely customer inputs, especially sample or master data needed for design validation."
            )
        elif "jde" in text or "mapping" in text or "integration" in text:
            comment.evidence_theme = "Integration Dependency"
            comment.interpreted_insight = (
                "Integration readiness remains exposed to unresolved JDE and field mapping decisions."
            )
        elif "calendar" in text or "meeting" in text:
            comment.evidence_theme = "Governance Cadence"
            comment.interpreted_insight = (
                "Required governance sessions are not fully locked, which may slow workshop outcomes and sign-offs."
            )
        elif "repeating" in text or "changed" in text:
            comment.evidence_theme = "Design Quality"
            comment.interpreted_insight = (
                "Configuration/design cleanup is still needed, indicating residual quality control work before downstream validation."
            )
        elif "covered all sessions" in text or "coverd all sessions" in text:
            comment.evidence_theme = "Positive Progress"
            comment.interpreted_insight = "Planned sessions were completed, showing delivery cadence is working where agenda ownership is clear."
        else:
            comment.evidence_theme = "General"
            comment.interpreted_insight = comment.text

    def _as_of_date(self, parsed: ParsedProject) -> datetime:
        value = parsed.summary.get("Today's Date")
        if isinstance(value, datetime):
            return value
        return datetime.now()

    def _summary_status_distribution(self, parsed: ParsedProject, tasks: list[ProjectTask]) -> dict[str, int]:
        if parsed.summary_task_counts:
            counts = dict(parsed.summary_task_counts)
            other = len(tasks) - sum(counts.values())
            if other > 0:
                counts["Other / Not Applicable"] = other
            return counts
        return dict(Counter(_status_bucket(t.status) for t in tasks))

    def _completion(self, parsed: ParsedProject, tasks: list[ProjectTask]) -> tuple[float, str]:
        summary_value = _safe_percent(parsed.summary_completion_percent)
        if summary_value is not None:
            return summary_value, "summary"
        percents = [t.percent_complete for t in tasks if t.percent_complete is not None]
        if not percents:
            return 0.0, "missing"
        return round(sum(percents) / len(percents), 2), "task_average"

    def _data_completeness(self, parsed: ParsedProject, tasks: list[ProjectTask]) -> tuple[dict[str, float], float, str, str, list[str]]:
        total = max(len(tasks), 1)
        summary_score = 100.0 if parsed.summary else 0.0
        dates = sum(1 for t in tasks if t.start_date and t.end_date) / total * 100
        milestones = 100.0 if any(t.phase_milestone for t in tasks) else 0.0
        comments = 100.0 if parsed.comments else 0.0
        schedule = sum(1 for t in tasks if _clean_health(t.schedule_health) != "Unknown") / total * 100
        variance = sum(1 for t in tasks if t.variance_days is not None) / total * 100
        baseline = sum(1 for t in tasks if t.baseline_start and t.baseline_finish) / total * 100
        completeness = {
            "summary": round(summary_score, 2),
            "dates": round(dates, 2),
            "milestones": round(milestones, 2),
            "comments": round(comments, 2),
            "schedule": round(schedule, 2),
            "variance": round(variance, 2),
            "baseline": round(baseline, 2),
        }
        weighted = round(
            summary_score * 0.18
            + dates * 0.12
            + milestones * 0.12
            + comments * 0.12
            + schedule * 0.12
            + variance * 0.17
            + baseline * 0.17,
            2,
        )
        if weighted >= 90:
            level = "High"
        elif weighted >= 60:
            level = "Medium"
        else:
            level = "Low"
        missing = []
        if variance < 75:
            missing.append("Baseline schedule variance is incomplete.")
        if baseline < 75:
            missing.append("Baseline start or finish dates are incomplete.")
        if comments == 0:
            missing.append("No commentary was available for qualitative assessment.")
        explanation = f"Data completeness is {level.lower()} ({weighted}%). "
        if variance < 75 or baseline < 75:
            explanation += (
                "Baseline schedule information was incomplete, so health was assessed using Summary values, task completion, "
                "milestones, schedule health, dependencies and project commentary. "
            )
        else:
            explanation += "Project health was assessed using Summary, task health, milestone, dependency, variance and commentary evidence. "
        return completeness, weighted, level, explanation, missing

    def _confidence_level(self, confidence: float) -> str:
        if confidence >= 85:
            return "High"
        if confidence >= 60:
            return "Medium"
        return "Low"

    def _milestone_rows(self, tasks: list[ProjectTask], as_of: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
        milestones: list[dict[str, Any]] = []
        delayed = 0
        for task in tasks:
            if not task.phase_milestone:
                continue
            complete = (task.percent_complete or 0) >= 100 or task.status.lower() == "completed"
            is_delayed = bool(task.end_date and task.end_date.date() < as_of.date() and not complete)
            delayed += 1 if is_delayed else 0
            milestones.append(
                {
                    "phase": task.phase_milestone,
                    "task": task.task_name,
                    "status": task.status,
                    "schedule_health": _clean_health(task.schedule_health),
                    "rag": task.rag or _clean_health(task.schedule_health),
                    "end_date": task.end_date.isoformat() if task.end_date else None,
                    "percent_complete": task.percent_complete,
                    "delayed": is_delayed,
                }
            )
        upcoming = [
            item
            for item in milestones
            if item["end_date"] and item["status"].lower() != "completed"
        ][:6]
        return milestones, upcoming, delayed

    def _risk_register(self, tasks: list[ProjectTask], comments: list[ProjectComment]) -> list[dict[str, Any]]:
        risks: list[dict[str, Any]] = []
        for task in tasks:
            health = _clean_health(task.schedule_health)
            if health == "Red" or task.on_hold or task.at_risk:
                risks.append(
                    {
                        "risk": task.task_name,
                        "source": "Project Plan",
                        "business_impact": self._impact_for_task(task.task_name),
                        "likelihood": "High" if health == "Red" or task.on_hold else "Medium",
                        "mitigation": self._mitigation_for_task(task.task_name),
                        "owner": task.assigned_to or task.project_manager or "Project leadership",
                    }
                )
        for comment in comments:
            if comment.evidence_theme in {"Customer Dependency", "Integration Dependency", "Schedule Constraint", "Governance Cadence"}:
                risks.append(
                    {
                        "risk": comment.interpreted_insight,
                        "source": f"Comment {comment.row_reference}".strip(),
                        "business_impact": self._impact_for_theme(comment.evidence_theme),
                        "likelihood": "Medium",
                        "mitigation": self._mitigation_for_theme(comment.evidence_theme),
                        "owner": comment.author or "PMO",
                    }
                )
        return risks[:12]

    def _impact_for_task(self, task_name: str) -> str:
        text = task_name.lower()
        if "integration" in text or "jde" in text:
            return "Integration delays may compress SIT/UAT validation windows and create cutover risk."
        if "data" in text or "supplier" in text:
            return "Customer data delays may postpone configuration validation and production readiness."
        if "hyper" in text:
            return "Hypercare readiness gaps may reduce post go-live support confidence."
        return "Delay may create downstream pressure on dependent phases and leadership commitments."

    def _mitigation_for_task(self, task_name: str) -> str:
        text = task_name.lower()
        if "integration" in text or "jde" in text:
            return "Run an integration closure forum with accountable technical owners and daily issue burn-down."
        if "data" in text or "supplier" in text:
            return "Secure a dated customer data commitment and define fallback validation samples."
        if "hold" in text or "d & b" in text:
            return "Assign an executive owner to unblock credentials, access or third-party prerequisites."
        return "Confirm owner, decision date and next action in the weekly governance forum."

    def _impact_for_theme(self, theme: str) -> str:
        return {
            "Customer Dependency": "Customer input delays can defer design sign-off and configuration validation.",
            "Integration Dependency": "Unresolved mapping can slow integration readiness and compress testing.",
            "Schedule Constraint": "Concurrent workstreams may absorb contingency and reduce recovery options.",
            "Governance Cadence": "Unscheduled governance can delay decisions and action closure.",
        }.get(theme, "The issue may reduce confidence in delivery commitments.")

    def _mitigation_for_theme(self, theme: str) -> str:
        return {
            "Customer Dependency": "Create a customer-owned input tracker with named owners and due dates.",
            "Integration Dependency": "Run a mapping closure workshop and freeze open design decisions.",
            "Schedule Constraint": "Re-sequence overlapping workstreams and protect critical workshops.",
            "Governance Cadence": "Lock recurring decision meetings and publish action owners within 24 hours.",
        }.get(theme, "Track through PMO action log.")

    def _insights(
        self,
        parsed: ParsedProject,
        tasks: list[ProjectTask],
        comments: list[ProjectComment],
        completion: float,
        late_tasks: int,
        open_risks: int,
        delayed_milestones: int,
        blocked_tasks: int,
        dependency_count: int,
    ) -> tuple[list[str], list[str], list[str], list[dict[str, str]], list[str], list[str]]:
        themes = Counter(c.evidence_theme for c in comments)
        findings = [
            f"{parsed.project_stage or 'The current delivery stage'} is progressing with {completion}% completion, but risk remains concentrated in unfinished critical work.",
            f"{open_risks} schedule risk indicators are present, with the strongest exposure in red-health tasks and blocked/on-hold items.",
            f"{dependency_count} task dependencies indicate delivery is sequencing-sensitive; late upstream decisions can affect downstream readiness.",
        ]
        if themes.get("Schedule Constraint"):
            findings.append("Implementation workstreams are becoming schedule constrained because workshop timing is being affected by parallel project activity.")
        if themes.get("Customer Dependency"):
            findings.append("Customer-provided data and samples are a material delivery dependency for configuration and design validation.")
        if themes.get("Integration Dependency"):
            findings.append("Integration mapping remains an active delivery risk, especially around JDE and PO/GR flow decisions.")
        if delayed_milestones:
            findings.append(f"{delayed_milestones} milestone(s) are delayed or incomplete against the workbook's reporting date.")
        if blocked_tasks:
            findings.append(f"{blocked_tasks} blocked or on-hold tasks require leadership attention to protect the critical path.")

        root_causes = []
        if themes.get("Schedule Constraint"):
            root_causes.append("Workshop delays are linked to parallel Phase 1 activities, suggesting capacity contention rather than only execution quality.")
        if themes.get("Customer Dependency"):
            root_causes.append("Customer input readiness is a root cause for remaining design and configuration risk.")
        if themes.get("Integration Dependency"):
            root_causes.append("JDE and field mapping decisions remain incomplete, creating integration closure risk.")
        if themes.get("Governance Cadence"):
            root_causes.append("Some required meetings are not fully calendarized, weakening governance cadence and decision velocity.")
        if not root_causes:
            root_causes.append("Root cause evidence is limited; confidence relies more heavily on plan status and schedule health than commentary.")

        impacts = [
            "If the current risks continue, downstream validation and UAT windows may be compressed.",
            "Customer data delays may postpone configuration validation and increase rework risk.",
            "Late mapping or approval decisions could affect go-live readiness and cutover confidence.",
        ]
        recommendations = [
            {
                "recommendation": "Establish a customer input closure tracker for sample data, master data and workflow details.",
                "evidence": "Comments reference OTK/customer sample data and workflow/CULT table inputs.",
            },
            {
                "recommendation": "Run a focused JDE and PO/GR mapping closure session with technical owners.",
                "evidence": "Comments state JDE mapping and PO outbound / GR inbound field mapping remain incomplete.",
            },
            {
                "recommendation": "Protect impacted workshops by re-sequencing parallel workstreams and confirming attendance.",
                "evidence": "Commentary links onsite workshop impact to parallel Phase 1 activities.",
            },
            {
                "recommendation": "Lock calendar meetings for open governance items and publish decision owners.",
                "evidence": "Comments request meetings to be placed on calendar for workshop outcomes.",
            },
            {
                "recommendation": "Prioritize red-health tasks in Build, Production/Cutover, Hypercare and P2P design areas.",
                "evidence": "Project plan contains red schedule-health tasks in these workstreams.",
            },
        ]
        positives = [c.interpreted_insight for c in comments if c.classification == "Positive"][:5]
        risk_comments = [c.interpreted_insight for c in comments if c.evidence_theme != "Positive Progress"][:8]
        return findings[:8], root_causes, impacts, recommendations, positives, risk_comments

    def run(self, parsed: ParsedProject) -> ProjectFeatures:
        tasks = parsed.tasks
        total = len(tasks)
        as_of = self._as_of_date(parsed)
        missing_data: list[str] = []
        evidence = build_evidence(parsed, as_of)
        parsed.comments = evidence["comments"]

        completion, completion_source = self._completion(parsed, tasks)
        if completion_source == "missing":
            missing_data.append("Task completion percentage is missing.")

        late_tasks = sum(
            1
            for t in tasks
            if t.end_date and t.end_date.date() < as_of.date() and (t.percent_complete or 0) < 100 and t.status.lower() != "not applicable"
        )
        milestones = evidence["milestones"]
        upcoming_milestones = evidence["upcoming_milestones"]
        delayed_milestones = evidence["delayed_milestones"]
        critical_tasks = sum(1 for t in tasks if t.critical or "critical" in t.task_name.lower())
        blocked_tasks = parsed.summary_task_counts.get("On Hold") or sum(
            1 for t in tasks if t.blocked or t.on_hold or "block" in t.status.lower() or "hold" in t.status.lower()
        )
        open_risks = sum(1 for t in tasks if t.at_risk or _clean_health(t.schedule_health) == "Red")
        variance_values = [float(t.variance_days) for t in tasks if t.variance_days is not None]
        dependencies = sum(1 for t in tasks if t.dependencies)

        health_distribution = Counter(_clean_health(t.schedule_health) for t in tasks)
        status_distribution = self._summary_status_distribution(parsed, tasks)
        comment_distribution = Counter(c.classification for c in parsed.comments)
        completeness, completeness_score, confidence_level, confidence_explanation, completeness_missing = self._data_completeness(parsed, tasks)
        algorithmic_confidence = float(evidence["confidence"])
        completeness_score = min(completeness_score, algorithmic_confidence)
        confidence_level = self._confidence_level(completeness_score)
        if evidence["confidence_notes"]:
            confidence_explanation += " " + " ".join(evidence["confidence_notes"])
        missing_data.extend(completeness_missing)
        if total == 0:
            missing_data.append("No task rows were parsed from the workbook.")
        if not parsed.project_start_date or not parsed.project_end_date:
            missing_data.append("Project start or end date is missing from Summary.")

        findings, roots, impacts, recs, positives, risk_comments = self._insights(
            parsed, tasks, parsed.comments, completion, late_tasks, open_risks, delayed_milestones, blocked_tasks, dependencies
        )
        root_cause_sentences = [
            f"{item['cause']}: {'; '.join(item['supporting_evidence'])} Confidence {item['confidence']}%."
            for item in evidence["root_causes"]
        ]
        risk_comments = [
            f"{risk['title']}: {'; '.join(risk['evidence'][:2])}"
            for risk in evidence["risks"][:8]
        ] or risk_comments
        positives = evidence["positive_signals"] or positives
        impacts = evidence["business_impacts"] or impacts
        recs = evidence["recommendations"] or recs
        roots = root_cause_sentences or roots
        findings = self._ensure_findings(findings, parsed, completion, evidence)

        return ProjectFeatures(
            completion_percent=completion,
            completion_source=completion_source,
            late_tasks=late_tasks,
            delayed_milestones=delayed_milestones,
            critical_tasks=critical_tasks,
            open_risks=open_risks,
            blocked_tasks=blocked_tasks,
            average_variance=round(sum(variance_values) / len(variance_values), 2) if variance_values else 0.0,
            variance_available_percent=completeness.get("variance", 0.0),
            schedule_health=parsed.schedule_health or "Unknown",
            project_stage=parsed.project_stage,
            project_status=parsed.project_status,
            health_distribution=dict(health_distribution),
            dependency_count=dependencies,
            task_status_distribution=status_distribution,
            summary_task_counts=parsed.summary_task_counts,
            comment_sentiment_distribution=dict(comment_distribution),
            positive_signals=positives,
            risk_comments=risk_comments,
            interpreted_comments=[
                {
                    "comment": c.text,
                    "theme": c.evidence_theme,
                    "classification": c.classification,
                    "insight": c.interpreted_insight,
                    "row_reference": c.row_reference,
                }
                for c in parsed.comments
            ],
            key_findings=findings,
            root_causes=roots,
            business_impacts=impacts,
            evidence_based_recommendations=recs,
            milestones=milestones,
            upcoming_milestones=upcoming_milestones,
            risk_register=evidence["risks"],
            data_completeness_score=completeness_score,
            data_completeness=completeness,
            confidence_level=confidence_level,
            confidence_explanation=confidence_explanation,
            total_tasks=total,
            missing_data=missing_data,
        )

    def _ensure_findings(self, findings: list[str], parsed: ParsedProject, completion: float, evidence: dict[str, Any]) -> list[str]:
        if not findings:
            findings = [f"{parsed.project_name} has {completion}% reported completion based on available workbook evidence."]
        if evidence["risks"]:
            findings.append(f"Top task risk is {evidence['risks'][0]['title']} with risk score {evidence['risks'][0]['risk_score']}.")
        if evidence["root_causes"]:
            findings.append(f"Primary root cause signal: {evidence['root_causes'][0]['cause']}.")
        if evidence["upcoming_milestones"]:
            findings.append(f"Next milestone requiring attention: {evidence['upcoming_milestones'][0]['task']}.")
        if len(findings) < 5:
            findings.append(f"Confidence is {evidence['confidence']}%, reflecting workbook completeness and evidence availability.")
        return list(dict.fromkeys(findings))[:8]
