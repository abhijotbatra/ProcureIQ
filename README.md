# ProcureIQ — AI-Powered Supply Chain Intelligence System

A production-grade Python system that combines real-time news analysis,
LLM-powered risk detection, and multi-agent AI to give procurement teams
a plain-English action plan every morning.

---

## Features

### 1. News Aggregation & Analysis
- Fetches headlines from NewsAPI (Reuters, Economic Times, Moneycontrol, etc.)
- Extracts supplier mentions from each article automatically
- Deduplicates and stores in SQLite database
- Falls back to realistic mock data when no API key is set

### 2. LLM-Powered Sentiment Analysis
- Uses Claude (claude-sonnet-4-6) for advanced sentiment classification
- Classifies: sentiment / risk_type / severity / recommended_action
- Batch-processes all articles in a single API call (efficient)
- Generates consensus risk signal across all articles

### 3. Multi-Agent Architecture (5 Agents in Parallel)
- **Risk Monitor** — scans news + supplier DB for disruptions
- **Demand Forecast** — reads 12-week order history, predicts Q3 spikes
- **Inventory Analyst** — flags SKUs with stockout risk in 14 days
- **Supplier Scorer** — weekly KPI scorecard (on-time, quality, financial)
- **Cost Optimizer** — finds cheaper sourcing, bulk order, freight savings
- All 5 run **simultaneously** via `ThreadPoolExecutor` — ~4s total

### 4. RAG Synthesis
- Collects all agent outputs into one structured context
- Claude writes a plain-English Monday morning briefing
- Specific actions, timeframes, and financial impact
- The difference between a dashboard and an AI assistant

### 5. Data Simulator
- Generates 142 suppliers, 847 SKUs, 12-week order history
- Saves to Excel files (relatable for any BA/ops team)
- Force-seeds key story suppliers and critical SKUs
- Runs automatically on first startup

### 6. Web Dashboard (Flask)
- Real-time portfolio stats, risk signals, inventory health
- All 10 pages fully navigable and data-driven
- Responsive — works on desktop, tablet, and mobile
- Engine start/stop, manual analysis trigger, JSON export

---

## Project Structure

```
ProcureIQ/
├── config/
│   └── config.yaml              # All settings — edit this first
├── src/
│   ├── database.py              # SQLite: all 7 tables
│   ├── news/
│   │   └── aggregator.py        # NewsAPI + mock headlines
│   ├── analysis/
│   │   └── sentiment.py         # LLM batch sentiment classifier
│   ├── agents/
│   │   ├── engine.py            # Main orchestrator — start/stop/analyze
│   │   ├── risk_monitor.py      # Agent 1: disruption detection
│   │   ├── demand_forecast.py   # Agent 2: Q3 demand trends
│   │   ├── inventory_analyst.py # Agent 3: stockout risk scanner
│   │   ├── supplier_scorer.py   # Agent 4: KPI scorecard
│   │   ├── cost_optimizer.py    # Agent 5: savings finder
│   │   └── rag_synthesiser.py   # RAG: plain-English action plan
│   ├── simulator/
│   │   └── simulator.py         # Seed data generator + live stats
│   └── ui/
│       └── dashboard.py         # Flask app + all API endpoints
├── templates/
│   └── index.html               # Full dashboard UI (10 pages)
├── static/
│   ├── css/dashboard.css        # Complete responsive styles
│   └── js/dashboard.js          # All JS: navigation, charts, API calls
├── data/                        # Generated Excel files live here
├── logs/                        # Rotating log files
├── tests/
│   └── test_system.py           # 30 tests — all passing
├── main.py                      # Entry point
├── requirements.txt
└── .env.example
```

---

## Installation

### 1. Clone / unzip
```bash
cd ProcureIQ
```

### 2. Create virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API keys
```bash
cp .env.example .env
```
Edit `.env`:
```
ANTHROPIC_API_KEY=your_key_here     # Required for AI features
NEWS_API_KEY=your_key_here          # Optional — free tier at newsapi.org
```
Or edit `config/config.yaml` directly.

