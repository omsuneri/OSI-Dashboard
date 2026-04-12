-- ============================================================
-- OSI Dashboard v3.0 — SQLite Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS repositories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    owner           TEXT NOT NULL,
    name            TEXT NOT NULL,
    full_name       TEXT NOT NULL UNIQUE,
    description     TEXT,
    primary_language TEXT,
    stars           INTEGER DEFAULT 0,
    forks           INTEGER DEFAULT 0,
    open_issues     INTEGER DEFAULT 0,
    created_at      TEXT,           -- ISO 8601 string
    synced_at       TEXT NOT NULL   -- ISO 8601 string
);

CREATE TABLE IF NOT EXISTS contributors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id         INTEGER NOT NULL REFERENCES repositories(id),
    username        TEXT NOT NULL,
    avatar_url      TEXT,
    total_commits   INTEGER DEFAULT 0,
    first_commit_at TEXT,
    last_commit_at  TEXT,
    UNIQUE(repo_id, username)
);

CREATE TABLE IF NOT EXISTS commits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id         INTEGER NOT NULL REFERENCES repositories(id),
    sha             TEXT NOT NULL UNIQUE,
    author_username TEXT,
    author_email    TEXT,
    message         TEXT,
    committed_at    TEXT NOT NULL,
    additions       INTEGER DEFAULT 0,
    deletions       INTEGER DEFAULT 0,
    files_changed   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pull_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id         INTEGER NOT NULL REFERENCES repositories(id),
    pr_number       INTEGER NOT NULL,
    title           TEXT,
    author_username TEXT,
    state           TEXT NOT NULL,          -- 'open' | 'closed'
    is_merged       INTEGER DEFAULT 0,      -- 0 or 1
    created_at      TEXT NOT NULL,
    merged_at       TEXT,
    closed_at       TEXT,
    additions       INTEGER DEFAULT 0,
    deletions       INTEGER DEFAULT 0,
    review_count    INTEGER DEFAULT 0,
    comment_count   INTEGER DEFAULT 0,
    labels          TEXT DEFAULT '[]',      -- JSON array string
    UNIQUE(repo_id, pr_number)
);

CREATE TABLE IF NOT EXISTS issues (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id         INTEGER NOT NULL REFERENCES repositories(id),
    issue_number    INTEGER NOT NULL,
    title           TEXT,
    author_username TEXT,
    state           TEXT NOT NULL,          -- 'open' | 'closed'
    created_at      TEXT NOT NULL,
    closed_at       TEXT,
    response_at     TEXT,                   -- first comment timestamp
    labels          TEXT DEFAULT '[]',      -- JSON array string
    comment_count   INTEGER DEFAULT 0,
    UNIQUE(repo_id, issue_number)
);

CREATE TABLE IF NOT EXISTS reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_id           INTEGER NOT NULL REFERENCES pull_requests(id),
    repo_id         INTEGER NOT NULL,
    reviewer_username TEXT,
    state           TEXT,                   -- 'APPROVED' | 'CHANGES_REQUESTED' | 'COMMENTED'
    submitted_at    TEXT
);

-- ============================================================
-- Indexes — critical for analytics query performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_commits_repo_date    ON commits(repo_id, committed_at);
CREATE INDEX IF NOT EXISTS idx_commits_author       ON commits(repo_id, author_username);
CREATE INDEX IF NOT EXISTS idx_prs_repo_state       ON pull_requests(repo_id, state);
CREATE INDEX IF NOT EXISTS idx_prs_author           ON pull_requests(repo_id, author_username);
CREATE INDEX IF NOT EXISTS idx_issues_repo_state    ON issues(repo_id, state);
CREATE INDEX IF NOT EXISTS idx_reviews_pr           ON reviews(pr_id);
CREATE INDEX IF NOT EXISTS idx_reviews_reviewer     ON reviews(repo_id, reviewer_username);
