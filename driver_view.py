import streamlit as st
from db import (
    get_driver_by_token,
    get_open_trip,
    get_vehicles,
    get_vehicle,
    get_authorized_vehicle_ids,
    start_trip,
    close_trip,
    cancel_trip,
    get_destinations,
    get_departments,
)
from translations import t


def render_driver_view(token):
    driver = get_driver_by_token(token)
    if not driver:
        st.error(t("en", "invalid_link"))
        return

    lang = driver.get("language") or "en"

    st.title(f"🚚 {driver['name']}")
    open_trip = get_open_trip(driver["id"])

    if open_trip:
        render_end_trip_form(open_trip, lang)
    else:
        render_start_trip_form(driver, lang)


def render_start_trip_form(driver, lang):
    st.subheader(t(lang, "start_trip_heading"))

    authorized_ids = set(get_authorized_vehicle_ids(driver["id"]))
    if not authorized_ids:
        st.error(t(lang, "no_authorized_vehicles"))
        return

    all_vehicles = get_vehicles()
    vehicles = [v for v in all_vehicles if v["id"] in authorized_ids]
    if not vehicles:
        st.error(t(lang, "no_authorized_vehicles"))
        return

    default_idx = 0
    if driver.get("primary_vehicle_id"):
        ids = [v["id"] for v in vehicles]
        if driver["primary_vehicle_id"] in ids:
            default_idx = ids.index(driver["primary_vehicle_id"])

    vehicle = st.selectbox(
        t(lang, "vehicle"), vehicles, index=default_idx, format_func=lambda v: v["vehicle_number"]
    )
    st.metric(t(lang, "current_odometer"), f"{vehicle['current_odometer']:,.0f} km")

    if st.button(t(lang, "start_trip_btn"), type="primary", use_container_width=True):
        trip = start_trip(driver["id"], vehicle["id"], vehicle["current_odometer"])
        if trip:
            st.success(t(lang, "trip_started"))
            st.rerun()
        else:
            st.error(t(lang, "start_trip_error"))


def render_end_trip_form(trip, lang):
    vehicle = get_vehicle(trip["vehicle_id"])
    st.subheader(t(lang, "end_trip_heading"))
    start_clock = trip["start_time"][11:16] if trip.get("start_time") else ""
    st.info(t(lang, "started_at", vehicle=vehicle["vehicle_number"], time=start_clock))
    st.metric(t(lang, "odometer_at_start"), f"{trip['start_odometer']:,.0f} km")

    end_km = st.number_input(
        t(lang, "odometer_now"), min_value=0.0, value=None, step=1.0, format="%.0f"
    )

    placeholder = t(lang, "select_placeholder")
    other_label = t(lang, "other")
    destinations = get_destinations()
    dest_options = [placeholder] + [d["name"] for d in destinations] + [other_label]
    dest_choice = st.selectbox(t(lang, "destination"), dest_options, index=0)
    dest_id, dest_other = None, None
    if dest_choice == other_label:
        dest_other = st.text_input(t(lang, "enter_destination"))
    elif dest_choice != placeholder:
        dest_id = next(d["id"] for d in destinations if d["name"] == dest_choice)

    not_specified = t(lang, "not_specified")
    departments = get_departments()
    dept_options = [not_specified] + [d["name"] for d in departments]
    dept_choice = st.selectbox(t(lang, "department"), dept_options, index=0)
    dept_id = None
    if dept_choice != not_specified:
        dept_id = next(d["id"] for d in departments if d["name"] == dept_choice)

    person_name = st.text_input(t(lang, "person_name"))
    remark = st.text_area(t(lang, "remark"))

    col1, col2 = st.columns(2)

    with col1:
        if st.button(t(lang, "end_trip_btn"), type="primary", use_container_width=True):
            if end_km is None:
                st.error(t(lang, "error_odometer_required"))
            elif dest_choice == placeholder:
                st.error(t(lang, "error_destination_required"))
            elif dest_choice == other_label and not dest_other.strip():
                st.error(t(lang, "error_destination_other_required"))
            else:
                try:
                    close_trip(trip["id"], end_km, dest_id, dest_other, dept_id, person_name, remark or None)
                    distance = end_km - trip["start_odometer"]
                    st.success(t(lang, "trip_ended", distance=f"{distance:,.0f}"))
                    st.rerun()
                except Exception as e:
                    st.error(t(lang, "save_error", error=e))

    with col2:
        if st.button(t(lang, "cancel_trip_btn"), use_container_width=True):
            try:
                cancel_trip(trip["id"], remark or None)
                st.success(t(lang, "trip_cancelled"))
                st.rerun()
            except Exception as e:
                st.error(t(lang, "save_error", error=e))
