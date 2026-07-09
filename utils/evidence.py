from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from utils.schemas import ParsedProject, ProjectComment, ProjectTask


NEGATIVE_COMMENT_CLASSES = {
    "Blocker",
    "Customer Dependency",
    "Vendor Dependency",
    "Resource Constraint",
    "Schedule Risk",
    "Issue",
    "Decision Required",
}


def clean_health(value: str) -> str:
    text = (value or "").strip().lower()
    if text in {"green", "g"}:
        return "Green"
    if text in {"yellow", "amber", "a"}:
        return "Amber"
    if text in {"red", "r"}:
        return "Red"
    return "Unknown"


def classify_comment(comment: ProjectComment) -> ProjectComment:
    """Classify comments using the priority order from the evidence specification."""
    text = comment.text.lower()
    rules = [
        ("Blocker", ["blocked", "cannot proceed", "waiting", "hold", "on hold"]),
        ("Customer Dependency", ["customer", "client", "awaiting client", "sample data", "approval", "otk", "titan", "provide sample", "master data"]),
        ("Vendor Dependency", ["vendor", "third party", "supplier", "d&b", "d & b"]),
        ("Resource Constraint", ["resource", "bandwidth", "parallel", "workload", "capacity"]),
        ("Schedule Risk", ["delay", "delayed", "slipped", "postponed", "overdue", "impacted"]),
        ("Issue", ["pending", "remain", "remaining", "repeating", "changed", "issue", "defect"]),
        ("Decision Required", ["decision", "sign off", "approve", "approval", "meeting", "calendar", "confirm"]),
        ("Positive Progress", ["completed", "finished", "delivered", "successful", "covered all sessions", "coverd all sessions"]),
    ]
    label = "Informational"
    for candidate, keywords in rules:
        if any(keyword in text for keyword in keywords):
            label = candidate
            break
    comment.classification = label
    comment.evidence_theme = label
    comment.interpreted_insight = interpret_comment(comment)
    return comment


def interpret_comment(comment: ProjectComment) -> str:
    text = comment.text.lower()
    if comment.classification == "Blocker":
        return "Work appears blocked or waiting; leadership should confirm the blocking owner and unblock date."
    if comment.classification == "Customer Dependency":
        return "Project delivery depends on timely customer inputs, approvals, samples or master data."
    if comment.classification == "Vendor Dependency":
        return "A supplier or third-party dependency may affect delivery sequencing or readiness."
    if comment.classification == "Resource Constraint":
        return "Schedule pressure appears linked to resource capacity or parallel workstream contention."
    if comment.classification == "Schedule Risk":
        return "The comment signals schedule pressure that may reduce downstream recovery time."
    if comment.classification == "Decision Required":
        return "A governance decision, meeting or approval is needed to keep execution moving."
    if comment.classification == "Positive Progress":
        return "Planned delivery activity was completed, showing execution momentum where ownership is clear."
    if "jde" in text or "mapping" in text or "integration" in text:
        return "Integration readiness remains exposed to unresolved mapping decisions."
    return "Comment captured as contextual project evidence with limited risk specificity."


def comments_by_row(comments: list[ProjectComment]) -> dict[int, list[ProjectComment]]:
    mapped: dict[int, list[ProjectComment]] = defaultdict(list)
    for comment in comments:
        match = re.search(r"\d+", comment.row_reference or "")
        if match:
            mapped[int(match.group(0))].append(comment)
    return mapped


def is_late(task: ProjectTask, as_of: datetime) -> bool:
    return bool(
        task.end_date
        and task.end_date.date() < as_of.date()
        and (task.percent_complete or 0) < 100
        and task.status.lower() != "not applicable"
    )


def variance_over_10(task: ProjectTask) -> bool:
    return task.variance_days is not None and abs(task.variance_days) > 10


def task_owner(task: ProjectTask) -> str:
    return task.assigned_to or task.project_manager or ""


