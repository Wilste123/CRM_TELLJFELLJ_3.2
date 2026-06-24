from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

AUTHOR_NAME = "William Berg Steffenak"
COPYRIGHT_LINE = "William Berg Steffenak - copyright"
BUCKET_NAME = "crm-files"

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".png", ".jpg", ".jpeg", ".webp", ".txt", ".csv"
}
MAX_FILE_SIZE_MB = 25


def _safe_filename(filename: str) -> str:
    filename = filename.strip().replace(" ", "_")
    filename = re.sub(r"[^A-Za-z0-9._-]", "", filename)
    return filename or "fil"


def _format_size(num_bytes: Optional[int]) -> str:
    if not num_bytes:
        return "-"
    size = float(num_bytes)
    units = ["B", "KB", "MB", "GB"]
    idx = 0
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1
    if idx == 0:
        return f"{int(size)} {units[idx]}"
    return f"{size:.1f} {units[idx]}"


def _ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def _category_folder(category: str) -> str:
    return (
        category.strip()
        .lower()
        .replace("æ", "ae")
        .replace("ø", "o")
        .replace("å", "a")
        .replace(" ", "_")
    )


def _signed_url(supabase, storage_path: str, expires_in: int = 3600) -> Optional[str]:
    try:
        res = supabase.storage.from_(BUCKET_NAME).create_signed_url(storage_path, expires_in)
        if isinstance(res, dict):
            return res.get("signedURL") or res.get("signed_url")
        return None
    except Exception:
        return None


def _delete_document(supabase, doc_id: str, storage_path: str) -> tuple[bool, str]:
    try:
        supabase.storage.from_(BUCKET_NAME).remove([storage_path])
    except Exception:
        pass

    try:
        supabase.table("documents").delete().eq("id", doc_id).execute()
        return True, "Dokument slettet."
    except Exception as e:
        return False, f"Kunne ikke slette dokumentrad i databasen: {e}"


