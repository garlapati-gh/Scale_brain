"""Configuration, constants, and default presets for ScaleScope."""

from __future__ import annotations

# Application Metadata
APP_NAME = "ScaleScope"
APP_TITLE = "ScaleScope | Operations Intelligence Platform"
APP_ICON = "⚡"
APP_VERSION = "1.0.0"

# Query Engine Limits
MAX_QUERY_ROWS = 250
DEFAULT_MODEL = "openai/gpt-4o-mini"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Allowed Database Tables
ALLOWED_TABLES = {"projects", "workers", "tasks", "reviews"}

# User Roles for Access Simulation
ROLES = {
    "Operations Executive": {
        "badge": "👑 Executive",
        "description": "Full access to high-level KPIs, budgets, team productivity, and cross-project health.",
        "can_export": True,
        "can_query": True,
        "can_view_insights": True,
    },
    "Operations Team Lead": {
        "badge": "🎯 Team Lead",
        "description": "Focused on team velocity, task backlogs, quality variance, and worker allocation.",
        "can_export": True,
        "can_query": True,
        "can_view_insights": True,
    },
    "Quality & Review Analyst": {
        "badge": "🔬 Analyst",
        "description": "Deep inspection of task rubrics, review scores, edge cases, and compliance.",
        "can_export": True,
        "can_query": True,
        "can_view_insights": False,
    },
}

# Curated Natural Language Suggested Inquiries
SUGGESTED_QUESTIONS = [
    "Which projects have the highest number of overdue tasks?",
    "Show average quality score and completed tasks by team.",
    "Who are the top 5 workers with the highest quality rating?",
    "What is the average task completion time by project priority?",
    "List all blocked tasks with assigned worker and project name.",
    "Which domain has the highest total budget allocated?",
]
