"""
tests/test_system.py
--------------------
25+ tests covering every layer of ProcureIQ.
Run: pytest tests/ -v
"""
import json, sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__),".."))
from unittest.mock import MagicMock, patch

# ── Fixtures ──────────────────────────────────────────────────────────────────

MOCK_CFG = {
    "llm":       {"model":"claude-sonnet-4-6","api_key":"test","max_tokens":1500},
    "inventory": {"critical_stock_pct":15,"low_stock_pct":35,"overstock_pct":90,"stockout_warning_days":14},
    "suppliers": {"risk_score_floor":60,"critical_ratings":["B-","C"]},
    "simulator": {"num_suppliers":5,"num_skus":10,"initial_budget_usd":1200000,
                  "warehouse_names":["Mumbai","Delhi"]},
    "news":      {"api_key":"","max_articles":5,"keywords":["supply chain"]},
    "dashboard": {"host":"0.0.0.0","port":5000},
    "logging":   {"level":"INFO","file":"logs/test.log"},
}

def mock_claude(text):
    m = MagicMock()
    m.content = [MagicMock(text=text)]
    return m

# ── Database tests ─────────────────────────────────────────────────────────────

class TestDatabase:
    def test_init_creates_tables(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.database.DB_PATH", str(tmp_path/"test.db"))
        from src.database import init_database, get_db
        init_database()
        with get_db() as c:
            tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "suppliers" in tables
        assert "inventory" in tables
        assert "news_articles" in tables
        assert "risk_alerts" in tables
        assert "analysis_runs" in tables

    def test_save_and_get_news(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.database.DB_PATH", str(tmp_path/"t.db"))
        from src.database import init_database, save_news_article, get_recent_news
        init_database()
        save_news_article({"headline":"Test headline","source":"Reuters","severity":"critical","risk_type":"port_delay"})
        news = get_recent_news()
        assert len(news) == 1
        assert news[0]["headline"] == "Test headline"

    def test_duplicate_news_ignored(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.database.DB_PATH", str(tmp_path/"t2.db"))
        from src.database import init_database, save_news_article, get_recent_news
        init_database()
        a = {"headline":"Same headline","source":"X","severity":"ok","risk_type":"none"}
        save_news_article(a); save_news_article(a)
        assert len(get_recent_news()) == 1

    def test_save_analysis_run(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.database.DB_PATH", str(tmp_path/"t3.db"))
        from src.database import init_database, save_analysis_run, get_analysis_history
        init_database()
        save_analysis_run("s1","test query",{"risks":[],"inventory_alerts":[],"action_plan":"Test","total_savings_found":1000,"critical_count":2},1.5)
        h = get_analysis_history()
        assert len(h) == 1
        assert h[0]["savings_found"] == 1000

    def test_get_active_alerts_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.database.DB_PATH", str(tmp_path/"t4.db"))
        from src.database import init_database, get_active_alerts
        init_database()
        assert get_active_alerts() == []

# ── News Aggregator tests ──────────────────────────────────────────────────────

class TestNewsAggregator:
    def test_mock_headlines_returned_without_key(self):
        from src.news.aggregator import NewsAggregator
        agg = NewsAggregator({"news":{"api_key":"","max_articles":5}})
        articles = agg.fetch_latest()
        assert len(articles) > 0
        assert "headline" in articles[0]

    def test_supplier_enrichment(self):
        from src.news.aggregator import NewsAggregator
        agg = NewsAggregator(MOCK_CFG)
        articles = agg._enrich([{"headline":"VendorX Ltd faces bankruptcy risk","related_suppliers":[]}])
        assert "VendorX Ltd." in articles[0]["related_suppliers"]

    def test_deduplication(self):
        from src.news.aggregator import NewsAggregator
        agg = NewsAggregator(MOCK_CFG)
        raw = [{"headline":"Same news headline","source":"X","url":"","published_at":"","related_suppliers":[]},
               {"headline":"Same news headline","source":"Y","url":"","published_at":"","related_suppliers":[]}]
        result = agg._enrich(raw)
        assert len(result) == 2  # enrichment doesn't dedup — that's in fetch_latest

    def test_asiatech_keyword_match(self):
        from src.news.aggregator import NewsAggregator
        agg = NewsAggregator(MOCK_CFG)
        articles = agg._enrich([{"headline":"AsiaTech Co reports strong Q2 results","related_suppliers":[]}])
        assert "AsiaTech Co." in articles[0]["related_suppliers"]

# ── Sentiment Analyser tests ───────────────────────────────────────────────────

class TestSentimentAnalyser:
    def test_analyse_batch_returns_enriched(self):
        from src.analysis.sentiment import SentimentAnalyser
        sa = SentimentAnalyser(MOCK_CFG)
        articles = [{"headline":"Port congestion causes major delays","source":"Reuters","related_suppliers":[]}]
        mock_resp = mock_claude(json.dumps([{"index":1,"sentiment":"negative","risk_type":"port_delay","severity":"critical","summary":"Port delay","recommended_action":"Raise emergency PO"}]))
        with patch.object(sa.client.messages,"create",return_value=mock_resp):
            result = sa.analyse_batch(articles)
        assert result[0]["severity"] == "critical"
        assert result[0]["risk_type"] == "port_delay"

    def test_fallback_on_bad_json(self):
        from src.analysis.sentiment import SentimentAnalyser
        sa = SentimentAnalyser(MOCK_CFG)
        articles = [{"headline":"Test","source":"X","related_suppliers":[]}]
        with patch.object(sa.client.messages,"create",return_value=mock_claude("not json")):
            result = sa.analyse_batch(articles)
        assert result[0]["sentiment"] == "neutral"

    def test_consensus_critical(self):
        from src.analysis.sentiment import SentimentAnalyser
        sa = SentimentAnalyser(MOCK_CFG)
        articles = [{"severity":"critical"},{"severity":"warning"},{"severity":"ok"}]
        c = sa.generate_consensus(articles)
        assert c["severity"] == "critical"
        assert c["critical_count"] == 1

    def test_consensus_empty(self):
        from src.analysis.sentiment import SentimentAnalyser
        sa = SentimentAnalyser(MOCK_CFG)
        c = sa.generate_consensus([])
        assert c["severity"] == "ok"

# ── Agent tests ────────────────────────────────────────────────────────────────

class TestRiskMonitorAgent:
    def test_returns_list_on_success(self):
        from src.agents.risk_monitor import RiskMonitorAgent
        agent = RiskMonitorAgent(MOCK_CFG)
        resp = mock_claude(json.dumps([{"supplier_name":"TestCo","risk_type":"financial","severity":"critical","description":"Test","recommended_action":"Act","source":"test"}]))
        with patch.object(agent.client.messages,"create",return_value=resp):
            result = agent.run("test query", [])
        assert isinstance(result, list)
        assert result[0]["severity"] == "critical"

    def test_fallback_on_bad_json(self):
        from src.agents.risk_monitor import RiskMonitorAgent
        agent = RiskMonitorAgent(MOCK_CFG)
        with patch.object(agent.client.messages,"create",return_value=mock_claude("garbage")):
            result = agent.run("test", [])
        assert len(result) > 0

class TestInventoryAnalystAgent:
    def test_returns_alerts(self):
        from src.agents.inventory_analyst import InventoryAnalystAgent
        agent = InventoryAnalystAgent(MOCK_CFG)
        resp = mock_claude(json.dumps([{"sku_id":"SKU-001","product_name":"Test","stock_pct":8.0,"days_remaining":5,"severity":"critical","reorder_quantity":1000}]))
        with patch.object(agent.client.messages,"create",return_value=resp):
            result = agent.run("test")
        assert result[0]["severity"] == "critical"

    def test_fallback_data(self):
        from src.agents.inventory_analyst import InventoryAnalystAgent
        agent = InventoryAnalystAgent(MOCK_CFG)
        with patch.object(agent.client.messages,"create",return_value=mock_claude("bad")):
            result = agent.run("test")
        assert len(result) >= 3

class TestCostOptimizerAgent:
    def test_returns_opportunities(self):
        from src.agents.cost_optimizer import CostOptimizerAgent
        agent = CostOptimizerAgent(MOCK_CFG)
        resp = mock_claude(json.dumps([{"opportunity_type":"supplier_swap","description":"Test swap","current_cost_annual":100000,"optimised_cost_annual":70000,"saving_amount":30000,"saving_pct":30.0,"action_required":"Contact","deadline":None}]))
        with patch.object(agent.client.messages,"create",return_value=resp):
            result = agent.run("test")
        assert result[0]["saving_amount"] == 30000

    def test_savings_positive(self):
        from src.agents.cost_optimizer import CostOptimizerAgent
        agent = CostOptimizerAgent(MOCK_CFG)
        with patch.object(agent.client.messages,"create",return_value=mock_claude("bad")):
            result = agent.run("test")
        for o in result:
            assert o.get("saving_amount",0) > 0

class TestSupplierScorerAgent:
    def test_scores_in_range(self):
        from src.agents.supplier_scorer import SupplierScorerAgent
        agent = SupplierScorerAgent(MOCK_CFG)
        resp = mock_claude(json.dumps([{"supplier_name":"TestCo","category":"Electronics","overall_score":85,"on_time_rate":90.0,"quality_rate":95.0,"financial_rating":"A","trend":"stable","recommended_action":"renew"}]))
        with patch.object(agent.client.messages,"create",return_value=resp):
            result = agent.run("test")
        for s in result:
            assert 0 <= s.get("overall_score",0) <= 100

# ── Simulator tests ────────────────────────────────────────────────────────────

class TestSimulator:
    def test_generate_all_creates_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.simulator.simulator.DATA_DIR", str(tmp_path))
        from src.simulator.simulator import ProcureIQSimulator
        sim = ProcureIQSimulator({"simulator":{"num_suppliers":10,"num_skus":20,"initial_budget_usd":1000000,"warehouse_names":["Mumbai"]}})
        sim.generate_all(force=True)
        assert os.path.exists(str(tmp_path/"suppliers.xlsx"))
        assert os.path.exists(str(tmp_path/"inventory.xlsx"))
        assert os.path.exists(str(tmp_path/"orders.xlsx"))

    def test_stats_update_after_analysis(self):
        from src.simulator.simulator import ProcureIQSimulator
        sim = ProcureIQSimulator(MOCK_CFG)
        sim.update_after_analysis({"total_savings_found":50000,"critical_count":2})
        stats = sim.get_stats()
        assert stats["savings_found"] == 50000
        assert stats["critical_count"] == 2
        assert stats["agent_runs_today"] == 1

    def test_set_engine_running(self):
        from src.simulator.simulator import ProcureIQSimulator
        sim = ProcureIQSimulator(MOCK_CFG)
        sim.set_engine_running(True)
        assert sim.get_stats()["engine_running"] == True

# ── Flask API tests ────────────────────────────────────────────────────────────

class TestFlaskAPI:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.database.DB_PATH", str(tmp_path/"t.db"))
        from src.database import init_database
        init_database()
        from src.simulator.simulator import ProcureIQSimulator
        from src.agents.engine import ProcureIQEngine
        from src.ui.dashboard import create_app
        sim = ProcureIQSimulator(MOCK_CFG)
        eng = ProcureIQEngine(MOCK_CFG, sim)
        app = create_app(eng, sim, MOCK_CFG)
        app.config["TESTING"] = True
        return app.test_client()

    def test_portfolio_returns_200(self, client):
        r = client.get("/api/portfolio")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "suppliers_tracked" in data

    def test_signals_returns_200(self, client):
        r = client.get("/api/signals")
        assert r.status_code == 200

    def test_positions_returns_200(self, client):
        r = client.get("/api/positions")
        assert r.status_code == 200

    def test_engine_status(self, client):
        r = client.get("/api/engine/status")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "running" in data

    def test_engine_start_stop(self, client):
        r = client.post("/api/engine/start")
        assert r.status_code == 200
        r2 = client.post("/api/engine/stop")
        assert r2.status_code == 200

    def test_export_returns_json(self, client):
        r = client.get("/api/export")
        assert r.status_code == 200
        assert b"exported_at" in r.data

    def test_index_returns_html(self, client):
        r = client.get("/")
        assert r.status_code == 200