### 5. Run
```bash
python main.py
```

Open **http://localhost:5000**

---

## Usage

### Simulator Mode (default — no ERP needed)
```bash
python main.py
```
- Auto-generates 142 suppliers, 847 SKUs, 12-week order data
- Engine starts automatically
- Dashboard at http://localhost:5000

### Manual Analysis
Click **Run Analysis** in the dashboard, or POST to the API:
```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "Which suppliers are at risk this week?"}'
```

### Live ERP Mode
Edit `config/config.yaml`:
```yaml
erp:
  enabled: true
  provider: "sap"
  api_url: "https://your-erp.com/api"
  api_key: "your-erp-key"
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/portfolio` | Budget stats, critical alerts, savings |
| GET | `/api/positions` | Open inventory alerts (stockout risks) |
| GET | `/api/signals` | Active risk signals from agents |
| GET | `/api/trades` | Analysis run history |
| GET | `/api/performance` | Full performance report |
| GET | `/api/suppliers` | All 142 suppliers + scores |
| GET | `/api/inventory` | Inventory summary + chart data |
| GET | `/api/demand` | Weekly demand + forecasts |
| GET | `/api/news` | Recent news articles with sentiment |
| GET | `/api/costs` | Cost optimisation opportunities |
| GET | `/api/engine/status` | Engine running state |
| POST | `/api/engine/start` | Start the engine |
| POST | `/api/engine/stop` | Stop the engine |
| POST | `/api/analyze` | Trigger manual analysis |
| GET | `/api/export` | Export all data as JSON |

---

## Running Tests

```bash
pytest tests/ -v
```

30 tests covering: database, news aggregator, sentiment analyser,
all 5 agents, simulator, and all Flask API endpoints.

---

## How the Engine Works

```
User query (natural language)
        ↓
   FastAPI / Flask
        ↓
   News Aggregator → Sentiment Analyser
        ↓
   ThreadPoolExecutor (5 agents run simultaneously):
   ├── Risk Monitor     → supplier DB + news → SupplierRisk[]
   ├── Demand Forecast  → orders.xlsx trend  → DemandForecast[]
   ├── Inventory Analyst→ inventory.xlsx      → InventoryAlert[]
   ├── Supplier Scorer  → suppliers.xlsx KPI  → SupplierScore[]
   └── Cost Optimizer   → pricing APIs        → CostOpportunity[]
        ↓
   RAG Synthesiser (Claude)
        ↓
   Plain-English action plan + JSON response
```

---

## Tech Stack

| Layer | Tool |
|-------|------|
| AI Model | Claude claude-sonnet-4-6 (Anthropic) |
| Web Framework | Flask + Flask-CORS |
| Agent Orchestration | ThreadPoolExecutor (parallel) |
| Data Processing | Pandas + NumPy |
| Database | SQLite (zero config) |
| Scheduling | schedule library |
| Testing | pytest + unittest.mock |
| Seed Data | Excel (openpyxl) |

---

## Key Concepts Explained Simply

**Multi-agent = 5 specialists, not 1 generalist.**
Each agent has one job. The Risk Monitor only looks for disruptions.
The Cost Optimizer only looks for savings. Separation makes each one better.

**Parallel execution = speed.**
All 5 agents run at the same time via threads. Total time ~4s vs ~20s sequential.

**RAG = data → decision.**
"Retrieval" = agents retrieved real data. "Augmented" = we fed it to Claude.
"Generation" = Claude writes the action plan. This is what makes it an assistant, not just a dashboard.

**Fallback everywhere = reliability.**
Every agent has hardcoded fallback data. If the LLM API is down or returns bad JSON,
the system still returns a sensible result. Never crashes the dashboard.

---

## Disclaimer

This tool is for educational and portfolio purposes.

⚠️ Always test thoroughly before connecting to live ERP systems.
Never make real procurement decisions based solely on AI output.
Use proper risk management and human oversight.