def render_documents_module(
    supabase,
    customer_id: str,
    customer_name: Optional[str] = None,
    current_user_id: Optional[str] = None,
):
    st.subheader("📁 Dokumenter")

    if not customer_id:
        st.info("Velg en kunde først for å bruke dokumentmodulen.")
        return

    if customer_name:
        st.caption(f"Kunde: {customer_name}")

    with st.expander("Last opp nytt dokument", expanded=True):
        col1, col2 = st.columns([1, 1])

        with col1:
            category = st.selectbox(
                "Kategori",
                ["Kontrakt", "Tilbud", "Faktura", "Bilde", "Rapport", "Annet"],
                key=f"doc_category_{customer_id}",
            )

        with col2:
            project_id = st.text_input(
                "Prosjekt-ID (valgfritt)",
                key=f"doc_project_id_{customer_id}",
            )

        custom_title = st.text_input(
            "Visningsnavn (valgfritt)",
            placeholder="Eks: Tilbud - Olsen - 2026-06-24",
            key=f"doc_custom_title_{customer_id}",
        )

        uploaded_file = st.file_uploader(
            "Velg fil",
            type=[ext.replace(".", "") for ext in sorted(ALLOWED_EXTENSIONS)],
            key=f"doc_upload_{customer_id}",
        )

        if st.button("Last opp dokument", key=f"doc_upload_btn_{customer_id}", type="primary"):
            if not uploaded_file:
                st.warning("Velg en fil først.")
            else:
                file_name_original = uploaded_file.name
                file_ext = _ext(file_name_original)

                if file_ext not in ALLOWED_EXTENSIONS:
                    st.error(f"Filtype {file_ext} er ikke tillatt.")
                    st.stop()

                file_bytes = uploaded_file.getvalue()
                file_size = len(file_bytes)

                if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                    st.error(f"Filen er for stor. Maks størrelse er {MAX_FILE_SIZE_MB} MB.")
                    st.stop()

                safe_original = _safe_filename(file_name_original)
                mime_type = uploaded_file.type or "application/octet-stream"

                if custom_title.strip():
                    safe_title = _safe_filename(custom_title.strip())
                    final_file_name = f"{safe_title}{file_ext}"
                else:
                    final_file_name = safe_original

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                folder = _category_folder(category)
                storage_path = f"customers/{customer_id}/{folder}/{timestamp}_{final_file_name}"

                try:
                    supabase.storage.from_(BUCKET_NAME).upload(
                        storage_path,
                        file_bytes,
                        {
                            "content-type": mime_type,
                            "upsert": "false",
                        },
                    )

                    payload = {
                        "customer_id": customer_id,
                        "project_id": project_id or None,
                        "file_name": final_file_name,
                        "file_type": mime_type,
                        "file_size": file_size,
                        "category": category,
                        "storage_path": storage_path,
                        "author_name": AUTHOR_NAME,
                        "copyright_line": COPYRIGHT_LINE,
                    }

                    if current_user_id:
                        payload["created_by"] = current_user_id

                    supabase.table("documents").insert(payload).execute()

                    st.success("Dokument lastet opp ✅")
                    st.rerun()

                except Exception as e:
                    st.error(f"Opplasting feilet: {e}")

    st.markdown("---")

    try:
        res = (
            supabase.table("documents")
            .select("*")
            .eq("customer_id", customer_id)
            .order("uploaded_at", desc=True)
            .execute()
        )
        docs = res.data or []
    except Exception as e:
        st.error(f"Kunne ikke hente dokumenter: {e}")
        return

    categories = ["Alle"] + sorted({doc.get("category", "Annet") for doc in docs})
    f1, f2 = st.columns([1, 2])

    with f1:
        selected_category = st.selectbox(
            "Filter kategori",
            categories,
            key=f"doc_filter_category_{customer_id}",
        )

    with f2:
        search_text = st.text_input(
            "Søk i filnavn",
            key=f"doc_search_{customer_id}",
            placeholder="Søk etter dokument...",
        ).strip().lower()

    filtered_docs = docs
    if selected_category != "Alle":
        filtered_docs = [d for d in filtered_docs if d.get("category") == selected_category]

    if search_text:
        filtered_docs = [
            d for d in filtered_docs
            if search_text in (d.get("file_name") or "").lower()
        ]

    st.markdown(f"**Antall dokumenter:** {len(filtered_docs)}")

    if not filtered_docs:
        st.info("Ingen dokumenter å vise.")
        return

    for doc in filtered_docs:
        doc_id = doc.get("id")
        file_name = doc.get("file_name", "-")
        category = doc.get("category", "-")
        file_size = _format_size(doc.get("file_size"))
        uploaded_at = doc.get("uploaded_at", "-")
        author_name = doc.get("author_name") or "-"
        copyright_line = doc.get("copyright_line") or "-"
        storage_path = doc.get("storage_path")

        signed_url = _signed_url(supabase, storage_path, 3600) if storage_path else None

        box = st.container(border=True)
        with box:
            left, right = st.columns([5, 1])

            with left:
                st.write(f"📄 **{file_name}**")
                st.caption(
                    f"Kategori: {category} | Størrelse: {file_size} | Lastet opp: {uploaded_at}"
                )
                st.caption(f"Forfatter: {author_name}")
                st.caption(copyright_line)

            with right:
                if signed_url:
                    st.link_button("Åpne", signed_url, key=f"open_{doc_id}")
                else:
                    st.caption("Ingen lenke")

            action_col1, action_col2 = st.columns([1, 4])

            with action_col1:
                if st.button("Slett", key=f"delete_btn_{doc_id}"):
                    st.session_state[f"confirm_delete_{doc_id}"] = True

            if st.session_state.get(f"confirm_delete_{doc_id}", False):
                with action_col2:
                    st.warning(f"Bekreft sletting av: {file_name}")
                    c1, c2 = st.columns([1, 1])

                    with c1:
                        if st.button("Bekreft", key=f"confirm_delete_btn_{doc_id}", type="primary"):
                            ok, msg = _delete_document(supabase, doc_id, storage_path)
                            if ok:
                                st.success(msg)
                                st.session_state[f"confirm_delete_{doc_id}"] = False
                                st.rerun()
                            else:
                                st.error(msg)

                    with c2:
                        if st.button("Avbryt", key=f"cancel_delete_btn_{doc_id}"):
                            st.session_state[f"confirm_delete_{doc_id}"] = False
                            st.rerun()
