"""
src/ui.py – Premium Healthcare SaaS UI Component Library

Enterprise-grade presentation layer for the PREAUTH Prior Authorization
Intelligence & Case Management platform.
"""

import base64
import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st
from src.pdf_report import generate_report

logger = logging.getLogger(__name__)


# ============================================================
# 1. CENTRALIZED CSS DESIGN SYSTEM
# ============================================================

def apply_custom_styles():
    """Inject the complete healthcare SaaS design system."""
    st.markdown(_CSS, unsafe_allow_html=True)


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* ─── Design Tokens ──────────────────────────────── */
:root {
  --white: #ffffff;
  --slate-50: #f8fafc;
  --slate-100: #f1f5f9;
  --slate-200: #e2e8f0;
  --slate-300: #cbd5e1;
  --slate-400: #94a3b8;
  --slate-500: #64748b;
  --slate-600: #475569;
  --slate-700: #334155;
  --slate-800: #1e293b;
  --slate-900: #0f172a;

  --blue-50: #eff6ff;
  --blue-100: #dbeafe;
  --blue-200: #bfdbfe;
  --blue-500: #3b82f6;
  --blue-600: #2563eb;
  --blue-700: #1d4ed8;
  --blue-800: #1e40af;
  --blue-900: #1e3a8a;

  --green-50: #f0fdf4;
  --green-100: #dcfce7;
  --green-500: #22c55e;
  --green-600: #16a34a;
  --green-700: #15803d;

  --red-50: #fef2f2;
  --red-100: #fee2e2;
  --red-500: #ef4444;
  --red-600: #dc2626;
  --red-700: #b91c1c;

  --amber-50: #fffbeb;
  --amber-100: #fef3c7;
  --amber-500: #f59e0b;
  --amber-600: #d97706;
  --amber-700: #b45309;

  --purple-50: #faf5ff;
  --purple-100: #f3e8ff;
  --purple-600: #9333ea;

  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --shadow-xs: 0 1px 2px 0 rgba(15,23,42,.04);
  --shadow-sm: 0 1px 3px 0 rgba(15,23,42,.06), 0 1px 2px -1px rgba(15,23,42,.06);
  --shadow-md: 0 4px 6px -1px rgba(15,23,42,.08), 0 2px 4px -2px rgba(15,23,42,.06);
  --shadow-lg: 0 10px 15px -3px rgba(15,23,42,.09), 0 4px 6px -4px rgba(15,23,42,.05);
}

/* ─── Global Base ────────────────────────────────── */
.stApp {
  background-color: var(--slate-50) !important;
  color: var(--slate-900) !important;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}
.main .block-container {
  max-width: 100% !important;
  padding: 0 2rem 3rem 2rem !important;
}
header[data-testid="stHeader"] {
  background: transparent !important;
  z-index: 99 !important;
  height: 2.5rem !important;
}
header[data-testid="stHeader"] [data-testid="stHeaderNav"] { display: none !important; }
footer { display: none !important; }

h1,h2,h3,h4,h5,h6 {
  font-family: 'Inter', sans-serif !important;
  color: var(--slate-900) !important;
  letter-spacing: -0.02em !important;
}

/* ─── Sidebar – Premium Nav ────────────────── */
[data-testid="stSidebar"] {
  background: var(--white) !important;
  border-right: 1px solid var(--slate-200) !important;
  padding: 0 !important;
  transition: all .2s ease-in-out !important;
}
[data-testid="stSidebar"] > div:first-child {
  padding: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
  font-size: 13px !important;
  color: var(--slate-600) !important;
}
button[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"],
button[kind="header"] {
  color: var(--slate-600) !important;
  background: transparent !important;
  border-radius: var(--radius-sm) !important;
}
button[data-testid="stSidebarCollapseButton"]:hover,
[data-testid="collapsedControl"]:hover,
button[kind="header"]:hover {
  background: var(--slate-100) !important;
  color: var(--blue-600) !important;
}

/* ─── Buttons ────────────────────────────────────── */
.stButton > button {
  border-radius: var(--radius-sm) !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  padding: 8px 16px !important;
  border: 1px solid var(--slate-300) !important;
  background: var(--white) !important;
  color: var(--slate-700) !important;
  box-shadow: var(--shadow-xs) !important;
  transition: all .15s ease !important;
  line-height: 1.4 !important;
}
.stButton > button:hover {
  border-color: var(--blue-500) !important;
  color: var(--blue-700) !important;
  background: var(--blue-50) !important;
}
.stButton > button[kind="primary"] {
  background: var(--blue-600) !important;
  color: var(--white) !important;
  border-color: var(--blue-600) !important;
  box-shadow: 0 2px 4px rgba(37,99,235,.2) !important;
}
.stButton > button[kind="primary"]:hover {
  background: var(--blue-700) !important;
  border-color: var(--blue-700) !important;
}

/* ─── Sidebar Nav Buttons ────────────────────────── */
[data-testid="stSidebar"] .stButton > button {
  text-align: left !important;
  justify-content: flex-start !important;
  padding: 10px 18px !important;
  margin: 1px 0 !important;
  border: none !important;
  border-left: 3px solid transparent !important;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0 !important;
  background: transparent !important;
  color: var(--slate-600) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  box-shadow: none !important;
  transition: all .12s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--slate-50) !important;
  color: var(--slate-900) !important;
  border-left-color: var(--slate-400) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: var(--blue-50) !important;
  color: var(--blue-700) !important;
  font-weight: 600 !important;
  border-left: 3px solid var(--blue-600) !important;
  box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
  background: var(--blue-100) !important;
  color: var(--blue-800) !important;
}

/* ─── File Uploader ──────────────────────────────── */
[data-testid="stFileUploader"] {
  background: var(--white) !important;
  border: 2px dashed var(--slate-300) !important;
  border-radius: var(--radius-lg) !important;
  padding: 24px !important;
}
[data-testid="stFileUploader"]:hover {
  border-color: var(--blue-500) !important;
  background: var(--blue-50) !important;
}
[data-testid="stFileUploader"] section { background: transparent !important; }

/* ─── Inputs & Selects ───────────────────────────── */
div[data-baseweb="input"], div[data-baseweb="input"]>div,
input[type="text"], [data-testid="stTextInput"] input {
  background: var(--white) !important; color: var(--slate-900) !important;
  border: 1px solid var(--slate-300) !important; border-radius: var(--radius-sm) !important;
  font-size: 13px !important;
}
div[data-baseweb="select"], div[data-baseweb="select"]>div {
  background: var(--white) !important; color: var(--slate-900) !important;
  border: 1px solid var(--slate-300) !important; border-radius: var(--radius-sm) !important;
  font-size: 13px !important;
}
ul[data-baseweb="menu"], div[data-baseweb="popover"], div[data-baseweb="popover"]>div {
  background: var(--white) !important; border: 1px solid var(--slate-200) !important;
  border-radius: var(--radius-sm) !important; box-shadow: var(--shadow-lg) !important;
}
li[data-baseweb="menu-item"] {
  color: var(--slate-800) !important; font-size: 13px !important; font-weight: 500 !important; padding: 8px 14px !important;
}
li[data-baseweb="menu-item"]:hover, li[data-baseweb="menu-item"][aria-selected="true"] {
  background: var(--blue-50) !important; color: var(--blue-700) !important;
}

/* ─── Expanders ──────────────────────────────────── */
[data-testid="stExpander"] {
  background: var(--white) !important;
  border: 1px solid var(--slate-200) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: var(--shadow-xs) !important;
  margin-bottom: 10px !important;
}
[data-testid="stExpander"] summary {
  font-size: 13px !important; font-weight: 600 !important;
  color: var(--slate-800) !important; padding: 12px 16px !important;
}

/* ─── Custom Component Styles ────────────────────── */

/* Top bar */
.top-bar {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--white); border-bottom: 1px solid var(--slate-200);
  padding: 10px 24px; margin: -1rem -2rem 24px -2rem;
  box-shadow: var(--shadow-xs);
}
.top-bar-left { display: flex; align-items: center; gap: 16px; }
.top-bar-right { display: flex; align-items: center; gap: 16px; }
.top-search {
  display: flex; align-items: center; gap: 8px;
  background: var(--slate-50); border: 1px solid var(--slate-200);
  border-radius: var(--radius-sm); padding: 7px 14px; min-width: 340px;
  font-size: 13px; color: var(--slate-400);
}
.top-search svg { width: 14px; height: 14px; }
.db-live-pill {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--green-50); color: var(--green-700);
  border: 1px solid var(--green-100); border-radius: 20px;
  padding: 4px 10px; font-size: 11px; font-weight: 600;
}
.db-offline-pill {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--red-50); color: var(--red-700);
  border: 1px solid var(--red-100); border-radius: 20px;
  padding: 4px 10px; font-size: 11px; font-weight: 600;
}
.user-chip {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: var(--slate-700); font-weight: 500;
}
.user-avatar {
  width: 30px; height: 30px; border-radius: 50%;
  background: var(--blue-600); color: var(--white);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700;
}

/* Sidebar brand */
.sidebar-brand {
  display: flex; align-items: center; gap: 10px;
  padding: 20px 20px 8px 20px;
}
.sidebar-logo {
  width: 34px; height: 34px; border-radius: var(--radius-md);
  background: var(--blue-600); color: var(--white);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 700;
  box-shadow: 0 2px 4px rgba(37,99,235,.25);
}
.sidebar-brand-text h2 { font-size: 16px !important; font-weight: 800 !important; margin: 0 !important; letter-spacing: .01em !important; color: var(--slate-900) !important; }
.sidebar-brand-text span { font-size: 10px; color: var(--slate-500); font-weight: 500; letter-spacing: .02em; }

/* Sidebar nav */
.sidebar-nav-section { font-size: 10px; font-weight: 700; color: var(--slate-400); text-transform: uppercase; letter-spacing: .08em; padding: 16px 20px 6px 20px; }
.sidebar-nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 20px; margin: 1px 8px; border-radius: var(--radius-sm);
  font-size: 13px; font-weight: 500; color: var(--slate-600);
  cursor: pointer; text-decoration: none !important; transition: all .12s ease;
  border-left: 3px solid transparent;
}
.sidebar-nav-item:hover { background: var(--slate-50); color: var(--slate-900); }
.sidebar-nav-item.active {
  background: var(--blue-50); color: var(--blue-700); font-weight: 600;
  border-left: 3px solid var(--blue-600);
}
.sidebar-nav-item.active svg, .sidebar-nav-item.active .nav-icon { color: var(--blue-600); }
.nav-icon { width: 18px; text-align: center; font-size: 15px; }
.sidebar-status-card {
  margin: 12px 12px; padding: 12px 14px; border-radius: var(--radius-md);
  background: var(--slate-50); border: 1px solid var(--slate-200); font-size: 12px;
}
.sidebar-status-row {
  display: flex; align-items: center; gap: 6px; padding: 3px 0; color: var(--slate-600);
}
.sidebar-status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.sidebar-footer {
  padding: 12px 20px; font-size: 11px; color: var(--slate-400); border-top: 1px solid var(--slate-100);
}

/* Metric cards */
.metrics-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 16px; margin-bottom: 24px; }
.metric-card {
  background: var(--white); border: 1px solid var(--slate-200);
  border-radius: var(--radius-lg); padding: 18px 20px;
  box-shadow: var(--shadow-sm); display: flex; align-items: flex-start; gap: 14px;
}
.metric-icon-circle {
  width: 42px; height: 42px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}
