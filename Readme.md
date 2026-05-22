# 🤖 Multi-Agent AI Workflow Automation Platform

Automatically analyzes failed deployment logs, identifies root causes,
creates Jira tickets, and notifies Slack — in under 60 seconds.

## What it does

| Manual Process | With This Tool |
|---|---|
| Read 500 lines of logs → 45 min | AI analysis → 10 seconds |
| Identify root cause → 20 min | Auto detected |
| Write Jira ticket → 10 min | Auto created |
| Notify team → 5 min | Auto Slack message |
| **Total: ~1 hour** | **Total: ~60 seconds** |

## Agent Pipeline
User pastes logs
↓
🧠 Planner → 🔍 RAG Search → 📋 Log Analysis
↓
💡 Recommendation → ✅ Validation → 🔧 Tool Execution
↓
Jira Ticket + Slack Notification (auto)

## Tech Stack

- **Backend** — FastAPI, Python, async
- **AI Pipeline** — LangGraph, LangChain, Groq LLM (llama-3.3-70b)
- **Database** — PostgreSQL, Alembic
- **Vector Memory** — ChromaDB, sentence-transformers
- **Integrations** — Jira API, Slack API
- **Auth** — JWT
- **Frontend** — Streamlit

## Setup

1. Clone the repo
2. Create virtual environment
3. Install dependencies
4. Configure `.env`
5. Run migrations
6. Start backend + frontend

See SETUP.md for detailed instructions.

## Environment Variables

Create `backend/.env`:
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/workflow_platform
GROQ_API_KEY=your-key
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_PROJECT_KEY=SCRUM
SLACK_BOT_TOKEN=your-token
SLACK_DEFAULT_CHANNEL=#incidents
SECRET_KEY=your-secret-key

## Features

- 6-agent LangGraph pipeline
- RAG memory — AI learns from past incidents
- Confidence scoring — flags uncertain analyses
- Auto Jira ticket creation with warning labels for low confidence
- Slack notifications with severity context
- Full audit trail in PostgreSQL
- JWT authentication
- Streamlit dashboard with history, RAG memory feed, workflow details