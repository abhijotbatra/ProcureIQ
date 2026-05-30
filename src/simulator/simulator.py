"""
src/simulator/simulator.py — Data Simulator
Generates 142 suppliers, 847 SKUs, 12-week orders into Excel files.
Tracks live dashboard stats in memory.
"""
import os, logging, numpy as np, pandas as pd
from datetime import datetime, timedelta

logger   = logging.getLogger(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__),"..","..","data")

class ProcureIQSimulator:
    def __init__(self, config: dict):
        s = config.get("simulator",{})
        self.n_sup  = s.get("num_suppliers",142)
        self.n_sku  = s.get("num_skus",847)
        self.budget = s.get("initial_budget_usd",1_200_000)
        self.whs    = s.get("warehouse_names",["Mumbai","Delhi","Bengaluru","Chennai","Pune","Hyderabad"])
        self._stats = {"total_budget":self.budget,"current_budget":self.budget,
                       "savings_found":84000,"critical_alerts":3,"critical_count":3,"warning_alerts":7,
                       "suppliers_tracked":self.n_sup,"skus_monitored":self.n_sku,
                       "stockout_risk_14d":9,"agent_runs_today":0,
                       "last_analysis":None,"engine_running":False}
        os.makedirs(DATA_DIR, exist_ok=True)

    def generate_all(self, force=False):
        files = ["suppliers.xlsx","inventory.xlsx","orders.xlsx"]
        if not force and all(os.path.exists(os.path.join(DATA_DIR,f)) for f in files):
            logger.info("[Sim] Data files exist — skipping"); return
        logger.info("[Sim] Generating seed data…")
        np.random.seed(42)
        self._gen_suppliers(); self._gen_inventory(); self._gen_orders()
        logger.info("[Sim] ✓ All seed data ready")

    def _gen_suppliers(self):
        cats = ["Electronics","Packaging","Logistics","Raw Materials","Components","Services"]
        rows = []
        for i in range(1, self.n_sup+1):
            sc = int(np.random.randint(30,99)); cat = cats[i%len(cats)]
            rows.append({"supplier_id":f"SUP-{i:03d}","supplier_name":f"Supplier_{i:03d} Ltd",
                "category":cat,"overall_score":sc,
                "on_time_rate":round(float(np.clip(sc+np.random.randint(-10,10),30,99)),1),
                "quality_rate":round(float(np.clip(sc+np.random.randint(-5,8),40,99)),1),
                "financial_rating":"A+" if sc>90 else "A" if sc>80 else "B+" if sc>70 else "B" if sc>60 else "B-" if sc>50 else "C",
                "country":np.random.choice(["China","Germany","India","USA","Vietnam","Malaysia"]),
                "annual_spend":int(np.random.randint(50000,2000000)),
                "contract_expiry":(datetime.now()+timedelta(days=int(np.random.randint(30,730)))).strftime("%Y-%m-%d"),
                "last_incident":np.random.choice(["none","late_delivery","quality_issue","financial_flag"])})
        for idx,name,cat,sc,otr,qr,fin,country,inc in [
            (0,"AsiaTech Co.","Electronics",94,97.0,99.0,"A+","India","none"),
            (1,"EuroMaterials","Raw Materials",81,88.0,94.0,"A","Germany","none"),
            (2,"VendorX Ltd.","Packaging",58,71.0,88.0,"B-","China","financial_flag"),
            (3,"PacificSource","Logistics",41,64.0,79.0,"B-","Vietnam","late_delivery"),
            (4,"GlobalParts Inc.","Components",76,82.0,91.0,"B+","China","none")]:
            rows[idx].update({"supplier_name":name,"category":cat,"overall_score":sc,
                "on_time_rate":otr,"quality_rate":qr,"financial_rating":fin,
                "country":country,"last_incident":inc})
        pd.DataFrame(rows).to_excel(os.path.join(DATA_DIR,"suppliers.xlsx"),index=False)
        logger.info(f"[Sim] ✓ suppliers.xlsx — {len(rows)} rows")

    def _gen_inventory(self):
        names=["Wireless Headset Pro","USB-C Hub 7-port","Laptop Stand Pro","Gaming Mouse Precision",
               "Mechanical Keyboard TKL","HDMI 2.1 Cable 2m","Webcam 4K Ultra","Desk Lamp LED Smart",
               "Monitor Stand Adj.","Cable Organiser Set","Wrist Rest Ergonomic","USB Microphone Cardioid",
               "Screen Cleaner Kit","Power Strip 6-port","Laptop Sleeve 15in","Blue Light Glasses",
               "Mouse Pad XL","Thermal Paste Premium","SSD Enclosure USB-C","Docking Station 14in1"]
        rows=[]
        for i in range(1, self.n_sku+1):
            sp=float(np.random.uniform(3,100)); mc=int(np.random.randint(500,5000))
            vl=float(np.random.uniform(5,80)); cu=int(mc*sp/100)
            bn=names[i%len(names)]; gen=i//len(names)
            rows.append({"sku_id":f"SKU-{i:03d}",
                "product_name":f"{bn} v{gen+1}" if gen>0 else bn,
                "category":np.random.choice(["Electronics","Accessories","Peripherals"]),
                "warehouse":self.whs[i%len(self.whs)],"stock_pct":round(sp,1),
                "current_units":cu,"max_capacity":mc,"daily_velocity":round(vl,1),
                "days_remaining":max(1,int(cu/max(vl,0.1))),"reorder_point":int(mc*0.20),
                "lead_time_days":int(np.random.randint(7,21)),
                "unit_cost_usd":round(float(np.random.uniform(5,250)),2),
                "supplier_id":f"SUP-{np.random.randint(1,self.n_sup+1):03d}"})
        for idx,sid,pn,sp,dr in [(8,"SKU-009","USB-C Hub 7-port",8.0,5),
                                   (14,"SKU-015","Mechanical Keyboard TKL",7.0,7),
                                   (20,"SKU-021","Monitor Stand Adj.",12.0,9)]:
            if idx < len(rows):
                rows[idx].update({"sku_id":sid,"product_name":pn,"stock_pct":sp,"days_remaining":dr})
        pd.DataFrame(rows).to_excel(os.path.join(DATA_DIR,"inventory.xlsx"),index=False)
        logger.info(f"[Sim] ✓ inventory.xlsx — {len(rows)} rows")

    def _gen_orders(self):
        weeks=pd.date_range("2025-02-01",periods=12,freq="W")
        skus=[f"SKU-{i:03d}" for i in range(1,51)]; rows=[]
        for sku in skus:
            base=int(np.random.randint(400,1200))
            for wi,w in enumerate(weeks):
                units=int(base*(1+wi*0.015)*float(np.random.uniform(0.88,1.15)))
                rows.append({"week_start":w.strftime("%Y-%m-%d"),"sku_id":sku,
                              "units_sold":units,"revenue_usd":round(units*float(np.random.uniform(15,180)),2)})
        pd.DataFrame(rows).to_excel(os.path.join(DATA_DIR,"orders.xlsx"),index=False)
        logger.info(f"[Sim] ✓ orders.xlsx — {len(rows)} rows")

    # stats
    def get_stats(self): return dict(self._stats)
    def set_engine_running(self,v): self._stats["engine_running"]=v
    def update_after_analysis(self,result):
        self._stats.update({"savings_found":result.get("total_savings_found",84000),
                            "critical_alerts":result.get("critical_count",3),
                            "critical_count":result.get("critical_count",3),
                            "last_analysis":datetime.now().isoformat()})
        self._stats["agent_runs_today"]+=1

    def get_inventory_summary(self):
        try:
            df=pd.read_excel(os.path.join(DATA_DIR,"inventory.xlsx"))
            df["days_remaining"]=(df["current_units"]/df["daily_velocity"].clip(lower=0.1)).astype(int)
            return {"total_skus":len(df),"critical_count":int(len(df[df["stock_pct"]<15])),
                    "low_count":int(len(df[(df["stock_pct"]>=15)&(df["stock_pct"]<35)])),
                    "overstock_count":int(len(df[df["stock_pct"]>90])),
                    "stockout_risk_14d":int(len(df[df["days_remaining"]<14])),
                    "chart_data":df.nsmallest(20,"days_remaining")[
                        ["sku_id","product_name","stock_pct","days_remaining"]].to_dict("records")}
        except: return {"total_skus":847,"critical_count":9,"low_count":23,"overstock_count":14,"stockout_risk_14d":9,"chart_data":[]}

    def get_suppliers_table(self):
        try:
            df=pd.read_excel(os.path.join(DATA_DIR,"suppliers.xlsx"))
            return df[["supplier_id","supplier_name","category","overall_score",
                        "on_time_rate","quality_rate","financial_rating","country"]].to_dict("records")
        except: return []

    def get_weekly_demand(self):
        try:
            df=pd.read_excel(os.path.join(DATA_DIR,"orders.xlsx"))
            return df.groupby("week_start").agg(total_units=("units_sold","sum"),
                total_revenue=("revenue_usd","sum")).reset_index().to_dict("records")
        except: return []