.metric-body { flex: 1; }
.metric-label { font-size: 12px; font-weight: 600; color: var(--slate-500); text-transform: uppercase; letter-spacing: .03em; margin-bottom: 2px; }
.metric-value { font-size: 26px; font-weight: 800; color: var(--slate-900); line-height: 1.2; }
.metric-sub { font-size: 11px; color: var(--slate-500); margin-top: 2px; }

/* Page header */
.page-header { margin-bottom: 24px; display: flex; align-items: flex-start; justify-content: space-between; }
.page-header-left h1 { font-size: 26px !important; font-weight: 700 !important; margin: 0 0 4px 0 !important; }
.page-header-left p { font-size: 14px; color: var(--slate-500); margin: 0; }

/* Filter toolbar */
.filter-toolbar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  background: var(--white); border: 1px solid var(--slate-200);
  border-radius: var(--radius-md); padding: 10px 16px; margin-bottom: 20px;
  box-shadow: var(--shadow-xs);
}
.filter-search {
  flex: 1; min-width: 240px; display: flex; align-items: center; gap: 8px;
  background: var(--slate-50); border: 1px solid var(--slate-200);
  border-radius: var(--radius-sm); padding: 7px 12px; font-size: 13px; color: var(--slate-400);
}
.filter-chip {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--white); border: 1px solid var(--slate-200);
  border-radius: var(--radius-sm); padding: 6px 12px; font-size: 12px;
  font-weight: 500; color: var(--slate-700); cursor: pointer;
}
.filter-chip:hover { border-color: var(--slate-400); }

/* Policy row */
.policy-row {
  background: var(--white); border: 1px solid var(--slate-200);
  border-radius: var(--radius-md); padding: 14px 20px;
  margin-bottom: 8px; box-shadow: var(--shadow-xs);
  display: flex; align-items: center; gap: 14px;
  transition: all .12s ease; cursor: pointer;
}
.policy-row:hover {
  border-color: var(--slate-300); box-shadow: var(--shadow-md);
}
.policy-expand-icon {
  width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;
  color: var(--slate-400); font-size: 14px; flex-shrink: 0;
}
.policy-doc-icon {
  width: 32px; height: 32px; border-radius: var(--radius-sm);
  background: var(--blue-50); color: var(--blue-700);
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; flex-shrink: 0;
}
.policy-info { flex: 1; min-width: 0; }
.policy-info-title { font-size: 14px; font-weight: 600; color: var(--slate-900); }
.policy-info-sub { font-size: 12px; color: var(--slate-500); margin-top: 1px; }
.policy-meta { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; font-weight: 600; padding: 3px 9px;
  border-radius: 20px; white-space: nowrap;
}
.badge-active { background: var(--green-50); color: var(--green-700); border: 1px solid var(--green-100); }
.badge-inactive { background: var(--slate-100); color: var(--slate-600); border: 1px solid var(--slate-200); }
.badge-commercial { background: var(--blue-50); color: var(--blue-700); border: 1px solid var(--blue-100); }
.badge-medicare { background: var(--purple-50); color: var(--purple-600); border: 1px solid var(--purple-100); }
.policy-date { font-size: 12px; color: var(--slate-500); white-space: nowrap; }
.policy-view-btn {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 600; color: var(--blue-700);
  background: none; border: none; cursor: pointer; padding: 4px 0;
}
.policy-view-btn:hover { color: var(--blue-800); text-decoration: underline; }

/* Pagination */
.pagination { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; font-size: 13px; color: var(--slate-500); }
.page-btns { display: flex; gap: 4px; }
.page-btn {
  min-width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--slate-200); border-radius: var(--radius-sm);
  font-size: 13px; font-weight: 500; background: var(--white); color: var(--slate-700);
  cursor: pointer; transition: all .1s;
}
.page-btn:hover { border-color: var(--blue-500); color: var(--blue-700); }
.page-btn.active { background: var(--blue-600); color: var(--white); border-color: var(--blue-600); }

/* Status badges (decisions) */
.status-badge {
  font-size: 11px !important; font-weight: 700 !important; padding: 4px 10px !important;
  border-radius: var(--radius-sm) !important; text-transform: uppercase !important;
  letter-spacing: .03em !important; display: inline-flex !important;
  align-items: center !important; gap: 5px !important; white-space: nowrap !important;
}
.badge-approved { background: var(--green-50) !important; color: var(--green-700) !important; border: 1px solid var(--green-100) !important; }
.badge-denied { background: var(--red-50) !important; color: var(--red-700) !important; border: 1px solid var(--red-100) !important; }
.badge-review { background: var(--amber-50) !important; color: var(--amber-700) !important; border: 1px solid var(--amber-100) !important; }
.badge-no-pa { background: var(--blue-50) !important; color: var(--blue-700) !important; border: 1px solid var(--blue-100) !important; }
.badge-pending { background: var(--slate-100) !important; color: var(--slate-700) !important; border: 1px solid var(--slate-200) !important; }

/* Clinical grid */
.clinical-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px 16px; background: var(--slate-50); border: 1px solid var(--slate-200);
  border-radius: var(--radius-md); padding: 16px; margin-bottom: 16px;
}
.clinical-item { display: flex; flex-direction: column; }
.clinical-label { font-size: 11px; font-weight: 600; color: var(--slate-500); text-transform: uppercase; letter-spacing: .03em; margin-bottom: 3px; }
.clinical-value { font-size: 13px; font-weight: 600; color: var(--slate-900); word-break: break-word; }
.mono-code { font-family: 'IBM Plex Mono', monospace !important; font-size: 12px !important; background: var(--white); padding: 2px 6px; border-radius: 4px; border: 1px solid var(--slate-200); display: inline-block; }

/* Case header */
.case-header-card {
  background: var(--white); border: 1px solid var(--slate-200);
  border-radius: var(--radius-lg); padding: 20px 24px;
  margin-bottom: 20px; box-shadow: var(--shadow-sm);
}
.case-section-title {
  font-size: 12px; font-weight: 700; color: var(--slate-500); text-transform: uppercase;
  letter-spacing: .06em; margin: 16px 0 12px 0; display: flex; align-items: center; gap: 8px;
  border-bottom: 1px solid var(--slate-100); padding-bottom: 6px;
}

/* Criterion cards */
.criterion-card { background: var(--white); border: 1px solid var(--slate-200); border-radius: var(--radius-md); padding: 12px 16px; margin-bottom: 8px; border-left: 4px solid var(--slate-300); }
.criterion-card-passed { border-left-color: var(--green-600) !important; }
.criterion-card-failed { border-left-color: var(--red-600) !important; }
.criterion-card-na { border-left-color: var(--slate-400) !important; }
.criterion-card-warn { border-left-color: var(--amber-600) !important; }
.criterion-top-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.criterion-title { font-size: 13px; font-weight: 600; color: var(--slate-900); display: flex; align-items: center; gap: 6px; }
.criterion-reason { font-size: 12px; color: var(--slate-600); padding-left: 20px; }

/* Decision banners */
.decision-banner { border-radius: var(--radius-md); padding: 18px 20px; margin-bottom: 18px; border-left: 4px solid transparent; }
.decision-banner-approved { background: var(--green-50); border: 1px solid var(--green-100); border-left-color: var(--green-600); }
.decision-banner-denied { background: var(--red-50); border: 1px solid var(--red-100); border-left-color: var(--red-600); }
.decision-banner-review { background: var(--amber-50); border: 1px solid var(--amber-100); border-left-color: var(--amber-600); }
.decision-banner-no-pa { background: var(--blue-50); border: 1px solid var(--blue-100); border-left-color: var(--blue-600); }

/* Audit timeline */
.audit-timeline { position: relative; padding-left: 24px; margin-top: 14px; border-left: 2px solid var(--slate-200); }
.timeline-step { position: relative; margin-bottom: 16px; }
.timeline-step:last-child { margin-bottom: 0; }
.timeline-dot { position: absolute; left: -31px; top: 2px; width: 12px; height: 12px; border-radius: 50%; background: var(--blue-600); border: 2px solid var(--white); box-shadow: 0 0 0 2px var(--slate-300); }
.timeline-content { font-size: 12px; }
.timeline-title { font-weight: 600; color: var(--slate-800); margin-bottom: 2px; }
.timeline-time { font-size: 11px; color: var(--slate-500); font-family: 'IBM Plex Mono', monospace; }

/* Request row */
.request-row-card {
  background: var(--white); border: 1px solid var(--slate-200);
  border-radius: var(--radius-md); padding: 14px 18px; margin-bottom: 10px;
  box-shadow: var(--shadow-xs); transition: all .12s ease;
}
.request-row-card:hover { border-color: var(--blue-500); box-shadow: var(--shadow-md); }

/* Empty state */
.empty-state-box {
  background: var(--white); border: 2px dashed var(--slate-300);
  border-radius: var(--radius-lg); padding: 48px 24px; text-align: center; margin: 24px 0;
}
.empty-state-icon { font-size: 40px; margin-bottom: 12px; color: var(--slate-400); }
.empty-state-title { font-size: 16px; font-weight: 600; color: var(--slate-800); margin-bottom: 6px; }
.empty-state-text { font-size: 13px; color: var(--slate-500); max-width: 420px; margin: 0 auto; }

