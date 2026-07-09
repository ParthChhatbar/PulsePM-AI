from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

Rag = Literal["Green", "Amber", "Red"]


class WorkbookIssue(BaseModel):
    level: Literal["warning", "error"]
    message: str


class ProjectTask(BaseModel):
    row_number: int
    task_name: str = ""
    status: str = ""
    start_date: datetime | None = None
    end_date: datetime | None = None
    percent_complete: float | None = None
    schedule_health: str = ""
    phase_milestone: str = ""
    project_manager: str = ""
    at_risk: bool | None = None
    on_hold: bool | None = None
    critical: bool | None = None
    blocked: bool | None = None
    variance_days: float | None = None
    dependencies: str = ""
    rag: str = ""
    assigned_to: str = ""
    baseline_start: datetime | None = None
    baseline_finish: datetime | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ProjectComment(BaseModel):
    row_reference: str = ""
    text: str
    author: str = ""
    created_at: datetime | None = None
    classification: str = "Neutral"
    interpreted_insight: str = ""
    evidence_theme: str = "General"


class ParsedProject(BaseModel):
    source_file: str
    parsed_at: datetime
    plan_sheet: str | None = None
    summary_sheet: str | None = None
    comments_sheet: str | None = None
    project_name: str = "Unknown Project"
    project_manager: str = ""
    project_stage: str = ""
    project_status: str = ""
    schedule_health: str = ""
    summary_completion_percent: float | None = None
    summary_task_counts: dict[str, int] = Field(default_factory=dict)
    project_start_date: datetime | None = None
    project_end_date: datetime | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    tasks: list[ProjectTask] = Field(default_factory=list)
    comments: list[ProjectComment] = Field(default_factory=list)
    issues: list[WorkbookIssue] = Field(default_factory=list)


class ProjectFeatures(BaseModel):
    completion_percent: float
    completion_source: str = "calculated"
    late_tasks: int
    delayed_milestones: int
    critical_tasks: int
    open_risks: int
    blocked_tasks: int
    average_variance: float
    variance_available_percent: float = 0.0
    schedule_health: str = "Unknown"
    project_stage: str = ""
    project_status: str = ""
    health_distribution: dict[str, int]
    dependency_count: int
    task_status_distribution: dict[str, int]
    summary_task_counts: dict[str, int] = Field(default_factory=dict)
    comment_sentiment_distribution: dict[str, int]
    positive_signals: list[str]
    risk_comments: list[str]
    interpreted_comments: list[dict[str, str]] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    root_causes: list[str] = Field(default_factory=list)
    business_impacts: list[str] = Field(default_factory=list)
    evidence_based_recommendations: list[dict[str, str]] = Field(default_factory=list)
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    upcoming_milestones: list[dict[str, Any]] = Field(default_factory=list)
    risk_register: list[dict[str, Any]] = Field(default_factory=list)
    data_completeness_score: float = 0.0
    data_completeness: dict[str, float] = Field(default_factory=dict)
    confidence_level: str = "Low"
    confidence_explanation: str = ""
    total_tasks: int
    missing_data: list[str]


class HealthScore(BaseModel):
    score: float
    confidence: float
    rag: Rag
    category_scores: dict[str, float]
    rationale: list[str]


class ExecutiveReasoning(BaseModel):
    executive_summary: str
    key_findings: list[str] = Field(default_factory=list)
    root_cause_analysis: list[str] = Field(default_factory=list)
    why: list[str]
    evidence: list[str]
    business_impact: str
    top_risks: list[str]
    recommendations: list[str]
    missing_information: list[str]
    data_quality_note: str = ""
    confidence: float


class TrendPoint(BaseModel):
    report_id: str
    generated_at: datetime
    week_number: int = 0
    project_name: str
    rag: Rag
    health_score: float
    completion_percent: float
    late_tasks: int
    open_risks: int
    sentiment_score: float
    critical_tasks: int
    dependencies: int
    delayed_milestones: int


class ProjectTrend(BaseModel):
    project_name: str
    status: Literal["Improving", "Stable", "Deteriorating", "Stagnant", "Insufficient History"]
    points: list[TrendPoint]
    insights: list[str]
    recurring_risks: list[str]
    risk_acceleration: str = "No acceleration detected"
    recovery_signal: str = "No recovery signal detected"


class WeeklyReport(BaseModel):
    report_id: str
    generated_at: datetime
    source_file: str
    project: ParsedProject
    features: ProjectFeatures
    scoring: HealthScore
    reasoning: ExecutiveReasoning
    week_number: int = 0
    trend: ProjectTrend | None = None
    markdown_path: str | None = None
    json_path: str | None = None


class MonthlySynthesis(BaseModel):
    generated_at: datetime
    reports_analyzed: int
    portfolio_overview: list[str] = Field(default_factory=list)
    portfolio_trends: list[str]
    projects_improving: list[str]
    projects_deteriorating: list[str] = Field(default_factory=list)
    projects_declining: list[str]
    risk_themes: list[str]
    common_dependencies: list[str] = Field(default_factory=list)
    emerging_risks: list[str] = Field(default_factory=list)
    positive_trends: list[str] = Field(default_factory=list)
    sentiment_trends: list[str]
    executive_recommendations: list[str]
    strategic_recommendations: list[str] = Field(default_factory=list)
    leadership_attention: list[str]
    project_snapshots: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float
    json_path: str | None = None
    ppt_path: str | None = None


def ensure_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(value)
