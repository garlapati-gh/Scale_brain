from __future__ import annotations

import random
import sqlite3
from threading import RLock
from datetime import date, datetime, timedelta

import pandas as pd

DB_LOCK = RLock()


def create_database() -> sqlite3.Connection:
    """Create a reproducible, in-memory operational dataset for the dashboard."""
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            client TEXT NOT NULL,
            domain TEXT NOT NULL,
            status TEXT NOT NULL,
            priority TEXT NOT NULL,
            start_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            budget_usd REAL NOT NULL
        );
        CREATE TABLE workers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            team TEXT NOT NULL,
            location TEXT NOT NULL,
            hourly_rate_usd REAL NOT NULL
        );
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id),
            worker_id INTEGER NOT NULL REFERENCES workers(id),
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            priority TEXT NOT NULL,
            created_at TEXT NOT NULL,
            due_date TEXT NOT NULL,
            completed_at TEXT,
            estimated_hours REAL NOT NULL,
            actual_hours REAL,
            quality_score REAL
        );
        CREATE TABLE reviews (
            id INTEGER PRIMARY KEY,
            task_id INTEGER NOT NULL REFERENCES tasks(id),
            reviewer_id INTEGER NOT NULL REFERENCES workers(id),
            score REAL NOT NULL,
            notes TEXT NOT NULL,
            reviewed_at TEXT NOT NULL
        );
        """
    )

    rng = random.Random(42)
    today = date.today()
    domains = ["Autonomous systems", "Retail intelligence", "Document AI", "Mapping"]
    clients = ["Northstar Labs", "Meridian AI", "Juniper Robotics", "Atlas Systems"]
    project_names = [
        "Warehouse scene understanding", "Receipt field extraction", "Road sign taxonomy",
        "Product catalog matching", "Industrial defect review", "Voice intent labeling",
        "Satellite object detection", "Safety policy evaluation", "Medical form parsing",
        "Retail shelf mapping", "Multilingual response grading", "Sensor fusion QA",
    ]
    locations = ["New York", "Austin", "London", "Manila", "Nairobi", "Remote"]
    teams = ["Data Operations", "Quality", "Expert Review", "Trust & Safety"]
    project_statuses = ["active", "active", "active", "at_risk", "completed", "planning"]

    projects = []
    for project_id, name in enumerate(project_names, start=1):
        start = today - timedelta(days=rng.randint(15, 150))
        due = today + timedelta(days=rng.randint(-18, 45))
        status = rng.choice(project_statuses)
        projects.append(
            (project_id, name, rng.choice(clients), rng.choice(domains), status,
             rng.choice(["standard", "high", "critical"]), start.isoformat(),
             due.isoformat(), round(rng.uniform(18000, 145000), 2))
        )
    connection.executemany(
        "INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", projects
    )

    first_names = ["Avery", "Jordan", "Morgan", "Taylor", "Riley", "Casey", "Quinn", "Jamie", "Drew", "Reese", "Skyler", "Cameron", "Rowan", "Emerson", "Parker", "Sage", "Alex", "Sam"]
    last_names = ["Chen", "Patel", "Rivera", "Kim", "Okafor", "Singh", "Morgan", "Brooks", "Ali", "Reyes", "Shah", "Diaz", "Nguyen", "Wilson", "Khan", "Park", "Bennett", "Lopez"]
    workers = [
        (worker_id, f"{first_names[worker_id - 1]} {last_names[worker_id - 1]}",
         rng.choice(teams), rng.choice(locations), round(rng.uniform(18, 58), 2))
        for worker_id in range(1, len(first_names) + 1)
    ]
    connection.executemany("INSERT INTO workers VALUES (?, ?, ?, ?, ?)", workers)

    task_titles = ["Image annotation", "Entity verification", "Transcript review", "Bounding box QA", "Policy classification", "Document validation", "Edge-case adjudication", "Metadata cleanup"]
    tasks = []
    reviews = []
    for task_id in range(1, 701):
        project_id = rng.randint(1, len(projects))
        worker_id = rng.randint(1, len(workers))
        created = today - timedelta(days=rng.randint(0, 119))
        due = created + timedelta(days=rng.randint(2, 14))
        status = rng.choices(["completed", "in_progress", "queued", "blocked"], [0.58, 0.22, 0.15, 0.05])[0]
        completed = None
        actual_hours = None
        quality = None
        if status == "completed":
            completed = (due + timedelta(days=rng.randint(-4, 6))).isoformat()
            actual_hours = round(rng.uniform(0.2, 7.5), 1)
            quality = round(min(5.0, max(1.0, rng.gauss(4.25, 0.55))), 2)
        tasks.append(
            (task_id, project_id, worker_id, rng.choice(task_titles), status,
             rng.choice(["low", "standard", "high", "critical"]),
             datetime.combine(created, datetime.min.time()).isoformat(), due.isoformat(),
             completed, round(rng.uniform(0.5, 8), 1), actual_hours, quality)
        )
        if status == "completed" and rng.random() < 0.42:
            reviews.append(
                (len(reviews) + 1, task_id, rng.randint(1, len(workers)),
                 round(min(5.0, max(1.0, quality + rng.uniform(-0.7, 0.7))), 2),
                 rng.choice(["Meets rubric", "Minor corrections", "Excellent consistency", "Escalated for review"]),
                 (date.fromisoformat(completed) + timedelta(days=rng.randint(0, 3))).isoformat())
            )
    connection.executemany(
        "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tasks
    )
    connection.executemany("INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?)", reviews)
    return connection


def read_frame(connection: sqlite3.Connection, query: str) -> pd.DataFrame:
    with DB_LOCK:
        return pd.read_sql_query(query, connection)