</style>
"""


# ============================================================
# 2. HELPERS
# ============================================================

def _get_decision(item: Dict[str, Any]) -> str:
    if not isinstance(item, dict):
        return "UNKNOWN"
    decs = item.get("decisions") or []
    if decs and len(decs) > 0:
        sorted_decs = sorted(decs, key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return str(sorted_decs[0].get("final_decision") or item.get("request_status") or "PENDING").upper()
    return str(item.get("request_status") or "PENDING").upper()


def safe_str(val, default="Not provided"):
    if val is None: return default
    s = str(val).strip()
    return s if s else default

def safe_title(val, default="Not provided"):
    if val is None: return default
    s = str(val).strip()
    return s.title() if s else default

def safe_upper(val, default="N/A"):
    if val is None: return default
    s = str(val).strip()
    return s.upper() if s else default

def format_iso_timestamp(ts):
    if not ts: return "—"
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(ts)[:10]

def format_iso_timestamp_full(ts):
    if not ts: return "—"
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime("%b %d, %Y • %I:%M %p")
    except Exception:
        return str(ts)[:19]

def get_status_badge_html(decision_str):
    d = str(decision_str).upper()
    if d == "APPROVED": return '<span class="status-badge badge-approved">✓ Approved</span>'
    if d == "DENIED": return '<span class="status-badge badge-denied">✕ Denied</span>'
    if d in ("MANUAL REVIEW","MANUAL_REVIEW"): return '<span class="status-badge badge-review">⚠ Manual Review</span>'
    if "NO_PRIOR_AUTH" in d or "NO PRIOR AUTH" in d: return '<span class="status-badge badge-no-pa">ℹ No Prior Auth</span>'
    return f'<span class="status-badge badge-pending">● {d}</span>'

def render_pdf_viewer(pdf_bytes, file_name="document.pdf", height=560):
    try:
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" style="border-radius:8px;border:1px solid var(--slate-200);background:var(--white);"></iframe>', unsafe_allow_html=True)
    except Exception as e:
        st.caption(f"PDF preview unavailable ({e})")


# ============================================================
# 3. SIDEBAR NAVIGATION (proper clickable items, no radio)
# ============================================================

_NAV_ITEMS = [
    ("dashboard", "🏠", "Dashboard"),
    ("requests", "📋", "Requests"),
    ("upload",   "📄", "New Request"),
    ("policies", "⚙️", "Policies"),
    ("audit",    "🕘", "Audit"),
]

def render_sidebar_nav(db_status: Dict[str, Any] = None) -> str:
    """Premium fixed sidebar with proper navigation items."""
    with st.sidebar:
        # Brand
        st.markdown("""
        <div class="sidebar-brand">
            <div class="sidebar-logo">✚</div>
            <div class="sidebar-brand-text">
                <h2>PREAUTH</h2>
                <span>Prior Authorization Intelligence</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sidebar-nav-section">MAIN NAVIGATION</div>', unsafe_allow_html=True)

        # Build navigation using buttons styled as nav items
        if "nav_page" not in st.session_state:
            st.session_state.nav_page = "dashboard"

        for key, icon, label in _NAV_ITEMS:
            is_active = st.session_state.nav_page == key
            btn_type = "primary" if is_active else "secondary"
            btn_label = f"{icon}  {label}"
            if st.button(btn_label, key=f"navbtn_{key}", use_container_width=True, type=btn_type):
                st.session_state.nav_page = key
                st.session_state.active_case = None
                st.rerun()

        # Platform status card
        st.markdown('<div class="sidebar-nav-section" style="margin-top: 12px;">QUICK INFO</div>', unsafe_allow_html=True)

        db_connected = (db_status or {}).get("status") == "connected"
        db_dot_color = "var(--green-500)" if db_connected else "var(--red-500)"
        storage_dot_color = "var(--green-500)" if db_connected else "var(--slate-400)"

        st.markdown(f"""
        <div class="sidebar-status-card">
            <div style="font-size: 11px; font-weight: 700; color: var(--slate-700); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px;">Platform Status</div>
            <div class="sidebar-status-row"><span class="sidebar-status-dot" style="background:{db_dot_color};"></span> Database {"connected" if db_connected else "offline"}</div>
            <div class="sidebar-status-row"><span class="sidebar-status-dot" style="background:var(--green-500);"></span> Policy engine active</div>
            <div class="sidebar-status-row"><span class="sidebar-status-dot" style="background:{storage_dot_color};"></span> Storage {"connected" if db_connected else "offline"}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="sidebar-footer">
            <div>© 2026 PREAUTH</div>
            <div style="margin-top: 2px;">All rights reserved.</div>
        </div>
        """, unsafe_allow_html=True)

    return st.session_state.nav_page


# ============================================================
# 4. TOP HEADER BAR
# ============================================================

def render_top_header(db_status: Dict[str, Any]):
    is_connected = db_status.get("status") == "connected"
    db_html = '<span class="db-live-pill">● PostgreSQL Live</span>' if is_connected else '<span class="db-offline-pill">○ Offline</span>'

    if "sidebar_collapsed" not in st.session_state:
        st.session_state["sidebar_collapsed"] = False

    if st.session_state["sidebar_collapsed"]:
        st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            margin-left: -280px !important;
            min-width: 0px !important;
            width: 0px !important;
            max-width: 0px !important;
            opacity: 0 !important;
            visibility: hidden !important;
            overflow: hidden !important;
        }
        .main .block-container {
            padding-left: 2rem !important;
            max-width: 100% !important;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            margin-left: 0px !important;
            min-width: 260px !important;
            width: 260px !important;
            max-width: 260px !important;
            opacity: 1 !important;
            visibility: visible !important;
        }
        </style>
        """, unsafe_allow_html=True)

    user_info = st.session_state.get("user") or {
        "name": "Alex Vance, RN",
        "role": "Senior Clinical Reviewer",
        "initials": "AV",
        "color": "#0f766e"
    }

    user_name = user_info.get("name", "User")
    user_role = user_info.get("role") or user_info.get("badge") or "Clinical Reviewer"
    user_initials = user_info.get("initials", "CR")
    user_color = user_info.get("color", "#0f766e")

    col_srch, col_right = st.columns([4.2, 3.8])

    with col_srch:
        st.text_input(
            "Global Search",
            placeholder="Search patients, requests, policies...",
            key="global_search_input",
            label_visibility="collapsed"
        )

    with col_right:
        col_db, col_user, col_logout = st.columns([1.5, 2.5, 1.2])
        with col_db:
            st.markdown(f'<div style="display:flex;align-items:center;height:38px;">{db_html}</div>', unsafe_allow_html=True)
        with col_user:
            st.markdown(f"""
            <div class="user-chip" title="{user_name} ({user_role})">
                <span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:130px;font-weight:600;font-size:12px;">{user_name}</span>
                <div class="user-avatar" style="background:{user_color};">{user_initials}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_logout:
            from src.auth import logout
            if st.button("Logout", key="top_bar_logout_btn", use_container_width=True):
                logout()


# ============================================================
# 5. DASHBOARD VIEW
# ============================================================

