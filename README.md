# 🚀 PulsePM AI

<p align="center">

# AI-Powered Project Health Copilot

Transform enterprise project workbooks into executive-ready insights using deterministic analytics and AI reasoning.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Deployed-red?logo=streamlit)](https://streamlit.io/)
[![Gemini](https://img.shields.io/badge/LLM-Gemini-orange)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-green)]()

</p>

---

# 🌐 Live Demo

**Application:** https://pulsepm-ai-7.streamlit.app/

---

# 📖 Overview

PulsePM AI is an AI-powered Project Management Office (PMO) Copilot that automatically analyzes enterprise Microsoft Excel project plans and generates executive-ready project health reports.

Instead of manually reviewing hundreds of project tasks every week, project managers simply upload an Excel workbook.

The application then:

- 📂 Discovers workbook structure dynamically
- 📊 Calculates deterministic project health
- 🤖 Extracts business evidence using AI
- ⚠️ Identifies risks and bottlenecks
- 📈 Generates executive insights
- 📄 Creates weekly reports
- 📉 Tracks historical trends
- 📽️ Generates executive PowerPoint presentations

---

# 🎯 Problem Statement

Professional Services teams spend hours every week manually reviewing Excel project plans and preparing status reports for leadership.

PulsePM AI automates the complete workflow while ensuring:

- Explainable Project Health
- Deterministic RAG Scoring
- Executive-Level Insights
- Historical Trend Analysis
- VP-ready PowerPoint Generation

---

# 🏗️ System Architecture

```text
                  Excel Workbook
                        │
                        ▼
              Workbook Discovery Agent
                        │
                        ▼
                Dynamic Excel Parser
                        │
                        ▼
              Feature Engineering Layer
                        │
                        ▼
        Deterministic Health Scoring Engine
                        │
                        ▼
          Evidence Extraction Engine
                        │
                        ▼
           Executive AI Reasoning Layer
                        │
                        ▼
          Weekly Report Generator
                        │
                        ▼
          Historical Report Storage
                        │
                        ▼
          Trend Analysis Engine
                        │
                        ▼
       Executive PowerPoint Generator
                        │
                        ▼
            Streamlit Dashboard
```

---

# ⚙️ Deterministic RAG Scoring

Unlike traditional AI dashboards, PulsePM AI **does not allow the LLM to determine project health.**

The project health is calculated using a deterministic weighted scoring model.

| Indicator | Weight |
|-----------|--------|
| Schedule Health | 30% |
| Milestone Health | 20% |
| Completion | 15% |
| Risks & Blockers | 15% |
| Stakeholder Sentiment | 10% |
| Critical Task Health | 10% |

### Final Classification

🟢 Green → 90–100

🟡 Amber → 75–89

🔴 Red → Below 75

The AI is only responsible for reasoning over structured evidence and generating executive recommendations.

---

# 🧠 Evidence Extraction Engine

Before invoking Gemini, the application extracts structured evidence from the workbook.

The engine identifies:

- Delayed Tasks
- Blocked Activities
- Customer Dependencies
- Resource Constraints
- Critical Tasks
- Upcoming Milestones
- Positive Signals
- Project Comments
- Missing Data
- Confidence Score

This significantly reduces hallucinations and produces explainable executive reports.

---

# ✨ Features

- ✅ Dynamic Excel Workbook Discovery
- ✅ Automatic Sheet Detection
- ✅ Deterministic RAG Scoring
- ✅ Evidence Extraction Engine
- ✅ AI Executive Reasoning (Gemini)
- ✅ Weekly Markdown Reports
- ✅ JSON Report Export
- ✅ Historical Trend Analysis
- ✅ Monthly Portfolio Report
- ✅ Executive PowerPoint Generation
- ✅ Monday Scheduler (08:00 AM)
- ✅ Streamlit Dashboard

---

# 📸 Application Screenshots

## 🏠 Executive Dashboard

<img src="screenshots/Screenshot 2026-07-10 124003.png" width="100%">

The dashboard provides:

- Executive Summary
- Deterministic RAG Status
- Health Score
- Completion Percentage
- Confidence Score
- Open Risks
- Late Tasks

---

## 🧠 Executive Insights

<img src="screenshots/Screenshot 2026-07-10 124014.png" width="100%">

Automatically generates:

- Key Findings
- Root Cause Analysis
- Business Impact
- Leadership Recommendations
- Confidence Explanation

---

## ⚠️ Risks & Milestones

<img src="screenshots/Screenshot 2026-07-10 124031.png" width="100%">

The Evidence Extraction Engine identifies:

- Top Risks
- Upcoming Milestones
- Positive Signals

without relying on hardcoded workbook structures.

---

## 📊 Evidence Dashboard

<img src="screenshots/Screenshot 2026-07-10 124105.png" width="100%">

Provides supporting analytics including:

- Schedule Health Distribution
- Task Status Breakdown
- Missing Data Handling
- Evidence-based Charts


---

# 📈 Monthly Executive Report

<img src="screenshots/Screenshot 2026-07-10 134013.png" width="100%">

PulsePM AI consolidates all weekly project analyses into a portfolio-level monthly executive report.

Rather than summarizing projects individually, the monthly synthesis identifies organization-wide trends and provides executive-level decision support.

### The report automatically highlights:

- 📊 Portfolio Health Distribution
- 📈 Cross-Project Trend Analysis
- 🚨 Emerging Risk Themes
- 📌 Recurring Blockers
- 📉 Projects Improving vs. Declining
- 🎯 Executive Recommendations
- 👥 Leadership Attention Areas

The monthly report is generated automatically from historical weekly reports, enabling leadership to monitor portfolio health over time instead of reviewing isolated project snapshots.

# 📊 Executive Presentation

<img src="screenshots/Screenshot 2026-07-10 133037.png" width="100%">

PulsePM AI automatically generates a management-ready PowerPoint presentation from the analyzed project portfolio.

The presentation is designed for project sponsors, PMO leadership, and executive stakeholders, requiring minimal manual edits before sharing.

The generated presentation includes:

- 📈 Portfolio Health Summary
- 🚦 RAG Distribution Across Projects
- ⚠️ Emerging Risks
- 📊 Trend Analysis
- 🎯 Leadership Recommendations
- 🌟 Project Spotlight (Best Performing & Highest Risk Projects)

This significantly reduces the manual effort required to prepare weekly and monthly executive review decks.

# 📂 Project Workflow

```text
Upload Workbook
        │
        ▼
Workbook Discovery
        │
        ▼
Dynamic Parsing
        │
        ▼
Feature Engineering
        │
        ▼
Deterministic Health Engine
        │
        ▼
Evidence Extraction
        │
        ▼
Executive AI Reasoning
        │
        ▼
Weekly Report Generation
        │
        ▼
Historical Storage
        │
        ▼
Trend Analysis
        │
        ▼
Executive PPT Generation
```

---

# ☁️ Streamlit Deployment

Required Streamlit Secrets

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

SCHEDULE_TIME = "08:00"
SCHEDULER_TIMEZONE = "Asia/Kolkata"

INPUT_FOLDER = "data"
OUTPUT_FOLDER = "output"
```

---

# 🚀 Installation

```bash
git clone https://github.com/ParthChhatbar/PulsePM-AI.git

cd PulsePM-AI

python -m venv .venv

.venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env`

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

Run locally

```bash
streamlit run streamlit_app.py
```

---

# 🛠️ Tech Stack

- Python
- Streamlit
- Google Gemini
- APScheduler
- Pandas
- OpenPyXL
- Plotly
- Pydantic
- Markdown
- python-pptx

---

# 👨‍💻 Author

**Parth Chhatbar**

AI Engineer

⭐ If you found this project interesting, consider giving it a star!
