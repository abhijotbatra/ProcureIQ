"""src/agents/risk_monitor.py — Risk Monitor Agent"""
import json, logging, os
import pandas as pd
from anthropic import Anthropic
from typing import List, Dict

logger   = logging.getLogger(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__),"..","..","data")

class RiskMonitorAgent:
    def __init__(self, config: dict):
        key=config.get("llm",{}).get("api_key","") or os.getenv("ANTHROPIC_API_KEY","")
        self.client=Anthropic(api_key=key)
        self.model=config.get("llm",{}).get("model","claude-sonnet-4-6")
        self.max_tok=config.get("llm",{}).get("max_tokens",1500)
        self.config=config

    def run(self, query:str, news_articles:List[Dict]) -> List[Dict]:
        logger.info("[RiskMonitor] Starting…")
        risky = self._load_risky_suppliers()
        bad   = [a for a in news_articles if a.get("severity") in ("critical","warning")]
        news_txt = "\n".join(f"- [{a.get('severity','?').upper()}] {a.get('headline','')} (Source: {a.get('source','')})" for a in bad) or "- No critical news today"
        prompt = f"""You are a supply chain risk analyst.
USER QUESTION: {query}

CRITICAL/WARNING NEWS:
{news_txt}

HIGH-RISK SUPPLIERS:
{json.dumps(risky, indent=2)}

Return a JSON array (max 6, critical first). Each object MUST have:
- supplier_name, risk_type (port_delay|financial|price_spike|weather|geopolitical), severity (critical|warning|ok), description, recommended_action, source
Return ONLY the JSON array."""
        try:
            resp=self.client.messages.create(model=self.model,max_tokens=self.max_tok,messages=[{"role":"user","content":prompt}])
            raw=resp.content[0].text.strip()
            if raw.startswith("```"): raw=raw.split("```")[1]; raw=raw[4:] if raw.startswith("json") else raw
            risks=json.loads(raw.strip())
            logger.info(f"[RiskMonitor] {len(risks)} risks found"); return risks
        except Exception as e:
            logger.error(f"[RiskMonitor] {e}"); return self._fallback()

    def _load_risky_suppliers(self):
        floor=self.config.get("suppliers",{}).get("risk_score_floor",60)
        bad_r=self.config.get("suppliers",{}).get("critical_ratings",["B-","C"])
        try:
            df=pd.read_excel(os.path.join(DATA_DIR,"suppliers.xlsx"))
            risky=df[(df["overall_score"]<floor)|(df["financial_rating"].isin(bad_r))|(df["last_incident"].isin(["financial_flag","quality_issue"]))]
            return risky[["supplier_name","category","overall_score","financial_rating","last_incident","country"]].head(10).to_dict("records")
        except:
            return [{"supplier_name":"VendorX Ltd.","category":"Packaging","overall_score":58,"financial_rating":"B-","last_incident":"financial_flag","country":"China"},
                    {"supplier_name":"PacificSource","category":"Logistics","overall_score":41,"financial_rating":"B-","last_incident":"late_delivery","country":"Vietnam"}]

    @staticmethod
    def _fallback():
        return [{"supplier_name":"Shanghai Port","risk_type":"port_delay","severity":"critical","description":"Port congestion causing 8-12 day delays on 14 SKUs","recommended_action":"Raise emergency PO within 48h","source":"Mock"},
                {"supplier_name":"VendorX Ltd.","risk_type":"financial","severity":"critical","description":"Credit rating downgraded BB-, payment delays detected","recommended_action":"Initiate backup supplier qualification","source":"Mock"},
                {"supplier_name":"Market","risk_type":"price_spike","severity":"warning","description":"Aluminium spot price +18% over 30 days","recommended_action":"Lock Q3 forward contract before Friday","source":"Mock"}]