def business_impact_for_text(text: str) -> str:
    lower = text.lower()
    if any(term in lower for term in ["customer", "sample", "master data", "approval", "otk", "titan"]):
        return "Customer input delay may defer configuration validation, which can compress testing and increase go-live risk."
    if any(term in lower for term in ["integration", "jde", "mapping", "po", "gr", "invoice"]):
        return "Integration closure delay may compress SIT/UAT windows and reduce cutover confidence."
    if any(term in lower for term in ["resource", "parallel", "workshop", "capacity", "bandwidth"]):
        return "Capacity contention may absorb schedule contingency and slow critical workshop outcomes."
    if any(term in lower for term in ["sign off", "approval", "decision", "calendar", "meeting"]):
        return "Delayed decisions may slow governance closure and push downstream milestone readiness."
    if any(term in lower for term in ["go live", "cutover", "deployment", "production"]):
        return "Production readiness risk may affect go-live commitments and hypercare stability."
    return "If unresolved, this may create downstream schedule pressure and reduce confidence in delivery commitments."


def mitigation_for_text(text: str) -> str:
    lower = text.lower()
    if any(term in lower for term in ["customer", "sample", "master data", "approval", "otk", "titan"]):
        return "Escalate a customer-owned action tracker with named owner, due date and fallback data option."
    if any(term in lower for term in ["integration", "jde", "mapping", "po", "gr", "invoice"]):
        return "Run a focused integration mapping closure forum and freeze open design decisions."
    if any(term in lower for term in ["resource", "parallel", "workshop", "capacity", "bandwidth"]):
        return "Re-sequence overlapping workstreams and add PMO control over critical workshop capacity."
    if any(term in lower for term in ["sign off", "approval", "decision", "calendar", "meeting"]):
        return "Lock the decision meeting, assign the approver and publish action closure within 24 hours."
    if any(term in lower for term in ["go live", "cutover", "deployment", "production"]):
        return "Create a daily cutover readiness review focused on blockers, owners and recovery actions."
    return "Assign an accountable owner and review closure in the weekly governance forum."


def likelihood(score: int) -> str:
    if score >= 45:
        return "High"
    if score >= 25:
        return "Medium"
    return "Low"


def task_risk_register(tasks: list[ProjectTask], comments: list[ProjectComment], as_of: datetime) -> list[dict[str, Any]]:
    row_comments = comments_by_row(comments)
    risks: list[dict[str, Any]] = []
    for task in tasks:
        evidence: list[str] = []
        score = 0
        related = row_comments.get(task.row_number, [])
        if is_late(task, as_of):
            score += 10
            evidence.append("Task is late against reporting date.")
        if task.critical:
            score += 20
            evidence.append("Task is marked critical.")
        if task.blocked:
            score += 25
            evidence.append("Task is marked blocked.")
        if variance_over_10(task):
            score += 15
            evidence.append(f"Variance exceeds 10 days ({task.variance_days}).")
        if task.dependencies:
            score += 5
            evidence.append(f"Dependency exists: {task.dependencies}.")
        if any(c.classification in NEGATIVE_COMMENT_CLASSES for c in related):
            score += 10
            evidence.extend([f"Comment: {c.interpreted_insight}" for c in related[:2]])
        if not task_owner(task):
            score += 5
            evidence.append("Owner is missing.")
        if task.on_hold or task.status.lower() == "on hold":
            score += 20
            evidence.append("Task is on hold.")
        if clean_health(task.schedule_health) == "Red":
            score += 15
            evidence.append("Schedule health is Red.")
        if score <= 0:
            continue
        title = task.task_name or f"Task row {task.row_number}"
        risks.append(
            {
                "risk": title,
                "title": title,
                "risk_score": score,
                "evidence": evidence or ["Risk inferred from project plan status."],
                "likelihood": likelihood(score),
                "impact": business_impact_for_text(title + " " + " ".join(evidence)),
                "business_impact": business_impact_for_text(title + " " + " ".join(evidence)),
                "recommended_mitigation": mitigation_for_text(title + " " + " ".join(evidence)),
                "mitigation": mitigation_for_text(title + " " + " ".join(evidence)),
                "owner": task_owner(task) or "Unassigned",
                "phase": task.phase_milestone or str(task.raw.get("Phase/Milestone") or ""),
                "status": task.status,
                "source": f"Project Plan row {task.row_number}",
            }
        )
    risks.sort(key=lambda item: item["risk_score"], reverse=True)
    return risks[:12]


