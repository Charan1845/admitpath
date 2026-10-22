"""Saved student profiles and their ordered choice lists (SQLite)."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from .predict import Student

DATA_DIR = Path(os.environ.get("ADMITPATH_DATA", Path(__file__).resolve().parent.parent / "data"))


@contextmanager
def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATA_DIR / "admitpath.db", timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS students (name TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS choices (student TEXT NOT NULL, position INTEGER NOT NULL,
                institute TEXT NOT NULL, program TEXT NOT NULL, PRIMARY KEY (student, position));
        """)
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_student(s: Student) -> None:
    with connect() as c:
        c.execute("INSERT OR REPLACE INTO students (name, data) VALUES (?, ?)", (s.name, json.dumps(asdict(s))))
        c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('current', ?)", (s.name,))


def current_student() -> Student | None:
    with connect() as c:
        row = c.execute("SELECT s.data FROM meta m JOIN students s ON s.name = m.value WHERE m.key = 'current'").fetchone()
    return Student(**json.loads(row["data"])) if row else None


def get_student(name: str) -> Student | None:
    with connect() as c:
        row = c.execute("SELECT data FROM students WHERE lower(name) = lower(?)", (name,)).fetchone()
    return Student(**json.loads(row["data"])) if row else None


def choices(student: str) -> list[tuple[str, str]]:
    with connect() as c:
        rows = c.execute("SELECT institute, program FROM choices WHERE student = ? ORDER BY position", (student,)).fetchall()
    return [(r["institute"], r["program"]) for r in rows]


def set_choices(student: str, items: list[tuple[str, str]]) -> None:
    with connect() as c:
        c.execute("DELETE FROM choices WHERE student = ?", (student,))
        c.executemany("INSERT INTO choices (student, position, institute, program) VALUES (?, ?, ?, ?)",
                      [(student, i + 1, inst, prog) for i, (inst, prog) in enumerate(items)])
