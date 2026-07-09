# PulsePM AI

PulsePM AI is a Streamlit application for project health monitoring, weekly executive reporting, monthly synthesis, and PowerPoint generation from Microsoft Excel project plans.

## Architecture

Excel Upload -> Parser Agent -> Feature Engineering -> Deterministic Health Engine -> Executive Reasoning Agent -> Weekly Report Storage -> Monthly Synthesis -> PPT Generator -> Streamlit Dashboard

The parser discovers workbook sheets dynamically, infers headers, and handles missing or corrupt workbook sections with structured warnings.

## Features

- Dynamic Excel sheet discovery with no hardcoded plan sheet names
- Summary, project plan, and comment parsing
- Deterministic Red / Amber / Green scoring
- Gemini usage restricted to comment classification and executive reasoning
- Weekly Markdown and JSON reports
- Monthly portfolio synthesis
- 7-slide executive PowerPoint generation
- APScheduler Monday 08:00 automation
- Streamlit dashboard with metric cards, charts, timeline, and downloads
- Structured logging in `logs/execution.log`

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Set `GEMINI_API_KEY` in `.env` to enable AI comment classification and executive reasoning. Without it, deterministic analysis, scoring, storage, monthly fallback synthesis, and PPT generation still run.

## Run Locally

```bash
streamlit run streamlit_app.py
```

Or run a workbook from the command line:

```bash
python main.py "C:\path\to\project-plan.xlsx" --output output
```

Generate monthly synthesis and PPT:

```bash
python main.py --monthly --output output
```

## Streamlit Cloud

1. Push this folder to GitHub.
2. Create a Streamlit Cloud app using `streamlit_app.py`.
3. Add `GEMINI_API_KEY`, `INPUT_FOLDER`, `OUTPUT_FOLDER`, and `SCHEDULE_TIME` in Streamlit secrets or environment configuration.
4. Deploy.

## Environment Variables

- `GEMINI_API_KEY`: Gemini API key for reasoning and comment classification.
- `INPUT_FOLDER`: Folder scanned by the scheduler. Defaults to `data`.
- `OUTPUT_FOLDER`: Report output folder. Defaults to `output`.
- `SCHEDULE_TIME`: Monday run time in `HH:MM`. Defaults to `08:00`.

## Scheduler

The Streamlit sidebar includes a scheduler toggle. When enabled, APScheduler runs every Monday at the configured time and analyzes all Excel files in `INPUT_FOLDER`.

## Project Flow

1. Upload Excel workbook.
2. Inspect discovered sheets and sample rows.
3. Run weekly analysis.
4. Review dashboard metrics and charts.
5. Download weekly Markdown or JSON.
6. Generate monthly synthesis.
7. Download executive PPT.

## Screenshots

Screenshots can be added after deployment from the Streamlit Cloud app.

## Future Improvements

- Role-based authentication for executive and PM users
- Email distribution for weekly packs
- Historical baseline comparison across named projects
- Custom enterprise scoring weights
