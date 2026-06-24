# =========================================
# Dato: 24.06.2026
# Forfatter: William Berg Steffenak - copyright
# Fil: app_v32_layout_cleaned.py
# Beskrivelse: Oppryddet og kjørbar CRM-app med Supabase Auth + RLS
# =========================================

from datetime import date, datetime
from io import BytesIO

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from supabase import Client, create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets.get("SUPABASE_PUBLISHABLE_KEY") or st.secrets.get("SUPABASE_KEY")

AUTHOR_NAME = "William Berg Steffenak"
COPYRIGHT_LINE = "William Berg Steffenak - copyright"
DOC_BUCKET = "crm-files"

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Lokal CRM",
    page_icon="📋",
    layout="wide",
)


# =========================================================
# SECRETS / CONFIG
# =========================================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets.get("SUPABASE_PUBLISHABLE_KEY") or st.secrets.get("SUPABASE_KEY")


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
    response = client.auth.sign_in_with_password({"email": email, "password": password})

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
    finally:
        st.session_state.pop("supabase_session", None)
        st.session_state.pop("auth_user", None)


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
    if df.empty or not search or not search.strip():
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
        hide_cols = [
            c for c in out.columns
            if c == "id" or c.endswith("_id") or c in {"created_at", "updated_at", "user_id"}
        ]
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
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for line in lines:
        story.append(Paragraph(str(line).replace("\n", "<br/>"), styles["BodyText"]))
        story.append(Spacer(1, 6))
    doc.build(story)
    output.seek(0)
    return output.getvalue()


def safe_date_input(value, fallback=None):
    if fallback is None:
        fallback = date.today()
    if value in (None, "", pd.NaT):
        return fallback
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return fallback


# =========================================================
# DATAHENTING (RLS-STYRT)
# =========================================================
@st.cache_data(ttl=10)
def fetch_table(_cache_key: str, table_name: str, order_by: str | None = None, ascending: bool = True):
    client = get_client_with_session()
    query = client.table(table_name).select("*")
    if order_by:
        query = query.order(order_by, desc=not ascending)
    result = query.execute()
    return result.data or []


def clear_all_caches():
    fetch_table.clear()


