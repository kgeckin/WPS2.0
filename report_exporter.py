# report_exporter.py
# ------------------
# Excel export module for WPS (WhatsApp Phishing Awareness Simulator).
# Builds a management-friendly XLSX with Raw_* sheets, KPIs, and Summaries.
# Exports event and aggregate metrics without credentials or individual contact details.

from __future__ import annotations
import os
import traceback
from datetime import datetime
from typing import Tuple, Dict, Any, List

import pandas as pd

# WPS DB utilities (already in your project)
from db_utils import (
    fetch_all_users,
    fetch_all_campaigns,
    fetch_campaign_tracking,
    fetch_login_attempts,
    fetch_import_logs,
    fetch_error_logs,
    fetch_action_logs,
    log_error,
)

def _as_df(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert list-of-dicts to DataFrame (empty if None)."""
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)

def _safe_rate(numer: float, denom: float) -> float:
    """Avoid division-by-zero."""
    return float(numer) / float(denom) if float(denom) else 0.0

def _timestamped_filename(prefix: str = "WPS_Report", ext: str = ".xlsx") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    os.makedirs(desktop, exist_ok=True)
    return os.path.join(desktop, f"{prefix}_{ts}{ext}")

def _safe_cell(value: Any) -> Any:
    """Avoid spreadsheet formula evaluation for untrusted strings."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _safe_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    return frame.apply(lambda column: column.map(_safe_cell))


def build_dataframes(include_passwords: bool = False) -> Dict[str, pd.DataFrame]:
    """Gather only the data needed for anonymized reporting.

    The old password export switch is rejected for compatibility with callers.
    """
    if include_passwords:
        raise ValueError("Export of submitted credentials is permanently disabled.")

    users = _as_df(fetch_all_users()).drop(columns=["email", "phone"], errors="ignore")
    campaigns = _as_df(fetch_all_campaigns())
    tracking = _as_df(fetch_campaign_tracking())
    attempts = _as_df(fetch_login_attempts())
    safe_columns = ["attempt_id", "user_id", "campaign_id", "timestamp"]
    attempts = attempts.reindex(columns=safe_columns)

    return {
        "users": _safe_frame(users),
        "campaigns": _safe_frame(campaigns),
        "tracking": _safe_frame(tracking),
        "attempts": _safe_frame(attempts),
        "import_logs": pd.DataFrame(),
        "error_logs": pd.DataFrame(),
        "action_logs": pd.DataFrame(),
    }


def compute_summaries(dfs: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Produce Summary_by_company, Summary_by_campaign and KPI dict."""
    users = dfs["users"].copy()
    tracking = dfs["tracking"].copy()

    for col in ("opened", "clicked", "compromised"):
        if col in tracking.columns:
            tracking[col] = tracking[col].astype("int64", errors="ignore")

    # Summary by campaign
    if tracking.empty:
        by_campaign = pd.DataFrame(columns=[
            "campaign_id", "targeted", "opens", "clicks", "compromises",
            "open_rate", "click_rate", "comp_rate"
        ])
    else:
        grp_c = tracking.groupby("campaign_id", dropna=False).agg(
            targeted=("tracking_id", "count"),
            opens=("opened", "sum"),
            clicks=("clicked", "sum"),
            compromises=("compromised", "sum"),
        ).reset_index()
        grp_c["open_rate"] = grp_c.apply(lambda r: _safe_rate(r["opens"], r["targeted"]), axis=1)
        grp_c["click_rate"] = grp_c.apply(lambda r: _safe_rate(r["clicks"], r["targeted"]), axis=1)
        grp_c["comp_rate"] = grp_c.apply(lambda r: _safe_rate(r["compromises"], r["targeted"]), axis=1)
        by_campaign = grp_c[
            ["campaign_id", "targeted", "opens", "clicks", "compromises", "open_rate", "click_rate", "comp_rate"]
        ].sort_values("campaign_id", kind="stable")

    # Summary by company
    if tracking.empty or users.empty:
        by_company = pd.DataFrame(columns=[
            "company_name", "targeted", "opens", "clicks", "compromises",
            "open_rate", "click_rate", "comp_rate"
        ])
    else:
        merged = tracking.merge(users[["user_id", "company_name"]], how="left", on="user_id")
        grp_u = merged.groupby("company_name", dropna=False).agg(
            targeted=("tracking_id", "count"),
            opens=("opened", "sum"),
            clicks=("clicked", "sum"),
            compromises=("compromised", "sum"),
        ).reset_index()
        grp_u["open_rate"] = grp_u.apply(lambda r: _safe_rate(r["opens"], r["targeted"]), axis=1)
        grp_u["click_rate"] = grp_u.apply(lambda r: _safe_rate(r["clicks"], r["targeted"]), axis=1)
        grp_u["comp_rate"] = grp_u.apply(lambda r: _safe_rate(r["compromises"], r["targeted"]), axis=1)
        by_company = grp_u[
            ["company_name", "targeted", "opens", "clicks", "compromises", "open_rate", "click_rate", "comp_rate"]
        ].sort_values("company_name", kind="stable")

    total_dispatched = int(by_campaign["targeted"].sum()) if not by_campaign.empty else int(tracking.shape[0])
    total_opens = int(tracking["opened"].sum()) if "opened" in tracking.columns else 0
    total_clicks = int(tracking["clicked"].sum()) if "clicked" in tracking.columns else 0
    total_compromises = int(tracking["compromised"].sum()) if "compromised" in tracking.columns else 0

    kpis = {
        "Total Dispatched": total_dispatched,
        "Opens": total_opens,
        "Clicks": total_clicks,
        "Compromises": total_compromises,
        "Open Rate": _safe_rate(total_opens, total_dispatched),
        "Click Rate": _safe_rate(total_clicks, total_dispatched),
        "Compromise Rate": _safe_rate(total_compromises, total_dispatched),
        "Unique Users Targeted": int(tracking["user_id"].nunique()) if "user_id" in tracking.columns else 0,
        "Unique Campaigns": int(tracking["campaign_id"].nunique()) if "campaign_id" in tracking.columns else 0,
        "Last Exported": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    return by_company, by_campaign, kpis

def export_to_excel(output_path: str | None = None, include_passwords: bool = False) -> str:
    """
    Build the Excel workbook and write to output_path.
    Returns the final written path.
    """
    try:
        dfs = build_dataframes(include_passwords=include_passwords)
        by_company, by_campaign, kpis = compute_summaries(dfs)

        if not output_path:
            output_path = _timestamped_filename()

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # README
            readme = pd.DataFrame({
                "How to use this file": [
                    "1) Do NOT edit the Raw_* sheets manually. They are exported from WPS.",
                    "2) KPIs are computed in Python for reliability and speed.",
                    "3) Build visuals with PivotTables/Charts from Raw_* or use Summary_* sheets.",
                    "4) For time trends, use 'timestamp' in Raw_login_attempts.",
                    "5) Do not share reports without authorization. Credentials and diagnostic logs are excluded.",
                ]
            })
            readme.to_excel(writer, sheet_name="README", index=False)

            # Raw sheets
            dfs["users"].to_excel(writer, sheet_name="Raw_users", index=False)
            dfs["campaigns"].to_excel(writer, sheet_name="Raw_campaigns", index=False)
            dfs["tracking"].to_excel(writer, sheet_name="Raw_campaign_tracking", index=False)
            dfs["attempts"].to_excel(writer, sheet_name="Raw_login_attempts", index=False)

            # Diagnostic logs may contain sensitive details and are not exported.

            # Summaries
            by_company.to_excel(writer, sheet_name="Summary_by_company", index=False)
            by_campaign.to_excel(writer, sheet_name="Summary_by_campaign", index=False)

            # KPIs
            kpi_df = pd.DataFrame({"Metric": list(kpis.keys()), "Value": list(kpis.values())})
            kpi_df.to_excel(writer, sheet_name="KPIs", index=False)

        return output_path

    except Exception as e:
        try:
            log_error("Excel Export Error", f"{e}\n{traceback.format_exc()}", "report_exporter")
        except Exception:
            pass
        raise

if __name__ == "__main__":
    path = export_to_excel()
    print(f"Exported: {path}")
