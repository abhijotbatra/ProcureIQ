"""
src/ui/dashboard.py — Flask Web Dashboard
All API endpoints matching SmartTrader's pattern exactly.
"""
import json, logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
from src.database import get_recent_news, get_active_alerts, get_analysis_history, get_cost_opportunities

logger = logging.getLogger(__name__)

def create_app(engine, simulator, config:dict) -> Flask:
    import os
    tdir=os.path.join(os.path.dirname(__file__),"..","..","templates")
    sdir=os.path.join(os.path.dirname(__file__),"..","..","static")
    app=Flask(__name__,template_folder=tdir,static_folder=sdir)
    app.secret_key=config.get("dashboard",{}).get("secret_key","procureiq-dev")
    CORS(app)

    @app.route("/")
    def index(): return render_template("index.html")

    @app.route("/api/portfolio")
    def api_portfolio():
        stats=simulator.get_stats(); r=engine.last_result() or {}
        return jsonify({"total_budget":stats.get("total_budget",1200000),
                        "current_budget":stats.get("current_budget",1200000),
                        "savings_found":stats.get("savings_found",0),
                        "critical_alerts":stats.get("critical_alerts",0),
                        "warning_alerts":7,
                        "suppliers_tracked":stats.get("suppliers_tracked",142),
                        "skus_monitored":stats.get("skus_monitored",847),
                        "stockout_risk_14d":stats.get("stockout_risk_14d",9),
                        "agent_runs_today":stats.get("agent_runs_today",0),
                        "last_analysis":stats.get("last_analysis"),
                        "engine_running":stats.get("engine_running",False),
                        "action_plan":r.get("action_plan","")})

    @app.route("/api/positions")
    def api_positions():
        r=engine.last_result() or {}; alerts=r.get("inventory_alerts",[]) or get_active_alerts()
        return jsonify({"positions":alerts,"count":len(alerts)})

    @app.route("/api/signals")
    def api_signals():
        r=engine.last_result() or {}; risks=r.get("risks",[]) or get_active_alerts()
        return jsonify({"signals":risks,"count":len(risks)})

    @app.route("/api/trades")
    def api_trades():
        h=get_analysis_history(20); return jsonify({"trades":h,"count":len(h)})

    @app.route("/api/performance")
    def api_performance():
        r=engine.last_result() or {}; h=get_analysis_history(50)
        return jsonify({"total_runs":len(h),
                        "total_savings_found":sum(x.get("savings_found",0) for x in h),
                        "avg_processing_secs":round(sum(x.get("processing_time_secs",0) for x in h)/max(len(h),1),2),
                        "avg_critical_per_run":round(sum(x.get("critical_count",0) for x in h)/max(len(h),1),1),
                        "last_result":r,"run_history":h[:10]})

    @app.route("/api/suppliers")
    def api_suppliers():
        r=engine.last_result() or {}
        return jsonify({"suppliers":simulator.get_suppliers_table(),"scores":r.get("supplier_scores",[])})

    @app.route("/api/inventory")
    def api_inventory():
        r=engine.last_result() or {}; s=simulator.get_inventory_summary()
        return jsonify({**s,"alerts":r.get("inventory_alerts",[])})

    @app.route("/api/demand")
    def api_demand():
        r=engine.last_result() or {}
        return jsonify({"weekly_demand":simulator.get_weekly_demand(),"forecasts":r.get("forecasts",[])})

    @app.route("/api/news")
    def api_news():
        a=get_recent_news(20); return jsonify({"articles":a,"count":len(a)})

    @app.route("/api/costs")
    def api_costs():
        r=engine.last_result() or {}; opps=r.get("cost_opportunities",[]) or get_cost_opportunities()
        return jsonify({"opportunities":opps,"total_savings":sum(o.get("saving_amount",0) for o in opps)})

    @app.route("/api/engine/status")
    def api_status(): return jsonify(engine.status())

    @app.route("/api/engine/start", methods=["POST"])
    def api_start(): engine.start(); return jsonify({"status":"started","message":"Engine started"})

    @app.route("/api/engine/stop", methods=["POST"])
    def api_stop(): engine.stop(); return jsonify({"status":"stopped","message":"Engine stopped"})

    @app.route("/api/analyze", methods=["POST"])
    def api_analyze():
        body=request.get_json(silent=True) or {}
        query=body.get("query","What are the most critical supply chain issues right now?")
        try: return jsonify(engine.analyze(query))
        except Exception as e: logger.error(f"[Dashboard] {e}"); return jsonify({"error":str(e)}),500

    @app.route("/api/export")
    def api_export():
        data={"exported_at":datetime.now().isoformat(),"suppliers":simulator.get_suppliers_table(),
              "inventory_summary":simulator.get_inventory_summary(),"active_alerts":get_active_alerts(),
              "cost_opportunities":get_cost_opportunities(),"analysis_history":get_analysis_history(20),
              "last_result":engine.last_result()}
        return Response(json.dumps(data,indent=2,default=str),mimetype="application/json",
                        headers={"Content-Disposition":"attachment;filename=procureiq_export.json"})
    return app
