import streamlit as st
from db import (
    get_driver_by_token,
    get_open_trip,
    get_vehicles,
    get_vehicle,
    start_trip,
    close_trip,
    get_destinations,
    get_departments,
)


def render_driver_view(token):
    driver = get_driver_by_token(token)
    if not driver:
        st.error("الرابط ده مش صحيح أو السواق غير مفعّل. برجاء التواصل مع المشرف.")
        return

    st.title(f"🚚 {driver['name']}")
    open_trip = get_open_trip(driver["id"])

    if open_trip:
        render_end_trip_form(open_trip)
    else:
        render_start_trip_form(driver)


def render_start_trip_form(driver):
    st.subheader("بدء رحلة جديدة")
    vehicles = get_vehicles()
    if not vehicles:
        st.warning("مفيش عربيات مضافة بعد. برجاء التواصل مع المشرف.")
        return

    default_idx = 0
    if driver.get("primary_vehicle_id"):
        ids = [v["id"] for v in vehicles]
        if driver["primary_vehicle_id"] in ids:
            default_idx = ids.index(driver["primary_vehicle_id"])

    vehicle = st.selectbox(
        "العربية", vehicles, index=default_idx, format_func=lambda v: v["vehicle_number"]
    )
    st.metric("قراءة العداد الحالية", f"{vehicle['current_odometer']:,.0f} كم")

    if st.button("بدء الرحلة", type="primary", use_container_width=True):
        trip = start_trip(driver["id"], vehicle["id"], vehicle["current_odometer"])
        if trip:
            st.success("تم بدء الرحلة ✓")
            st.rerun()
        else:
            st.error("حصل خطأ أثناء بدء الرحلة، حاول تاني.")


def render_end_trip_form(trip):
    vehicle = get_vehicle(trip["vehicle_id"])
    st.subheader("إنهاء الرحلة الحالية")
    start_clock = trip["start_time"][11:16] if trip.get("start_time") else ""
    st.info(f"العربية: {vehicle['vehicle_number']} — بدأت الساعة {start_clock}")
    st.metric("قراءة العداد عند البداية", f"{trip['start_odometer']:,.0f} كم")

    end_km = st.number_input(
        "قراءة العداد الآن", min_value=float(trip["start_odometer"]), step=1.0
    )

    destinations = get_destinations()
    dest_names = [d["name"] for d in destinations] + ["أخرى"]
    dest_choice = st.selectbox("الوجهة", dest_names)
    dest_id, dest_other = None, None
    if dest_choice == "أخرى":
        dest_other = st.text_input("اكتب الوجهة")
    else:
        dest_id = next(d["id"] for d in destinations if d["name"] == dest_choice)

    departments = get_departments()
    dept_names = [d["name"] for d in departments] + ["غير محدد"]
    dept_choice = st.selectbox("الجهة / القسم", dept_names)
    dept_id = None
    if dept_choice != "غير محدد":
        dept_id = next(d["id"] for d in departments if d["name"] == dept_choice)

    person_name = st.text_input("اسم الشخص (اختياري)")

    if st.button("إنهاء الرحلة", type="primary", use_container_width=True):
        try:
            close_trip(trip["id"], end_km, dest_id, dest_other, dept_id, person_name)
            distance = end_km - trip["start_odometer"]
            st.success(f"تم تسجيل الرحلة بنجاح — المسافة: {distance:,.0f} كم ✓")
            st.rerun()
        except Exception as e:
            st.error(f"حصل خطأ أثناء الحفظ: {e}")
