"""
main.py — ProcureIQ Entry Point
================================
Run this to start everything:
    python main.py

Or for development with auto-reload:
    FLASK_ENV=development python main.py

Opens: http://localhost:5000
API docs: http://localhost:5000/api/portfolio
"""
import os, sys, logging, logging.handlers, yaml

# ── logging setup ──────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)

def setup_logging(cfg: dict):
    level = getattr(logging, cfg.get("logging",{}).get("level","INFO"), logging.INFO)
    fmt   = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers = [logging.StreamHandler(sys.stdout)]
    logfile = cfg.get("logging",{}).get("file","logs/procureiq.log")
    os.makedirs(os.path.dirname(logfile), exist_ok=True)
    handlers.append(logging.handlers.RotatingFileHandler(
        logfile, maxBytes=cfg.get("logging",{}).get("max_bytes",10_485_760),
        backupCount=cfg.get("logging",{}).get("backup_count",5)))
    logging.basicConfig(level=level, format=fmt, handlers=handlers)

# ── load config ─────────────────────────────────────────────────────────────────
with open("config/config.yaml","r") as f:
    config = yaml.safe_load(f)

setup_logging(config)
logger = logging.getLogger(__name__)

# ── sys path ────────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from src.database             import init_database
from src.simulator.simulator  import ProcureIQSimulator
from src.agents.engine        import ProcureIQEngine
from src.ui.dashboard         import create_app

def main():
    logger.info("=" * 60)
    logger.info("  ProcureIQ — Supply Chain Intelligence System")
    logger.info("=" * 60)

    # 1. DB
    logger.info("[Boot] Initialising database…")
    init_database()

    # 2. Simulator (generate seed data if needed)
    logger.info("[Boot] Starting simulator…")
    simulator = ProcureIQSimulator(config)
    simulator.generate_all()

    # 3. Engine
    logger.info("[Boot] Initialising engine…")
    engine = ProcureIQEngine(config, simulator)

    # 4. Auto-start engine if configured
    if config.get("simulator",{}).get("enabled", True):
        logger.info("[Boot] Auto-starting engine in simulator mode…")
        engine.start()

    # 5. Flask dashboard
    logger.info("[Boot] Starting web dashboard…")
    app  = create_app(engine, simulator, config)
    host = config.get("dashboard",{}).get("host","0.0.0.0")
    port = config.get("dashboard",{}).get("port",5000)

    logger.info(f"[Boot] ✓ ProcureIQ running at http://{host}:{port}")
    logger.info(f"[Boot] ✓ API endpoints at  http://{host}:{port}/api/portfolio")
    logger.info("[Boot] Press Ctrl+C to stop")

    app.run(host=host, port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()
