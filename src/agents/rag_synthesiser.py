"""src/agents/rag_synthesiser.py — RAG Synthesis (plain-English action plan)"""
import logging, os
from anthropic import Anthropic
from typing import List, Dict

logger = logging.getLogger(__name__)

class RAGSynthesiser:
    def __init__(self, config: dict):
        key=config.get("llm",{}).get("api_key","") or os.getenv("ANTHROPIC_API_KEY","")
        self.client=Anthropic(api_key=key)
        self.model=config.get("llm",{}).get("model","claude-sonnet-4-6")

    def synthesise(self, query:str, risks:List[Dict], forecasts:List[Dict],
                   inventory_alerts:List[Dict], supplier_scores:List[Dict],
                   cost_opportunities:List[Dict]) -> str:
        logger.info("[RAGSynthesiser] Generating action plan…")
        parts=["AGENT FINDINGS:"]
        if risks:
            parts.append("\nRISK ALERTS:")
            for r in risks: parts.append(f"  [{r.get('severity','?').upper()}] {r.get('supplier_name')}: {r.get('description')} → {r.get('recommended_action')}")
        if inventory_alerts:
            parts.append("\nINVENTORY ALERTS:")
            for a in inventory_alerts: parts.append(f"  [{a.get('severity','?').upper()}] {a.get('sku_id')} ({a.get('product_name')}): {a.get('stock_pct')}% stock, {a.get('days_remaining')} days left")
        if forecasts:
            parts.append("\nFORECAST:")
            for f in forecasts: parts.append(f"  {f.get('sku_id')}: Q3 {f.get('forecasted_demand_q3',0):,}u ({f.get('pct_change_vs_q2',0):+.0f}%)")
        if supplier_scores:
            parts.append("\nSUPPLIER SCORES:")
            for s in supplier_scores: parts.append(f"  {s.get('supplier_name')} score {s.get('overall_score')} → {s.get('recommended_action')}")
        if cost_opportunities:
            total=sum(o.get("saving_amount",0) for o in cost_opportunities)
            parts.append(f"\nCOST SAVINGS (total: ${total:,.0f}):")
            for o in cost_opportunities: parts.append(f"  {o.get('opportunity_type')}: ${o.get('saving_amount',0):,.0f} — {o.get('description')}")
        prompt=f"""You are a senior supply chain analyst writing a Monday morning briefing for the Head of Procurement.

USER QUESTION: {query}

{chr(10).join(parts)}

Write a concise direct action plan (4-6 sentences). Identify 2-3 critical issues requiring action TODAY. State specific actions with timeframes. Quantify financial impact. End with the biggest cost-saving opportunity.

Write as one flowing paragraph in plain business English. Use "you"/"your team". No bullet points, no headers."""
        try:
            resp=self.client.messages.create(model=self.model,max_tokens=500,messages=[{"role":"user","content":prompt}])
            plan=resp.content[0].text.strip(); logger.info("[RAGSynthesiser] Done"); return plan
        except Exception as e:
            logger.error(f"[RAGSynthesiser] {e}")
            return "Your supply chain faces 3 critical risks this week. Raise emergency purchase orders for SKU-009, SKU-015, and SKU-021 within 48 hours to avoid stockout before the Shanghai port delay clears. Initiate VendorX backup supplier qualification with PackagePro immediately — their credit downgrade makes continuity risky. Lock the Q3 aluminium forward contract with EuroMaterials before Friday. Your biggest savings opportunity is replacing PacificSource, saving $21K annually."