def fetch_all_data(user_id: str):
    return {
        "customers": fetch_table(user_id, "customers", "created_at", ascending=False),
        "leads": fetch_table(user_id, "leads", "created_at", ascending=False),
        "projects": fetch_table(user_id, "projects", "created_at", ascending=False),
        "pricing": fetch_table(user_id, "pricing_calculations", "created_at", ascending=False),
        "quotes": fetch_table(user_id, "quotes", "created_at", ascending=False),
        "project_logs": fetch_table(user_id, "project_logs", "created_at", ascending=False),
        "equipment": fetch_table(user_id, "equipment", "created_at", ascending=False),
        "courses": fetch_table(user_id, "courses", "created_at", ascending=False),
        "project_log_equipment": fetch_table(user_id, "project_log_equipment", "created_at", ascending=False),
        "equipment_service_logs": fetch_table(user_id, "equipment_service_logs", "service_date", ascending=False),
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
# APP / DATA
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

# Oppslag
customer_lookup = {}
if not customers_df.empty and "id" in customers_df.columns:
    for _, row in customers_df.iterrows():
        customer_lookup[row["id"]] = row.to_dict()

if not quotes_df.empty and "customer_id" in quotes_df.columns:
    quotes_df["customer_name"] = quotes_df["customer_id"].map(
        lambda x: customer_lookup.get(x, {}).get("name", "Ukjent")
    )

if not pricing_df.empty and "customer_id" in pricing_df.columns:
    pricing_df["customer_name"] = pricing_df["customer_id"].map(
        lambda x: customer_lookup.get(x, {}).get("name", "Ukjent")
    )

if not leads_df.empty and "customer_id" in leads_df.columns:
    leads_df["customer_name"] = leads_df["customer_id"].map(
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

# Invoice-basis
if not projects_df.empty:
    log_hours = {}
    log_count = {}
    if not project_logs_df.empty and "project_id" in project_logs_df.columns:
        for _, row in project_logs_df.iterrows():
            pid = row["project_id"]
            log_hours[pid] = log_hours.get(pid, 0) + safe_number(row.get("hours", 0))
            log_count[pid] = log_count.get(pid, 0) + 1
    projects_df["total_logged_hours"] = projects_df["id"].map(lambda x: log_hours.get(x, 0.0))
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

    equipment_df[["maintenance_status", "remaining_hours_to_service"]] = equipment_df.apply(
        lambda row: pd.Series(maintenance_status(row)), axis=1
    )


# =========================================================
# HEADER / SIDEBAR / KPI
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
    st.write(f"Bruker: **{user.get('email', '-')}**")
    global_search = st.text_input("Globalt søk")
    show_internal_ids = st.toggle("Vis tekniske ID-er", value=False)
    if st.button("Oppdater data"):
        clear_all_caches()
        st.rerun()
    if st.button("Logg ut"):
        logout()
        st.rerun()

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Kunder", len(customers_df))
k2.metric("Leads", len(leads_df))
k3.metric("Oppdrag", len(projects_df))
k4.metric("Tilbud", len(quotes_df))
k5.metric(
    "Klar for fakturering",
    int(projects_df["ready_for_invoice"].fillna(False).sum())
    if not projects_df.empty and "ready_for_invoice" in projects_df.columns
    else 0,
)
k6.metric(
    "Fakturert",
    int(projects_df["invoiced"].fillna(False).sum())
    if not projects_df.empty and "invoiced" in projects_df.columns
    else 0,
)

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
        st.markdown('<p class="section-title">Nyeste aktivitet</p>', unsafe_allow_html=True)
        dashboard_logs = filter_df(project_logs_df, global_search, ["project_label", "task", "performed_by", "note"])
        if dashboard_logs.empty:
            st.info("Ingen aktivitet registrert.")
        else:
            cols = [c for c in ["project_label", "log_date", "hours", "performed_by", "task", "next_step"] if c in dashboard_logs.columns]
            st.dataframe(display_df(dashboard_logs[cols], show_internal_ids), use_container_width=True, hide_index=True)
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
if area == "Kunder":
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
        cols = st.columns(2)
        for idx, (_, row) in enumerate(view.iterrows()):
            with cols[idx % 2]:
                st.markdown(
                    f"""
                    <div class="card">
                        <p class="section-title" style="margin-bottom:6px;">{row.get('name', '-')}</p>
                        <div><strong>Type:</strong> {value_label(row.get('customer_type'))}</div>
                        <div><strong>Telefon:</strong> {value_label(row.get('phone'))}</div>
                        <div><strong>E-post:</strong> {value_label(row.get('email'))}</div>
                        <div><strong>Adresse:</strong> {value_label(row.get('address'))}</div>
                        <div><strong>Notat:</strong> {value_label(row.get('note'))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with st.expander("Vis kundetabell"):
            st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown(
            """
            <div class="card">
                <h3>Ny kunde</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("new_customer_form", clear_on_submit=True):
            name = st.text_input("Navn *")
            phone = st.text_input("Telefon")
            email = st.text_input("E-post")
            address = st.text_input("Adresse")
            customer_type = st.selectbox("Kundetype", ["Privat", "Bedrift", "Borettslag", "Annet"])
            note = st.text_area("Notat")
            submitted = st.form_submit_button("Lagre kunde")

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

        st.markdown("---")
        st.markdown("### 📁 Dokumenter")

        customer_options = {}
        if not customers_df.empty and "id" in customers_df.columns:
            customer_options = {
                f"{row.get('name', 'Ukjent')} • {short_id(row['id'])}": row["id"]
                for _, row in customers_df.iterrows()
            }

        if not customer_options:
            st.info("Du må ha minst én kunde for å bruke dokumentmodulen.")
        else:
            selected_customer_label = st.selectbox(
                "Velg kunde for dokumenter",
                list(customer_options.keys()),
                key="documents_customer_select"
            )
            customer_id = customer_options[selected_customer_label]

            doc_category = st.selectbox(
                "Kategori",
                ["Kontrakt", "Tilbud", "Faktura", "Bilde", "Rapport", "Annet"],
                key=f"doc_category_{customer_id}"
            )

            uploaded_doc = st.file_uploader(
                "Last opp dokument",
                type=["pdf", "doc", "docx", "xls", "xlsx", "png", "jpg", "jpeg", "webp", "txt", "csv"],
                key=f"doc_upload_{customer_id}"
            )

            if st.button("Last opp dokument", key=f"doc_upload_btn_{customer_id}"):
                if not uploaded_doc:
                    st.warning("Velg en fil først.")
                else:
                    try:
                        file_bytes = uploaded_doc.getvalue()
                        file_name = uploaded_doc.name
                        file_type = uploaded_doc.type or "application/octet-stream"
                        file_size = len(file_bytes)

                        safe_name = file_name.replace(" ", "_")
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        category_folder = (
                            doc_category.lower()
                            .replace(" ", "_")
                            .replace("æ", "ae")
                            .replace("ø", "o")
                            .replace("å", "a")
                        )
                        storage_path = f"customers/{customer_id}/{category_folder}/{timestamp}_{safe_name}"

                        client.storage.from_(DOC_BUCKET).upload(
                            storage_path,
                            file_bytes,
                            {"content-type": file_type}
                        )

                        payload = {
                            "customer_id": customer_id,
                            "file_name": file_name,
                            "file_type": file_type,
                            "file_size": file_size,
                            "category": doc_category,
                            "storage_path": storage_path,
                            "created_by": user_id,
                            "author_name": AUTHOR_NAME,
                            "copyright_line": COPYRIGHT_LINE,
                        }

                        client.table("documents").insert(payload).execute()

                        st.success("Dokument lastet opp ✅")
                        clear_all_caches()
                        st.rerun()

                    except Exception as e:
                        st.error(f"Opplasting feilet: {e}")

            st.markdown("#### Dokumentliste")

            try:
                docs_res = (
                    client.table("documents")
                    .select("*")
                    .eq("customer_id", customer_id)
                    .order("uploaded_at", desc=True)
                    .execute()
                )
                docs = docs_res.data if docs_res.data else []

                if docs:
                    for doc in docs:
                        col1, col2, col3 = st.columns([5, 1, 1])

                        with col1:
                            st.write(f"📄 **{doc.get('file_name', '-')}**")
                            st.caption(f"Kategori: {doc.get('category', '-')}")

                        with col2:
                            try:
                                signed = client.storage.from_(DOC_BUCKET).create_signed_url(
                                    doc["storage_path"],
                                    3600
                                )

                                signed_url = None

                                if isinstance(signed, dict):
                                    signed_url = (
                                        signed.get("signedURL")
                                        or signed.get("signed_url")
                                        or (signed.get("data") or {}).get("signedURL")
                                        or (signed.get("data") or {}).get("signed_url")
                                        or (signed.get("data") or {}).get("signedUrl")
                                        )
                                elif hasattr(signed, "data"):
                                    data_obj = signed.data
                                if isinstance(data_obj, dict):
                                    signed_url = (
                                        data_obj.get("signedURL")
                                        or data_obj.get("signed_url")
                                        or data_obj.get("signedUrl")
                                    )

                            if signed_url:
                                st.link_button("Åpne", signed_url, key=f"open_{doc['id']}")
                            else:
                                st.caption("Ingen lenke")
                                st.caption(f"Path: {doc.get('storage_path', '-')}")
                                st.code(str(signed), language="python")

                        except Exception as e:
                            st.caption("Feil lenke")
                            st.caption(f"Path: {doc.get('storage_path', '-')}")
                            st.code(str(e), language="python")


                        with col3:
                            if st.button("Slett", key=f"delete_doc_{doc['id']}"):
                                try:
                                    try:
                                        client.storage.from_(DOC_BUCKET).remove([doc["storage_path"]])
                                    except Exception:
                                        pass

                                    client.table("documents").delete().eq("id", doc["id"]).execute()

                                    st.success("Dokument slettet ✅")
                                    clear_all_caches()
                                    st.rerun()

                                except Exception as e:
                                    st.error(f"Sletting feilet: {e}")
                else:
                    st.info("Ingen dokumenter registrert på denne kunden ennå.")

            except Exception as e:
                st.error(f"Kunne ikke hente dokumenter: {e}")

        st.markdown("\n", unsafe_allow_html=True)

# =========================================================
# SALG
# =========================================================
if area == "Salg":
    tab_leads, tab_pricing, tab_quotes = st.tabs(["Leads", "Kalkyle", "Tilbud"])

    with tab_leads:
        left, right = st.columns([1.05, 0.95])

        with left:
            search = st.text_input("Søk i leads")
            status_filter = st.selectbox("Status", ["Alle", "Ny", "Kontaktet", "Tilbud sendt", "Vunnet", "Tapt"])
            view = filter_df(leads_df, global_search, ["description", "source", "status", "note"])
            view = filter_df(view, search, ["description", "source", "status", "note"])

            if status_filter != "Alle" and not view.empty:
                view = view[view["status"] == status_filter]

            if not view.empty:
                st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True)
            else:
                st.info("Ingen leads.")

        with right:
            customers_opts = {
                f"{row['name']} • {short_id(row['id'])}": row["id"]
                for _, row in customers_df.iterrows()
            } if not customers_df.empty else {}

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

    with tab_pricing:
        left, right = st.columns([1.05, 0.95])

        with left:
            search = st.text_input("Søk i kalkyler")
            view = filter_df(pricing_df, global_search, ["job_type", "complexity", "note"])
            view = filter_df(view, search, ["job_type", "complexity", "note"])

            if not view.empty:
                st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True)
            else:
                st.info("Ingen kalkyler.")

        with right:
            customers_opts = {
                f"{row['name']} • {short_id(row['id'])}": row["id"]
                for _, row in customers_df.iterrows()
            } if not customers_df.empty else {}

            lead_opts = {
                f"{row['description']} • {short_id(row['id'])}": row["id"]
                for _, row in leads_df.iterrows()
            } if not leads_df.empty else {}

            with st.form("new_pricing_form", clear_on_submit=True):
                customer_label = st.selectbox("Kunde *", list(customers_opts.keys()) if customers_opts else [])
                lead_label = st.selectbox("Lead (valgfri)", ["Ingen"] + list(lead_opts.keys()))
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
                calculated_price = max(
                    minimum_price,
                    round((base_labor + travel_cost + extra_equipment_cost + disposal_cost) * multiplier / 100) * 100
                )

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

    with tab_quotes:
        st.info("Tilbud-delen kan vi legge inn igjen når Salg-blokken starter uten syntax-feil.")
# =========================================================
# DRIFT
# =========================================================
if area == "Drift":
    tab_project_card, tab_project_logs, tab_equipment = st.tabs(["Oppdragskort", "Oppdragslogg", "Utstyr"])

    with tab_project_card:
        left, right = st.columns([1.05, 0.95])

        with left:
            search = st.text_input("Søk i oppdrag")
            status_filter = st.selectbox("Oppdragsstatus", ["Alle", "Planlagt", "Pågår", "Fullført", "Fakturert", "Avsluttet"])
            view = filter_df(projects_df, global_search, ["customer_name", "project_type", "address", "status", "note"])
            view = filter_df(view, search, ["customer_name", "project_type", "address", "status", "note"])
            if status_filter != "Alle" and not view.empty and "status" in view.columns:
                view = view[view["status"] == status_filter]
            if not view.empty:
                st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True)
            else:
                st.info("Ingen oppdrag.")

        with right:
            project_opts = {
                f"{row.get('customer_name', 'Ukjent')} • {row.get('project_type', '')} • {short_id(row['id'])}": row
                for _, row in projects_df.iterrows()
            } if not projects_df.empty else {}
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
            else:
                st.info("Ingen oppdrag tilgjengelig.")

    with tab_project_logs:
        left, right = st.columns([1.05, 0.95])

        with left:
            search = st.text_input("Søk i oppdragslogg")
            view = filter_df(project_logs_df, global_search, ["project_label", "task", "performed_by", "deviation", "next_step", "note"])
            view = filter_df(view, search, ["project_label", "task", "performed_by", "deviation", "next_step", "note"])
            if not view.empty:
                st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True)
            else:
                st.info("Ingen loggposter.")
                st.markdown("### Utstyr koblet til loggposter")
            if not project_log_equipment_df.empty:
                st.dataframe(display_df(project_log_equipment_df, show_internal_ids), use_container_width=True, hide_index=True)
            else:
                st.caption("Ingen koblinger ennå.")

        with right:
            project_opts = {
                f"{row.get('customer_name', 'Ukjent')} • {row.get('project_type', '')} • {short_id(row['id'])}": row["id"]
                for _, row in projects_df.iterrows()
            } if not projects_df.empty else {}
            equipment_opts = {
                f"{row.get('name')} • {row.get('category', '')} • {short_id(row['id'])}": row["id"]
                for _, row in equipment_df.iterrows()
            } if not equipment_df.empty else {}

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

    with tab_equipment:
        left, right = st.columns([1.05, 0.95])

        with left:
            search = st.text_input("Søk i utstyr")
            view = filter_df(equipment_df, global_search, ["name", "category", "status", "note", "maintenance_status"])
            view = filter_df(view, search, ["name", "category", "status", "note", "maintenance_status"])
            if not view.empty:
                st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True)
            else:
                st.info("Ingen utstyr.")
                st.markdown("### Servicehistorikk")
            if not equipment_service_logs_df.empty:
                st.dataframe(display_df(equipment_service_logs_df, show_internal_ids), use_container_width=True, hide_index=True)
            else:
                st.caption("Ingen servicehistorikk.")

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
            equipment_opts = {
                f"{row.get('name')} • {short_id(row['id'])}": row["id"]
                for _, row in equipment_df.iterrows()
            } if not equipment_df.empty else {}
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
                        clear_all_caches()
                        st.success("Service registrert.")
                        st.rerun()


