from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

from agents.feature_engineering import FeatureEngineeringAgent
from agents.parser_agent import ParserAgent
from agents.ppt_agent import PPTAgent
from agents.reasoning_agent import ReasoningAgent
from agents.scoring_agent import ScoringAgent
from agents.synthesis_agent import MonthlySynthesisAgent
from utils.logger import logger
from utils.schemas import WeeklyReport
from utils.storage import load_weekly_reports, save_monthly_synthesis, save_weekly_report
from utils.trends import build_project_trend

load_dotenv()


def analyze_workbook(path: str | Path, output_root: str | Path = "output") -> WeeklyReport:
    started = datetime.now()
    logger.info("Analysis started file=%s", path)
    parsed = ParserAgent().run(path)
    features = FeatureEngineeringAgent().run(parsed)
    scoring = ScoringAgent().run(features)
    reasoning = ReasoningAgent().run(parsed, features, scoring)
    historical = [r for r in load_weekly_reports(output_root) if r.project.project_name == parsed.project_name]
    week_number = len(historical) + 1
    report = WeeklyReport(
        report_id=started.strftime("%Y%m%d%H%M%S"),
        generated_at=started,
        source_file=str(path),
        project=parsed,
        features=features,
        scoring=scoring,
        reasoning=reasoning,
        week_number=week_number,
    )
    report.trend = build_project_trend(parsed.project_name, historical + [report])
    saved = save_weekly_report(report, output_root)
    logger.info("Analysis completed file=%s rag=%s score=%s", path, scoring.rag, scoring.score)
    return saved


def generate_monthly(output_root: str | Path = "output", create_ppt: bool = True):
    reports = load_weekly_reports(output_root)
    synthesis = MonthlySynthesisAgent().run(reports)
    synthesis = save_monthly_synthesis(synthesis, output_root)
    if create_ppt:
        synthesis = PPTAgent().run(synthesis, reports, output_root)
        save_monthly_synthesis(synthesis, output_root)
    return synthesis


def main() -> None:
    parser = argparse.ArgumentParser(description="PulsePM AI project health analysis")
    parser.add_argument("workbook", nargs="?", help="Excel workbook to analyze")
    parser.add_argument("--output", default="output", help="Output folder")
    parser.add_argument("--monthly", action="store_true", help="Generate monthly synthesis and PPT")
    args = parser.parse_args()
    if args.monthly:
        synthesis = generate_monthly(args.output)
        print(synthesis.model_dump_json(indent=2))
    elif args.workbook:
        report = analyze_workbook(args.workbook, args.output)
        print(
            {
                "project": report.project.project_name,
                "rag": report.scoring.rag,
                "score": report.scoring.score,
                "json_path": report.json_path,
                "markdown_path": report.markdown_path,
            }
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
