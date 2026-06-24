# =========================================
# Dato: 23.06.2026
# Forfatter: William Berg Steffenak - copyright
# Versjon: V3.3 Secure
# =========================================

import streamlit as st
from supabase import create_client

# =========================
# CONFIG
# =========================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="CRM Secure", layout="wide")

# =========================
# LOGIN
# =========================
def login():
    st.title("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Logg inn"):
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if res.user:
            st.session_state["user"] = res.user
            st.session_state["access_token"] = res.session.access_token
            st.success("Logget inn ✅")
            st.rerun()
        else:
            st.error("Feil login")

# =========================
# USER SESSION
# =========================
if "user" not in st.session_state:
    login()
    st.stop()

user = st.session_state["user"]
user_id = user.id

st.sidebar.write(f"Innlogget som: {user.email}")

# =========================
# HELPER
# =========================
def insert(table, payload):
    payload["user_id"] = user_id
    return supabase.table(table).insert(payload).execute()

def select(table):
    return supabase.table(table).select("*").execute().data

# =========================
# UI
# =========================

st.title("CRM (Secure)")

tab1, tab2 = st.tabs(["Kunder", "Oppdrag"])

# =========================
# KUNDER
# =========================
with tab1:
    st.subheader("Kunder")

    name = st.text_input("Navn")
    phone = st.text_input("Telefon")

    if st.button("Lagre kunde"):
        insert("customers", {
            "name": name,
            "phone": phone
        })
        st.success("Lagret")

    data = select("customers")
    st.dataframe(data)

# =========================
# PROSJEKTER
# =========================
with tab2:
    st.subheader("Oppdrag")

    project_name = st.text_input("Oppdrag")

    if st.button("Lagre oppdrag"):
        insert("projects", {
            "project_type": project_name
        })
        st.success("Lagret")

    data = select("projects")
    st.dataframe(data)

# =========================
# LOGOUT
# =========================
if st.sidebar.button("Logg ut"):
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()

# Dato skrevet: 23.06.2026
# Forfatter: William Berg Steffenak - copyright
# Fil: app.py
# Beskrivelse: Lokal CRM med Supabase Auth + RLS

from datetime import date, datetime
from io import BytesIO

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from supabase import create_client, Client

st.set_page_config(
    page_title="Lokal CRM",
    page_icon="📋",
    layout="wide",
)

# =========================================================
# KONFIG FRA STREAMLIT SECRETS
# =========================================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_PUBLISHABLE_KEY"]


