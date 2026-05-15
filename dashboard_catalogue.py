"""Streamlit UI for merchant product catalogue — full CRUD + CSV import/export."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from dashboard import (
    hint_box_html,
    page_stack_close_html,
    page_stack_open_html,
    section_header_html,
    section_heading_html,
)
from session_runtime import mark_data_changed
from tools.catalogue_tools import (
    catalogue_version,
    delete_catalogue_item,
    find_catalogue_item,
    generate_catalogue_sku,
    load_product_catalogue_from_csv,
    normalize_catalogue_row,
    normalize_catalogue_tool,
    save_product_catalogue_tool,
    upsert_catalogue_item,
    validate_catalogue_tool,
)

CATEGORIES = ["makanan", "minuman", "catering", "snack", "other"]
NEW_PRODUCT_KEY = "__new__"


def _cat() -> list[dict[str, Any]]:
    if "product_catalogue" not in st.session_state or not st.session_state.product_catalogue:
        st.session_state.product_catalogue = load_product_catalogue_from_csv()
    return st.session_state.product_catalogue


def _save_and_refresh(cat: list[dict[str, Any]]) -> None:
    st.session_state.product_catalogue = normalize_catalogue_tool(cat)
    st.session_state.catalogue_version = catalogue_version(st.session_state.product_catalogue)
    save_product_catalogue_tool(st.session_state.product_catalogue)
    mark_data_changed("catalogue_updated")


def _display_dataframe(cat: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for r in cat:
        aliases = r.get("aliases") or []
        alias_str = " · ".join(aliases[:4])
        if len(aliases) > 4:
            alias_str += " …"
        rows.append(
            {
                "SKU": r.get("sku"),
                "Produk": r.get("product_name"),
                "Alias": alias_str,
                "Kategori": r.get("category"),
                "Harga": f"Rp {int(r.get('unit_price') or 0):,}",
                "Satuan": r.get("unit"),
                "Status": "Aktif" if r.get("is_active", True) else "Nonaktif",
                "Catatan": r.get("notes") or "",
            }
        )
    return pd.DataFrame(rows)


def _product_label(row: dict[str, Any]) -> str:
    name = row.get("product_name") or "?"
    sku = row.get("sku") or ""
    price = int(row.get("unit_price") or 0)
    return f"{name} — Rp {price:,} ({sku})"


def _row_from_form(
    *,
    sku: str,
    name: str,
    aliases: str,
    category: str,
    price: int,
    unit: str,
    active: bool,
    notes: str,
) -> dict[str, Any]:
    return normalize_catalogue_row(
        {
            "sku": sku.strip() or generate_catalogue_sku(_cat()),
            "product_name": name.strip(),
            "aliases": aliases.strip() or name.strip(),
            "category": category,
            "unit_price": price,
            "unit": unit.strip() or "porsi",
            "is_active": active,
            "notes": notes.strip(),
        }
    )


def _render_crud_form(cat: list[dict[str, Any]], edit_sku: str) -> None:
    is_new = edit_sku == NEW_PRODUCT_KEY
    existing = None if is_new else find_catalogue_item(cat, edit_sku)
    if not is_new and existing is None:
        st.warning("Produk tidak ditemukan — pilih lagi dari daftar.")
        return

    default_aliases = ""
    if existing:
        aliases_list = existing.get("aliases") or []
        default_aliases = "|".join(
            a for a in aliases_list if a != existing.get("product_name")
        )

    title = "Tambah produk baru" if is_new else f"Ubah: {existing.get('product_name')}"
    st.markdown(f"**{title}**")

    with st.form(f"cat_crud_{edit_sku}", clear_on_submit=is_new):
        if not is_new:
            st.text_input("SKU", value=existing.get("sku", ""), disabled=True)
        name = st.text_input(
            "Nama produk *",
            value="" if is_new else str(existing.get("product_name") or ""),
            placeholder="Pisang Goreng",
        )
        aliases = st.text_input(
            "Alias (pisahkan dengan |)",
            value=default_aliases,
            placeholder="pisang goreng|pisgor",
            help="Kata yang dipakai pelanggan di WhatsApp, mis. nasgor untuk Nasi Goreng.",
        )
        c1, c2 = st.columns(2)
        with c1:
            idx = 0
            if existing and existing.get("category") in CATEGORIES:
                idx = CATEGORIES.index(str(existing.get("category")))
            category = st.selectbox("Kategori", CATEGORIES, index=idx)
            price = st.number_input(
                "Harga satuan (Rp) *",
                min_value=0,
                value=8000 if is_new else int(existing.get("unit_price") or 0),
                step=500,
            )
        with c2:
            unit = st.text_input(
                "Satuan",
                value="pcs" if is_new else str(existing.get("unit") or "porsi"),
            )
            active = st.checkbox(
                "Aktif (bisa dipesan)",
                value=True if is_new else bool(existing.get("is_active", True)),
            )
        notes = st.text_input(
            "Catatan",
            value="" if is_new else str(existing.get("notes") or ""),
        )

        submitted = st.form_submit_button(
            "Simpan produk" if is_new else "Simpan perubahan",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        if not name.strip():
            st.error("Nama produk wajib diisi.")
            return
        if price <= 0:
            st.error("Harga harus lebih dari Rp 0.")
            return
        sku_val = generate_catalogue_sku(cat) if is_new else str(existing.get("sku"))
        row = _row_from_form(
            sku=sku_val,
            name=name,
            aliases=aliases,
            category=category,
            price=int(price),
            unit=unit,
            active=active,
            notes=notes,
        )
        updated = upsert_catalogue_item(cat, row)
        _save_and_refresh(updated)
        st.session_state.catalogue_edit_sku = row["sku"]
        st.success(f"{row['product_name']} tersimpan.")
        st.rerun()


def _render_delete_block(cat: list[dict[str, Any]], edit_sku: str) -> None:
    if edit_sku == NEW_PRODUCT_KEY:
        return
    row = find_catalogue_item(cat, edit_sku)
    if not row:
        return
    st.markdown("---")
    confirm_key = f"cat_del_confirm_{edit_sku}"
    if not st.session_state.get(confirm_key):
        if st.button(
            f"Hapus {row.get('product_name')}",
            key=f"cat_del_{edit_sku}",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state[confirm_key] = True
            st.rerun()
    else:
        st.warning(
            f"Yakin hapus **{row.get('product_name')}** ({edit_sku})? "
            "Pesanan lama tidak terhapus, tapi alias tidak akan cocok lagi."
        )
        dc1, dc2 = st.columns(2)
        with dc1:
            if st.button("Ya, hapus", key=f"cat_del_yes_{edit_sku}", type="primary"):
                updated, ok = delete_catalogue_item(cat, edit_sku)
                if ok:
                    _save_and_refresh(updated)
                    st.session_state.catalogue_edit_sku = NEW_PRODUCT_KEY
                    st.session_state.pop(confirm_key, None)
                    st.success("Produk dihapus.")
                    st.rerun()
                st.error("Gagal menghapus produk.")
        with dc2:
            if st.button("Batal", key=f"cat_del_no_{edit_sku}"):
                st.session_state.pop(confirm_key, None)
                st.rerun()


def render_product_catalogue_page() -> None:
    st.markdown(
        section_heading_html(
            "Katalog produk",
            "Kelola menu warung di sini — tambah, ubah, hapus. CSV tetap tersedia untuk impor/ekspor.",
        ),
        unsafe_allow_html=True,
    )

    cat = _cat()
    val = validate_catalogue_tool(cat)
    active_n = sum(1 for r in cat if r.get("is_active", True))
    m1, m2, m3 = st.columns(3)
    m1.metric("Total produk", len(cat))
    m2.metric("Aktif", active_n)
    m3.metric("Nonaktif", len(cat) - active_n)

    if val.get("warnings"):
        for w in val["warnings"]:
            st.warning(w)

    st.markdown(page_stack_open_html(), unsafe_allow_html=True)
    st.markdown(
        hint_box_html(
            "Ubah harga atau alias di sini — pesanan WhatsApp dan bot langsung memakai katalog terbaru."
        ),
        unsafe_allow_html=True,
    )

    tab_list, tab_csv = st.tabs(["Kelola produk", "Import / ekspor CSV"])

    with tab_list:
        st.markdown(
            section_header_html(
                "Daftar menu",
                "Semua produk yang bisa dipesan pelanggan.",
                icon="restaurant_menu",
                variant="default",
            ),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            if cat:
                st.dataframe(
                    _display_dataframe(cat),
                    use_container_width=True,
                    height=min(120 + 42 * len(cat), 420),
                    hide_index=True,
                )
            else:
                st.info("Belum ada produk — tambah produk pertama di bawah.")

        st.markdown(
            section_header_html(
                "Tambah atau ubah produk",
                "Pilih produk dari daftar, atau buat yang baru.",
                icon="edit",
                variant="accent",
            ),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            options = {NEW_PRODUCT_KEY: "➕ Tambah produk baru"}
            for r in sorted(cat, key=lambda x: str(x.get("product_name") or "")):
                options[str(r.get("sku"))] = _product_label(r)

            if "catalogue_edit_sku" not in st.session_state:
                st.session_state.catalogue_edit_sku = NEW_PRODUCT_KEY

            selected = st.selectbox(
                "Pilih produk untuk diubah atau dihapus",
                options=list(options.keys()),
                format_func=lambda k: options[k],
                key="catalogue_picker",
                index=list(options.keys()).index(st.session_state.catalogue_edit_sku)
                if st.session_state.catalogue_edit_sku in options
                else 0,
            )
            st.session_state.catalogue_edit_sku = selected

            _render_crud_form(cat, selected)
            _render_delete_block(cat, selected)

    with tab_csv:
        st.markdown(
            section_header_html(
                "Import & ekspor CSV",
                "Backup atau migrasi banyak produk sekaligus.",
                icon="upload_file",
                variant="muted",
            ),
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                uploaded = st.file_uploader("Unggah CSV", type=["csv"], key="cat_upload")
                if uploaded is not None:
                    text = uploaded.getvalue().decode("utf-8")
                    rows = [
                        normalize_catalogue_row(r) for r in csv.DictReader(StringIO(text))
                    ]
                    if st.button("Terapkan unggahan", key="cat_apply_upload"):
                        _save_and_refresh(rows)
                        st.success(f"{len(rows)} produk diimpor.")
                        st.rerun()
            with c2:
                out_path = save_product_catalogue_tool(cat)
                csv_bytes = Path(out_path).read_bytes()
                st.download_button(
                    "Unduh CSV",
                    data=csv_bytes,
                    file_name="product_catalogue.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with c3:
                if st.button(
                    "Reset ke sample bawaan", use_container_width=True, key="cat_reset"
                ):
                    fresh = load_product_catalogue_from_csv()
                    _save_and_refresh(fresh)
                    st.session_state.catalogue_edit_sku = NEW_PRODUCT_KEY
                    st.rerun()

    st.markdown(page_stack_close_html(), unsafe_allow_html=True)
    st.caption(
        "Setelah mengubah katalog, analisis otomatis refresh — coba pesan "
        "'nasgor 2' di WhatsApp Bot untuk cek harga terbaru."
    )