def detect_milestones(tasks: list[ProjectTask], as_of: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    keywords = ["go live", "uat", "sit", "workshop complete", "configuration complete", "sign off", "deployment", "milestone"]
    milestones: list[dict[str, Any]] = []
    for task in tasks:
        duration = str(task.raw.get("Duration") or "").strip().lower()
        name = task.task_name.lower()
        is_zero_duration = duration in {"0", "0d", "0 day", "0 days"}
        detected = bool(task.phase_milestone or is_zero_duration or any(keyword in name for keyword in keywords))
        if not detected:
            continue
        complete = (task.percent_complete or 0) >= 100 or task.status.lower() == "completed"
        delayed = bool(task.end_date and task.end_date.date() < as_of.date() and not complete)
        at_risk = delayed or clean_health(task.schedule_health) == "Red" or (task.rag or "").lower() in {"red", "yellow", "amber"}
        if complete:
            state = "Completed"
        elif delayed:
            state = "Delayed"
        elif at_risk:
            state = "At Risk"
        else:
            state = "Upcoming"
        milestones.append(
            {
                "phase": task.phase_milestone or "Detected milestone",
                "task": task.task_name,
                "status": task.status,
                "milestone_status": state,
                "schedule_health": clean_health(task.schedule_health),
                "rag": task.rag or clean_health(task.schedule_health),
                "end_date": task.end_date.isoformat() if task.end_date else None,
                "percent_complete": task.percent_complete,
                "delayed": delayed,
                "owner": task_owner(task) or "Unassigned",
                "source": f"Project Plan row {task.row_number}",
            }
        )
    upcoming = [m for m in milestones if m["milestone_status"] in {"Upcoming", "At Risk", "Delayed"}][:8]
    if not upcoming:
        upcoming = milestones[-5:]
    delayed_count = sum(1 for m in milestones if m["milestone_status"] == "Delayed")
    return milestones, upcoming, delayed_count


def detect_root_causes(tasks: list[ProjectTask], comments: list[ProjectComment], as_of: datetime) -> list[dict[str, Any]]:
    delayed = [task for task in tasks if is_late(task, as_of)]
    causes: list[dict[str, Any]] = []
    if delayed:
        phase_by_row: dict[int, str] = {}
        current_phase = "Unspecified phase"
        for task in sorted(tasks, key=lambda item: item.row_number):
            if task.phase_milestone:
                current_phase = task.phase_milestone
            phase_by_row[task.row_number] = current_phase
        phase_counts = Counter(phase_by_row.get(t.row_number, "Unspecified phase") for t in delayed)
        phase, count = phase_counts.most_common(1)[0]
        if count / len(delayed) >= 0.3:
            causes.append(
                {
                    "cause": "Phase bottleneck",
                    "supporting_evidence": [f"{count} of {len(delayed)} delayed tasks are concentrated in {phase}."],
                    "confidence": 85,
                    "business_impact": f"Concentration of delayed tasks in {phase} can push downstream validation and readiness milestones.",
                }
            )
    comment_counts = Counter(c.classification for c in comments)
    if comment_counts.get("Customer Dependency", 0) >= 1:
        causes.append(
            {
                "cause": "Customer dependency",
                "supporting_evidence": [c.text for c in comments if c.classification == "Customer Dependency"][:3],
                "confidence": min(95, 65 + comment_counts["Customer Dependency"] * 10),
                "business_impact": business_impact_for_text("customer sample data approval"),
            }
        )
    if comment_counts.get("Resource Constraint", 0) >= 1:
        causes.append(
            {
                "cause": "Resource or parallel workstream constraint",
                "supporting_evidence": [c.text for c in comments if c.classification == "Resource Constraint"][:3],
                "confidence": min(90, 60 + comment_counts["Resource Constraint"] * 10),
                "business_impact": business_impact_for_text("resource parallel workload workshop"),
            }
        )
    predecessor_counts = Counter(t.dependencies for t in tasks if t.dependencies and (is_late(t, as_of) or clean_health(t.schedule_health) == "Red"))
    if predecessor_counts:
        predecessor, count = predecessor_counts.most_common(1)[0]
        if count >= 2:
            causes.append(
                {
                    "cause": "Dependency chain",
                    "supporting_evidence": [f"{count} risk-bearing tasks share dependency/predecessor {predecessor}."],
                    "confidence": 75,
                    "business_impact": "A shared predecessor can create cascading delay if not closed quickly.",
                }
            )
    owner_counts = Counter(task_owner(t) for t in tasks if task_owner(t))
    if owner_counts:
        owner, count = owner_counts.most_common(1)[0]
        if count / max(len(tasks), 1) >= 0.15:
            causes.append(
                {
                    "cause": "Resource bottleneck",
                    "supporting_evidence": [f"{owner} owns or manages {count} task rows."],
                    "confidence": 65,
                    "business_impact": "Heavy ownership concentration can slow decision turnaround and execution throughput.",
                }
            )
    if not causes:
        causes.append(
            {
                "cause": "Insufficient clustered evidence",
                "supporting_evidence": ["Workbook evidence did not show a dominant recurring delay or dependency cluster."],
                "confidence": 45,
                "business_impact": "Low clustered evidence means leadership should interpret root causes with caution.",
            }
        )
    return causes[:6]


def positive_signals(tasks: list[ProjectTask], comments: list[ProjectComment]) -> list[str]:
    signals: list[str] = []
    for task in tasks:
        if task.critical and (task.percent_complete or 0) >= 100:
            signals.append(f"Completed critical task: {task.task_name}.")
        if task.phase_milestone and task.status.lower() == "completed":
            signals.append(f"Completed milestone: {task.phase_milestone} / {task.task_name}.")
        if task.variance_days is not None and task.variance_days > 0 and task.status.lower() == "completed":
            signals.append(f"Ahead-of-schedule completion signal: {task.task_name}.")
    for comment in comments:
        if comment.classification == "Positive Progress":
            signals.append(comment.interpreted_insight)
    if not signals:
        signals.append("No strong positive signal was detected; confidence depends on plan metrics rather than positive commentary.")
    return list(dict.fromkeys(signals))[:5]


def confidence_score(parsed: ParsedProject, tasks: list[ProjectTask], comments: list[ProjectComment], milestones: list[dict[str, Any]]) -> tuple[int, list[str]]:
    score = 100
    notes: list[str] = []
    if not parsed.summary:
        score -= 20
        notes.append("Missing Summary sheet reduced confidence.")
    if not comments:
        score -= 10
        notes.append("Missing Comments sheet reduced confidence.")
    if not milestones:
        score -= 15
        notes.append("No milestones detected reduced confidence.")
    if any(not (task.start_date and task.end_date) for task in tasks):
        score -= 10
        notes.append("Some task dates are missing.")
    if any(task.variance_days is None for task in tasks):
        score -= 10
        notes.append("Some variance values are missing.")
    if any(not task_owner(task) for task in tasks):
        score -= 5
        notes.append("Some task owners are missing.")
    return max(0, min(100, score)), notes


def build_evidence(parsed: ParsedProject, as_of: datetime) -> dict[str, Any]:
    tasks = parsed.tasks
    comments = [classify_comment(comment) for comment in parsed.comments]
    risks = task_risk_register(tasks, comments, as_of)
    milestones, upcoming, delayed_count = detect_milestones(tasks, as_of)
    roots = detect_root_causes(tasks, comments, as_of)
    positives = positive_signals(tasks, comments)
    confidence, confidence_notes = confidence_score(parsed, tasks, comments, milestones)
    business_impacts = [cause["business_impact"] for cause in roots]
    recommendations = [
        {
            "recommendation": risk["recommended_mitigation"],
            "evidence": "; ".join(risk["evidence"][:2]),
            "risk": risk["title"],
        }
        for risk in risks[:5]
    ]
    if not recommendations:
        recommendations = [
            {
                "recommendation": "Improve evidence capture before leadership decisions are made.",
                "evidence": "Risk engine did not find enough task or comment evidence for a ranked mitigation.",
                "risk": "Evidence gap",
            }
        ]
    return {
        "comments": comments,
        "risks": risks,
        "milestones": milestones,
        "upcoming_milestones": upcoming,
        "delayed_milestones": delayed_count,
        "root_causes": roots,
        "positive_signals": positives,
        "business_impacts": business_impacts or ["Business impact could not be determined from available evidence."],
        "recommendations": recommendations,
        "confidence": confidence,
        "confidence_notes": confidence_notes,
    }