# =========================================================
# STIL
# =========================================================
st.markdown(
    """
    <style>
    .block-container {padding-top: 1rem; max-width: 1450px;}
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 14px 16px;
    }
    .hero {
        background: linear-gradient(135deg,#0f172a 0%, #1e293b 65%, #334155 100%);
        color: white;
        border-radius: 20px;
        padding: 20px 24px;
        margin-bottom: 12px;
    }
    .hero h1 {margin:0; font-size:2rem;}
    .hero p {margin:8px 0 0 0; color:#cbd5e1;}
    .section-title {font-size:1.15rem; font-weight:700; margin-bottom:10px;}
    .card {
        background:#ffffff;
        border:1px solid #e2e8f0;
        border-radius:18px;
        padding:16px 18px;
        box-shadow:0 1px 2px rgba(15,23,42,0.05);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# AUTH / CLIENT
# =========================================================
def normalize_supabase_url(raw_url: str) -> str:
    url = raw_url.strip().rstrip("/")
    for suffix in ("/rest/v1", "/auth/v1", "/storage/v1"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url


@st.cache_resource
def get_base_client() -> Client:
    return create_client(normalize_supabase_url(SUPABASE_URL), SUPABASE_KEY)


def get_client_with_session() -> Client:
    client = get_base_client()
    session_data = st.session_state.get("supabase_session")

    if session_data:
        try:
            client.auth.set_session(
                session_data["access_token"],
                session_data["refresh_token"],
            )
        except Exception:
            st.session_state.pop("supabase_session", None)
            st.session_state.pop("auth_user", None)
    return client


def current_user():
    return st.session_state.get("auth_user")


def login(email: str, password: str):
    client = get_base_client()
    response = client.auth.sign_in_with_password(
        {"email": email, "password": password}
    )

    if not response or not response.user or not response.session:
        raise RuntimeError("Innlogging feilet.")

    st.session_state["auth_user"] = {
        "id": response.user.id,
        "email": response.user.email,
    }
    st.session_state["supabase_session"] = {
        "access_token": response.session.access_token,
        "refresh_token": response.session.refresh_token,
    }


def logout():
    try:
        client = get_client_with_session()
        client.auth.sign_out()
    except Exception:
        pass

    st.session_state.pop("auth_user", None)
    st.session_state.pop("supabase_session", None)


# =========================================================
# HJELPEFUNKSJONER
# =========================================================
def as_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def safe_number(value, default=0.0) -> float:
    try:
        if value in (None, ""):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def value_label(value) -> str:
    return "-" if value in (None, "") else str(value)


def format_currency(value) -> str:
    return f"{safe_number(value):,.0f} kr".replace(",", " ")


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


def display_df(df: pd.DataFrame, show_internal_ids: bool = False) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if not show_internal_ids:
        hide_cols = [c for c in out.columns if c == "id" or c.endswith("_id") or c in {"created_at", "updated_at", "user_id"}]
        out = out.drop(columns=hide_cols, errors="ignore")
    return out


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

    story = [
        Paragraph(title, styles["Title"]),
        Spacer(1, 12),
        Paragraph("Dato skrevet: 23.06.2026", styles["BodyText"]),
        Paragraph("Forfatter: William Berg Steffenak - copyright", styles["BodyText"]),
        Spacer(1, 12),
    ]

    for line in lines:
        story.append(Paragraph(line, styles["BodyText"]))
        story.append(Spacer(1, 6))

    doc.build(story)
    output.seek(0)
    return output.getvalue()


# =========================================================
# DATAHENTING (RLS-STYRT)
# =========================================================
@st.cache_data(ttl=10)
def fetch_table(_cache_key: str, table_name: str, order_by: str | None = None, ascending: bool = True):
    client = get_client_with_session()
    query = client.table(table_name).select("*")
    if order_by:
        query = query.order(order_by, desc=not ascending)
    return query.execute().data or []


def clear_all_caches():
    fetch_table.clear()


def fetch_all_data(user_id: str):
    customers = fetch_table(user_id, "customers", "created_at", ascending=False)
    leads = fetch_table(user_id, "leads", "created_at", ascending=False)
    projects = fetch_table(user_id, "projects", "created_at", ascending=False)
    pricing = fetch_table(user_id, "pricing_calculations", "created_at", ascending=False)
    quotes = fetch_table(user_id, "quotes", "created_at", ascending=False)
    project_logs = fetch_table(user_id, "project_logs", "created_at", ascending=False)
    equipment = fetch_table(user_id, "equipment", "created_at", ascending=False)
    courses = fetch_table(user_id, "courses", "created_at", ascending=False)
    project_log_equipment = fetch_table(user_id, "project_log_equipment", "created_at", ascending=False)
    equipment_service_logs = fetch_table(user_id, "equipment_service_logs", "service_date", ascending=False)

    return {
        "customers": customers,
        "leads": leads,
        "projects": projects,
        "pricing": pricing,
        "quotes": quotes,
        "project_logs": project_logs,
        "equipment": equipment,
        "courses": courses,
        "project_log_equipment": project_log_equipment,
        "equipment_service_logs": equipment_service_logs,
    }


# =========================================================
# LOGIN-SKJERM
# =========================================================
if not current_user():
    st.markdown(
        """
        <div class="hero">
            <h1>Lokal CRM</h1>
            <p>Logg inn med Supabase Auth for å få tilgang til dine egne data.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([0.8, 1.2])

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Innlogging</p>', unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("E-post")
            password = st.text_input("Passord", type="password")
            submitted = st.form_submit_button("Logg inn")

            if submitted:
                try:
                    login(email, password)
                    st.success("Innlogging ok.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Innlogging feilet: {e}")

        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Viktig</p>', unsafe_allow_html=True)
        st.write(
            "- Appen bruker Supabase Auth + RLS.\n"
            "- Brukeren ser kun sine egne rader.\n"
            "- Nye rader lagres med brukerens `user_id`."
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


# =========================================================
# APP
# =========================================================
user = current_user()
user_id = user["id"]
client = get_client_with_session()

data = fetch_all_data(user_id)

customers_df = as_df(data["customers"])
leads_df = as_df(data["leads"])
projects_df = as_df(data["projects"])
pricing_df = as_df(data["pricing"])
quotes_df = as_df(data["quotes"])
project_logs_df = as_df(data["project_logs"])
equipment_df = as_df(data["equipment"])
courses_df = as_df(data["courses"])
project_log_equipment_df = as_df(data["project_log_equipment"])
equipment_service_logs_df = as_df(data["equipment_service_logs"])

# Enkle oppslag
customer_lookup = {}
if not customers_df.empty and "id" in customers_df.columns:
    for _, row in customers_df.iterrows():
        customer_lookup[row["id"]] = row.to_dict()

if not quotes_df.empty and "customer_id" in quotes_df.columns:
    quotes_df["customer_name"] = quotes_df["customer_id"].map(
        lambda x: customer_lookup.get(x, {}).get("name", "Ukjent")
    )

if not projects_df.empty and "customer_id" in projects_df.columns:
    projects_df["customer_name"] = projects_df["customer_id"].map(
        lambda x: customer_lookup.get(x, {}).get("name", "Ukjent")
    )

if not project_logs_df.empty and "project_id" in project_logs_df.columns and not projects_df.empty:
    project_map = {
        row["id"]: f"{row.get('customer_name', 'Ukjent')} • {row.get('project_type', '')}"
        for _, row in projects_df.iterrows()
    }
    project_logs_df["project_label"] = project_logs_df["project_id"].map(
        lambda x: project_map.get(x, "Ukjent oppdrag")
    )

# Lokalt “invoice basis”
if not projects_df.empty:
    log_hours = {}
    log_count = {}
    if not project_logs_df.empty:
        for _, row in project_logs_df.iterrows():
            pid = row["project_id"]
            log_hours[pid] = log_hours.get(pid, 0) + safe_number(row.get("hours", 0))
            log_count[pid] = log_count.get(pid, 0) + 1

    projects_df["total_logged_hours"] = projects_df["id"].map(lambda x: log_hours.get(x, 0))
    projects_df["log_entries"] = projects_df["id"].map(lambda x: log_count.get(x, 0))
else:
    projects_df["total_logged_hours"] = []
    projects_df["log_entries"] = []

# Utstyrsstatus
if not equipment_df.empty:
    def maintenance_status(row):
        category = row.get("category")
        interval = row.get("service_interval")
        hours_used = safe_number(row.get("hours_used", 0))
        if category == "Verneutstyr":
            return "Årlig kontroll", None
        if interval in (None, ""):
            return "Ingen intervall", None
        remaining = safe_number(interval) - hours_used
        if remaining <= 0:
            return "Service forfalt", remaining
        if remaining <= 10:
            return "Service snart", remaining
        return "OK", remaining

    ms = equipment_df.apply(maintenance_status, axis=1)
    equipment_df["maintenance_status"] = [x[0] for x in ms]
    equipment_df["remaining_hours_to_service"] = [x[1] for x in ms]


# =========================================================
# HEADER
# =========================================================
st.markdown(
    f"""
    <div class="hero">
        <h1>Lokal CRM</h1>
        <p>Innlogget som: {user.get('email', '-')}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.write(f"Bruker: **{user.get('email', '-') }**")
    global_search = st.text_input("Globalt søk")
    show_internal_ids = st.toggle("Vis tekniske ID-er", value=False)
    if st.button("Oppdater data"):
        clear_all_caches()
        st.rerun()
    if st.button("Logg ut"):
        logout()
        st.rerun()

# KPI
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Kunder", len(customers_df))
k2.metric("Leads", len(leads_df))
k3.metric("Oppdrag", len(projects_df))
k4.metric("Tilbud", len(quotes_df))
k5.metric("Klar for fakturering", int(projects_df["ready_for_invoice"].fillna(False).sum()) if not projects_df.empty and "ready_for_invoice" in projects_df.columns else 0)
k6.metric("Fakturert", int(projects_df["invoiced"].fillna(False).sum()) if not projects_df.empty and "invoiced" in projects_df.columns else 0)

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
        st.markdown('<p class="section-title">Oppdrag</p>', unsafe_allow_html=True)
        proj_view = filter_df(projects_df, global_search, ["customer_name", "project_type", "status", "address", "note"])
        if proj_view.empty:
            st.info("Ingen oppdrag.")
        else:
            cols = [c for c in ["customer_name", "project_type", "address", "status", "price", "ready_for_invoice", "invoiced"] if c in proj_view.columns]
            st.dataframe(display_df(proj_view[cols], show_internal_ids), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Vedlikeholdsstatus</p>', unsafe_allow_html=True)
        equip_view = filter_df(equipment_df, global_search, ["name", "category", "maintenance_status", "note"])
        if equip_view.empty:
            st.info("Ingen utstyr.")
        else:
            cols = [c for c in ["name", "category", "hours_used", "service_interval", "remaining_hours_to_service", "maintenance_status"] if c in equip_view.columns]
            st.dataframe(display_df(equip_view[cols], show_internal_ids), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# KUNDER
# =========================================================
elif area == "Kunder":
    left, right = st.columns([1.05, 0.95])

    with left:
        search = st.text_input("Søk i kunder")
        view = filter_df(customers_df, global_search, ["name", "phone", "email", "address", "customer_type", "note"])
        view = filter_df(view, search, ["name", "phone", "email", "address", "customer_type", "note"])
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="section-title">Kundeliste</p>', unsafe_allow_html=True)
        if view.empty:
            st.info("Ingen kunder.")
        else:
            cols = [c for c in ["name", "phone", "email", "address", "customer_type", "note"] if c in view.columns]
            st.dataframe(display_df(view[cols], show_internal_ids), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
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
                        "user_id": user_id,
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
        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# SALG
# =========================================================
elif area == "Salg":
    tabs = st.tabs(["Leads", "Kalkyle", "Tilbud"])

left, right = st.columns([1.05, 0.95])

        with left:
            search = st.text_input("Søk i leads")
            status_filter = st.selectbox("Status", ["Alle", "Ny", "Kontaktet", "Tilbud sendt", "Vunnet", "Tapt"])
            view = filter_df(leads_df, global_search, ["description", "source", "status", "note"])
            view = filter_df(view, search, ["description", "source", "status", "note"])
            if status_filter != "Alle" and not view.empty:
                view = view[view["status"] == status_filter]
            st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True) if not view.empty else st.info("Ingen leads.")

        with right:
            customers_opts = {f"{row['name']} • {short_id(row['id'])}": row["id"] for _, row in customers_df.iterrows()} if not customers_df.empty else {}
            with st.form("new_lead_form", clear_on_submit=True):
                customer_label = st.selectbox("Kunde *", list(customers_opts.keys()) if customers_opts else [])
                description = st.text_input("Beskrivelse *")
                source = st.text_input("Kilde", value="Tips")
                status = st.selectbox("Status", ["Ny", "Kontaktet", "Tilbud sendt", "Vunnet", "Tapt"])
                estimated_value = st.number_input("Estimert verdi", min_value=0.0, value=0.0, step=500.0)
                follow_up_date = st.date_input("Neste oppfølging", value=date.today())
                note = st.text_area("Notat")
                submitted = st.form_submit_button("Legg til lead")
                if submitted:
                    if not customers_opts:
                        st.warning("Du må ha minst én kunde.")
                    elif not description.strip():
                        st.warning("Beskrivelse må fylles ut.")
                    else:
                        client.table("leads").insert({
                            "user_id": user_id,
                            "customer_id": customers_opts[customer_label],
                            "description": description.strip(),
                            "source": source.strip() or None,
                            "status": status,
                            "estimated_value": float(estimated_value),
                            "follow_up_date": follow_up_date.isoformat(),
                            "note": note.strip() or None,
                        }).execute()
                        clear_all_caches()
                        st.success("Lead lagret.")
                        st.rerun()

    with tabsleft, right = st.columns([1.05, 0.95])

        with left:
            search = st.text_input("Søk i kalkyler")
            view = filter_df(pricing_df, global_search, ["job_type", "complexity", "note"])
            view = filter_df(view, search, ["job_type", "complexity", "note"])
            st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True) if not view.empty else st.info("Ingen kalkyler.")

        with right:
            customers_opts = {f"{row['name']} • {short_id(row['id'])}": row["id"] for _, row in customers_df.iterrows()} if not customers_df.empty else {}
            lead_opts = {f"{row['description']} • {short_id(row['id'])}": row["id"] for _, row in leads_df.iterrows()} if not leads_df.empty else {}

            with st.form("new_pricing_form", clear_on_submit=True):
                customer_label = st.selectbox("Kunde *", list(customers_opts.keys()) if customers_opts else [])
                lead_label = st.selectbox("Lead (valgfri)", ["Ingen"] + list(lead_opts.keys())) if lead_opts else st.selectbox("Lead (valgfri)", ["Ingen"])
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
                    if not customers_opts:
                        st.warning("Du må ha minst én kunde.")
                    elif not job_type.strip():
                        st.warning("Oppdragstype må fylles ut.")
                    else:
                        client.table("pricing_calculations").insert({
                            "user_id": user_id,
                            "customer_id": customers_opts[customer_label],
                            "lead_id": None if lead_label == "Ingen" else lead_opts[lead_label],
                            "job_type": job_type.strip(),
                            "travel_km": float(travel_km),
                            "complexity": complexity,
                            "estimated_hours": float(estimated_hours),
                            "hourly_rate": float(hourly_rate),
                            "extra_equipment_cost": float(extra_equipment_cost),
                            "disposal_cost": float(disposal_cost),
                            "minimum_price": float(minimum_price),
                            "calculated_price": float(calculated_price),
                            "valid_until": valid_until.isoformat(),
                            "note": note.strip() or None,
                        }).execute()
                        clear_all_caches()
                        st.success("Kalkyle lagret.")
                        st.rerun()

    with tabsleft, right = st.columns([1.05, 0.95])

        with left:
            search = st.text_input("Søk i tilbud")
            status_filter = st.selectbox("Tilbudsstatus", ["Alle", "Utkast", "Sendt", "Akseptert", "Avslått"])
            view = filter_df(quotes_df, global_search, ["customer_name", "job_type", "status", "send_method", "note"])
            view = filter_df(view, search, ["customer_name", "job_type", "status", "send_method", "note"])
            if status_filter != "Alle" and not view.empty:
                view = view[view["status"] == status_filter]
            st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True) if not view.empty else st.info("Ingen tilbud.")

            if not quotes_df.empty:
                export_map = {f"{row.get('customer_name', 'Ukjent')} • {row.get('job_type', '')} • {short_id(row['id'])}": row for _, row in quotes_df.iterrows()}
                selected_label = st.selectbox("Velg tilbud for eksport", list(export_map.keys()))
                selected_row = export_map[selected_label]
                quote_pdf = pdf_from_lines("Tilbud", [
                    f"Kunde: {selected_row.get('customer_name', '-')}",
                    f"Tilbud-ID: {selected_row.get('id', '-')}",
                    f"Oppdragstype: {selected_row.get('job_type', '-')}",
                    f"Status: {selected_row.get('status', '-')}",
                    f"Pris: {format_currency(selected_row.get('price', 0))}",
                    f"Gyldig til: {value_label(selected_row.get('valid_until'))}",
                    f"Notat: {value_label(selected_row.get('note'))}",
                ])
                quote_xlsx = dataframe_to_excel_bytes(pd.DataFrame([selected_row]), sheet_name="Tilbud")
                a, b = st.columns(2)
                with a:
                    st.download_button("Tilbud PDF", data=quote_pdf, file_name=f"tilbud_{short_id(selected_row['id'])}.pdf", mime="application/pdf")
                with b:
                    st.download_button("Tilbud Excel", data=quote_xlsx, file_name=f"tilbud_{short_id(selected_row['id'])}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        with right:
            pricing_opts = {f"{row['job_type']} • {format_currency(row['calculated_price'])} • {short_id(row['id'])}": row for _, row in pricing_df.iterrows()} if not pricing_df.empty else {}

            with st.form("new_quote_form", clear_on_submit=True):
                pricing_label = st.selectbox("Kalkyle *", list(pricing_opts.keys()) if pricing_opts else [])
                status = st.selectbox("Status", ["Utkast", "Sendt", "Akseptert", "Avslått"])
                send_method = st.text_input("Sendemetode", value="E-postutkast")
                valid_until = st.date_input("Gyldig til", value=date.today())
                note = st.text_area("Notat")
                submitted = st.form_submit_button("Opprett tilbud")
                if submitted:
                    if not pricing_opts:
                        st.warning("Du må ha minst én kalkyle.")
                    else:
                        selected = pricing_opts[pricing_label]
                        payload = {
                            "user_id": user_id,
                            "customer_id": selected["customer_id"],
                            "job_type": selected["job_type"],
                            "estimated_hours": selected["estimated_hours"],
                            "price": selected["calculated_price"],
                            "status": status,
                            "valid_until": valid_until.isoformat(),
                            "send_method": send_method.strip() or None,
                            "note": note.strip() or None,
                            "pricing_calculation_id": selected["id"],
                            "lead_id": selected.get("lead_id"),
                        }
                        now = datetime.now().astimezone().isoformat()
                        if status == "Sendt":
                            payload["sent_at"] = now
                        elif status == "Akseptert":
                            payload["accepted_at"] = now
                        elif status == "Avslått":
                            payload["declined_at"] = now

                        client.table("quotes").insert(payload).execute()
                        clear_all_caches()
                        st.success("Tilbud opprettet.")
                        st.rerun()

            st.markdown("---")
            st.markdown("### Aksepter tilbud → opprett oppdrag")
            quote_opts = {f"{row.get('customer_name', 'Ukjent')} • {row.get('job_type', '')} • {short_id(row['id'])}": row for _, row in quotes_df.iterrows()} if not quotes_df.empty else {}

            with st.form("quote_to_project_form"):
                quote_label = st.selectbox("Velg tilbud", list(quote_opts.keys()) if quote_opts else [])
                project_address = st.text_input("Adresse")
                project_status = st.selectbox("Oppdragsstatus", ["Planlagt", "Pågår", "Fullført", "Fakturert", "Avsluttet"])
                project_start = st.date_input("Startdato", value=date.today())
                hms = st.checkbox("HMS-vurdering", value=True)
                project_note = st.text_area("Prosjektnotat")
                submitted = st.form_submit_button("Aksepter tilbud og opprett oppdrag")
                if submitted:
                    if not quote_opts:
                        st.warning("Ingen tilbud tilgjengelig.")
                    else:
                        selected = quote_opts[quote_label]
                        client.table("quotes").update({
                            "status": "Akseptert",
                            "accepted_at": datetime.now().astimezone().isoformat(),
                        }).eq("id", selected["id"]).execute()

                        client.table("projects").insert({
                            "user_id": user_id,
                            "customer_id": selected["customer_id"],
                            "project_type": selected["job_type"],
                            "address": project_address or None,
                            "status": project_status,
                            "price": safe_number(selected["price"], 0),
                            "start_date": project_start.isoformat(),
                            "hms": hms,
                            "ready_for_invoice": False,
                            "invoiced": False,
                            "invoice_number": None,
                            "note": project_note or f"Opprettet fra tilbud {short_id(selected['id'])}",
                            "quote_id": selected["id"],
                        }).execute()

                        clear_all_caches()
                        st.success("Tilbud akseptert og oppdrag opprettet.")
                        st.rerun()

# =========================================================
# DRIFT
# =========================================================
elif area == "Drift":
    tabs = st.tabs(["Oppdragskort", "Oppdragslogg", "Utstyr"])

    with tabsleft, right = st.columns([1.05, 0.95])

        with left:
            search = st.text_input("Søk i oppdrag")
            status_filter = st.selectbox("Oppdragsstatus", ["Alle", "Planlagt", "Pågår", "Fullført", "Fakturert", "Avsluttet"])
            view = filter_df(projects_df, global_search, ["customer_name", "project_type", "address", "status", "note"])
            view = filter_df(view, search, ["customer_name", "project_type", "address", "status", "note"])
            if status_filter != "Alle" and not view.empty:
                view = view[view["status"] == status_filter]
            st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True) if not view.empty else st.info("Ingen oppdrag.")

        with right:
            project_opts = {f"{row.get('customer_name', 'Ukjent')} • {row.get('project_type', '')} • {short_id(row['id'])}": row for _, row in projects_df.iterrows()} if not projects_df.empty else {}
            if project_opts:
                label = st.selectbox("Velg oppdrag", list(project_opts.keys()))
                row = project_opts[label]
                project_id = row["id"]

                related_logs = project_logs_df[project_logs_df["project_id"] == project_id] if not project_logs_df.empty and "project_id" in project_logs_df.columns else pd.DataFrame()
                total_hours = float(related_logs["hours"].fillna(0).sum()) if not related_logs.empty and "hours" in related_logs.columns else 0.0
                related_links = project_log_equipment_df[project_log_equipment_df["project_log_id"].isin(related_logs["id"].tolist())] if not project_log_equipment_df.empty and not related_logs.empty and "id" in related_logs.columns else pd.DataFrame()

                st.markdown(f"**Kunde:** {row.get('customer_name', '-')}")
                st.markdown(f"**Oppdragstype:** {row.get('project_type', '-')}")
                st.markdown(f"**Adresse:** {value_label(row.get('address'))}")
                st.markdown(f"**Status:** {value_label(row.get('status'))}")
                st.markdown(f"**Pris:** {format_currency(row.get('price', 0))}")
                st.markdown(f"**Timer logget:** {total_hours}")
                st.markdown(f"**Loggposter:** {len(related_logs)}")
                st.markdown(f"**Utstyrskoblinger:** {len(related_links)}")
                st.markdown(f"**Klar for fakturering:** {value_label(row.get('ready_for_invoice'))}")
                st.markdown(f"**Fakturert:** {value_label(row.get('invoiced'))}")
                st.markdown(f"**Fakturanummer:** {value_label(row.get('invoice_number'))}")

                if not related_logs.empty:
                    st.dataframe(display_df(related_logs, show_internal_ids), use_container_width=True, hide_index=True)

                pdf_data = pdf_from_lines("Oppdragskort", [
                    f"Kunde: {row.get('customer_name', '-')}",
                    f"Oppdrag-ID: {row.get('id', '-')}",
                    f"Oppdragstype: {row.get('project_type', '-')}",
                    f"Adresse: {value_label(row.get('address'))}",
                    f"Status: {value_label(row.get('status'))}",
                    f"Pris: {format_currency(row.get('price', 0))}",
                    f"Timer logget: {total_hours}",
                    f"Loggposter: {len(related_logs)}",
                    f"Utstyrskoblinger: {len(related_links)}",
                    f"Fakturanummer: {value_label(row.get('invoice_number'))}",
                ])
                xlsx_data = dataframe_to_excel_bytes(pd.DataFrame([row]), sheet_name="Oppdragskort")
                a, b = st.columns(2)
                with a:
                    st.download_button("Oppdragskort PDF", data=pdf_data, file_name=f"oppdragskort_{short_id(project_id)}.pdf", mime="application/pdf")
                with b:
                    st.download_button("Oppdragskort Excel", data=xlsx_data, file_name=f"oppdragskort_{short_id(project_id)}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with tabsleft, right = st.columns([1.05, 0.95])

        with left:
            search = st.text_input("Søk i oppdragslogg")
            view = filter_df(project_logs_df, global_search, ["project_label", "task", "performed_by", "deviation", "next_step", "note"])
            view = filter_df(view, search, ["project_label", "task", "performed_by", "deviation", "next_step", "note"])
            st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True) if not view.empty else st.info("Ingen loggposter.")
            st.markdown("### Utstyr koblet til loggposter")
            st.dataframe(display_df(project_log_equipment_df, show_internal_ids), use_container_width=True, hide_index=True) if not project_log_equipment_df.empty else st.caption("Ingen koblinger ennå.")

        with right:
            project_opts = {f"{row.get('customer_name', 'Ukjent')} • {row.get('project_type', '')} • {short_id(row['id'])}": row["id"] for _, row in projects_df.iterrows()} if not projects_df.empty else {}
            equipment_opts = {f"{row.get('name')} • {row.get('category', '')} • {short_id(row['id'])}": row["id"] for _, row in equipment_df.iterrows()} if not equipment_df.empty else {}

            with st.form("new_log_form", clear_on_submit=True):
                project_label = st.selectbox("Oppdrag *", list(project_opts.keys()) if project_opts else [])
                log_date_value = st.date_input("Dato", value=date.today())
                hours = st.number_input("Timer", min_value=0.0, value=1.0, step=0.5)
                performed_by = st.text_input("Utført av", value="William")
                task = st.text_input("Hva ble gjort *")
                equipment_used = st.text_input("Utstyr brukt (fritekst)")
                deviation = st.text_input("Avvik / hendelser")
                next_step = st.text_input("Neste steg")
                note = st.text_area("Notat")

                eq1 = st.selectbox("Utstyr 1", ["Ingen"] + list(equipment_opts.keys())) if equipment_opts else st.selectbox("Utstyr 1", ["Ingen"])
                eq1_hours = st.number_input("Timer utstyr 1", min_value=0.0, value=0.0, step=0.5)
                eq2 = st.selectbox("Utstyr 2", ["Ingen"] + list(equipment_opts.keys()), key="eq2") if equipment_opts else st.selectbox("Utstyr 2", ["Ingen"], key="eq2")
                eq2_hours = st.number_input("Timer utstyr 2", min_value=0.0, value=0.0, step=0.5, key="eq2h")

                submitted = st.form_submit_button("Lagre loggpost")
                if submitted:
                    if not project_opts:
                        st.warning("Du må ha minst ett oppdrag.")
                    elif not task.strip():
                        st.warning("Du må skrive hva som ble gjort.")
                    else:
                        inserted = client.table("project_logs").insert({
                            "user_id": user_id,
                            "project_id": project_opts[project_label],
                            "log_date": log_date_value.isoformat(),
                            "hours": float(hours),
                            "performed_by": performed_by.strip() or None,
                            "task": task.strip(),
                            "equipment_used": equipment_used.strip() or None,
                            "deviation": deviation.strip() or None,
                            "next_step": next_step.strip() or None,
                            "note": note.strip() or None,
                        }).execute()

                        new_log = inserted.data[0]
                        if eq1 != "Ingen":
                            client.table("project_log_equipment").insert({
                                "user_id": user_id,
                                "project_log_id": new_log["id"],
                                "equipment_id": equipment_opts[eq1],
                                "hours_used": float(eq1_hours),
                                "note": f"Registrert fra app {datetime.now().isoformat()}",
                            }).execute()
                        if eq2 != "Ingen":
                            client.table("project_log_equipment").insert({
                                "user_id": user_id,
                                "project_log_id": new_log["id"],
                                "equipment_id": equipment_opts[eq2],
                                "hours_used": float(eq2_hours),
                                "note": f"Registrert fra app {datetime.now().isoformat()}",
                            }).execute()

                        clear_all_caches()
                        st.success("Loggpost lagret.")
                        st.rerun()

    with tabsleft, right = st.columns([1.05, 0.95])

        with left:
            search = st.text_input("Søk i utstyr")
            view = filter_df(equipment_df, global_search, ["name", "category", "status", "note", "maintenance_status"])
            view = filter_df(view, search, ["name", "category", "status", "note", "maintenance_status"])
            st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True) if not view.empty else st.info("Ingen utstyr.")
            st.markdown("### Servicehistorikk")
            st.dataframe(display_df(equipment_service_logs_df, show_internal_ids), use_container_width=True, hide_index=True) if not equipment_service_logs_df.empty else st.caption("Ingen servicehistorikk.")

        with right:
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
                            "user_id": user_id,
                            "name": name.strip(),
                            "category": category,
                            "hours_used": float(hours_used),
                            "service_interval": float(service_interval),
                            "last_service": last_service.isoformat(),
                            "status": status,
                            "note": note.strip() or None,
                        }).execute()
                        clear_all_caches()
                        st.success("Utstyr lagret.")
                        st.rerun()

            st.markdown("---")
            equipment_opts = {f"{row.get('name')} • {short_id(row['id'])}": row["id"] for _, row in equipment_df.iterrows()} if not equipment_df.empty else {}
            with st.form("service_form", clear_on_submit=True):
                equipment_label = st.selectbox("Velg utstyr", list(equipment_opts.keys()) if equipment_opts else [])
                service_date = st.date_input("Servicedato", value=date.today())
                hours_at_service = st.number_input("Timer ved service", min_value=0.0, value=0.0, step=0.5)
                description = st.text_input("Beskrivelse", value="Service registrert")
                cost = st.number_input("Kostnad", min_value=0.0, value=0.0, step=100.0)
                performed_by = st.text_input("Utført av", value="William")
                submitted = st.form_submit_button("Registrer service")
                if submitted:
                    if not equipment_opts:
                        st.warning("Ingen utstyr å registrere service på.")
                    else:
                        equipment_id = equipment_opts[equipment_label]
                        client.table("equipment_service_logs").insert({
                            "user_id": user_id,
                            "equipment_id": equipment_id,
                            "service_date": service_date.isoformat(),
                            "hours_at_service": float(hours_at_service),
                            "description": description.strip() or None,
                            "cost": float(cost),
                            "performed_by": performed_by.strip() or None,
                        }).execute()

                        client.table("equipment").update({
                            "last_service": service_date.isoformat(),
                            "hours_used": 0,
                            "status": "I drift",
                            "note": f"Service registrert {service_date.isoformat()}",
                        }).eq("id", equipment_id).execute()

                        clear_all_caches()
                        st.success("Service registrert.")
                        st.rerun()

# =========================================================
# FAKTURERING
# =========================================================
elif area == "Fakturering":
    left, right = st.columns([1.05, 0.95])

    with left:
        invoice_view = projects_df.copy()
        invoice_view = filter_df(invoice_view, global_search, ["customer_name", "project_type", "status", "note", "invoice_number"])
        cols = [c for c in ["customer_name", "project_type", "price", "total_logged_hours", "ready_for_invoice", "invoiced", "invoice_number"] if c in invoice_view.columns]
        st.dataframe(display_df(invoice_view[cols], show_internal_ids), use_container_width=True, hide_index=True) if not invoice_view.empty else st.info("Ingen fakturagrunnlag.")

        if not projects_df.empty:
            export_map = {f"{row.get('customer_name', 'Ukjent')} • {row.get('project_type', '')} • {short_id(row['id'])}": row for _, row in projects_df.iterrows()}
            label = st.selectbox("Velg oppdrag for eksport", list(export_map.keys()))
            row = export_map[label]
            pdf_data = pdf_from_lines("Fakturagrunnlag", [
                f"Kunde: {row.get('customer_name', '-')}",
                f"Oppdrag-ID: {row.get('id', '-')}",
                f"Oppdragstype: {row.get('project_type', '-')}",
                f"Prisgrunnlag: {format_currency(row.get('price', 0))}",
                f"Timer logget: {value_label(row.get('total_logged_hours'))}",
                f"Fakturanummer: {value_label(row.get('invoice_number'))}",
            ])
            excel_data = dataframe_to_excel_bytes(pd.DataFrame([row]), sheet_name="Fakturagrunnlag")
            a, b = st.columns(2)
            with a:
                st.download_button("Fakturagrunnlag PDF", data=pdf_data, file_name=f"fakturagrunnlag_{short_id(row['id'])}.pdf", mime="application/pdf")
            with b:
                st.download_button("Fakturagrunnlag Excel", data=excel_data, file_name=f"fakturagrunnlag_{short_id(row['id'])}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with right:
        project_opts = {f"{row.get('customer_name', 'Ukjent')} • {row.get('project_type', '')} • {short_id(row['id'])}": row for _, row in projects_df.iterrows()} if not projects_df.empty else {}
        with st.form("invoice_update_form"):
            project_label = st.selectbox("Velg oppdrag", list(project_opts.keys()) if project_opts else [])
            invoice_number = st.text_input("Fakturanummer")
            mark_ready = st.form_submit_button("Sett som klar for fakturering")
            mark_done = st.form_submit_button("Marker som fakturert")

            if mark_ready:
                if project_opts:
                    row = project_opts[project_label]
                    client.table("projects").update({"ready_for_invoice": True}).eq("id", row["id"]).execute()
                    clear_all_caches()
                    st.success("Oppdrag satt som klar for fakturering.")
                    st.rerun()

            if mark_done:
                if project_opts:
                    row = project_opts[project_label]
                    client.table("projects").update({
                        "ready_for_invoice": True,
                        "invoiced": True,
                        "invoice_number": invoice_number.strip() or None,
                        "status": "Fakturert",
                    }).eq("id", row["id"]).execute()
                    clear_all_caches()
                    st.success("Oppdrag markert som fakturert.")
                    st.rerun()

# =========================================================
# KURSING
# =========================================================
elif area == "Kursing":
    left, right = st.columns([1.05, 0.95])

    with left:
        search = st.text_input("Søk i kurs")
        view = filter_df(courses_df, global_search, ["title", "course_type", "provider", "note"])
        view = filter_df(view, search, ["title", "course_type", "provider", "note"])
        st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True) if not view.empty else st.info("Ingen kurs.")

    with right:
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
                        "user_id": user_id,
                        "title": title.strip(),
                        "course_type": course_type.strip() or None,
                        "provider": provider.strip() or None,
                        "course_date": course_date.isoformat(),
                        "duration": duration.strip() or None,
                        "documentation": documentation,
                        "note": note.strip() or None,
                    }).execute()
                    clear_all_caches()
                    st.success("Kurs lagret.")
                    st.rerun()

st.markdown("---")
st.caption(
    "Denne versjonen bruker Supabase Auth + RLS. "
    "Alle nye rader lagres med user_id, og hver bruker ser kun egne data."
)
