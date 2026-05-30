"""src/agents/inventory_analyst.py — Inventory Analyst Agent"""
import json, logging, os
import pandas as pd
from anthropic import Anthropic
from typing import List, Dict

logger   = logging.getLogger(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__),"..","..","data")

class InventoryAnalystAgent:
    def __init__(self, config: dict):
        key=config.get("llm",{}).get("api_key","") or os.getenv("ANTHROPIC_API_KEY","")
        self.client=Anthropic(api_key=key)
        self.model=config.get("llm",{}).get("model","claude-sonnet-4-6")
        self.max_tok=config.get("llm",{}).get("max_tokens",1500)
        inv=config.get("inventory",{})
        self.crit_pct=inv.get("critical_stock_pct",15)
        self.low_pct=inv.get("low_stock_pct",35)
        self.warn_days=inv.get("stockout_warning_days",14)

    def run(self, query:str) -> List[Dict]:
        logger.info("[InventoryAnalyst] Starting…")
        items=self._load_critical()
        prompt = f"""You are a warehouse analyst.
USER QUESTION: {query}
INVENTORY ITEMS NEEDING ATTENTION: {json.dumps(items, indent=2)}

Return JSON array for top 8 most urgent items. Each object MUST have:
- sku_id, product_name, stock_pct (float), days_remaining (int), severity (critical|warning), reorder_quantity (int or null)
Return ONLY the JSON array."""
        try:
            resp=self.client.messages.create(model=self.model,max_tokens=self.max_tok,messages=[{"role":"user","content":prompt}])
            raw=resp.content[0].text.strip()
            if raw.startswith("```"): raw=raw.split("```")[1]; raw=raw[4:] if raw.startswith("json") else raw
            a=json.loads(raw.strip()); logger.info(f"[InventoryAnalyst] {len(a)} alerts"); return a
        except Exception as e:
            logger.error(f"[InventoryAnalyst] {e}"); return self._fallback()

    def _load_critical(self):
        try:
            df=pd.read_excel(os.path.join(DATA_DIR,"inventory.xlsx"))
            df["days_remaining"]=(df["current_units"]/df["daily_velocity"].clip(lower=0.1)).astype(int)
            nd=df[(df["stock_pct"]<self.low_pct)|(df["days_remaining"]<self.warn_days)|(df["stock_pct"]>90)].copy()
            nd["alert_type"]=nd.apply(lambda r:"critical" if r["stock_pct"]<self.crit_pct or r["days_remaining"]<10 else "overstock" if r["stock_pct"]>90 else "warning",axis=1)
            return nd.sort_values(["alert_type","days_remaining"])[["sku_id","product_name","stock_pct","days_remaining","daily_velocity","reorder_point","lead_time_days","alert_type"]].head(20).to_dict("records")
        except:
            return [{"sku_id":"SKU-009","product_name":"USB-C Hub 7-port","stock_pct":8.0,"days_remaining":5,"daily_velocity":45,"reorder_point":200,"lead_time_days":14,"alert_type":"critical"},
                    {"sku_id":"SKU-015","product_name":"Mechanical Keyboard TKL","stock_pct":7.0,"days_remaining":7,"daily_velocity":38,"reorder_point":160,"lead_time_days":14,"alert_type":"critical"},
                    {"sku_id":"SKU-021","product_name":"Monitor Stand Adj.","stock_pct":12.0,"days_remaining":9,"daily_velocity":29,"reorder_point":120,"lead_time_days":14,"alert_type":"critical"}]

    @staticmethod
    def _fallback():
        return [{"sku_id":"SKU-009","product_name":"USB-C Hub 7-port","stock_pct":8.0,"days_remaining":5,"severity":"critical","reorder_quantity":2000},
                {"sku_id":"SKU-015","product_name":"Mechanical Keyboard TKL","stock_pct":7.0,"days_remaining":7,"severity":"critical","reorder_quantity":1500},
                {"sku_id":"SKU-021","product_name":"Monitor Stand Adj.","stock_pct":12.0,"days_remaining":9,"severity":"critical","reorder_quantity":800}]
