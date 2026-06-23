# Dato skrevet: 23.06.2026
# Forfatter: William Berg Steffenak - copyright
# Prosjekt: Lokal CRM / Entreprenør-system V3.2 Layout
# Fil: app_v32_layout.py

from datetime import date, datetime
from io import BytesIO
import re

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from supabase import create_client, Client

# =========================================================
# HARDCODET SUPABASE-KONFIG
# =========================================================
SUPABASE_URL = "https://ktfbfqdwhetjjlhjcyqq.supabase.co/rest/v1/"
SUPABASE_KEY = "sb_publishable_HNzmTyr-Qd-cWDV1OsMVaA_LzUaZgYO"

st.set_page_config(page_title="Lokal CRM V3.2", page_icon="📋", layout="wide")

# =========================================================
# STIL / LAYOUT
# =========================================================
CUSTOM_CSS = """
<style>
.block-container {padding-top: 1.1rem; padding-bottom: 1.2rem; max-width: 1500px;}
div[data-testid="stMetric"] {background:#f8fafc; border:1px solid #e2e8f0; padding:14px 16px; border-radius:16px;}
.card {background:#ffffff; border:1px solid #e2e8f0; border-radius:18px; padding:16px 18px; box-shadow:0 1px 2px rgba(15,23,42,0.05);} 
.hero {background:linear-gradient(135deg,#0f172a 0%, #1e293b 60%, #334155 100%); color:white; border-radius:22px; padding:20px 24px; margin-bottom:12px;}
.hero h1 {margin:0; font-size:2.1rem;}
.hero p {margin:8px 0 0 0; color:#cbd5e1;}
.section-title {font-size:1.2rem; font-weight:700; margin:0 0 10px 0;}
.soft {color:#64748b; font-size:0.95rem;}
.pill {display:inline-block; padding:4px 10px; border-radius:999px; font-size:0.82rem; font-weight:600; margin:0 6px 6px 0;}
.pill-blue {background:#dbeafe; color:#1d4ed8;}
.pill-green {background:#dcfce7; color:#15803d;}
.pill-amber {background:#fef3c7; color:#b45309;}
.pill-red {background:#fee2e2; color:#b91c1c;}
.pill-slate {background:#e2e8f0; color:#334155;}
.small-note {font-size:0.82rem; color:#64748b;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# =========================================================
# HJELPEFUNKSJONER
# =========================================================
def normalize_supabase_url(raw_url: str) -> str:
    url = raw_url.strip().rstrip("/")
    for suffix in ("/rest/v1", "/auth/v1", "/storage/v1"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url


@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(normalize_supabase_url(SUPABASE_URL), SUPABASE_KEY.strip())


client = get_supabase_client()


def clear_all_caches():
    for fn in [
        fetch_table,
        fetch_invoice_basis,
        fetch_equipment_maintenance_status,
        fetch_customers_minimal,
        fetch_leads_minimal,
        fetch_quotes_enriched,
        fetch_projects_enriched,
        fetch_project_logs_enriched,
        fetch_equipment_minimal,
        fetch_project_log_equipment,
        fetch_equipment_service_logs,
    ]:
        fn.clear()


@st.cache_data(ttl=10)
def fetch_table(table_name: str, order_by: str | None = None, ascending: bool = True):
    query = client.table(table_name).select("*")
    if order_by:
        query = query.order(order_by, desc=not ascending)
    return query.execute().data or []


@st.cache_data(ttl=10)
def fetch_invoice_basis():
    return client.table("v_invoice_basis").select("*").order("updated_at", desc=True).execute().data or []


@st.cache_data(ttl=10)
def fetch_equipment_maintenance_status():
    return client.table("v_equipment_maintenance_status").select("*").order("name").execute().data or []


@st.cache_data(ttl=10)
def fetch_customers_minimal():
    return client.table("customers").select("id,name,address,phone,email,customer_type,note").order("name").execute().data or []


@st.cache_data(ttl=10)
def fetch_leads_minimal():
    return client.table("leads").select("id,description,customer_id,status").order("created_at", desc=True).execute().data or []


@st.cache_data(ttl=10)
def fetch_equipment_minimal():
    return client.table("equipment").select("id,name,category,status").order("name").execute().data or []


@st.cache_data(ttl=10)
def fetch_project_log_equipment():
    return client.table("project_log_equipment").select("*").order("created_at", desc=True).execute().data or []


@st.cache_data(ttl=10)
def fetch_equipment_service_logs():
    return client.table("equipment_service_logs").select("*").order("service_date", desc=True).execute().data or []


@st.cache_data(ttl=10)
def fetch_quotes_enriched():
    quotes = fetch_table("quotes", "created_at", ascending=False)
    customer_lookup = {c["id"]: c for c in fetch_customers_minimal()}
    enriched = []
    for q in quotes:
        row = dict(q)
        cust = customer_lookup.get(q.get("customer_id"), {})
        row["customer_name"] = cust.get("name", "Ukjent")
        row["customer_address"] = cust.get("address")
        enriched.append(row)
    return enriched


@st.cache_data(ttl=10)
def fetch_projects_enriched():
    projects = fetch_table("projects", "created_at", ascending=False)
    customer_lookup = {c["id"]: c for c in fetch_customers_minimal()}
    quote_lookup = {q["id"]: q for q in fetch_quotes_enriched()}
    enriched = []
    for p in projects:
        row = dict(p)
        cust = customer_lookup.get(p.get("customer_id"), {})
        row["customer_name"] = cust.get("name", "Ukjent")
        row["customer_phone"] = cust.get("phone")
        row["customer_email"] = cust.get("email")
        row["customer_type"] = cust.get("customer_type")
        row["quote_status"] = quote_lookup.get(p.get("quote_id"), {}).get("status")
        row["quote_price"] = quote_lookup.get(p.get("quote_id"), {}).get("price")
        enriched.append(row)
    return enriched


@st.cache_data(ttl=10)
def fetch_project_logs_enriched():
    logs = fetch_table("project_logs", "created_at", ascending=False)
    project_lookup = {p["id"]: p for p in fetch_projects_enriched()}
    enriched = []
    for log in logs:
        row = dict(log)
        project = project_lookup.get(log.get("project_id"), {})
        row["project_label"] = f"{project.get('customer_name', 'Ukjent')} • {project.get('project_type', '')}"
        enriched.append(row)
    return enriched


def as_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def safe_number(value, default=0.0) -> float:
    try:
        if value in (None, ""):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def format_currency(value) -> str:
    return f"{safe_number(value):,.0f} kr".replace(",", " ")


def value_label(value) -> str:
    return "-" if value in (None, "") else str(value)


def short_id(value: str | None) -> str:
    if not value:
        return "-"
    return str(value)[:8]


def filter_df(df: pd.DataFrame, search: str, columns: list[str] | None = None) -> pd.DataFrame:
    if df.empty or not search.strip():
        return df
    columns = columns or list(df.columns)
    s = search.strip().lower()
    mask = pd.Series([False] * len(df), index=df.index)
    for col in columns:
        if col in df.columns:
            mask = mask | df[col].astype(str).str.lower().str.contains(s, na=False)
    return df[mask]


def slugify(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9æøåÆØÅ]+", "_", text.strip())
    return text.strip("_")[:40] or "eksport"


def display_df(df: pd.DataFrame, show_internal_ids: bool = False) -> pd.DataFrame:
    if df.empty:
        return df
    display = df.copy()
    if not show_internal_ids:
        hide_cols = [c for c in display.columns if c == "id" or c.endswith("_id") or c in {"created_at", "updated_at"}]
        display = display.drop(columns=hide_cols, errors="ignore")
    return display


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Data") -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    output.seek(0)
    return output.getvalue()


def pdf_from_lines(title: str, lines: list[str]) -> bytes:
    output = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output, pagesize=A4)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    story.append(Paragraph("Dato skrevet: 23.06.2026", styles["BodyText"]))
    story.append(Paragraph("Forfatter: William Berg Steffenak - copyright", styles["BodyText"]))
    story.append(Spacer(1, 12))
    for line in lines:
        story.append(Paragraph(line, styles["BodyText"]))
        story.append(Spacer(1, 6))
    doc.build(story)
    output.seek(0)
    return output.getvalue()


def quote_export_lines(quote_row: dict) -> list[str]:
    return [
        f"Kunde: {quote_row.get('customer_name', '-')}",
        f"Tilbud-ID: {quote_row.get('id', '-')}",
        f"Oppdragstype: {quote_row.get('job_type', '-')}",
        f"Status: {quote_row.get('status', '-')}",
        f"Pris: {format_currency(quote_row.get('price', 0))}",
        f"Estimert timer: {value_label(quote_row.get('estimated_hours'))}",
        f"Gyldig til: {value_label(quote_row.get('valid_until'))}",
        f"Sendemetode: {value_label(quote_row.get('send_method'))}",
        f"Notat: {value_label(quote_row.get('note'))}",
    ]


def invoice_export_lines(row: dict) -> list[str]:
    return [
        f"Kunde: {row.get('customer_name', '-')}",
        f"Oppdrag-ID: {row.get('project_id', '-')}",
        f"Oppdragstype: {row.get('project_type', '-')}",
        f"Adresse: {value_label(row.get('address'))}",
        f"Status: {value_label(row.get('status'))}",
        f"Prisgrunnlag: {format_currency(row.get('project_price', 0))}",
        f"Timer logget: {value_label(row.get('total_logged_hours'))}",
        f"Antall loggposter: {value_label(row.get('log_entries'))}",
        f"Klar for fakturering: {value_label(row.get('ready_for_invoice'))}",
        f"Fakturert: {value_label(row.get('invoiced'))}",
        f"Fakturanummer: {value_label(row.get('invoice_number'))}",
        f"Prosjektnotat: {value_label(row.get('project_note'))}",
    ]


def project_card_lines(project_row: dict, total_hours: float, logs_count: int, linked_equipment_count: int) -> list[str]:
    return [
        f"Kunde: {project_row.get('customer_name', '-')}",
        f"Oppdrag-ID: {project_row.get('id', '-')}",
        f"Oppdragstype: {project_row.get('project_type', '-')}",
        f"Adresse: {value_label(project_row.get('address'))}",
        f"Status: {value_label(project_row.get('status'))}",
        f"Pris: {format_currency(project_row.get('price', 0))}",
        f"Startdato: {value_label(project_row.get('start_date'))}",
        f"Sluttdato: {value_label(project_row.get('end_date'))}",
        f"HMS: {value_label(project_row.get('hms'))}",
        f"Klar for fakturering: {value_label(project_row.get('ready_for_invoice'))}",
        f"Fakturert: {value_label(project_row.get('invoiced'))}",
        f"Fakturanummer: {value_label(project_row.get('invoice_number'))}",
        f"Totale timer: {total_hours}",
        f"Antall loggposter: {logs_count}",
        f"Antall utstyrskoblinger: {linked_equipment_count}",
        f"Prosjektnotat: {value_label(project_row.get('note'))}",
    ]


def status_pill(status: str | None) -> str:
    s = (status or "").lower()
    if s in {"sendt", "fakturert", "pågår"}:
        cls = "pill-blue"
    elif s in {"akseptert", "fullført", "i drift", "ok"}:
        cls = "pill-green"
    elif s in {"utkast", "planlagt", "service snart", "klar"}:
        cls = "pill-amber"
    elif s in {"avslått", "tapt", "service forfalt", "ute"}:
        cls = "pill-red"
    else:
        cls = "pill-slate"
    text = status or "Ukjent"
    return f'<span class="pill {cls}">{text}</span>'


def create_project_from_quote(quote_row: dict, project_address: str, project_status: str, start_date_value, hms: bool, note: str):
    payload = {
        "customer_id": quote_row["customer_id"],
        "project_type": quote_row.get("job_type") or "Oppdrag",
        "address": project_address or None,
        "status": project_status,
        "price": safe_number(quote_row.get("price"), 0),
        "start_date": start_date_value.isoformat() if start_date_value else None,
        "hms": hms,
        "ready_for_invoice": False,
        "invoiced": False,
        "invoice_number": None,
        "note": note or f"Opprettet fra tilbud {quote_row.get('id')}",
        "quote_id": quote_row.get("id"),
    }
    return client.table("projects").insert(payload).execute()


def update_quote_status(quote_id: str, status: str):
    payload = {"status": status}
    now = datetime.now().astimezone().isoformat()
    if status == "Akseptert":
        payload["accepted_at"] = now
    elif status == "Sendt":
        payload["sent_at"] = now
    elif status == "Avslått":
        payload["declined_at"] = now
    return client.table("quotes").update(payload).eq("id", quote_id).execute()


def add_project_log_with_equipment(project_id: str, log_date_value, hours: float, performed_by: str, task: str, equipment_used_text: str, deviation: str, next_step: str, note: str, selected_equipment_rows: list[tuple[str, float]]):
    log_payload = {
        "project_id": project_id,
        "log_date": log_date_value.isoformat() if log_date_value else None,
        "hours": float(hours),
        "performed_by": performed_by.strip() or None,
        "task": task.strip(),
        "equipment_used": equipment_used_text.strip() or None,
        "deviation": deviation.strip() or None,
        "next_step": next_step.strip() or None,
        "note": note.strip() or None,
    }
    inserted = client.table("project_logs").insert(log_payload).execute()
    if not inserted.data:
        raise RuntimeError("Klarte ikke å opprette loggpost.")
    log_id = inserted.data[0]["id"]
    for equipment_id, eq_hours in selected_equipment_rows:
        if eq_hours > 0:
            client.table("project_log_equipment").insert({
                "project_log_id": log_id,
                "equipment_id": equipment_id,
                "hours_used": float(eq_hours),
                "note": f"Opprettet fra app V3.2 {datetime.now().astimezone().isoformat()}",
            }).execute()
    return log_id


def mark_project_ready(project_id: str, ready: bool):
    return client.table("projects").update({"ready_for_invoice": ready}).eq("id", project_id).execute()


def mark_project_invoiced(project_id: str, invoice_number: str):
    return client.table("projects").update({
        "ready_for_invoice": True,
        "invoiced": True,
        "invoice_number": invoice_number.strip() or None,
        "status": "Fakturert",
    }).eq("id", project_id).execute()


def register_equipment_service(equipment_id: str, service_date_value, hours_at_service: float, description: str, cost: float, performed_by: str):
    current_equipment = client.table("equipment").select("*").eq("id", equipment_id).execute().data or []
    if not current_equipment:
        raise RuntimeError("Finner ikke utstyr.")
    client.table("equipment_service_logs").insert({
        "equipment_id": equipment_id,
        "service_date": service_date_value.isoformat() if service_date_value else None,
        "hours_at_service": float(hours_at_service),
        "description": description.strip() or None,
        "cost": float(cost),
        "performed_by": performed_by.strip() or None,
    }).execute()
    client.table("equipment").update({
        "last_service": service_date_value.isoformat() if service_date_value else None,
        "hours_used": 0,
        "status": "I drift",
        "note": f"Service registrert {service_date_value.isoformat() if service_date_value else ''}".strip(),
    }).eq("id", equipment_id).execute()

# =========================================================
# LAST DATA
# =========================================================
customers = fetch_table("customers", "created_at", ascending=False)
leads = fetch_table("leads", "created_at", ascending=False)
projects = fetch_projects_enriched()
quotes = fetch_quotes_enriched()
pricing_calculations = fetch_table("pricing_calculations", "created_at", ascending=False)
project_logs = fetch_project_logs_enriched()
equipment = fetch_table("equipment", "created_at", ascending=False)
courses = fetch_table("courses", "created_at", ascending=False)
invoice_basis = fetch_invoice_basis()
equipment_status = fetch_equipment_maintenance_status()
project_log_equipment = fetch_project_log_equipment()
equipment_service_logs = fetch_equipment_service_logs()

customers_df = as_df(customers)
leads_df = as_df(leads)
projects_df = as_df(projects)
quotes_df = as_df(quotes)
pricing_df = as_df(pricing_calculations)
project_logs_df = as_df(project_logs)
equipment_df = as_df(equipment)
courses_df = as_df(courses)
invoice_basis_df = as_df(invoice_basis)
equipment_status_df = as_df(equipment_status)
project_log_equipment_df = as_df(project_log_equipment)
equipment_service_logs_df = as_df(equipment_service_logs)

# =========================================================
# HEADER / SIDEBAR
# =========================================================
st.markdown('<div class="hero"><h1>Lokal CRM V3.2</h1><p>Layout- og designfokus med mindre teknisk støy. ID-er skjules i hovedvisning og brukes kun der de faktisk hjelper arbeidsflyten.</p></div>', unsafe_allow_html=True)
st.caption("Dato skrevet: 23.06.2026 • William Berg Steffenak - copyright")

with st.sidebar:
    st.subheader("Tilkobling")
    st.write("Status:", "✅ Koblet til Supabase")
    st.markdown("---")
    global_search = st.text_input("Globalt søk", placeholder="Kunde, lead, oppdrag, tilbud ...")
    show_internal_ids = st.toggle("Vis tekniske ID-er og metadata", value=False)
    st.caption("Anbefaling: La denne være AV i daglig bruk. Slå den bare på ved feilsøking eller koblinger.")
    if st.button("Oppdater data fra database"):
        clear_all_caches()
        st.rerun()

# =========================================================
# DASHBOARD KPI
# =========================================================
st.subheader("Oversikt")
metric_cols = st.columns(6)
metric_cols[0].metric("Kunder", len(customers))
metric_cols[1].metric("Leads", len(leads))
metric_cols[2].metric("Oppdrag", len(projects))
metric_cols[3].metric("Tilbud", len(quotes))
metric_cols[4].metric("Klar for fakturering", int(projects_df["ready_for_invoice"].fillna(False).sum()) if not projects_df.empty and "ready_for_invoice" in projects_df.columns else 0)
metric_cols[5].metric("Fakturert", int(projects_df["invoiced"].fillna(False).sum()) if not projects_df.empty and "invoiced" in projects_df.columns else 0)

st.markdown("---")

area = st.segmented_control(
    "Arbeidsområde",
    options=["Dashboard", "Kunder", "Salg", "Drift", "Fakturering", "Kursing"],
    default="Dashboard",
)

# =========================================================
# DASHBOARD
# =========================================================
if area == "Dashboard":
    left, right = st.columns([1.2, 0.8])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Rask oversikt</p>', unsafe_allow_html=True)
        st.markdown(
            f"{status_pill('Planlagt')}{status_pill('Pågår')}{status_pill('Fullført')}{status_pill('Fakturert')}",
            unsafe_allow_html=True,
        )
        dash_projects = filter_df(projects_df, global_search, ["customer_name", "project_type", "status", "address", "note"])
        if dash_projects.empty:
            st.info("Ingen oppdrag å vise.")
        else:
            cols = [c for c in ["customer_name", "project_type", "address", "status", "price", "ready_for_invoice", "invoiced"] if c in dash_projects.columns]
            st.dataframe(display_df(dash_projects[cols], show_internal_ids), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card" style="margin-top:12px;">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Siste leads</p>', unsafe_allow_html=True)
        dash_leads = filter_df(leads_df, global_search, ["description", "status", "source", "note"])
        if dash_leads.empty:
            st.info("Ingen leads å vise.")
        else:
            cols = [c for c in ["description", "status", "estimated_value", "follow_up_date"] if c in dash_leads.columns]
            st.dataframe(display_df(dash_leads[cols], show_internal_ids), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Varsler</p>', unsafe_allow_html=True)
        near_service = equipment_status_df[equipment_status_df["maintenance_status"].isin(["Service snart", "Service forfalt"])] if not equipment_status_df.empty and "maintenance_status" in equipment_status_df.columns else pd.DataFrame()
        if near_service.empty:
            st.success("Ingen utstyrsenheter trenger umiddelbar service.")
        else:
            st.warning(f"{len(near_service)} utstyrsenheter trenger oppfølging.")
            st.dataframe(display_df(near_service[[c for c in ["name", "category", "maintenance_status", "remaining_hours_to_service"] if c in near_service.columns]], show_internal_ids), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card" style="margin-top:12px;">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Fakturagrunnlag</p>', unsafe_allow_html=True)
        dash_invoice = filter_df(invoice_basis_df, global_search, ["customer_name", "project_type", "status", "project_note"])
        if dash_invoice.empty:
            st.info("Ingen fakturagrunnlag å vise.")
        else:
            cols = [c for c in ["customer_name", "project_type", "project_price", "ready_for_invoice", "invoiced", "invoice_number"] if c in dash_invoice.columns]
            st.dataframe(display_df(dash_invoice[cols], show_internal_ids), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# KUNDER
# =========================================================
elif area == "Kunder":
    left, right = st.columns([1.05, 0.95])
    customer_search = st.text_input("Søk i kunder", key="customer_search")
    customer_view_df = filter_df(customers_df, global_search, ["name", "phone", "email", "address", "customer_type", "note"])
    customer_view_df = filter_df(customer_view_df, customer_search, ["name", "phone", "email", "address", "customer_type", "note"])

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Kundeliste</p>', unsafe_allow_html=True)
        if customer_view_df.empty:
            st.info("Ingen kunder registrert.")
        else:
            show_cols = [c for c in ["name", "phone", "email", "address", "customer_type", "note"] if c in customer_view_df.columns]
            st.dataframe(display_df(customer_view_df[show_cols], show_internal_ids), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Kundekort</p>', unsafe_allow_html=True)
        customer_options = fetch_customers_minimal()
        customer_map = {f"{row['name']} • {short_id(row['id'])}": row for row in customer_options}
        if customer_map:
            label = st.selectbox("Velg kunde", list(customer_map.keys()))
            customer = customer_map[label]
            customer_id = customer["id"]
            st.markdown(f"**Navn:** {customer.get('name', '-')}")
            st.markdown(f"**Telefon:** {value_label(customer.get('phone'))}")
            st.markdown(f"**E-post:** {value_label(customer.get('email'))}")
            st.markdown(f"**Adresse:** {value_label(customer.get('address'))}")
            st.markdown(f"**Type:** {value_label(customer.get('customer_type'))}")
            st.markdown(f"**Notat:** {value_label(customer.get('note'))}")
            if show_internal_ids:
                st.caption(f"Kunde-ID: {customer_id}")

            rel_leads = leads_df[leads_df["customer_id"] == customer_id] if not leads_df.empty and "customer_id" in leads_df.columns else pd.DataFrame()
            rel_projects = projects_df[projects_df["customer_id"] == customer_id] if not projects_df.empty and "customer_id" in projects_df.columns else pd.DataFrame()
            rel_quotes = quotes_df[quotes_df["customer_id"] == customer_id] if not quotes_df.empty and "customer_id" in quotes_df.columns else pd.DataFrame()

            st.markdown("**Leads**")
            st.dataframe(display_df(rel_leads[[c for c in ["description", "status", "estimated_value", "follow_up_date"] if c in rel_leads.columns]], show_internal_ids), use_container_width=True, hide_index=True) if not rel_leads.empty else st.caption("Ingen leads.")
            st.markdown("**Oppdrag**")
            st.dataframe(display_df(rel_projects[[c for c in ["project_type", "status", "price", "start_date", "invoice_number"] if c in rel_projects.columns]], show_internal_ids), use_container_width=True, hide_index=True) if not rel_projects.empty else st.caption("Ingen oppdrag.")
            st.markdown("**Tilbud**")
            st.dataframe(display_df(rel_quotes[[c for c in ["job_type", "status", "price", "valid_until"] if c in rel_quotes.columns]], show_internal_ids), use_container_width=True, hide_index=True) if not rel_quotes.empty else st.caption("Ingen tilbud.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card" style="margin-top:12px;">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Ny kunde</p>', unsafe_allow_html=True)
        with st.form("new_customer_form", clear_on_submit=True):
            name = st.text_input("Navn *")
            phone = st.text_input("Telefon")
            email = st.text_input("E-post")
            address = st.text_input("Adresse")
            customer_type = st.selectbox("Kundetype", ["Privat", "Gård", "Sameie", "Bedrift", "Annet"])
            note = st.text_area("Notat")
            submitted = st.form_submit_button("Legg til kunde")
            if submitted:
                if not name.strip():
                    st.warning("Navn må fylles ut.")
                else:
                    client.table("customers").insert({
                        "name": name.strip(),
                        "phone": phone.strip() or None,
                        "email": email.strip() or None,
                        "address": address.strip() or None,
                        "customer_type": customer_type,
                        "note": note.strip() or None,
                    }).execute()
                    clear_all_caches()
                    st.success("Kunde lagret.")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# SALG
# =========================================================
elif area == "Salg":
    sale_tab = st.tabs(["Leads", "Kalkyle", "Tilbud"])
    with sale_tab[0]:
        left, right = st.columns([1.1, 0.9])
        lead_search = st.text_input("Søk i leads", key="lead_search")
        lead_status_filter = st.selectbox("Filtrer status", ["Alle", "Ny", "Kontaktet", "Tilbud sendt", "Vunnet", "Tapt"], key="lead_status")
        lead_view_df = filter_df(leads_df, global_search, ["description", "source", "status", "note"])
        lead_view_df = filter_df(lead_view_df, lead_search, ["description", "source", "status", "note"])
        if lead_status_filter != "Alle" and not lead_view_df.empty:
            lead_view_df = lead_view_df[lead_view_df["status"] == lead_status_filter]
        with left:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<p class="section-title">Lead-oversikt</p>', unsafe_allow_html=True)
            if lead_view_df.empty:
                st.info("Ingen leads registrert.")
            else:
                st.dataframe(display_df(lead_view_df[[c for c in ["description", "source", "status", "estimated_value", "follow_up_date", "note"] if c in lead_view_df.columns]], show_internal_ids), use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with right:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<p class="section-title">Ny lead</p>', unsafe_allow_html=True)
            customer_options = fetch_customers_minimal()
            customer_map = {f"{row['name']} • {short_id(row['id'])}": row["id"] for row in customer_options}
            with st.form("new_lead_form", clear_on_submit=True):
                customer_label = st.selectbox("Kunde *", list(customer_map.keys()) if customer_map else [])
                description = st.text_input("Beskrivelse *")
                source = st.text_input("Kilde", value="Tips")
                status = st.selectbox("Status", ["Ny", "Kontaktet", "Tilbud sendt", "Vunnet", "Tapt"])
                estimated_value = st.number_input("Estimert verdi", min_value=0.0, value=0.0, step=500.0)
                follow_up_date = st.date_input("Neste oppfølging", value=date.today())
                note = st.text_area("Notat")
                submitted = st.form_submit_button("Legg til lead")
                if submitted:
                    if not customer_map:
                        st.warning("Du må ha minst én kunde før du kan opprette lead.")
                    elif not description.strip():
                        st.warning("Beskrivelse må fylles ut.")
                    else:
                        client.table("leads").insert({
                            "customer_id": customer_map[customer_label],
                            "description": description.strip(),
                            "source": source.strip() or None,
                            "status": status,
                            "estimated_value": float(estimated_value),
                            "follow_up_date": follow_up_date.isoformat() if follow_up_date else None,
                            "note": note.strip() or None,
                        }).execute()
                        clear_all_caches()
                        st.success("Lead lagret.")
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with sale_tab[1]:
        left, right = st.columns([1.1, 0.9])
        pricing_search = st.text_input("Søk i kalkyler", key="pricing_search")
        pricing_view_df = filter_df(pricing_df, global_search, ["job_type", "complexity", "note"])
        pricing_view_df = filter_df(pricing_view_df, pricing_search, ["job_type", "complexity", "note"])
        with left:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<p class="section-title">Kalkyler</p>', unsafe_allow_html=True)
            if pricing_view_df.empty:
                st.info("Ingen kalkyler registrert.")
            else:
                st.dataframe(display_df(pricing_view_df[[c for c in ["job_type", "complexity", "estimated_hours", "hourly_rate", "calculated_price", "valid_until", "note"] if c in pricing_view_df.columns]], show_internal_ids), use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with right:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<p class="section-title">Ny kalkyle</p>', unsafe_allow_html=True)
            customer_options = fetch_customers_minimal()
            customer_map = {f"{row['name']} • {short_id(row['id'])}": row["id"] for row in customer_options}
            leads_options = fetch_leads_minimal()
            lead_map = {f"{row['description']} • {short_id(row['id'])}": row["id"] for row in leads_options}
            with st.form("new_pricing_form", clear_on_submit=True):
                customer_label = st.selectbox("Kunde *", list(customer_map.keys()) if customer_map else [])
                lead_label = st.selectbox("Lead (valgfri)", ["Ingen"] + list(lead_map.keys())) if lead_map else st.selectbox("Lead (valgfri)", ["Ingen"])
                job_type = st.text_input("Oppdragstype *", value="Trefelling")
                travel_km = st.number_input("Reise km", min_value=0.0, value=20.0, step=1.0)
                complexity = st.selectbox("Kompleksitet", ["Lav", "Middels", "Høy"])
                estimated_hours = st.number_input("Estimerte timer", min_value=0.0, value=6.0, step=0.5)
                hourly_rate = st.number_input("Timepris", min_value=0.0, value=850.0, step=50.0)
                extra_equipment_cost = st.number_input("Ekstra utstyr", min_value=0.0, value=500.0, step=100.0)
                disposal_cost = st.number_input("Bortkjøring / avfall", min_value=0.0, value=0.0, step=100.0)
                minimum_price = st.number_input("Minstepris", min_value=0.0, value=3500.0, step=100.0)
                valid_until = st.date_input("Gyldig til", value=date.today())
                note = st.text_area("Notat")
                travel_cost = travel_km * 8
                base_labor = estimated_hours * hourly_rate
                multiplier = {"Lav": 1.0, "Middels": 1.2, "Høy": 1.45}[complexity]
                calculated_price = max(minimum_price, round((base_labor + travel_cost + extra_equipment_cost + disposal_cost) * multiplier / 100) * 100)
                st.info(f"Beregnet pris: {format_currency(calculated_price)}")
                submitted = st.form_submit_button("Lagre kalkyle")
                if submitted:
                    if not customer_map:
                        st.warning("Du må ha minst én kunde før du kan opprette kalkyle.")
                    elif not job_type.strip():
                        st.warning("Oppdragstype må fylles ut.")
                    else:
                        client.table("pricing_calculations").insert({
                            "customer_id": customer_map[customer_label],
                            "lead_id": None if lead_label == "Ingen" else lead_map[lead_label],
                            "job_type": job_type.strip(),
                            "travel_km": float(travel_km),
                            "complexity": complexity,
                            "estimated_hours": float(estimated_hours),
                            "hourly_rate": float(hourly_rate),
                            "extra_equipment_cost": float(extra_equipment_cost),
                            "disposal_cost": float(disposal_cost),
                            "minimum_price": float(minimum_price),
                            "calculated_price": float(calculated_price),
                            "valid_until": valid_until.isoformat() if valid_until else None,
                            "note": note.strip() or None,
                        }).execute()
                        clear_all_caches()
                        st.success("Kalkyle lagret.")
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with sale_tab[2]:
        left, right = st.columns([1.1, 0.9])
        quote_search = st.text_input("Søk i tilbud", key="quote_search")
        quote_status_filter = st.selectbox("Filtrer tilbudsstatus", ["Alle", "Utkast", "Sendt", "Akseptert", "Avslått"], key="quote_status")
        quote_view_df = filter_df(quotes_df, global_search, ["customer_name", "job_type", "status", "send_method", "note"])
        quote_view_df = filter_df(quote_view_df, quote_search, ["customer_name", "job_type", "status", "send_method", "note"])
        if quote_status_filter != "Alle" and not quote_view_df.empty:
            quote_view_df = quote_view_df[quote_view_df["status"] == quote_status_filter]
        with left:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<p class="section-title">Tilbud</p>', unsafe_allow_html=True)
            if quote_view_df.empty:
                st.info("Ingen tilbud registrert.")
            else:
                st.dataframe(display_df(quote_view_df[[c for c in ["customer_name", "job_type", "status", "price", "valid_until", "send_method"] if c in quote_view_df.columns]], show_internal_ids), use_container_width=True, hide_index=True)
            st.markdown("<p class='small-note'>ID-er er skjult i hovedlisten. De brukes kun internt i koblinger og eksportnavn.</p>", unsafe_allow_html=True)
            quote_export_map = {f"{row.get('customer_name', 'Ukjent')} • {row.get('job_type', '')} • {short_id(row['id'])}": row for row in quotes}
            if quote_export_map:
                export_quote_label = st.selectbox("Velg tilbud for eksport", list(quote_export_map.keys()), key="quote_export_select")
                export_quote_row = quote_export_map[export_quote_label]
                quote_pdf = pdf_from_lines("Tilbud", quote_export_lines(export_quote_row))
                quote_xlsx = dataframe_to_excel_bytes(pd.DataFrame([export_quote_row]), sheet_name="Tilbud")
                d1, d2 = st.columns(2)
                with d1:
                    st.download_button("Last ned tilbud PDF", data=quote_pdf, file_name=f"tilbud_{slugify(export_quote_row.get('customer_name', 'kunde'))}_{short_id(export_quote_row['id'])}.pdf", mime="application/pdf")
                with d2:
                    st.download_button("Last ned tilbud Excel", data=quote_xlsx, file_name=f"tilbud_{slugify(export_quote_row.get('customer_name', 'kunde'))}_{short_id(export_quote_row['id'])}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.markdown('</div>', unsafe_allow_html=True)
        with right:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<p class="section-title">Opprett tilbud fra kalkyle</p>', unsafe_allow_html=True)
            pricing_rows = fetch_table("pricing_calculations", "created_at", ascending=False)
            pricing_map = {f"{row.get('job_type', 'Ukjent')} • {format_currency(row.get('calculated_price', 0))} • {short_id(row['id'])}": row for row in pricing_rows}
            with st.form("new_quote_form", clear_on_submit=True):
                if pricing_map:
                    pricing_label = st.selectbox("Kalkyle *", list(pricing_map.keys()))
                    selected = pricing_map[pricing_label]
                    status = st.selectbox("Status", ["Utkast", "Sendt", "Akseptert", "Avslått"])
                    send_method = st.text_input("Sendemetode", value="E-postutkast")
                    valid_until = st.date_input("Gyldig til", value=date.today())
                    note = st.text_area("Notat")
                    submitted = st.form_submit_button("Opprett tilbud")
                    if submitted:
                        payload = {
                            "customer_id": selected["customer_id"],
                            "job_type": selected["job_type"],
                            "estimated_hours": selected["estimated_hours"],
                            "price": selected["calculated_price"],
                            "status": status,
                            "valid_until": valid_until.isoformat() if valid_until else None,
                            "send_method": send_method.strip() or None,
                            "note": note.strip() or None,
                            "pricing_calculation_id": selected["id"],
                            "lead_id": selected.get("lead_id"),
                        }
                        if status == "Sendt":
                            payload["sent_at"] = datetime.now().astimezone().isoformat()
                        elif status == "Akseptert":
                            payload["accepted_at"] = datetime.now().astimezone().isoformat()
                        elif status == "Avslått":
                            payload["declined_at"] = datetime.now().astimezone().isoformat()
                        client.table("quotes").insert(payload).execute()
                        clear_all_caches()
                        st.success("Tilbud opprettet.")
                        st.rerun()
                else:
                    st.info("Du må opprette minst én kalkyle før du kan opprette tilbud.")
            st.markdown("---")
            st.markdown('<p class="section-title">Aksepter tilbud → opprett oppdrag</p>', unsafe_allow_html=True)
            quote_map = {f"{row.get('customer_name', 'Ukjent')} • {row.get('job_type', '')} • {short_id(row['id'])}": row for row in quotes}
            if quote_map:
                selected_quote_label = st.selectbox("Velg tilbud", list(quote_map.keys()))
                selected_quote = quote_map[selected_quote_label]
                with st.form("accept_quote_to_project_form"):
                    project_address = st.text_input("Adresse for oppdrag", value=selected_quote.get("customer_address") or "")
                    project_status = st.selectbox("Oppdragsstatus", ["Planlagt", "Pågår", "Fullført", "Fakturert", "Avsluttet"], index=0)
                    project_start = st.date_input("Startdato", value=date.today())
                    hms = st.checkbox("HMS-vurdering", value=True)
                    project_note = st.text_area("Prosjektnotat", value=f"Opprettet fra tilbud {short_id(selected_quote.get('id'))}")
                    create_project_btn = st.form_submit_button("Aksepter tilbud og opprett oppdrag")
                    if create_project_btn:
                        update_quote_status(selected_quote["id"], "Akseptert")
                        create_project_from_quote(selected_quote, project_address, project_status, project_start, hms, project_note)
                        clear_all_caches()
                        st.success("Tilbud akseptert og oppdrag opprettet.")
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# DRIFT
# =========================================================
elif area == "Drift":
    drift_tabs = st.tabs(["Oppdragskort", "Oppdragslogg", "Utstyr"])
    with drift_tabs[0]:
        left, right = st.columns([1.05, 0.95])
        project_search = st.text_input("Søk i oppdrag", key="project_search")
        project_status_filter = st.selectbox("Filtrer oppdragsstatus", ["Alle", "Planlagt", "Pågår", "Fullført", "Fakturert", "Avsluttet"], key="project_status")
        project_view_df = filter_df(projects_df, global_search, ["customer_name", "project_type", "address", "status", "note"])
        project_view_df = filter_df(project_view_df, project_search, ["customer_name", "project_type", "address", "status", "note"])
        if project_status_filter != "Alle" and not project_view_df.empty:
            project_view_df = project_view_df[project_view_df["status"] == project_status_filter]
        with left:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<p class="section-title">Oppdragsliste</p>', unsafe_allow_html=True)
            if project_view_df.empty:
                st.info("Ingen oppdrag registrert.")
            else:
                st.dataframe(display_df(project_view_df[[c for c in ["customer_name", "project_type", "address", "status", "price", "start_date"] if c in project_view_df.columns]], show_internal_ids), use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with right:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<p class="section-title">Oppdragskort</p>', unsafe_allow_html=True)
            project_map = {f"{row.get('customer_name', 'Ukjent')} • {row.get('project_type', '')} • {short_id(row['id'])}": row for row in projects}
            if project_map:
                project_card_label = st.selectbox("Velg oppdrag", list(project_map.keys()))
                project_card = project_map[project_card_label]
                project_id = project_card["id"]
                related_logs = project_logs_df[project_logs_df["project_id"] == project_id] if not project_logs_df.empty and "project_id" in project_logs_df.columns else pd.DataFrame()
                total_hours = float(related_logs["hours"].fillna(0).sum()) if not related_logs.empty and "hours" in related_logs.columns else 0.0
                related_links = project_log_equipment_df[project_log_equipment_df["project_log_id"].isin(related_logs["id"].tolist())] if not project_log_equipment_df.empty and not related_logs.empty and "id" in related_logs.columns else pd.DataFrame()
                st.markdown(f"**Kunde:** {project_card.get('customer_name', '-')}")
                st.markdown(f"**Oppdragstype:** {project_card.get('project_type', '-')}")
                st.markdown(f"**Adresse:** {value_label(project_card.get('address'))}")
                st.markdown(f"**Status:** {status_pill(project_card.get('status'))}", unsafe_allow_html=True)
                st.markdown(f"**Pris:** {format_currency(project_card.get('price', 0))}")
                st.markdown(f"**Timer logget:** {total_hours}")
                st.markdown(f"**Loggposter:** {len(related_logs)}")
                st.markdown(f"**Utstyrskoblinger:** {len(related_links)}")
                st.markdown(f"**Fakturanummer:** {value_label(project_card.get('invoice_number'))}")
                if show_internal_ids:
                    st.caption(f"Oppdrag-ID: {project_id}")
                if not related_logs.empty:
                    st.markdown("**Logghistorikk**")
                    st.dataframe(display_df(related_logs[[c for c in ["log_date", "hours", "performed_by", "task", "deviation", "next_step"] if c in related_logs.columns]], show_internal_ids), use_container_width=True, hide_index=True)
                card_pdf = pdf_from_lines("Oppdragskort", project_card_lines(project_card, total_hours, len(related_logs), len(related_links)))
                card_xlsx = dataframe_to_excel_bytes(pd.DataFrame([project_card]), sheet_name="Oppdragskort")
                b1, b2 = st.columns(2)
                with b1:
                    st.download_button("Last ned oppdragskort PDF", data=card_pdf, file_name=f"oppdragskort_{slugify(project_card.get('customer_name', 'kunde'))}_{short_id(project_id)}.pdf", mime="application/pdf")
                with b2:
                    st.download_button("Last ned oppdragskort Excel", data=card_xlsx, file_name=f"oppdragskort_{slugify(project_card.get('customer_name', 'kunde'))}_{short_id(project_id)}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.markdown('</div>', unsafe_allow_html=True)

    with drift_tabs[1]:
        left, right = st.columns([1.05, 0.95])
        log_search = st.text_input("Søk i oppdragslogg", key="log_search")
        log_view_df = filter_df(project_logs_df, global_search, ["project_label", "task", "performed_by", "deviation", "next_step", "note"])
        log_view_df = filter_df(log_view_df, log_search, ["project_label", "task", "performed_by", "deviation", "next_step", "note"])
        with left:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<p class="section-title">Oppdragslogg</p>', unsafe_allow_html=True)
            if log_view_df.empty:
                st.info("Ingen loggposter registrert.")
            else:
                st.dataframe(display_df(log_view_df[[c for c in ["project_label", "log_date", "hours", "performed_by", "task", "equipment_used", "deviation", "next_step", "note"] if c in log_view_df.columns]], show_internal_ids), use_container_width=True, hide_index=True)
            st.markdown("**Koblet utstyr**")
            if project_log_equipment_df.empty:
                st.caption("Ingen koblinger ennå.")
            else:
                st.dataframe(display_df(project_log_equipment_df, show_internal_ids), use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with right:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<p class="section-title">Ny loggpost</p>', unsafe_allow_html=True)
            project_map = {f"{row.get('customer_name', 'Ukjent')} • {row.get('project_type', '')} • {short_id(row['id'])}": row["id"] for row in projects}
            equipment_rows = fetch_equipment_minimal()
            equipment_map = {f"{row.get('name')} • {row.get('category', '')} • {short_id(row['id'])}": row["id"] for row in equipment_rows}
            with st.form("new_log_form", clear_on_submit=True):
                project_label = st.selectbox("Oppdrag *", list(project_map.keys()) if project_map else [])
                log_date_value = st.date_input("Dato", value=date.today())
                hours = st.number_input("Timer", min_value=0.0, value=1.0, step=0.5)
                performed_by = st.text_input("Utført av", value="William")
                task = st.text_input("Hva ble gjort *")
                equipment_used_text = st.text_input("Utstyr brukt (fritekst)")
                deviation = st.text_input("Avvik / hendelser")
                next_step = st.text_input("Neste steg")
                note = st.text_area("Notat")
                st.markdown("**Koble utstyr til loggpost**")
                eq1_label = st.selectbox("Utstyr 1", ["Ingen"] + list(equipment_map.keys())) if equipment_map else st.selectbox("Utstyr 1", ["Ingen"])
                eq1_hours = st.number_input("Timer utstyr 1", min_value=0.0, value=0.0, step=0.5)
                eq2_label = st.selectbox("Utstyr 2", ["Ingen"] + list(equipment_map.keys()), key="eq2") if equipment_map else st.selectbox("Utstyr 2", ["Ingen"], key="eq2")
                eq2_hours = st.number_input("Timer utstyr 2", min_value=0.0, value=0.0, step=0.5, key="eq2h")
                log_submit = st.form_submit_button("Lagre loggpost")
                if log_submit:
                    if not project_map:
                        st.warning("Du må ha minst ett oppdrag før du kan opprette loggpost.")
                    elif not task.strip():
                        st.warning("Du må skrive hva som ble gjort.")
                    else:
                        selected_equipment_rows = []
                        if eq1_label != "Ingen":
                            selected_equipment_rows.append((equipment_map[eq1_label], float(eq1_hours)))
                        if eq2_label != "Ingen":
                            selected_equipment_rows.append((equipment_map[eq2_label], float(eq2_hours)))
                        add_project_log_with_equipment(project_map[project_label], log_date_value, hours, performed_by, task, equipment_used_text, deviation, next_step, note, selected_equipment_rows)
                        clear_all_caches()
                        st.success("Loggpost lagret.")
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with drift_tabs[2]:
        left, right = st.columns([1.05, 0.95])
        equipment_search = st.text_input("Søk i utstyr", key="equipment_search")
        equipment_status_filter = st.selectbox("Filtrer vedlikeholdsstatus", ["Alle", "OK", "Service snart", "Service forfalt", "Årlig kontroll", "Ingen intervall"], key="equipment_maintenance_filter")
        equipment_view_df = filter_df(equipment_df, global_search, ["name", "category", "status", "note"])
        equipment_view_df = filter_df(equipment_view_df, equipment_search, ["name", "category", "status", "note"])
        status_view = filter_df(equipment_status_df, global_search, ["name", "category", "maintenance_status"])
        status_view = filter_df(status_view, equipment_search, ["name", "category", "maintenance_status"])
        if equipment_status_filter != "Alle" and not status_view.empty:
            status_view = status_view[status_view["maintenance_status"] == equipment_status_filter]
        with left:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<p class="section-title">Utstyr</p>', unsafe_allow_html=True)
            if equipment_view_df.empty:
                st.info("Ingen utstyrsenheter registrert.")
            else:
                st.dataframe(display_df(equipment_view_df[[c for c in ["name", "category", "status", "hours_used", "service_interval", "last_service", "note"] if c in equipment_view_df.columns]], show_internal_ids), use_container_width=True, hide_index=True)
            st.markdown("**Vedlikeholdsstatus**")
            if status_view.empty:
                st.caption("Ingen vedlikeholdsstatus å vise.")
            else:
                st.dataframe(display_df(status_view[[c for c in ["name", "category", "hours_used", "service_interval", "remaining_hours_to_service", "maintenance_status"] if c in status_view.columns]], show_internal_ids), use_container_width=True, hide_index=True)
            st.markdown("**Servicehistorikk**")
            if equipment_service_logs_df.empty:
                st.caption("Ingen servicehistorikk ennå.")
            else:
                st.dataframe(display_df(equipment_service_logs_df, show_internal_ids), use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with right:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<p class="section-title">Nytt utstyr</p>', unsafe_allow_html=True)
            with st.form("new_equipment_form", clear_on_submit=True):
                name = st.text_input("Navn *")
                category = st.selectbox("Kategori", ["Motorsag", "Henger", "Vinsj", "Verneutstyr", "Annet"])
                hours_used = st.number_input("Timer brukt", min_value=0.0, value=0.0, step=1.0)
                service_interval = st.number_input("Serviceintervall", min_value=0.0, value=50.0, step=5.0)
                last_service = st.date_input("Sist service", value=date.today())
                status = st.selectbox("Status", ["I drift", "Service", "Ute"])
                note = st.text_area("Notat")
                submitted = st.form_submit_button("Legg til utstyr")
                if submitted:
                    if not name.strip():
                        st.warning("Navn må fylles ut.")
                    else:
                        client.table("equipment").insert({
                            "name": name.strip(),
                            "category": category,
                            "hours_used": float(hours_used),
                            "service_interval": float(service_interval),
                            "last_service": last_service.isoformat() if last_service else None,
                            "status": status,
                            "note": note.strip() or None,
                        }).execute()
                        clear_all_caches()
                        st.success("Utstyr lagret.")
                        st.rerun()
            st.markdown("---")
            st.markdown('<p class="section-title">Registrer service</p>', unsafe_allow_html=True)
            equipment_min = fetch_equipment_minimal()
            service_map = {f"{row['name']} • {short_id(row['id'])}": row["id"] for row in equipment_min}
            if service_map:
                with st.form("register_equipment_service_form"):
                    equipment_label = st.selectbox("Velg utstyr", list(service_map.keys()))
                    service_date_value = st.date_input("Servicedato", value=date.today(), key="service_date")
                    hours_at_service = st.number_input("Timer ved service", min_value=0.0, value=0.0, step=0.5)
                    description = st.text_input("Beskrivelse", value="Service registrert")
                    cost = st.number_input("Kostnad", min_value=0.0, value=0.0, step=100.0)
                    performed_by = st.text_input("Utført av", value="William")
                    save_service = st.form_submit_button("Registrer service")
                    if save_service:
                        register_equipment_service(service_map[equipment_label], service_date_value, hours_at_service, description, cost, performed_by)
                        clear_all_caches()
                        st.success("Service registrert og utstyr oppdatert.")
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# FAKTURERING
# =========================================================
elif area == "Fakturering":
    left, right = st.columns([1.1, 0.9])
    invoice_search = st.text_input("Søk i fakturagrunnlag", key="invoice_search")
    invoice_view_df = filter_df(invoice_basis_df, global_search, ["customer_name", "project_type", "address", "status", "project_note", "invoice_number"])
    invoice_view_df = filter_df(invoice_view_df, invoice_search, ["customer_name", "project_type", "address", "status", "project_note", "invoice_number"])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Fakturagrunnlag</p>', unsafe_allow_html=True)
        if invoice_view_df.empty:
            st.info("Ingen rader i v_invoice_basis.")
        else:
            st.dataframe(display_df(invoice_view_df[[c for c in ["customer_name", "project_type", "project_price", "total_logged_hours", "ready_for_invoice", "invoiced", "invoice_number"] if c in invoice_view_df.columns]], show_internal_ids), use_container_width=True, hide_index=True)
        invoice_export_map = {f"{row.get('customer_name', 'Ukjent')} • {row.get('project_type', '')} • {short_id(row['project_id'])}": row for row in invoice_basis}
        if invoice_export_map:
            export_label = st.selectbox("Velg fakturagrunnlag for eksport", list(invoice_export_map.keys()), key="invoice_export_select")
            export_row = invoice_export_map[export_label]
            invoice_pdf = pdf_from_lines("Fakturagrunnlag", invoice_export_lines(export_row))
            invoice_xlsx = dataframe_to_excel_bytes(pd.DataFrame([export_row]), sheet_name="Fakturagrunnlag")
            d1, d2 = st.columns(2)
            with d1:
                st.download_button("Last ned fakturagrunnlag PDF", data=invoice_pdf, file_name=f"fakturagrunnlag_{slugify(export_row.get('customer_name', 'kunde'))}_{short_id(export_row['project_id'])}.pdf", mime="application/pdf")
            with d2:
                st.download_button("Last ned fakturagrunnlag Excel", data=invoice_xlsx, file_name=f"fakturagrunnlag_{slugify(export_row.get('customer_name', 'kunde'))}_{short_id(export_row['project_id'])}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Fakturastyring</p>', unsafe_allow_html=True)
        invoice_project_map = {f"{row.get('customer_name', 'Ukjent')} • {row.get('project_type', '')} • {short_id(row['project_id'])}": row for row in invoice_basis}
        if invoice_project_map:
            label = st.selectbox("Velg oppdrag for fakturering", list(invoice_project_map.keys()))
            row = invoice_project_map[label]
            st.markdown(f"**Kunde:** {row.get('customer_name', '-')}")
            st.markdown(f"**Prosjektpris:** {format_currency(row.get('project_price', 0))}")
            st.markdown(f"**Timer logget:** {value_label(row.get('total_logged_hours'))}")
            st.markdown(f"**Status:** {status_pill(row.get('status'))}", unsafe_allow_html=True)
            with st.form("invoice_mark_form"):
                invoice_number = st.text_input("Fakturanummer")
                mark_ready = st.form_submit_button("Sett som klar for fakturering")
                mark_done = st.form_submit_button("Marker som fakturert")
                if mark_ready:
                    mark_project_ready(row["project_id"], True)
                    clear_all_caches()
                    st.success("Oppdrag satt som klar for fakturering.")
                    st.rerun()
                if mark_done:
                    mark_project_invoiced(row["project_id"], invoice_number)
                    clear_all_caches()
                    st.success("Oppdrag markert som fakturert.")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# KURSING
# =========================================================
elif area == "Kursing":
    left, right = st.columns([1.1, 0.9])
    course_search = st.text_input("Søk i kurs", key="course_search")
    course_view_df = filter_df(courses_df, global_search, ["title", "course_type", "provider", "note"])
    course_view_df = filter_df(course_view_df, course_search, ["title", "course_type", "provider", "note"])
    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Kurs og opplæring</p>', unsafe_allow_html=True)
        if course_view_df.empty:
            st.info("Ingen kurs registrert.")
        else:
            st.dataframe(display_df(course_view_df[[c for c in ["title", "course_type", "provider", "course_date", "duration", "documentation", "note"] if c in course_view_df.columns]], show_internal_ids), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Registrer kurs</p>', unsafe_allow_html=True)
        with st.form("new_course_form", clear_on_submit=True):
            title = st.text_input("Tittel *")
            course_type = st.text_input("Type", value="Internopplæring")
            provider = st.text_input("Leverandør / ansvarlig")
            course_date = st.date_input("Dato", value=date.today())
            duration = st.text_input("Varighet", value="1 dag")
            documentation = st.checkbox("Dokumentasjon finnes", value=True)
            note = st.text_area("Notat")
            submitted = st.form_submit_button("Lagre kurs")
            if submitted:
                if not title.strip():
                    st.warning("Tittel må fylles ut.")
                else:
                    client.table("courses").insert({
                        "title": title.strip(),
                        "course_type": course_type.strip() or None,
                        "provider": provider.strip() or None,
                        "course_date": course_date.isoformat() if course_date else None,
                        "duration": duration.strip() or None,
                        "documentation": documentation,
                        "note": note.strip() or None,
                    }).execute()
                    clear_all_caches()
                    st.success("Kurs lagret.")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.caption(
    "V3.2 fokuserer på layout og design: mer arbeidsflate-basert navigasjon, mindre teknisk støy, skjulte ID-er i hovedvisninger og tydeligere informasjonskort. "
    "Neste steg etter testing: farge-/ikonhierarki, kompakte kort, statusknapper og finere mobil-/feltbruk."
)