# =========================================================
# FAKTURERING
# =========================================================
if area == "Fakturering":
    left, right = st.columns([1.05, 0.95])

    invoice_view = projects_df.copy()
    if not invoice_view.empty:
        invoice_view = filter_df(invoice_view, global_search, ["customer_name", "project_type", "address", "status", "note", "invoice_number"])

    with left:
        st.markdown("### Oppdrag til fakturering")
        if invoice_view.empty:
            st.info("Ingen oppdrag tilgjengelig.")
        else:
            cols = [
                c for c in [
                    "customer_name",
                    "project_type",
                    "address",
                    "status",
                    "price",
                    "total_logged_hours",
                    "ready_for_invoice",
                    "invoiced",
                    "invoice_number",
                    "start_date",
                ]
                if c in invoice_view.columns
            ]
            st.dataframe(display_df(invoice_view[cols], show_internal_ids), use_container_width=True, hide_index=True)

    with right:
        project_opts = {
            f"{row.get('customer_name', 'Ukjent')} • {row.get('project_type', '')} • {short_id(row['id'])}": row
            for _, row in projects_df.iterrows()
        } if not projects_df.empty else {}

        with st.form("invoice_update_form"):
            project_label = st.selectbox("Velg oppdrag", list(project_opts.keys()) if project_opts else [])
            ready_for_invoice = st.checkbox("Klar for fakturering", value=True)
            invoiced = st.checkbox("Fakturert", value=False)
            invoice_number = st.text_input("Fakturanummer")
            invoice_note = st.text_area("Notat")
            submitted = st.form_submit_button("Oppdater fakturastatus")
            if submitted:
                if not project_opts:
                    st.warning("Ingen oppdrag tilgjengelig.")
                else:
                    selected = project_opts[project_label]
                    payload = {
                        "ready_for_invoice": ready_for_invoice,
                        "invoiced": invoiced,
                        "invoice_number": invoice_number.strip() or None,
                    }
                    if invoice_note.strip():
                        existing_note = selected.get("note") or ""
                        payload["note"] = (existing_note + "\n" + invoice_note.strip()).strip()
                    client.table("projects").update(payload).eq("id", selected["id"]).execute()
                    clear_all_caches()
                    st.success("Fakturastatus oppdatert.")
                    st.rerun()


