"""
src/agents/engine.py — Main Orchestration Engine
Mirrors SmartTrader's engine.py: start/stop/analyze/status.
Runs all 5 agents in parallel via ThreadPoolExecutor.
Schedules automatic hourly runs.
"""
import logging, threading, time, schedule
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional

from src.news.aggregator         import NewsAggregator
from src.analysis.sentiment      import SentimentAnalyser
from src.agents.risk_monitor     import RiskMonitorAgent
from src.agents.demand_forecast  import DemandForecastAgent
from src.agents.inventory_analyst import InventoryAnalystAgent
from src.agents.supplier_scorer  import SupplierScorerAgent
from src.agents.cost_optimizer   import CostOptimizerAgent
from src.agents.rag_synthesiser  import RAGSynthesiser
from src.database import save_analysis_run, save_news_article, save_risk_alert, save_cost_opportunity

logger = logging.getLogger(__name__)

class ProcureIQEngine:
    def __init__(self, config: dict, simulator):
        self.config    = config
        self.simulator = simulator
        self.news_agg  = NewsAggregator(config)
        self.sentiment = SentimentAnalyser(config)
        self.agents    = {
            "risk":      RiskMonitorAgent(config),
            "forecast":  DemandForecastAgent(config),
            "inventory": InventoryAnalystAgent(config),
            "scorer":    SupplierScorerAgent(config),
            "cost":      CostOptimizerAgent(config),
        }
        self.rag         = RAGSynthesiser(config)
        self._running    = False
        self._thread     = None
        self._last_result= None
        self._run_count  = 0
        self._start_time = None
        self._lock       = threading.Lock()
        self.default_q   = "What are the most critical supply chain risks and actions needed this week?"

    # ── public ──────────────────────────────────────────────────────────────
    def start(self):
        if self._running: return
        self._running=True; self._start_time=datetime.now()
        self.simulator.set_engine_running(True)
        self._thread=threading.Thread(target=self._run_loop,daemon=True)
        self._thread.start()
        logger.info("[Engine] ✓ Started")

    def stop(self):
        self._running=False; self.simulator.set_engine_running(False)
        schedule.clear(); logger.info("[Engine] Stopped")

    def analyze(self, query:Optional[str]=None) -> Dict[str,Any]:
        query=query or self.default_q
        logger.info(f"[Engine] Manual run: '{query}'")
        return self._run_analysis(query)

    def status(self) -> Dict[str,Any]:
        stats=self.simulator.get_stats()
        return {"running":self._running,"run_count":self._run_count,
                "start_time":self._start_time.isoformat() if self._start_time else None,
                "agent_count":len(self.agents),"agents":list(self.agents.keys()),**stats}

    def last_result(self) -> Optional[Dict]:
        return self._last_result

    # ── internal ─────────────────────────────────────────────────────────────
    def _run_loop(self):
        try: self._run_analysis(self.default_q)
        except Exception as e: logger.error(f"[Engine] Initial run failed: {e}")
        interval=self.config.get("news",{}).get("refresh_interval_minutes",60)
        schedule.every(interval).minutes.do(lambda:self._run_analysis(self.default_q))
        while self._running: schedule.run_pending(); time.sleep(30)

    def _run_analysis(self, query:str) -> Dict[str,Any]:
        t0=time.time(); sid=f"run_{int(t0)}"
        logger.info("[Engine] === Analysis cycle start ===")

        # Step 1: news
        try:
            raw=self.news_agg.fetch_latest(); articles=self.sentiment.analyse_batch(raw)
            for a in articles:
                try: save_news_article(a)
                except: pass
            logger.info(f"[Engine] News: {len(articles)} articles")
        except Exception as e:
            logger.error(f"[Engine] News failed: {e}"); articles=[]

        # Step 2: 5 agents in parallel
        agent_calls={"risk":lambda:self.agents["risk"].run(query,articles),
                     "forecast":lambda:self.agents["forecast"].run(query),
                     "inventory":lambda:self.agents["inventory"].run(query),
                     "scorer":lambda:self.agents["scorer"].run(query),
                     "cost":lambda:self.agents["cost"].run(query)}
        results={}
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures={pool.submit(fn):name for name,fn in agent_calls.items()}
            for future in as_completed(futures,timeout=60):
                name=futures[future]
                try: results[name]=future.result(); logger.info(f"[Engine] Agent '{name}' ✓")
                except Exception as e: logger.error(f"[Engine] Agent '{name}' failed: {e}"); results[name]=[]

        risks=results.get("risk",[]); forecasts=results.get("forecast",[])
        inv=results.get("inventory",[]); scores=results.get("scorer",[]); costs=results.get("cost",[])

        # Step 3: RAG
        try: plan=self.rag.synthesise(query,risks,forecasts,inv,scores,costs)
        except Exception as e: logger.error(f"[Engine] RAG failed: {e}"); plan="Analysis complete."

        # Step 4: persist
        for r in risks:
            try: save_risk_alert(r)
            except: pass
        for o in costs:
            try: save_cost_opportunity(o)
            except: pass

        # Step 5: assemble
        total_sav=sum(o.get("saving_amount",0) for o in costs)
        crit=sum(1 for r in risks if r.get("severity")=="critical")+sum(1 for a in inv if a.get("severity")=="critical")
        elapsed=round(time.time()-t0,2)
        result={"session_id":sid,"query":query,"action_plan":plan,
                "risks":risks,"forecasts":forecasts,"inventory_alerts":inv,
                "supplier_scores":scores,"cost_opportunities":costs,
                "total_savings_found":total_sav,"critical_count":crit,
                "processing_time_seconds":elapsed,"timestamp":datetime.now().isoformat()}
        try: save_analysis_run(sid,query,result,elapsed)
        except: pass
        self.simulator.update_after_analysis(result)
        with self._lock: self._last_result=result; self._run_count+=1
        logger.info(f"[Engine] === Done in {elapsed}s | Critical:{crit} | Savings:${total_sav:,.0f} ===")
        return result
