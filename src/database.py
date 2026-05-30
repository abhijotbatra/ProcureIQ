"""
src/database.py  —  SQLite persistence layer
All tables: suppliers, inventory, orders, news_articles,
            risk_alerts, cost_opportunities, analysis_runs
"""
import sqlite3, os, logging
from contextlib import contextmanager
from datetime import datetime

logger  = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "procureiq.db")

@contextmanager
def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn; conn.commit()
    except Exception as e:
        conn.rollback(); logger.error(f"[DB] {e}"); raise
    finally:
        conn.close()

def init_database():
    with get_db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS suppliers(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id TEXT UNIQUE NOT NULL, supplier_name TEXT NOT NULL,
            category TEXT, overall_score INTEGER, on_time_rate REAL,
            quality_rate REAL, financial_rating TEXT, country TEXT,
            annual_spend REAL, contract_expiry TEXT, last_incident TEXT,
            updated_at TEXT DEFAULT(datetime('now')));
        CREATE TABLE IF NOT EXISTS inventory(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku_id TEXT UNIQUE NOT NULL, product_name TEXT, category TEXT,
            warehouse TEXT, stock_pct REAL, current_units INTEGER,
            max_capacity INTEGER, daily_velocity REAL, days_remaining INTEGER,
            reorder_point INTEGER, lead_time_days INTEGER,
            unit_cost_usd REAL, supplier_id TEXT,
            updated_at TEXT DEFAULT(datetime('now')));
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT, sku_id TEXT, units_sold INTEGER,
            revenue_usd REAL, created_at TEXT DEFAULT(datetime('now')));
        CREATE TABLE IF NOT EXISTS news_articles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            headline TEXT NOT NULL, source TEXT, url TEXT,
            published_at TEXT, sentiment TEXT, risk_type TEXT, severity TEXT,
            recommended_action TEXT,
            created_at TEXT DEFAULT(datetime('now')), UNIQUE(headline));
        CREATE TABLE IF NOT EXISTS risk_alerts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_name TEXT, risk_type TEXT, severity TEXT,
            description TEXT, recommended_action TEXT, source TEXT,
            is_active INTEGER DEFAULT 1, resolved_at TEXT,
            created_at TEXT DEFAULT(datetime('now')));
        CREATE TABLE IF NOT EXISTS cost_opportunities(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_type TEXT, description TEXT,
            current_cost_annual REAL, optimised_cost_annual REAL,
            saving_amount REAL, saving_pct REAL,
            action_required TEXT, deadline TEXT, is_actioned INTEGER DEFAULT 0,
            created_at TEXT DEFAULT(datetime('now')));
        CREATE TABLE IF NOT EXISTS analysis_runs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, query TEXT,
            risks_found INTEGER DEFAULT 0, alerts_found INTEGER DEFAULT 0,
            savings_found REAL DEFAULT 0, critical_count INTEGER DEFAULT 0,
            action_plan TEXT, processing_time_secs REAL,
            created_at TEXT DEFAULT(datetime('now')));
        """)
    logger.info(f"[DB] Ready → {DB_PATH}")

# ── write ──────────────────────────────────────────────────────
def save_analysis_run(session_id, query, result, elapsed):
    with get_db() as c:
        c.execute("""INSERT INTO analysis_runs
          (session_id,query,risks_found,alerts_found,savings_found,
           critical_count,action_plan,processing_time_secs)
          VALUES(?,?,?,?,?,?,?,?)""",
          (session_id, query,
           len(result.get("risks",[])), len(result.get("inventory_alerts",[])),
           result.get("total_savings_found",0), result.get("critical_count",0),
           result.get("action_plan",""), elapsed))

def save_news_article(a):
    with get_db() as c:
        c.execute("""INSERT OR IGNORE INTO news_articles
          (headline,source,url,published_at,sentiment,risk_type,severity,recommended_action)
          VALUES(?,?,?,?,?,?,?,?)""",
          (a.get("headline"),a.get("source"),a.get("url"),a.get("published_at"),
           a.get("sentiment"),a.get("risk_type"),a.get("severity"),a.get("recommended_action")))

def save_risk_alert(a):
    with get_db() as c:
        c.execute("""INSERT INTO risk_alerts
          (supplier_name,risk_type,severity,description,recommended_action,source)
          VALUES(?,?,?,?,?,?)""",
          (a.get("supplier_name"),a.get("risk_type"),a.get("severity"),
           a.get("description"),a.get("recommended_action"),a.get("source","agent")))

def save_cost_opportunity(o):
    with get_db() as c:
        c.execute("""INSERT INTO cost_opportunities
          (opportunity_type,description,current_cost_annual,optimised_cost_annual,
           saving_amount,saving_pct,action_required,deadline)
          VALUES(?,?,?,?,?,?,?,?)""",
          (o.get("opportunity_type"),o.get("description"),
           o.get("current_cost_annual"),o.get("optimised_cost_annual"),
           o.get("saving_amount"),o.get("saving_pct"),
           o.get("action_required"),o.get("deadline")))

# ── read ───────────────────────────────────────────────────────
def get_recent_news(limit=20):
    with get_db() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM news_articles ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()]

def get_active_alerts():
    with get_db() as c:
        return [dict(r) for r in c.execute("""
            SELECT * FROM risk_alerts WHERE is_active=1
            ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END,
            created_at DESC""").fetchall()]

def get_analysis_history(limit=20):
    with get_db() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM analysis_runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()]

def get_cost_opportunities(limit=10):
    with get_db() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM cost_opportunities ORDER BY saving_amount DESC LIMIT ?", (limit,)).fetchall()]
