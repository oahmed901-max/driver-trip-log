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

    st.title("Supervisor Dashboard")
    pw = st.text_input("password", type="password")
    if st.button("Login"):
        if pw and pw == st.secrets.get("SUPERVISOR_PASSWORD"):
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Incorrect password")
    return False


def render_supervisor_view():
    if not check_login():
        return

    st.title("Monitoring Dashboard")
    tab1, tab2, tab3, tab4 = st.tabs(["Trip Log", "Drivers", "Vehicles", "Destinations & Departments"])

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
        st.info("No trips recorded yet.")
        return

    rows = []
    for t in trips:
        rows.append({
            "Date": t.get("trip_date"),
            "Driver": (t.get("drivers") or {}).get("name"),
            "Vehicle": (t.get("vehicles") or {}).get("vehicle_number"),
            "Start Odometer": t.get("start_odometer"),
            "End Odometer": t.get("end_odometer"),
            "Distance (km)": t.get("distance"),
            "start_time": t.get("start_time"),
            "end_time": t.get("end_time"),
            "destinations": (t.get("destinations") or {}).get("name") or t.get("destination_other"),
            "departments": (t.get("departments") or {}).get("name"),
            "Person": t.get("person_name"),
            "Status": t.get("status"),
        })
    df = pd.DataFrame(rows)

    col1, col2 = st.columns(2)
    with col1:
        driver_filter = st.text_input("Search by driver name")
    with col2:
        status_filter = st.selectbox("status", ["All", "active", "cancelled", "corrected"])

    filtered = df.copy()
    if driver_filter:
        filtered = filtered[filtered["Driver"].str.contains(driver_filter, case=False, na=False)]
    if status_filter != "All":
        filtered = filtered[filtered["status"] == status_filter]

    st.dataframe(filtered, use_container_width=True)
    st.caption(f"عدد الحركات المعروضة: {len(filtered)} من إجمالي {len(df)}")

    buf = BytesIO()
    filtered.to_excel(buf, index=False, engine="openpyxl")
    st.download_button(
        "Export Excel", buf.getvalue(),
        file_name="driver-trips.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def render_drivers_tab():
    st.subheader("Add New Driver")
    with st.form("add_driver_form", clear_on_submit=True):
        name = st.text_input("Driver Name")
        submitted = st.form_submit_button("Add + Generate Link")
        if submitted and name.strip():
            add_driver(name.strip())
            st.success("Driver added")
            st.rerun()

    st.subheader("Current Drivers")
    drivers = get_drivers()
    base_url = st.secrets.get("APP_BASE_URL", "")
    if not drivers:
        st.info("No drivers added yet.")
        return

    for d in drivers:
        link = f"{base_url}?d={d['unique_token']}"
        status = "Active" if d.get("active") else "Inactive"
        with st.expander(f"{d['name']} — {status}"):
            st.code(link)
            st.image(make_qr_bytes(link), width=180)
            toggle_label = "Deactivate Driver" if d.get("active") else "Activate Driver"
            if st.button(toggle_label, key=f"toggle_{d['id']}"):
                set_driver_active(d["id"], not d.get("active"))
                st.rerun()


def render_vehicles_tab():
    st.subheader("Add New Vehicle")
    with st.form("add_vehicle_form", clear_on_submit=True):
        num = st.text_input("Vehicle Number")
        odo = st.number_input("Current Odometer Reading", min_value=0.0, step=1.0)
        submitted = st.form_submit_button("Add Vehicle")
        if submitted and num.strip():
            add_vehicle(num.strip(), current_odometer=odo)
            st.success("Vehicle added")
            st.rerun()

    st.subheader("Current Vehicles")
    vehicles = get_vehicles(active_only=False)
    if not vehicles:
        st.info("No vehicles added yet.")
        return

    for v in vehicles:
        status = "Active" if v.get("active") else "Inactive"
        cols = st.columns([3, 2, 2])
        cols[0].write(f"**{v['vehicle_number']}** — {status}")
        cols[1].write(f"العداد: {v['current_odometer']:,.0f} كم")
        toggle_label = "Deactivate" if v.get("active") else "active"
        if cols[2].button(toggle_label, key=f"veh_toggle_{v['id']}"):
            set_vehicle_active(v["id"], not v.get("active"))
            st.rerun()


def render_lists_tab():
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Destinations")
        with st.form("add_dest_form", clear_on_submit=True):
            name = st.text_input("New destination")
            if st.form_submit_button("Add") and name.strip():
                add_destination(name.strip())
                st.rerun()
        for d in get_destinations():
            st.write("•", d["name"])

    with col2:
        st.subheader("Entities / Departments")
        with st.form("add_dept_form", clear_on_submit=True):
            name = st.text_input("New entity/department")
            if st.form_submit_button("Add") and name.strip():
                add_department(name.strip())
                st.rerun()
        for d in get_departments():
            st.write("•", d["name"])
