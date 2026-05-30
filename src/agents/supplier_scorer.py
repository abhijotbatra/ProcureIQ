"""src/agents/supplier_scorer.py — Supplier Scorer Agent"""
import json, logging, os
import pandas as pd
from anthropic import Anthropic
from typing import List, Dict

logger   = logging.getLogger(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__),"..","..","data")
FIN_MAP  = {"A+":100,"A":90,"B+":75,"B":65,"B-":45,"C":20}

class SupplierScorerAgent:
    def __init__(self, config: dict):
        key=config.get("llm",{}).get("api_key","") or os.getenv("ANTHROPIC_API_KEY","")
        self.client=Anthropic(api_key=key)
        self.model=config.get("llm",{}).get("model","claude-sonnet-4-6")
        self.max_tok=config.get("llm",{}).get("max_tokens",1500)

    def run(self, query:str) -> List[Dict]:
        logger.info("[SupplierScorer] Starting…")
        scored=self._score_all()
        prompt=f"""You are a supplier relationship manager.
USER QUESTION: {query}
SUPPLIER SCORES: {json.dumps(scored, indent=2)}

Return JSON array. Each object MUST have:
- supplier_name, category, overall_score (int), on_time_rate (float), quality_rate (float), financial_rating, trend (improving|stable|declining), recommended_action (renew|monitor|qualify_backup|replace)
Return ONLY the JSON array."""
        try:
            resp=self.client.messages.create(model=self.model,max_tokens=self.max_tok,messages=[{"role":"user","content":prompt}])
            raw=resp.content[0].text.strip()
            if raw.startswith("```"): raw=raw.split("```")[1]; raw=raw[4:] if raw.startswith("json") else raw
            s=json.loads(raw.strip()); logger.info(f"[SupplierScorer] {len(s)} scored"); return s
        except Exception as e:
            logger.error(f"[SupplierScorer] {e}"); return self._fallback()

    def _score_all(self):
        try:
            df=pd.read_excel(os.path.join(DATA_DIR,"suppliers.xlsx"))
            df["fin_num"]=df["financial_rating"].map(FIN_MAP).fillna(50)
            df["computed"]=(df["on_time_rate"]*0.40+df["quality_rate"]*0.30+df["fin_num"]*0.20+70*0.10).round(1)
            df["trend"]=df.apply(lambda r:"improving" if r["computed"]>r["overall_score"]+3 else "declining" if r["computed"]<r["overall_score"]-3 else "stable",axis=1)
            df["recommended_action"]=df["computed"].apply(lambda s:"renew" if s>=88 else "monitor" if s>=70 else "qualify_backup" if s>=55 else "replace")
            focus=pd.concat([df.nlargest(5,"computed"),df.nsmallest(5,"computed")]).drop_duplicates()
            return focus[["supplier_name","category","computed","on_time_rate","quality_rate","financial_rating","trend","recommended_action"]].rename(columns={"computed":"overall_score"}).to_dict("records")
        except: return self._fallback()

    @staticmethod
    def _fallback():
        return [{"supplier_name":"AsiaTech Co.","category":"Electronics","overall_score":94,"on_time_rate":97.0,"quality_rate":99.0,"financial_rating":"A+","trend":"stable","recommended_action":"renew"},
                {"supplier_name":"EuroMaterials","category":"Raw Materials","overall_score":81,"on_time_rate":88.0,"quality_rate":94.0,"financial_rating":"A","trend":"improving","recommended_action":"monitor"},
                {"supplier_name":"VendorX Ltd.","category":"Packaging","overall_score":58,"on_time_rate":71.0,"quality_rate":88.0,"financial_rating":"B-","trend":"declining","recommended_action":"qualify_backup"},
                {"supplier_name":"PacificSource","category":"Logistics","overall_score":41,"on_time_rate":64.0,"quality_rate":79.0,"financial_rating":"B-","trend":"declining","recommended_action":"replace"}]