# =========================================================
# KURSING
# =========================================================
if area == "Kursing":
    left, right = st.columns([1.05, 0.95])

    with left:
        search = st.text_input("Søk i kurs")
        view = filter_df(courses_df, global_search, ["title", "course_type", "provider", "documentation", "note"])
        view = filter_df(view, search, ["title", "course_type", "provider", "documentation", "note"])
        if not view.empty:
            st.dataframe(display_df(view, show_internal_ids), use_container_width=True, hide_index=True)
        else:
            st.info("Ingen kurs registrert.")

    with right:
        with st.form("new_course_form", clear_on_submit=True):
            title = st.text_input("Kurstittel *")
            course_type = st.selectbox("Type", ["Kurs", "Sertifisering", "Opplæring", "Annet"])
            provider = st.text_input("Tilbyder")
            course_date = st.date_input("Dato", value=date.today())
            duration = st.text_input("Varighet", value="1 dag")
            documentation = st.text_input("Dokumentasjon / lenke")
            note = st.text_area("Notat")
            submitted = st.form_submit_button("Lagre kurs")
            if submitted:
                if not title.strip():
                    st.warning("Kurstittel må fylles ut.")
                else:
                    client.table("courses").insert({
                        "user_id": user_id,
                        "title": title.strip(),
                        "course_type": course_type,
                        "provider": provider.strip() or None,
                        "course_date": course_date.isoformat(),
                        "duration": duration.strip() or None,
                        "documentation": documentation.strip() or None,
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
