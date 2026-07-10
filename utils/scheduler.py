from __future__ import annotations

import os
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from utils.logger import logger


def run_folder_analysis(input_folder: str | Path, output_folder: str | Path) -> int:
    from main import analyze_workbook

    count = 0

    input_folder = Path(input_folder)
    output_folder = Path(output_folder)

    # Ensure output directory exists
    output_folder.mkdir(parents=True, exist_ok=True)

    for path in input_folder.glob("*.xls*"):
        logger.info("Scheduled analysis started for %s", path)
        analyze_workbook(path, output_folder)
        count += 1

    logger.info("Scheduled analysis completed. files=%s", count)
    return count


def start_scheduler(
    input_folder: str | Path | None = None,
    output_folder: str | Path | None = None,
) -> BackgroundScheduler:

    # Read schedule configuration from environment / Streamlit secrets
    schedule_time = os.getenv("SCHEDULE_TIME", "08:00")
    timezone = os.getenv("SCHEDULER_TIMEZONE", "Asia/Kolkata")

    hour, minute = [int(part) for part in schedule_time.split(":", 1)]

    scheduler = BackgroundScheduler(
        timezone=timezone
    )

    scheduler.add_job(
        run_folder_analysis,
        CronTrigger(
            day_of_week="mon",
            hour=hour,
            minute=minute,
            timezone=timezone,
        ),
        args=[
            input_folder or os.getenv("INPUT_FOLDER", "data"),
            output_folder or os.getenv("OUTPUT_FOLDER", "output"),
        ],
        id="pulsepm_weekly_analysis",
        replace_existing=True,
    )

    scheduler.start()

    logger.info(
        "Scheduler started. Next execution: Every Monday at %02d:%02d (%s)",
        hour,
        minute,
        timezone,
    )

    return scheduler
