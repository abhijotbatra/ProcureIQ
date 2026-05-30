"""src/agents/cost_optimizer.py — Cost Optimizer Agent"""
import json, logging, os
import pandas as pd, numpy as np
from anthropic import Anthropic
from typing import List, Dict

logger   = logging.getLogger(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__),"..","..","data")

class CostOptimizerAgent:
    def __init__(self, config: dict):
        key=config.get("llm",{}).get("api_key","") or os.getenv("ANTHROPIC_API_KEY","")
        self.client=Anthropic(api_key=key)
        self.model=config.get("llm",{}).get("model","claude-sonnet-4-6")
        self.max_tok=config.get("llm",{}).get("max_tokens",1500)

    def run(self, query:str) -> List[Dict]:
        logger.info("[CostOptimizer] Starting…")
        raw=self._find_opportunities()
        prompt=f"""You are a procurement cost analyst.
USER QUESTION: {query}
OPPORTUNITIES: {json.dumps(raw, indent=2)}

Return JSON array sorted by saving_amount DESC. Each object MUST have:
- opportunity_type (supplier_swap|bulk_order|freight_consolidation|commodity_hedge), description, current_cost_annual (float), optimised_cost_annual (float), saving_amount (float), saving_pct (float), action_required, deadline (ISO date or null)
Return ONLY the JSON array."""
        try:
            resp=self.client.messages.create(model=self.model,max_tokens=self.max_tok,messages=[{"role":"user","content":prompt}])
            raw_t=resp.content[0].text.strip()
            if raw_t.startswith("```"): raw_t=raw_t.split("```")[1]; raw_t=raw_t[4:] if raw_t.startswith("json") else raw_t
            o=json.loads(raw_t.strip()); total=sum(x.get("saving_amount",0) for x in o)
            logger.info(f"[CostOptimizer] {len(o)} opportunities · ${total:,.0f}"); return o
        except Exception as e:
            logger.error(f"[CostOptimizer] {e}"); return self._fallback()

    def _find_opportunities(self):
        try:
            df=pd.read_excel(os.path.join(DATA_DIR,"suppliers.xlsx"))
            risky=df[(df["overall_score"]<70)&(df["annual_spend"]>100000)].sort_values("annual_spend",ascending=False)
            opps=[]
            for _,row in risky.head(2).iterrows():
                curr=float(row["annual_spend"]); p=0.20+0.17*(1-row["overall_score"]/100); opt=curr*(1-p)
                opps.append({"type":"supplier_swap","current_supplier":row["supplier_name"],"category":row["category"],"current_cost":round(curr,2),"saving":round(curr-opt,2),"saving_pct":round(p*100,1)})
            return opps or self._fallback_raw()
        except: return self._fallback_raw()

    @staticmethod
    def _fallback_raw():
        return [{"type":"supplier_swap","description":"VendorX→PackagePro","current_cost":112000,"saving":42000,"saving_pct":37.5,"deadline":"2025-08-01"},
                {"type":"freight_consolidation","description":"Merge Routes 4+7","current_cost":85000,"saving":21000,"saving_pct":24.7,"deadline":None},
                {"type":"bulk_order","description":"Advance order SKU-001","current_cost":95000,"saving":14000,"saving_pct":14.7,"deadline":"2025-07-15"},
                {"type":"commodity_hedge","description":"Lock Q3 aluminium contract","current_cost":58000,"saving":7000,"saving_pct":12.1,"deadline":"2025-06-27"}]

    @staticmethod
    def _fallback():
        return [{"opportunity_type":"supplier_swap","description":"Replace VendorX with PackagePro — 37% cheaper same spec","current_cost_annual":112000,"optimised_cost_annual":70000,"saving_amount":42000,"saving_pct":37.5,"action_required":"Contact PackagePro for qualification","deadline":"2025-08-01"},
                {"opportunity_type":"freight_consolidation","description":"Merge Routes 4 & 7 into single bi-weekly shipment","current_cost_annual":85000,"optimised_cost_annual":64000,"saving_amount":21000,"saving_pct":24.7,"action_required":"Request logistics review meeting","deadline":None},
                {"opportunity_type":"bulk_order","description":"Advance bulk order SKU-001 before Q3 demand spike","current_cost_annual":95000,"optimised_cost_annual":81000,"saving_amount":14000,"saving_pct":14.7,"action_required":"Raise advance PO by July 15","deadline":"2025-07-15"},
                {"opportunity_type":"commodity_hedge","description":"Lock Q3 aluminium forward contract with EuroMaterials","current_cost_annual":58000,"optimised_cost_annual":51000,"saving_amount":7000,"saving_pct":12.1,"action_required":"Contact EuroMaterials for forward pricing","deadline":"2025-06-27"}]