def render_dashboard_view(requests, on_select_case_callback=None):
    st.markdown("""
    <div class="page-header">
        <div class="page-header-left">
            <h1>Dashboard</h1>
            <p>Overview of authorization requests and case activity.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KPI metrics from real data
    total = len(requests)
    approved = sum(1 for r in requests if _get_decision(r) == "APPROVED")
    denied = sum(1 for r in requests if _get_decision(r) == "DENIED")
    review = total - approved - denied

    st.markdown(f"""
    <div class="metrics-row">
        <div class="metric-card">
            <div class="metric-icon-circle" style="background:var(--blue-50);color:var(--blue-600);">📋</div>
            <div class="metric-body">
                <div class="metric-label">Total Requests</div>
                <div class="metric-value">{total}</div>
                <div class="metric-sub">Active queue</div>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-icon-circle" style="background:var(--green-50);color:var(--green-600);">✓</div>
            <div class="metric-body">
                <div class="metric-label">Approved</div>
                <div class="metric-value" style="color:var(--green-700);">{approved}</div>
                <div class="metric-sub">Criteria met</div>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-icon-circle" style="background:var(--red-50);color:var(--red-600);">✕</div>
            <div class="metric-body">
                <div class="metric-label">Denied</div>
                <div class="metric-value" style="color:var(--red-700);">{denied}</div>
                <div class="metric-sub">Failed rules</div>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-icon-circle" style="background:var(--amber-50);color:var(--amber-600);">⚠</div>
            <div class="metric-body">
                <div class="metric-label">Manual Review</div>
                <div class="metric-value" style="color:var(--amber-700);">{review}</div>
                <div class="metric-sub">Clinician review</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    global_q = st.session_state.get("global_search_input", "").strip()
    dash_q = st.text_input("Search", value=global_q, placeholder="Search by patient, MRN, CPT code...", label_visibility="collapsed", key="dash_srch").strip()
    active_search = dash_q or global_q

    if active_search:
        col_lbl, col_clr = st.columns([4, 1])
        with col_lbl:
            st.markdown(f'<div style="font-size:13px;font-weight:600;color:var(--slate-700);margin:8px 0 12px 0;">Search results for "<strong>{active_search}</strong>"</div>', unsafe_allow_html=True)
        with col_clr:
            if st.button("✕ Clear Search", key="clear_dash_srch"):
                st.session_state["global_search_input"] = ""
                st.session_state["dash_srch"] = ""
                st.rerun()

    if not requests:
        render_empty_state()
        return

    matching_requests = [r for r in requests if _matches_search(r, active_search)]

    if not matching_requests:
        render_empty_state(
            "No matching patients, requests, or policies found.",
            "Try searching with a different patient name, MRN, CPT code, or request number."
        )
        return

    st.markdown(f'<h3 style="font-size:15px;font-weight:700;margin:16px 0 12px 0;">Recent Requests ({len(matching_requests)})</h3>', unsafe_allow_html=True)
    for idx, r in enumerate(matching_requests[:10]):
        _render_request_row(r, idx, on_select_case_callback)


# ============================================================
# 6. REQUESTS VIEW
# ============================================================

def render_all_requests_view(requests, on_select_case_callback=None):
    st.markdown("""
    <div class="page-header">
        <div class="page-header-left">
            <h1>Authorization Requests</h1>
            <p>Complete case management queue.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not requests:
        render_empty_state()
        return

    global_q = st.session_state.get("global_search_input", "").strip()
    col_s, col_f = st.columns([3, 1])
    with col_s:
        all_q = st.text_input("Search", value=global_q, placeholder="Search by patient, MRN, CPT...", label_visibility="collapsed", key="allreq_srch").strip()
    with col_f:
        filt = st.selectbox("Status", ["All","APPROVED","DENIED","MANUAL REVIEW"], label_visibility="collapsed", key="allreq_filt")

    active_search = all_q or global_q
    if active_search:
        col_lbl, col_clr = st.columns([4, 1])
        with col_lbl:
            st.markdown(f'<div style="font-size:13px;font-weight:600;color:var(--slate-700);margin:8px 0 12px 0;">Search results for "<strong>{active_search}</strong>"</div>', unsafe_allow_html=True)
        with col_clr:
            if st.button("✕ Clear Search", key="clear_allreq_srch"):
                st.session_state["global_search_input"] = ""
                st.session_state["allreq_srch"] = ""
                st.rerun()

    matching_requests = []
    for r in requests:
        d = _get_decision(r)
        if active_search and not _matches_search(r, active_search): continue
        if filt != "All" and filt.replace(" ","_") not in d.replace(" ","_"): continue
        matching_requests.append(r)

    if not matching_requests:
        render_empty_state(
            "No matching patients, requests, or policies found.",
            "Try searching with a different patient name, MRN, CPT code, or request number."
        )
        return

    for idx, r in enumerate(matching_requests):
        _render_request_row(r, idx, on_select_case_callback)


def _render_request_row(item, idx, on_select_case_callback):
    p = item.get("patients") or {}
    name = safe_title(p.get("patient_name","Unknown"))
    pid = safe_str(p.get("patient_id","N/A"))
    svc = safe_title(item.get("requested_service") or "Service")
    cpt = safe_upper(item.get("cpt_hcpcs_code") or "N/A")
    payer = safe_title(item.get("payer") or p.get("payer") or "N/A")
    dt = format_iso_timestamp(item.get("created_at"))
    dec = _get_decision(item)
    badge = get_status_badge_html(dec)
    req_id_short = str(item.get('id',''))[:8]

    col_i, col_a = st.columns([5, 1])
    with col_i:
        st.markdown(f"""<div class="request-row-card"><div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;"><div><span style="font-size:14px;font-weight:700;color:var(--slate-900);">👤 {name}</span> <span style="font-size:12px;color:var(--slate-500);margin-left:8px;font-family:monospace;">MRN: {pid}</span></div><div>{badge}</div></div><div style="font-size:13px;color:var(--slate-700);margin-bottom:4px;"><strong>{svc}</strong> · <code>{cpt}</code> · {payer}</div><div style="font-size:11px;color:var(--slate-500);">📅 {dt} · <span style="font-family:monospace;">ID: {req_id_short}</span></div></div>""", unsafe_allow_html=True)
    with col_a:
        st.write("")
        if st.button("Open Case →", key=f"open_{item.get('id')}_{idx}", use_container_width=True):
            if on_select_case_callback: on_select_case_callback(item)



# ============================================================
# 7. POLICIES VIEW (Matching reference image)
# ============================================================

def render_policies_view(policies_data):
    # Page header with action button
    col_h, col_btn = st.columns([4, 1])
    with col_h:
        st.markdown("""
        <div class="page-header-left">
            <h1>Medical Coverage Policies</h1>
            <p>Configured commercial and Medicare prior authorization rules.</p>
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        st.write("")
        st.button("+ New Policy", type="primary", use_container_width=True, key="btn_new_pol")

    total = len(policies_data)
    active_count = sum(1 for p in policies_data if str(p.get("policy_status", "")).strip().lower() == "active")
    payers = {}
    for p in policies_data:
        pyr = str(p.get("payer","")).lower()
        if "medicare" in pyr or "cms" in pyr:
            payers["medicare"] = payers.get("medicare", 0) + 1
        else:
            payers["commercial"] = payers.get("commercial", 0) + 1
    commercial = payers.get("commercial", 0)
    medicare = payers.get("medicare", 0)
    comm_pct = f"{int(commercial/total*100)}%" if total else "0%"
    med_pct = f"{int(medicare/total*100)}%" if total else "0%"

    # Latest updated timestamp
    last_updated = "Aug 17, 2026"

    st.markdown(f"""
    <div class="metrics-row">
        <div class="metric-card">
            <div class="metric-icon-circle" style="background:var(--teal-50);color:var(--teal-600);">✓</div>
            <div class="metric-body">
                <div class="metric-label">Total Policies</div>
                <div class="metric-value">{total}</div>
                <div class="metric-sub" style="color:var(--teal-600);">{active_count} Active policies</div>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-icon-circle" style="background:var(--blue-50);color:var(--blue-600);">📋</div>
            <div class="metric-body">
                <div class="metric-label">Commercial</div>
                <div class="metric-value">{commercial}</div>
                <div class="metric-sub">{comm_pct} of total</div>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-icon-circle" style="background:var(--green-50);color:var(--green-600);">⊕</div>
            <div class="metric-body">
                <div class="metric-label">Medicare</div>
                <div class="metric-value">{medicare}</div>
                <div class="metric-sub">{med_pct} of total</div>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-icon-circle" style="background:var(--amber-50);color:var(--amber-600);">🕘</div>
            <div class="metric-body">
                <div class="metric-label">Last Updated</div>
                <div class="metric-value" style="font-size:18px;">{last_updated}</div>
                <div class="metric-sub" style="color:var(--amber-600);">10:57 PM UTC</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    global_q = st.session_state.get("global_search_input", "").strip()
    col_ps, col_pf1, col_pf2, col_pf3, col_pf4 = st.columns([2.5, 1, 1, 1, 1])
    with col_ps:
        psearch = st.text_input("Pol Search", value=global_q, placeholder="Search policies by ID, name, or keyword...", label_visibility="collapsed", key="pol_search").strip()
    with col_pf1:
        payer_filter = st.selectbox("Payer", ["All Payers","Commercial","Medicare"], label_visibility="collapsed", key="pol_payer")
    with col_pf2:
        st.selectbox("Plan", ["All Plans"], label_visibility="collapsed", key="pol_plan")
    with col_pf3:
        status_filter = st.selectbox("Status", ["All","● Active","Inactive"], label_visibility="collapsed", key="pol_status")
    with col_pf4:
        st.selectbox("Sort", ["Newest","Oldest","Name A-Z"], label_visibility="collapsed", key="pol_sort")

    active_search = psearch or global_q

    if active_search:
        col_lbl, col_clr = st.columns([4, 1])
        with col_lbl:
            st.markdown(f'<div style="font-size:13px;font-weight:600;color:var(--slate-700);margin:8px 0 12px 0;">Policy search results for "<strong>{active_search}</strong>"</div>', unsafe_allow_html=True)
        with col_clr:
            if st.button("✕ Clear Search", key="clear_pol_srch"):
                st.session_state["global_search_input"] = ""
                st.session_state["pol_search"] = ""
                st.rerun()

    if not policies_data:
        render_empty_state("No policies configured", "Add medical coverage policies to data/policies.json.")
        return

    # Filter
    filtered = []
    for p in policies_data:
        pyr = str(p.get("payer","")).lower()
        pid = str(p.get("policy_id","")).lower()
        pname = str(p.get("policy_name","")).lower()
        sname = str(p.get("service_name","")).lower()
        cpt_str = " ".join(p.get("cpt_hcpcs_codes", [])).lower()
        icd_str = " ".join(p.get("icd10_codes", [])).lower()
        pol_stat = str(p.get("policy_status", "active")).strip().lower()
        is_active = (pol_stat == "active")

        if active_search:
            q = active_search.lower()
            if q not in pid and q not in pname and q not in pyr and q not in sname and q not in cpt_str and q not in icd_str:
                continue
        if payer_filter == "Commercial" and ("medicare" in pyr or "cms" in pyr): continue
        if payer_filter == "Medicare" and "medicare" not in pyr and "cms" not in pyr: continue
        if status_filter in ("● Active", "Active") and not is_active: continue
        if status_filter == "Inactive" and is_active: continue

        filtered.append(p)

    if not filtered:
        render_empty_state("No matching policies found", "Try searching with a different policy ID, name, or service keyword.")
        return

    # Pagination
    page_size = 6
    total_pages = max(1, math.ceil(len(filtered) / page_size))
    if "pol_page" not in st.session_state: st.session_state.pol_page = 1
    st.session_state.pol_page = min(st.session_state.pol_page, total_pages)
    page = st.session_state.pol_page
    start = (page - 1) * page_size
    page_items = filtered[start:start + page_size]

    # Policy rows
    for p in page_items:
        pol_id = p.get("policy_id","POL-000")
        pol_name = p.get("policy_name","Medical Policy")
        payer_name = p.get("payer","Payer")
        status = str(p.get("policy_status","active")).strip()
        is_active = status.lower() == "active"
        pyr_lower = payer_name.lower()
        is_medicare = "medicare" in pyr_lower or "cms" in pyr_lower
        payer_badge_cls = "badge-medicare" if is_medicare else "badge-commercial"
        payer_badge_label = "Medicare" if is_medicare else "Commercial"
        status_badge = f'<span class="badge badge-active">🟢 ACTIVE</span>' if is_active else f'<span class="badge badge-inactive">🔴 INACTIVE</span>'

        with st.expander(f"📄  {pol_id} — {pol_name} ({payer_name})", expanded=False):
            # Top metadata row
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap;">
                {status_badge}
                <span class="badge {payer_badge_cls}">{payer_badge_label}</span>
                <span style="font-size:12px;color:var(--slate-500);">Updated Aug 17, 2026</span>
            </div>
            """, unsafe_allow_html=True)

            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown("##### Policy Information")
                rules = p.get("rules", {})
                cpt_codes = p.get("cpt_hcpcs_codes", [])
                icd_codes = p.get("icd10_codes", [])
                age_req = p.get("age_requirement", {})
                sev_req = p.get("severity_requirement", {})
                prev_treat = p.get("previous_treatment_requirement", {})
                doc_req = p.get("documentation_requirement", [])
                prov_spec = p.get("provider_specialty_requirement", [])
                fac_type = p.get("facility_type_requirement", [])

                kv_rows = [
                    ("Policy ID", f'<span class="mono-code">{pol_id}</span>'),
                    ("Policy Name", pol_name),
                    ("Plan", payer_name),
                    ("Service", p.get("service_name", "—")),
                    ("Status", status.title()),
                ]
                for k, v in kv_rows:
                    st.markdown(f"**{k}:** {v}", unsafe_allow_html=True)

            with col_right:
                st.markdown("##### Authorization Criteria")
                cpt_str = ", ".join([f"`{c}`" for c in cpt_codes]) if cpt_codes else "—"
                icd_str = ", ".join([f"`{c}`" for c in icd_codes]) if icd_codes else "—"
                age_str = "—"
                if age_req and age_req.get("required"):
                    age_str = f"{age_req.get('minimum_age', '—')}–{age_req.get('maximum_age', '—')}"
                sev_str = ", ".join(sev_req.get("allowed_levels", [])) if sev_req and sev_req.get("required") else "—"
                doc_str = ", ".join(doc_req) if doc_req else "—"
                prov_str = ", ".join(prov_spec) if prov_spec else "—"
                fac_str = ", ".join(fac_type) if fac_type else "—"

                st.markdown(f"**CPT / HCPCS:** {cpt_str}", unsafe_allow_html=True)
                st.markdown(f"**ICD-10:** {icd_str}", unsafe_allow_html=True)
                st.markdown(f"**Age:** {age_str}")
                st.markdown(f"**Severity:** {sev_str}")
                st.markdown(f"**Documentation:** {doc_str}")
                st.markdown(f"**Provider Specialty:** {prov_str}")
                st.markdown(f"**Facility:** {fac_str}")

            # Coverage criteria checklist
            st.markdown("##### Coverage Criteria Checklist")
            checks = []
            if cpt_codes: checks.append(("✓", "CPT / HCPCS requirement", f"Codes: {', '.join(cpt_codes)}"))
            if icd_codes: checks.append(("✓", "Diagnosis requirement", f"ICD-10 codes required"))
            if age_req and age_req.get("required"): checks.append(("✓", "Age requirement", f"Ages {age_req.get('minimum_age','—')}–{age_req.get('maximum_age','—')}"))
            if sev_req and sev_req.get("required"): checks.append(("✓", "Severity requirement", f"{', '.join(sev_req.get('allowed_levels',[]))}"))
            if prev_treat and prev_treat.get("required"): checks.append(("✓", "Previous treatment requirement", f"Min {prev_treat.get('minimum_duration_days','—')} days"))
            if doc_req: checks.append(("✓", "Documentation requirement", f"{len(doc_req)} documents"))
            if prov_spec: checks.append(("✓", "Provider specialty requirement", f"{', '.join(prov_spec)}"))
            if fac_type: checks.append(("✓", "Facility type requirement", f"{', '.join(fac_type)}"))

            for icon, title, detail in checks:
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:13px;">
                    <span style="color:var(--green-600);font-weight:700;">{icon}</span>
                    <span style="font-weight:600;color:var(--slate-800);">{title}</span>
                    <span style="color:var(--slate-500);font-size:12px;margin-left:auto;">{detail}</span>
                </div>
                """, unsafe_allow_html=True)

    # Pagination controls
    pag_text = f"Showing {start+1} to {min(start+page_size, len(filtered))} of {len(filtered)} policies"
    st.markdown(f'<div style="font-size:13px;color:var(--slate-500);margin-top:8px;">{pag_text}</div>', unsafe_allow_html=True)

    if total_pages > 1:
        page_cols = st.columns(total_pages + 2)
        with page_cols[0]:
            if st.button("‹", key="pol_prev", disabled=(page <= 1)):
                st.session_state.pol_page = max(1, page - 1)
                st.rerun()
        for i in range(total_pages):
            with page_cols[i + 1]:
                if st.button(str(i + 1), key=f"pol_pg_{i+1}", type="primary" if (i+1)==page else "secondary"):
                    st.session_state.pol_page = i + 1
                    st.rerun()
        with page_cols[total_pages + 1]:
            if st.button("›", key="pol_next", disabled=(page >= total_pages)):
                st.session_state.pol_page = min(total_pages, page + 1)
                st.rerun()


# ============================================================
# 8. CASE VIEW (Unified)
# ============================================================

def render_case_view(case_data, on_back_callback=None, on_resubmit_callback=None):
    patient = case_data.get("patient") or {}
    request_info = case_data.get("request") or {}
    decision_info = case_data.get("decision") or {}
    prediction_info = case_data.get("prediction") or {}
    criteria_list = case_data.get("criteria") or []
    pdf_info = case_data.get("pdf") or {}
    audit_info = case_data.get("audit") or {}

    name = safe_title(patient.get("patient_name","Unknown"))
    pid = safe_str(patient.get("patient_id","N/A"))
    req_id = safe_str(request_info.get("id") or audit_info.get("request_id") or "REQ-001")
    svc = safe_title(request_info.get("requested_service") or patient.get("requested_service") or "Procedure")
    cpt = safe_upper(request_info.get("cpt_hcpcs_code") or patient.get("cpt_hcpcs_code") or "N/A")
    payer = safe_title(request_info.get("payer") or patient.get("payer") or "N/A")
    final_dec = str(decision_info.get("decision") or request_info.get("status") or "PENDING").upper()
    dt = format_iso_timestamp_full(request_info.get("created_at") or audit_info.get("created_at"))
    badge = get_status_badge_html(final_dec)

    col_hdr_l, col_hdr_r = st.columns([1, 1])
    with col_hdr_l:
        if st.button("← Back to Requests", key="btn_back"):
            if on_back_callback: on_back_callback()
            st.rerun()

    with col_hdr_r:
        try:
            report_pdf_bytes = generate_report(case_data)
            st.download_button(
                label="📑 Download Decision Report (PDF)",
                data=report_pdf_bytes,
                file_name=f"Prior_Auth_Decision_Report_{req_id}.pdf",
                mime="application/pdf",
                key=f"dl_rep_hdr_{req_id}",
                type="primary",
                use_container_width=True
            )
        except Exception as e:
            logger.warning(f"Could not render top report download button: {e}")

    st.markdown(f"""
    <div class="case-header-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
            <div>
                <div style="font-size:11px;font-weight:700;color:var(--teal-700);text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px;">Prior Authorization Case</div>
                <div style="font-size:16px;font-weight:700;font-family:'IBM Plex Mono',monospace;color:var(--slate-900);">{str(req_id)[:18]}</div>
            </div>
            <div>{badge}</div>
        </div>
        <div style="display:flex;align-items:baseline;gap:10px;margin-bottom:4px;">
            <h2 style="font-size:22px;font-weight:700;margin:0;">👤 {name}</h2>
            <span style="font-size:13px;color:var(--slate-500);font-family:'IBM Plex Mono',monospace;">MRN: {pid}</span>
        </div>
        <div style="font-size:14px;color:var(--slate-700);font-weight:500;">{svc} · <span class="mono-code">CPT {cpt}</span> · {payer}</div>
    </div>
    """, unsafe_allow_html=True)

    # Summary grid
    age = safe_str(patient.get("age")); gender = safe_title(patient.get("gender"))
    spec = safe_title(patient.get("provider_specialty")); fac = safe_title(patient.get("facility_type"))
    qty = safe_str(request_info.get("quantity") or patient.get("quantity") or "1")
    freq = safe_str(request_info.get("frequency") or patient.get("frequency") or "Single")

    st.markdown(f"""
    <div class="clinical-grid">
        <div class="clinical-item"><span class="clinical-label">Patient</span><span class="clinical-value">{name}</span></div>
        <div class="clinical-item"><span class="clinical-label">Age / Gender</span><span class="clinical-value">{age} / {gender}</span></div>
        <div class="clinical-item"><span class="clinical-label">Payer</span><span class="clinical-value">{payer}</span></div>
        <div class="clinical-item"><span class="clinical-label">Service</span><span class="clinical-value">{svc}</span></div>
        <div class="clinical-item"><span class="clinical-label">CPT / HCPCS</span><span class="clinical-value mono-code">{cpt}</span></div>
        <div class="clinical-item"><span class="clinical-label">Provider</span><span class="clinical-value">{spec}</span></div>
        <div class="clinical-item"><span class="clinical-label">Facility</span><span class="clinical-value">{fac}</span></div>
        <div class="clinical-item"><span class="clinical-label">Units</span><span class="clinical-value">{qty} ({freq})</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Missing Information Alert ───────────────────────────────
    missing_fields = []

    # CPT / HCPCS code check
    raw_cpt = patient.get("cpt_hcpcs_code") or request_info.get("cpt_hcpcs_code")
    if not raw_cpt or str(raw_cpt).strip().upper() in ("", "N/A", "NONE", "NULL"):
        missing_fields.append(("CPT / HCPCS Code", "The procedure code (CPT/HCPCS) was not found in the clinical document. Policy matching requires a valid CPT code."))

    # Diagnosis check
    if not patient.get("diagnosis"):
        missing_fields.append(("Diagnosis", "No diagnosis was extracted from the clinical document."))

    # ICD-10 code check
    if not patient.get("icd10_code"):
        missing_fields.append(("ICD-10 Code", "No ICD-10 diagnosis code was found in the clinical document."))

    # Age check
    if patient.get("age") is None:
        missing_fields.append(("Patient Age", "Patient age was not found in the clinical document."))

    # Payer check
    raw_payer = patient.get("payer")
    if not raw_payer or str(raw_payer).strip().upper() in ("", "N/A", "NONE", "NULL"):
        missing_fields.append(("Payer / Insurance", "No payer or insurance information was found."))

    # Severity check
    if not patient.get("severity"):
        missing_fields.append(("Severity", "Clinical severity level was not documented."))

    # Provider specialty check
    if not patient.get("provider_specialty"):
        missing_fields.append(("Provider Specialty", "The referring or ordering provider specialty was not found."))

    # Facility type check
    if not patient.get("facility_type"):
        missing_fields.append(("Facility Type", "The facility type was not documented."))

    # Requested service check
    raw_svc = patient.get("requested_service") or request_info.get("requested_service")
    if not raw_svc or str(raw_svc).strip().upper() in ("", "N/A", "NONE", "NULL"):
        missing_fields.append(("Requested Service", "No requested service or procedure name was extracted."))

    # Documentation items check — find items marked False
    doc_data = patient.get("documentation") or {}
    missing_doc_items = [k for k, v in doc_data.items() if v is False or v is None]
    if missing_doc_items:
        doc_list = ", ".join(missing_doc_items)
        missing_fields.append(("Documentation Items", f"The following documentation items are missing or not confirmed: {doc_list}"))

    # Check if documentation dict is empty entirely
    if not doc_data:
        missing_fields.append(("Documentation", "No documentation items were extracted from the clinical document."))

    if missing_fields:
        items_html = ""
        for field_name, field_desc in missing_fields:
            items_html += f"""
            <div style="display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid rgba(220,38,38,0.08);">
                <span style="flex-shrink:0;width:20px;height:20px;border-radius:50%;background:var(--red-100);color:var(--red-600);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:bold;margin-top:1px;">✕</span>
                <div>
                    <div style="font-size:13px;font-weight:600;color:var(--red-700);">{field_name}</div>
                    <div style="font-size:12px;color:var(--slate-600);margin-top:1px;">{field_desc}</div>
                </div>
            </div>"""

        st.markdown(f"""
        <div style="background:linear-gradient(135deg, #fef2f2 0%, #fff1f2 100%);border:1px solid var(--red-200, #fecaca);border-left:4px solid var(--red-500);border-radius:var(--radius-md);padding:16px 18px;margin-bottom:18px;box-shadow:var(--shadow-sm);">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
                <span style="font-size:18px;">⚠️</span>
                <span style="font-size:14px;font-weight:700;color:var(--red-700);">Missing Information Detected</span>
                <span style="font-size:11px;font-weight:600;color:var(--white);background:var(--red-500);padding:2px 8px;border-radius:10px;margin-left:auto;">{len(missing_fields)} item{"s" if len(missing_fields) != 1 else ""}</span>
            </div>
            <div style="font-size:12px;color:var(--slate-600);margin-bottom:10px;">The following required fields could not be extracted from the uploaded clinical document. This may affect policy evaluation and authorization decisions.</div>
            <div style="background:rgba(255,255,255,0.7);border-radius:var(--radius-sm);padding:4px 12px;">{items_html}</div>
        </div>
        """, unsafe_allow_html=True)

    col_l, col_r = st.columns([1.05, 1.15])

    with col_l:
        # PDF Document
        st.markdown('<div class="case-section-title">📄 Clinical Document</div>', unsafe_allow_html=True)
        pdf_bytes = pdf_info.get("bytes"); pdf_name = pdf_info.get("filename","Record.pdf"); pdf_size = pdf_info.get("size_str","PDF")
        if pdf_bytes:
            st.markdown(f'<div style="font-size:13px;margin-bottom:8px;"><strong>File:</strong> <code>{pdf_name}</code> · {pdf_size} · {dt}</div>', unsafe_allow_html=True)
            st.download_button("⬇ Download", data=pdf_bytes, file_name=pdf_name, mime="application/pdf", key=f"dl_{req_id}")
            with st.expander("📄 View PDF", expanded=True):
                render_pdf_viewer(pdf_bytes, height=450)
        else:
            st.caption("PDF not available in local cache.")

        # Extracted info
        st.markdown('<div class="case-section-title">🩺 Clinical Information</div>', unsafe_allow_html=True)
        diag = safe_title(patient.get("diagnosis")); icd = safe_upper(patient.get("icd10_code"))
        sev = safe_title(patient.get("severity")); sev_ev = patient.get("severity_evidence") or []
        sev_str = ", ".join(sev_ev) if sev_ev else "Documented"
        prev = patient.get("previous_treatment") or []
        if prev:
            ts = []
            for t in prev:
                if isinstance(t, dict):
                    n = t.get("treatment") or t.get("specific_treatment","Treatment")
                    d = f" ({t.get('duration_days')} days)" if t.get("duration_days") else ""
                    ts.append(f"{n}{d}")
                else: ts.append(str(t))
            treat_str = ", ".join(ts)
        else: treat_str = "None documented"
        doc = patient.get("documentation") or {}
        doc_html = " ".join([f'<span style="background:{"var(--green-50)" if v else "var(--red-50)"};color:{"var(--green-700)" if v else "var(--red-700)"};font-size:11px;padding:2px 6px;border-radius:4px;border:1px solid {"var(--green-100)" if v else "var(--red-100)"};margin-right:4px;">{"✓" if v else "✕"} {k}</span>' for k, v in doc.items()]) if doc else "Standard documentation"

        st.markdown(f"""
        <div style="background:var(--white);border:1px solid var(--slate-200);border-radius:var(--radius-md);padding:14px;margin-bottom:14px;">
            <div style="margin-bottom:8px;"><span style="font-size:11px;font-weight:700;color:var(--slate-500);text-transform:uppercase;">Diagnosis & ICD-10</span><div style="font-size:13px;font-weight:600;color:var(--slate-900);">{diag} <span class="mono-code">{icd}</span></div></div>
            <div style="margin-bottom:8px;"><span style="font-size:11px;font-weight:700;color:var(--slate-500);text-transform:uppercase;">Severity</span><div style="font-size:13px;color:var(--slate-800);">{sev} — {sev_str}</div></div>
            <div style="margin-bottom:8px;"><span style="font-size:11px;font-weight:700;color:var(--slate-500);text-transform:uppercase;">Prior Treatment</span><div style="font-size:13px;color:var(--slate-800);">{treat_str}</div></div>
            <div><span style="font-size:11px;font-weight:700;color:var(--slate-500);text-transform:uppercase;display:block;margin-bottom:4px;">Documentation</span><div>{doc_html}</div></div>
        </div>
        """, unsafe_allow_html=True)

        clin_info = patient.get("clinical_information") or {}
        if clin_info:
            with st.expander("📋 Clinical Narrative", expanded=False):
                for k, v in clin_info.items():
                    st.markdown(f"**{k.replace('_',' ').title()}:** {v}")

    with col_r:
        pol_obj = case_data.get("policy") or decision_info.get("policy") or {}
        raw_status = pol_obj.get("policy_status") if isinstance(pol_obj, dict) else None
        if not raw_status:
            dec_reason_lower = str(decision_info.get("reason", "")).lower()
            if "inactive" in dec_reason_lower:
                raw_status = "inactive"
            else:
                raw_status = "active"

        is_active_pol = str(raw_status).strip().lower() == "active"
        pol_name = decision_info.get("policy_name","Medical Policy")
        pol_id = decision_info.get("policy_id","POL-001")

        # ── 1. FINAL DETERMINATION ────────────────────────────────────
        st.markdown('<div class="case-section-title">🎯 Final Determination</div>', unsafe_allow_html=True)
        reason = decision_info.get("reason","Rule-engine evaluation completed.")
        failed = decision_info.get("failed_criteria") or []
        manual = decision_info.get("manual_review_reasons") or []

        if final_dec == "APPROVED":
            bc, ic, dc, hd = "decision-banner-approved", "✓", "var(--green-700)", "All coverage criteria met."
        elif final_dec == "DENIED":
            bc, ic, dc, hd = "decision-banner-denied", "✕", "var(--red-700)", "One or more required coverage criteria were not satisfied."
        elif final_dec in ("MANUAL REVIEW", "MANUAL_REVIEW"):
            bc, ic, dc, hd = "decision-banner-review", "⚠", "var(--amber-700)", "Additional information or manual evaluation is required."
        else:
            bc, ic, dc, hd = "decision-banner-no-pa", "ℹ", "var(--blue-700)", "Prior auth not required."

        fail_html = "".join([f"<li>{f}</li>" for f in failed]) if (failed and is_active_pol) else ""
        st.markdown(f"""
        <div class="decision-banner {bc}">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;"><span style="font-size:20px;font-weight:bold;color:{dc};">{ic}</span><span style="font-size:18px;font-weight:700;color:{dc};">{final_dec}</span></div>
            <div style="font-size:13px;color:var(--slate-800);margin-bottom:10px;">{hd}</div>
            <div style="font-size:12px;color:var(--slate-600);border-top:1px solid rgba(0,0,0,.06);padding-top:8px;"><strong>Policy:</strong> {pol_name} <span class="mono-code">{pol_id}</span></div>
            {f"<div style='margin-top:6px;font-size:12px;color:var(--red-700);'><strong>Failed:</strong><ul style='margin:4px 0 0 18px;padding:0;'>{fail_html}</ul></div>" if fail_html else ""}
        </div>
        """, unsafe_allow_html=True)

        try:
            report_pdf_bytes = generate_report(case_data)
            st.download_button(
                label="📑 Download Official Decision Report (PDF)",
                data=report_pdf_bytes,
                file_name=f"Prior_Auth_Decision_Report_{req_id}.pdf",
                mime="application/pdf",
                key=f"dl_rep_banner_{req_id}",
                use_container_width=True
            )
        except Exception as e:
            logger.warning(f"Could not render banner report download button: {e}")

        # ── 2. POLICY EVALUATION CRITERIA ─────────────────────────────
        st.markdown('<div class="case-section-title">⚙️ Policy Evaluation</div>', unsafe_allow_html=True)
        if is_active_pol and criteria_list:
            for c in criteria_list: _render_criterion(c)
        elif not is_active_pol:
            st.markdown("""
            <div style="background:var(--slate-100);border:1px solid var(--slate-200);border-radius:var(--radius-md);padding:12px 16px;font-size:12px;color:var(--slate-600);margin-bottom:14px;">
                <strong>⛔ Evaluation Halted:</strong> Individual criteria were not evaluated because the policy is inactive.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.caption("No criteria evaluated.")

        # ── 3. MANUAL REVIEW WORKFLOW SECTION ───────────────────────
        if final_dec in ("MANUAL REVIEW", "MANUAL_REVIEW"):
            st.markdown('<div class="case-section-title">📂 Additional Information Required</div>', unsafe_allow_html=True)

            missing_items = []
            if criteria_list:
                for c in criteria_list:
                    if str(c.get("status", "")).upper() in ("UNKNOWN", "MISSING"):
                        missing_items.append((c.get("criterion", "Required Evidence"), c.get("reason", "")))
            if not missing_items and manual:
                for m in manual:
                    missing_items.append(("Required Evidence", m))

            missing_html_list = []
            for crit_name, item_reason in missing_items:
                item_str = str(item_reason or crit_name)
                crit_norm = str(crit_name).lower()
                if "neuro" in item_str.lower() or "neuro" in crit_norm:
                    missing_html_list.append(
                        "<div style='margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid rgba(217,119,6,0.15);'>"
                        "<span style='font-size:13px;font-weight:700;color:var(--amber-700);'>⚠ Neurological examination</span><br/>"
                        "<span style='font-size:12px;color:var(--slate-600);'>Please provide documented neurological examination findings (e.g. sensory, motor strength, reflexes, straight-leg raise findings).</span>"
                        "</div>"
                    )
                elif any(img in item_str.lower() or img in crit_norm for img in ["imaging", "x-ray", "xray", "mri", "ct"]):
                    missing_html_list.append(
                        "<div style='margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid rgba(217,119,6,0.15);'>"
                        "<span style='font-size:13px;font-weight:700;color:var(--amber-700);'>⚠ Relevant imaging report</span><br/>"
                        "<span style='font-size:12px;color:var(--slate-600);'>Please provide the relevant X-ray/MRI/CT REPORT or documented imaging findings.</span>"
                        "</div>"
                    )
                else:
                    missing_html_list.append(
                        f"<div style='margin-bottom:8px;'><span style='font-size:13px;font-weight:700;color:var(--amber-700);'>⚠ {crit_name}</span><br/><span style='font-size:12px;color:var(--slate-600);'>{item_str}</span></div>"
                    )

            missing_details_html = "".join(missing_html_list) if missing_html_list else "<div style='font-size:12px;color:var(--amber-700);'>⚠ Required policy evidence was not available in submitted documents.</div>"

            st.markdown(f"""
            <div style="background:var(--amber-50);border:1px solid var(--amber-200, #fde68a);border-radius:var(--radius-md);padding:16px;margin-bottom:14px;">
                <div style="font-size:13px;font-weight:700;color:var(--amber-800);margin-bottom:4px;">ADDITIONAL INFORMATION REQUIRED</div>
                <div style="font-size:12px;color:var(--slate-700);margin-bottom:12px;">The authorization cannot be automatically approved because the following required evidence was not found:</div>
                {missing_details_html}
                <div style="font-size:12px;color:var(--slate-600);font-style:italic;margin-top:8px;">Upload only the clinical document(s) requested above. You do not need to resubmit the original Patient History or Prior Authorization Form.</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='font-weight:700;font-size:13px;color:var(--slate-800);margin-bottom:4px;'>Provide Missing Clinical Evidence</div>", unsafe_allow_html=True)
            supp_files = st.file_uploader(
                "Provide Missing Clinical Evidence",
                type=["pdf"],
                accept_multiple_files=True,
                key=f"resubmit_pdf_{req_id}",
                help="Upload supplemental text-based clinical report PDF(s)"
            )
            st.markdown(
                "<div style='font-size:11px;color:var(--slate-500);margin-top:2px;margin-bottom:10px;'>"
                "<strong>Examples:</strong> Neurological examination report, X-ray/MRI/CT report, treatment documentation, procedure report."
                "</div>",
                unsafe_allow_html=True
            )

            if supp_files:
                if st.button("Submit Additional Information & Re-evaluate →", type="primary", use_container_width=True, key=f"btn_resubmit_{req_id}"):
                    if on_resubmit_callback:
                        on_resubmit_callback(case_data, supp_files)

        # ── 4. AUDIT TIMELINE ──────────────────────────────────────────
        st.markdown('<div class="case-section-title">📋 Audit Timeline</div>', unsafe_allow_html=True)
        _render_timeline(case_data)


# ============================================================
# 9. DEPRECATED AI PREDICTION HELPER (REMOVED FROM UI)
# ============================================================

def _render_ai_prediction(pred):
    """Deprecated AI prediction renderer. Retained as empty no-op for backward compatibility."""
    pass


def _render_criterion(c):
    s = str(c.get("status","UNKNOWN")).upper(); n = c.get("criterion","Criterion"); r = c.get("reason","")
    if s in ("PASSED", "PASS"): cc, ic, st_txt, sc = "criterion-card-passed","✓","PASSED","var(--green-700)"
    elif s in ("FAILED", "FAIL"): cc, ic, st_txt, sc = "criterion-card-failed","✕","FAILED","var(--red-700)"
    elif s in ("NOT_APPLICABLE", "N/A"): cc, ic, st_txt, sc = "criterion-card-na","—","N/A","var(--slate-500)"
    else: cc, ic, st_txt, sc = "criterion-card-warn","⚠","MISSING" if s == "UNKNOWN" else s,"var(--amber-700)"
    st.markdown(f"""
    <div class="criterion-card {cc}">
        <div class="criterion-top-row"><span class="criterion-title"><span style="color:{sc};font-weight:bold;">{ic}</span> {n}</span><span style="font-size:11px;font-weight:700;color:{sc};font-family:'IBM Plex Mono',monospace;">{st_txt}</span></div>
        <div class="criterion-reason">{r}</div>
    </div>
    """, unsafe_allow_html=True)


def _render_timeline(case_data):
    a = case_data.get("audit") or {}
    req = case_data.get("request") or {}
    dt = format_iso_timestamp_full(a.get("created_at") or req.get("created_at"))
    rid = safe_str(a.get("request_id") or req.get("id"))
    pid = safe_str(a.get("patient_db_id") or case_data.get("patient",{}).get("id"))
    did = safe_str(a.get("decision_id") or case_data.get("decision",{}).get("id"))
    pol_id = safe_str(case_data.get("decision",{}).get("policy_id") or "POL-001")
    resubmitted = case_data.get("resubmitted") or req.get("resubmitted") or False

    # Check Patient Insurance Validation State
    cov_val = case_data.get("coverage_validation") or case_data.get("decision", {}).get("coverage_validation") or {}
    ins_info = case_data.get("insurance") or case_data.get("decision", {}).get("insurance") or {}

    is_valid_cov = cov_val.get("is_valid")
    if is_valid_cov is None:
        if ins_info and "is_valid" in ins_info:
            is_valid_cov = ins_info.get("is_valid")
        else:
            dec_reason = str(case_data.get("decision", {}).get("reason", "")).lower()
            is_valid_cov = not any(w in dec_reason for w in ["insurance coverage", "coverage expired", "does not have valid coverage"])

    cov_stat_text = str(cov_val.get("status") or ins_info.get("coverage_status") or ("ACTIVE" if is_valid_cov else "EXPIRED")).upper()

    pol_obj = case_data.get("policy") or case_data.get("decision", {}).get("policy") or {}
    raw_status = pol_obj.get("policy_status") if isinstance(pol_obj, dict) else None
    if not raw_status:
        dec_reason_lower = str(case_data.get("decision", {}).get("reason", "")).lower()
        if "inactive" in dec_reason_lower:
            raw_status = "inactive"
        else:
            raw_status = "active"

    is_active_pol = str(raw_status).strip().lower() == "active"

    steps = [
        f'<div class="timeline-step"><div class="timeline-dot"></div><div class="timeline-content"><div class="timeline-title">📄 Document Received</div><div class="timeline-time">{dt}</div></div></div>',
        f'<div class="timeline-step"><div class="timeline-dot"></div><div class="timeline-content"><div class="timeline-title">👤 Patient Data Extracted</div><div class="timeline-time">DB: {pid[:12]}...</div></div></div>',
        f'<div class="timeline-step"><div class="timeline-dot"></div><div class="timeline-content"><div class="timeline-title">🔒 Patient Identity Verified</div><div class="timeline-time">PII Isolation Engine</div></div></div>',
    ]

    if is_valid_cov:
        steps.append(f'<div class="timeline-step"><div class="timeline-dot"></div><div class="timeline-content"><div class="timeline-title">🛡️ Patient Insurance Checked</div><div class="timeline-time">Status: <span style="color:var(--green-700);font-weight:700;">🟢 ACTIVE</span></div></div></div>')
        steps.append(f'<div class="timeline-step"><div class="timeline-dot"></div><div class="timeline-content"><div class="timeline-title">📋 Policy Matched</div><div class="timeline-time">Policy: {pol_id}</div></div></div>')

        if is_active_pol:
            status_badge_html = '<span style="color:var(--green-700);font-weight:700;">🟢 ACTIVE</span>'
            eval_step_html = '<div class="timeline-step"><div class="timeline-dot"></div><div class="timeline-content"><div class="timeline-title">⚙️ Policy Criteria Evaluated</div><div class="timeline-time">Deterministic Rule Engine</div></div></div>'
        else:
            status_badge_html = '<span style="color:var(--red-700);font-weight:700;">🔴 INACTIVE</span>'
            eval_step_html = '<div class="timeline-step"><div class="timeline-dot" style="background:var(--red-500);"></div><div class="timeline-content"><div class="timeline-title">⛔ Rule Evaluation</div><div class="timeline-time" style="color:var(--red-700);font-weight:600;">NOT PERFORMED (Policy is inactive)</div></div></div>'

        steps.append(f'<div class="timeline-step"><div class="timeline-dot"></div><div class="timeline-content"><div class="timeline-title">🛡️ Policy Status Checked</div><div class="timeline-time">Status: {status_badge_html}</div></div></div>')
        steps.append(eval_step_html)
    else:
        steps.append(f'<div class="timeline-step"><div class="timeline-dot" style="background:var(--red-500);"></div><div class="timeline-content"><div class="timeline-title">🛡️ Patient Insurance Checked</div><div class="timeline-time" style="color:var(--red-700);font-weight:600;">Status: 🔴 {cov_stat_text}</div></div></div>')
        steps.append(f'<div class="timeline-step"><div class="timeline-dot" style="background:var(--red-500);"></div><div class="timeline-content"><div class="timeline-title">⛔ Policy Evaluation</div><div class="timeline-time" style="color:var(--red-700);font-weight:600;">NOT PERFORMED (Patient insurance is {cov_stat_text})</div></div></div>')

    steps.append(f'<div class="timeline-step"><div class="timeline-dot"></div><div class="timeline-content"><div class="timeline-title">🎯 Decision Recorded</div><div class="timeline-time">Decision Recorded · Req: {rid[:12]}...</div></div></div>')

    if resubmitted and is_valid_cov and is_active_pol:
        steps.extend([
            '<div class="timeline-step"><div class="timeline-dot" style="background:var(--blue-600);"></div><div class="timeline-content"><div class="timeline-title">📂 Additional Information Submitted</div><div class="timeline-time">Supplemental Document Received (Existing Request Re-evaluation)</div></div></div>',
            '<div class="timeline-step"><div class="timeline-dot" style="background:var(--blue-600);"></div><div class="timeline-content"><div class="timeline-title">⚙️ Policy Re-evaluated</div><div class="timeline-time">Existing Request Policy Criteria Re-evaluation</div></div></div>',
            f'<div class="timeline-step"><div class="timeline-dot" style="background:var(--blue-600);"></div><div class="timeline-content"><div class="timeline-title">🎯 Updated Decision Recorded</div><div class="timeline-time">Updated Decision: {did[:12]}...</div></div></div>'
        ])

    steps_body = "\n".join(steps)
    timeline_html = f'<div class="audit-timeline">\n{steps_body}\n</div>'

    st.markdown(timeline_html, unsafe_allow_html=True)


# ============================================================
# 10. AUDIT VIEW
# ============================================================

def render_audit_view(db_status, requests):
    st.markdown("""
    <div class="page-header"><div class="page-header-left">
        <h1>Audit & System Health</h1>
        <p>Database connectivity and persistence logs.</p>
    </div></div>
    """, unsafe_allow_html=True)

    is_conn = db_status.get("status") == "connected"
    st.markdown(f"""
    <div style="background:var(--white);border:1px solid var(--slate-200);border-radius:var(--radius-lg);padding:20px;margin-bottom:20px;box-shadow:var(--shadow-sm);">
        <h3 style="font-size:16px;margin:0 0 12px 0;">Database Status</h3>
        <div style="display:flex;gap:24px;font-size:13px;">
            <div><strong>Connection:</strong> {db_status.get('status','unknown').upper()}</div>
            <div><strong>Message:</strong> {db_status.get('message','—')}</div>
            <div><strong>Persisted Cases:</strong> {len(requests)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if requests:
        st.markdown("### Activity Ledger")
        for r in requests[:15]:
            p = r.get("patients") or {}; dl = r.get("decisions") or []
            dec = dl[0].get("final_decision",r.get("request_status")) if dl else r.get("request_status","")
            badge = get_status_badge_html(dec)
            st.markdown(f"""
            <div style="background:var(--white);border:1px solid var(--slate-200);border-radius:var(--radius-sm);padding:10px 14px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;font-size:12px;">
                <div><span style="font-family:'IBM Plex Mono',monospace;font-weight:600;">{str(r.get('id',''))[:14]}...</span> · Patient: {p.get('patient_name','Unknown')} · {r.get('requested_service','—')}</div>
                <div style="display:flex;align-items:center;gap:12px;"><span style="color:var(--slate-500);font-family:'IBM Plex Mono',monospace;">{format_iso_timestamp(r.get('created_at'))}</span>{badge}</div>
            </div>
            """, unsafe_allow_html=True)


# ============================================================
# 11. EMPTY & ERROR STATES
# ============================================================

def render_empty_state(title="No authorization requests yet", text="Upload a clinical document in New Request to begin."):
    st.markdown(f"""
    <div class="empty-state-box">
        <div class="empty-state-icon">📋</div>
        <div class="empty-state-title">{title}</div>
        <div class="empty-state-text">{text}</div>
    </div>
    """, unsafe_allow_html=True)

def render_error_state(msg="Unable to load records.", tech_err=None):
    st.markdown(f"""
    <div style="background:var(--red-50);border:1px solid var(--red-100);border-radius:var(--radius-md);padding:16px;margin:16px 0;">
        <div style="font-size:14px;font-weight:600;color:var(--red-700);margin-bottom:4px;">⚠ {msg}</div>
        <div style="font-size:12px;color:var(--slate-600);">Verify database connectivity or reload.</div>
    </div>
    """, unsafe_allow_html=True)
    if tech_err:
        with st.expander("Technical Details"):
            st.code(tech_err, language="text")


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _get_decision(r):
    dl = r.get("decisions") or []
    if dl and len(dl) > 0:
        sorted_decs = sorted(dl, key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return str(sorted_decs[0].get("final_decision") or r.get("request_status") or "PENDING").upper()
    return str(r.get("request_status") or "PENDING").upper()

def _matches_search(r, q):
    if not q:
        return True
    q = str(q).lower().strip()
    if not q:
        return True
    p = r.get("patients") or {}
    searchable_values = [
        p.get("patient_name", ""),
        p.get("patient_number", ""),
        p.get("patient_id", ""),
        r.get("request_number", ""),
        r.get("id", ""),
        r.get("cpt_hcpcs_code", ""),
        r.get("requested_service", ""),
        r.get("payer", ""),
        p.get("payer", ""),
        _get_decision(r)
    ]
    return any(q in str(v).lower() for v in searchable_values if v is not None)


# ============================================================
# 12. PRIVACY & VERIFICATION UI COMPONENTS
# ============================================================

def render_intake_stage_tracker(current_stage: int = 1):
    """
    Renders the 5-step Privacy & Intake workflow stage tracker.
    STEP 1 Upload -> STEP 2 Verify Patient -> STEP 3 Protect Patient Data -> STEP 4 AI Analysis -> STEP 5 Authorization Decision
    """
    stages = [
        ("1", "Upload Documents"),
        ("2", "Verify Patient"),
        ("3", "Protect Patient Data"),
        ("4", "AI Analysis"),
        ("5", "Authorization Decision")
    ]

    html_steps = []
    for idx, (num, label) in enumerate(stages, 1):
        if idx < current_stage:
            css = "background: var(--green-600); color: white; border-color: var(--green-600);"
            icon = "✓"
            text_style = "color: var(--green-700); font-weight: 600;"
        elif idx == current_stage:
            css = "background: var(--blue-600); color: white; border-color: var(--blue-600);"
            icon = num
            text_style = "color: var(--slate-900); font-weight: 700;"
        else:
            css = "background: var(--slate-100); color: var(--slate-500); border-color: var(--slate-300);"
            icon = num
            text_style = "color: var(--slate-500); font-weight: 400;"

        step_html = f'<div style="display: flex; align-items: center; gap: 8px;"><div style="width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; {css}">{icon}</div><div style="font-size: 13px; {text_style}">{label}</div></div>'
        html_steps.append(step_html)

    div_bar = f'<div style="background: white; border: 1px solid var(--slate-200); border-radius: var(--radius-lg); padding: 14px 20px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">{"".join(html_steps)}</div>'
    st.markdown(div_bar, unsafe_allow_html=True)


def render_verification_status(verification: Dict[str, Any]):
    """
    Renders structured patient identity verification results card,
    field match breakdown badges, age discrepancy warnings, and PII protection banner.
    """
    is_verified = verification.get("verified", False)
    status = str(verification.get("status", "UNKNOWN")).upper()
    score = verification.get("score", 0)
    fields = verification.get("fields", {})
    discrepancies = verification.get("discrepancies", [])
    age_warnings = verification.get("age_warnings", [])
    calc_age = verification.get("calculated_age")

    hist_id = verification.get("history_identity") or {}
    pa_id = verification.get("pa_identity") or {}
    hist_name = hist_id.get("patient_name") or "Document 1"
    pa_name = pa_id.get("patient_name") or "Document 2"

    if status in ("INSUFFICIENT_DATA", "INSUFFICIENT"):
        st.markdown(f'''<div style="background: var(--amber-50); border: 1.5px solid var(--amber-500); border-radius: var(--radius-lg); padding: 18px 22px; margin: 16px 0;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
<div style="display: flex; align-items: center; gap: 10px;">
<div style="background: var(--amber-600); color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 700;">⚠</div>
<div>
<div style="font-size: 16px; font-weight: 700; color: var(--amber-800);">INSUFFICIENT IDENTITY INFORMATION</div>
<div style="font-size: 12px; color: var(--slate-700);">Complete identity fields were not available for cross-document matching</div>
</div>
</div>
</div>
</div>''', unsafe_allow_html=True)

    elif is_verified:
        st.markdown(f'''<div style="background: var(--green-50); border: 1.5px solid var(--green-600); border-radius: var(--radius-lg); padding: 18px 22px; margin: 16px 0;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
<div style="display: flex; align-items: center; gap: 10px;">
<div style="background: var(--green-600); color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 700;">✓</div>
<div>
<div style="font-size: 16px; font-weight: 800; color: var(--green-700); letter-spacing: .01em;">✓ IDENTITY VERIFIED</div>
<div style="font-size: 12px; color: var(--slate-700);">Patient identity matched deterministically across Patient History &amp; PA Request Form</div>
</div>
</div>
<div style="background: var(--green-100); color: var(--green-700); font-weight: 700; font-size: 13px; padding: 6px 14px; border-radius: 20px; border: 1px solid var(--green-100);">
✓ MATCH ({score}%)
</div>
</div>
<div style="display: flex; gap: 24px; font-size: 12px; color: var(--slate-700); background: white; padding: 10px 14px; border-radius: var(--radius-md); border: 1px solid var(--green-100);">
<div><span style="font-weight: 600; color: var(--slate-500); font-size: 11px; text-transform: uppercase;">Patient History:</span> <strong>{hist_name}</strong></div>
<div><span style="font-weight: 600; color: var(--slate-500); font-size: 11px; text-transform: uppercase;">PA Request:</span> <strong>{pa_name}</strong></div>
</div>
</div>''', unsafe_allow_html=True)

    else:
        diff_items = "".join([f"<li>{d}</li>" for d in discrepancies])
        st.markdown(f'''<div style="background: var(--red-50); border: 1.5px solid var(--red-600); border-radius: var(--radius-lg); padding: 20px 24px; margin: 16px 0;">
<div style="display: flex; align-items: flex-start; gap: 12px;">
<div style="font-size: 24px;">✕</div>
<div style="flex: 1;">
<div style="font-size: 18px; font-weight: 800; color: var(--red-700); margin-bottom: 6px;">✕ IDENTITY VERIFICATION FAILED</div>
<div style="font-size: 14px; color: var(--slate-800); margin-bottom: 10px;">The patient information in the submitted documents does not match. Differences detected:</div>
<ul style="color: var(--red-700); font-size: 13px; font-weight: 600; margin: 0 0 12px 0; padding-left: 20px;">{diff_items}</ul>
<div style="background: white; border: 1px solid var(--red-100); border-radius: var(--radius-md); padding: 10px 14px; font-size: 13px; font-weight: 700; color: var(--red-700);">🚫 MISMATCH — Authorization evaluation has been stopped.</div>
</div>
</div>
</div>''', unsafe_allow_html=True)

    # Field Badges Grid
    if fields:
        cols = st.columns(len(fields))
        for col, (f_name, f_status) in zip(cols, fields.items()):
            label = f_name.replace('_', ' ').title()
            if f_status == "MATCH":
                badge_css = "background: var(--green-50); color: var(--green-700); border: 1px solid var(--green-100);"
                icon = "✓ MATCH"
            elif f_status == "MISMATCH":
                badge_css = "background: var(--red-50); color: var(--red-700); border: 1px solid var(--red-100);"
                icon = "✕ MISMATCH"
            else:
                badge_css = "background: var(--amber-50); color: var(--amber-700); border: 1px solid var(--amber-100);"
                icon = "⚠ N/A"

            with col:
                st.markdown(f'''<div style="background: white; border: 1px solid var(--slate-200); border-radius: var(--radius-md); padding: 10px; text-align: center;">
<div style="font-size: 11px; color: var(--slate-500); text-transform: uppercase; font-weight: 600;">{label}</div>
<div style="font-size: 12px; font-weight: 700; margin-top: 4px; padding: 2px 6px; border-radius: 4px; display: inline-block; {badge_css}">{icon}</div>
</div>''', unsafe_allow_html=True)

    # Age Warnings
    if age_warnings:
        warn_html = "".join([f"<div>⚠️ {w}</div>" for w in age_warnings])
        st.markdown(f'''<div style="background: var(--amber-50); border: 1px solid var(--amber-100); border-radius: var(--radius-md); padding: 12px 16px; margin-top: 12px; font-size: 13px; color: var(--amber-700); font-weight: 600;">{warn_html}</div>''', unsafe_allow_html=True)

    # PII Protection Banner (if verified)
    if is_verified:
        age_str = f"Calculated Age: {calc_age}" if calc_age is not None else "Age derived"
        st.markdown(f'''<div style="background: var(--slate-50); border: 1px solid var(--slate-200); border-radius: var(--radius-md); padding: 14px 18px; margin-top: 14px;">
<div style="font-size: 13px; font-weight: 700; color: var(--slate-800); margin-bottom: 6px;">🔒 Privacy Boundary &amp; De-identification Active</div>
<div style="display: flex; gap: 16px; font-size: 12px; color: var(--slate-600); flex-wrap: wrap;">
<span>✓ PII Identified &amp; Separated</span>
<span>✓ Raw Text Redacted</span>
<span>✓ {age_str}</span>
<span>✓ Zero PII passed to LLM</span>
</div>
</div>''', unsafe_allow_html=True)


def render_processing_insurance_validation(cov_validation: Dict[str, Any]):
    """
    Renders a compact, high-precision processing-stage Patient Insurance Validation card during New Request workflow.
    """
    if not cov_validation:
        return

    ins = cov_validation.get("insurance") or {}
    member_id = ins.get("member_id", "MEM-1005")
    policy_id = ins.get("policy_id", "POL-001")
    start_date = ins.get("coverage_start_date", "—")
    end_date = ins.get("coverage_end_date") or "No End Date"
    is_valid = cov_validation.get("is_valid", False)
    status = str(cov_validation.get("status") or "INACTIVE").upper()

    if is_valid:
        st.markdown(f"""
        <div style="background:var(--green-50);border:1px solid var(--green-100);border-left:4px solid var(--green-600);border-radius:var(--radius-md);padding:10px 14px;margin:8px 0 12px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                <div style="font-size:12px;font-weight:700;color:var(--slate-900);">🛡️ PATIENT INSURANCE VALIDATION · Member ID: <span class="mono-code">{member_id}</span></div>
                <div style="background:var(--green-100);color:var(--green-700);font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;border:1px solid var(--green-100);">🟢 COVERAGE ACTIVE</div>
            </div>
            <div style="font-size:11px;color:var(--slate-700);"><strong>Coverage Period:</strong> {start_date} – {end_date} | <strong>Policy:</strong> <span class="mono-code">{policy_id}</span></div>
            <div style="font-size:11px;color:var(--slate-700);margin-top:2px;">Patient has valid coverage for this authorization request date.</div>
            <div style="font-size:11px;color:var(--slate-500);margin-top:2px;">→ Continue to Policy Retrieval</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:var(--red-50);border:1px solid var(--red-100);border-left:4px solid var(--red-600);border-radius:var(--radius-md);padding:10px 14px;margin:8px 0 12px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                <div style="font-size:12px;font-weight:700;color:var(--slate-900);">🛡️ PATIENT INSURANCE VALIDATION · Member ID: <span class="mono-code">{member_id}</span></div>
                <div style="background:var(--red-100);color:var(--red-700);font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;border:1px solid var(--red-100);">🔴 COVERAGE {status}</div>
            </div>
            <div style="font-size:11px;color:var(--slate-700);"><strong>Coverage Period:</strong> {start_date} – {end_date} | <strong>Policy:</strong> <span class="mono-code">{policy_id}</span></div>
            <div style="font-size:11px;color:var(--red-700);font-weight:600;margin-top:2px;">Patient does not have valid coverage for the authorization request date.</div>
            <div style="font-size:11px;color:var(--red-700);margin-top:2px;font-weight:600;">→ Automated policy evaluation stopped. Request will proceed to Manual Review.</div>
        </div>
        """, unsafe_allow_html=True)


def render_processing_policy_validation(policy: Dict[str, Any]):
    """
    Renders a compact, high-precision processing-stage Policy Validation card during New Request workflow.
    """
    if not policy:
        return

    pol_id = policy.get("policy_id", "POL-001")
    pol_name = policy.get("policy_name", "Medical Coverage Policy")
    raw_status = policy.get("policy_status")
    is_active = (raw_status is not None) and (str(raw_status).strip().lower() == "active")

    if is_active:
        st.markdown(f"""
        <div style="background:var(--green-50);border:1px solid var(--green-100);border-left:4px solid var(--green-600);border-radius:var(--radius-md);padding:10px 14px;margin:8px 0 12px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                <div style="font-size:12px;font-weight:700;color:var(--slate-900);">🛡️ POLICY VALIDATION · {pol_name} <span class="mono-code">{pol_id}</span></div>
                <div style="background:var(--green-100);color:var(--green-700);font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;border:1px solid var(--green-100);">🟢 ACTIVE</div>
            </div>
            <div style="font-size:11px;color:var(--slate-700);"><strong>Evaluation:</strong> <span style="color:var(--green-700);font-weight:700;">PROCEED</span> — Policy is active and eligible for authorization evaluation.</div>
            <div style="font-size:11px;color:var(--slate-500);margin-top:2px;">→ Proceeding to Rule Engine...</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:var(--red-50);border:1px solid var(--red-100);border-left:4px solid var(--red-600);border-radius:var(--radius-md);padding:10px 14px;margin:8px 0 12px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                <div style="font-size:12px;font-weight:700;color:var(--slate-900);">🛡️ POLICY VALIDATION · {pol_name} <span class="mono-code">{pol_id}</span></div>
                <div style="background:var(--red-100);color:var(--red-700);font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;border:1px solid var(--red-100);">🔴 INACTIVE</div>
            </div>
            <div style="font-size:11px;color:var(--slate-700);"><strong>Evaluation:</strong> <span style="color:var(--red-700);font-weight:700;">NOT PERFORMED</span> — Policy is currently inactive and cannot be used for authorization evaluation.</div>
            <div style="font-size:11px;color:var(--red-700);margin-top:2px;font-weight:600;">→ Rule evaluation halted. Request will proceed to Manual Review.</div>
        </div>
        """, unsafe_allow_html=True)

