from io import BytesIO

import pandas as pd
import streamlit as st

from db import (
    get_drivers,
    add_driver,
    set_driver_active,
    get_vehicles,
    add_vehicle,
    set_vehicle_active,
    get_trips,
    get_destinations,
    add_destination,
    get_departments,
    add_department,
)
from qr_utils import make_qr_bytes


def check_login():
    if st.session_state.get("authed"):
        return True

    st.title("🔐 لوحة المشرف")
    pw = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        if pw and pw == st.secrets.get("SUPERVISOR_PASSWORD"):
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("كلمة مرور غلط")
    return False


def render_supervisor_view():
    if not check_login():
        return

    st.title("لوحة المتابعة")
    tab1, tab2, tab3, tab4 = st.tabs(["سجل الحركات", "السواقين", "العربيات", "الوجهات والجهات"])

    with tab1:
        render_trips_tab()
    with tab2:
        render_drivers_tab()
    with tab3:
        render_vehicles_tab()
    with tab4:
        render_lists_tab()


def render_trips_tab():
    trips = get_trips()
    if not trips:
        st.info("لا توجد رحلات مسجلة بعد.")
        return

    rows = []
    for t in trips:
        rows.append({
            "التاريخ": t.get("trip_date"),
            "السواق": (t.get("drivers") or {}).get("name"),
            "العربية": (t.get("vehicles") or {}).get("vehicle_number"),
            "بداية العداد": t.get("start_odometer"),
            "نهاية العداد": t.get("end_odometer"),
            "المسافة (كم)": t.get("distance"),
            "وقت البداية": t.get("start_time"),
            "وقت النهاية": t.get("end_time"),
            "الوجهة": (t.get("destinations") or {}).get("name") or t.get("destination_other"),
            "الجهة": (t.get("departments") or {}).get("name"),
            "الشخص": t.get("person_name"),
            "الحالة": t.get("status"),
        })
    df = pd.DataFrame(rows)

    col1, col2 = st.columns(2)
    with col1:
        driver_filter = st.text_input("بحث باسم السواق")
    with col2:
        status_filter = st.selectbox("الحالة", ["الكل", "active", "cancelled", "corrected"])

    filtered = df.copy()
    if driver_filter:
        filtered = filtered[filtered["السواق"].str.contains(driver_filter, case=False, na=False)]
    if status_filter != "الكل":
        filtered = filtered[filtered["الحالة"] == status_filter]

    st.dataframe(filtered, use_container_width=True)
    st.caption(f"عدد الحركات المعروضة: {len(filtered)} من إجمالي {len(df)}")

    buf = BytesIO()
    filtered.to_excel(buf, index=False, engine="openpyxl")
    st.download_button(
        "⬇️ تصدير Excel", buf.getvalue(),
        file_name="driver-trips.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def render_drivers_tab():
    st.subheader("إضافة سواق جديد")
    with st.form("add_driver_form", clear_on_submit=True):
        name = st.text_input("اسم السواق")
        submitted = st.form_submit_button("إضافة + إنشاء رابط")
        if submitted and name.strip():
            add_driver(name.strip())
            st.success("تم إضافة السواق")
            st.rerun()

    st.subheader("السواقين الحاليين")
    drivers = get_drivers()
    base_url = st.secrets.get("APP_BASE_URL", "")
    if not drivers:
        st.info("لسه مفيش سواقين مضافين.")
        return

    for d in drivers:
        link = f"{base_url}?d={d['unique_token']}"
        status = "🟢 مفعّل" if d.get("active") else "🔴 معطّل"
        with st.expander(f"{d['name']} — {status}"):
            st.code(link)
            st.image(make_qr_bytes(link), width=180)
            toggle_label = "تعطيل السواق" if d.get("active") else "تفعيل السواق"
            if st.button(toggle_label, key=f"toggle_{d['id']}"):
                set_driver_active(d["id"], not d.get("active"))
                st.rerun()


def render_vehicles_tab():
    st.subheader("إضافة عربية جديدة")
    with st.form("add_vehicle_form", clear_on_submit=True):
        num = st.text_input("رقم العربية")
        odo = st.number_input("قراءة العداد الحالية", min_value=0.0, step=1.0)
        submitted = st.form_submit_button("إضافة العربية")
        if submitted and num.strip():
            add_vehicle(num.strip(), current_odometer=odo)
            st.success("تمت إضافة العربية")
            st.rerun()

    st.subheader("العربيات الحالية")
    vehicles = get_vehicles(active_only=False)
    if not vehicles:
        st.info("لسه مفيش عربيات مضافة.")
        return

    for v in vehicles:
        status = "🟢 مفعّلة" if v.get("active") else "🔴 معطّلة"
        cols = st.columns([3, 2, 2])
        cols[0].write(f"**{v['vehicle_number']}** — {status}")
        cols[1].write(f"العداد: {v['current_odometer']:,.0f} كم")
        toggle_label = "تعطيل" if v.get("active") else "تفعيل"
        if cols[2].button(toggle_label, key=f"veh_toggle_{v['id']}"):
            set_vehicle_active(v["id"], not v.get("active"))
            st.rerun()


def render_lists_tab():
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("الوجهات")
        with st.form("add_dest_form", clear_on_submit=True):
            name = st.text_input("وجهة جديدة")
            if st.form_submit_button("إضافة") and name.strip():
                add_destination(name.strip())
                st.rerun()
        for d in get_destinations():
            st.write("•", d["name"])

    with col2:
        st.subheader("الجهات / الأقسام")
        with st.form("add_dept_form", clear_on_submit=True):
            name = st.text_input("جهة/قسم جديد")
            if st.form_submit_button("إضافة") and name.strip():
                add_department(name.strip())
                st.rerun()
        for d in get_departments():
            st.write("•", d["name"])
