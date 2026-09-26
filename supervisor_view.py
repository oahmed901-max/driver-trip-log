from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from db import (
    get_drivers,
    add_driver,
    update_driver,
    set_driver_active,
    get_authorized_vehicle_ids,
    set_driver_authorized_vehicles,
    get_vehicles,
    add_vehicle,
    update_vehicle,
    set_vehicle_active,
    get_trips,
    get_destinations,
    add_destination,
    update_destination,
    get_departments,
    add_department,
    update_department,
    correct_trip_odometer,
)
from qr_utils import make_qr_bytes


def format_dt(iso_str):
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso_str


def format_duration(minutes):
    if minutes is None:
        return ""
    try:
        total = int(round(float(minutes)))
        h, m = divmod(total, 60)
        return f"{h}h {m}m" if h else f"{m}m"
    except Exception:
        return ""


def check_login():
    if st.session_state.get("authed"):
        return True

    st.title("🔐 Supervisor Login")
    pw = st.text_input("Password", type="password")
    if st.button("Log in"):
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


# =====================================================================
# Trip Log
# =====================================================================

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
            "Start KM": t.get("start_odometer"),
            "End KM": t.get("end_odometer"),
            "Distance (km)": t.get("distance"),
            "Start Time": format_dt(t.get("start_time")),
            "End Time": format_dt(t.get("end_time")),
            "Duration": format_duration(t.get("duration_minutes")),
            "Destination": (t.get("destinations") or {}).get("name") or t.get("destination_other"),
            "Department": (t.get("departments") or {}).get("name"),
            "Person": t.get("person_name"),
            "Remark": t.get("notes"),
            "Status": t.get("status"),
            "Correction reason": t.get("correction_reason"),
        })
    df = pd.DataFrame(rows)

    col1, col2 = st.columns(2)
    with col1:
        driver_filter = st.text_input("Search by driver name")
    with col2:
        status_filter = st.selectbox("Status", ["All", "in_progress", "completed", "cancelled", "corrected"])

    filtered = df.copy()
    if driver_filter:
        filtered = filtered[filtered["Driver"].str.contains(driver_filter, case=False, na=False)]
    if status_filter != "All":
        filtered = filtered[filtered["Status"] == status_filter]

    st.dataframe(filtered, use_container_width=True)
    st.caption(f"Showing {len(filtered)} of {len(df)} trips")

    buf = BytesIO()
    filtered.to_excel(buf, index=False, engine="openpyxl")
    st.download_button(
        "⬇️ Export Excel", buf.getvalue(),
        file_name="driver-trips.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.divider()
    render_correction_section(trips)


def render_correction_section(trips):
    st.subheader("Correct a trip's odometer reading")
    st.caption(
        "Use this only to fix a data-entry mistake. It changes the start and/or end "
        "odometer reading and recalculates the distance. A reason is required."
    )

    options = {
        f"{(t.get('drivers') or {}).get('name')} — {(t.get('vehicles') or {}).get('vehicle_number')} — "
        f"{t.get('trip_date')} (start {t.get('start_odometer')}, end {t.get('end_odometer')})": t
        for t in trips
    }
    if not options:
        return

    choice = st.selectbox("Select trip", list(options.keys()), key="correction_trip_select")
    trip = options[choice]

    col1, col2 = st.columns(2)
    with col1:
        new_start = st.number_input(
            "Start KM", value=float(trip.get("start_odometer") or 0), step=1.0, key="corr_start"
        )
    with col2:
        current_end = trip.get("end_odometer")
        new_end = st.number_input(
            "End KM", value=float(current_end) if current_end is not None else 0.0,
            step=1.0, key="corr_end"
        )

    reason = st.text_input("Reason for correction (required)", key="corr_reason")

    if st.button("Save correction", type="primary"):
        if not reason.strip():
            st.error("A reason is required to save a correction.")
        else:
            try:
                end_value = new_end if current_end is not None else None
                correct_trip_odometer(trip["id"], new_start, end_value, reason.strip())
                st.success("Trip corrected ✓")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving correction: {e}")


# =====================================================================
# Drivers
# =====================================================================

def render_drivers_tab():
    all_vehicles = get_vehicles(active_only=False)
    vehicle_options = {v["vehicle_number"]: v["id"] for v in all_vehicles}

    st.subheader("Add a new driver")
    with st.form("add_driver_form", clear_on_submit=True):
        name = st.text_input("Driver name")
        employee_id = st.text_input("Employee ID")
        job_title = st.text_input("Job title")
        phone_number = st.text_input("Phone number")
        company_name = st.text_input("Company")
        col1, col2 = st.columns(2)
        with col1:
            license_number = st.text_input("Driving license number")
            license_category = st.text_input("License category")
        with col2:
            license_expiry = st.date_input("License expiry", value=None)
        language = st.selectbox(
            "Driver screen language", ["en", "ur"],
            format_func=lambda x: "English" if x == "en" else "Urdu",
        )

        authorized_names = st.multiselect("Authorized vehicles", list(vehicle_options.keys()))
        primary_name = st.selectbox("Primary vehicle", ["None"] + list(vehicle_options.keys()))

        submitted = st.form_submit_button("Add + generate link")
        if submitted and name.strip():
            primary_id = vehicle_options.get(primary_name) if primary_name != "None" else None
            driver = add_driver(
                name.strip(), employee_id=employee_id.strip() or None,
                job_title=job_title.strip() or None,
                phone_number=phone_number.strip() or None,
                company_name=company_name.strip() or None,
                license_number=license_number.strip() or None,
                license_category=license_category.strip() or None,
                license_expiry=license_expiry,
                language=language,
                primary_vehicle_id=primary_id,
            )
            if driver:
                authorized_ids = [vehicle_options[n] for n in authorized_names]
                set_driver_authorized_vehicles(driver["id"], authorized_ids)
            st.success("Driver added")
            st.rerun()

    st.subheader("Current drivers")
    drivers = get_drivers()
    base_url = st.secrets.get("APP_BASE_URL", "")
    if not drivers:
        st.info("No drivers added yet.")
        return

    for d in drivers:
        link = f"{base_url}?d={d['unique_token']}"
        status = "🟢 Active" if d.get("active") else "🔴 Inactive"
        with st.expander(f"{d['name']} — {status}"):
            st.code(link)
            st.image(make_qr_bytes(link), width=180)

            current_auth_ids = set(get_authorized_vehicle_ids(d["id"]))
            current_auth_names = [name for name, vid in vehicle_options.items() if vid in current_auth_ids]
            current_primary_id = d.get("primary_vehicle_id")
            current_primary_name = next(
                (name for name, vid in vehicle_options.items() if vid == current_primary_id), "None"
            )

            with st.form(f"edit_driver_{d['id']}"):
                name = st.text_input("Name", value=d.get("name") or "")
                employee_id = st.text_input("Employee ID", value=d.get("employee_id") or "")
                job_title = st.text_input("Job title", value=d.get("job_title") or "")
                phone_number = st.text_input("Phone number", value=d.get("phone_number") or "")
                company_name = st.text_input("Company", value=d.get("company_name") or "")
                col1, col2 = st.columns(2)
                with col1:
                    license_number = st.text_input("License number", value=d.get("license_number") or "")
                    license_category = st.text_input("License category", value=d.get("license_category") or "")
                with col2:
                    license_expiry = st.date_input("License expiry", value=d.get("license_expiry"))
                language = st.selectbox(
                    "Driver screen language", ["en", "ur"],
                    index=0 if (d.get("language") or "en") == "en" else 1,
                    format_func=lambda x: "English" if x == "en" else "Urdu",
                    key=f"lang_{d['id']}",
                )

                authorized_names_edit = st.multiselect(
                    "Authorized vehicles", list(vehicle_options.keys()),
                    default=current_auth_names, key=f"auth_{d['id']}",
                )
                primary_idx = (["None"] + list(vehicle_options.keys())).index(current_primary_name)
                primary_name_edit = st.selectbox(
                    "Primary vehicle", ["None"] + list(vehicle_options.keys()),
                    index=primary_idx, key=f"primary_{d['id']}",
                )

                if st.form_submit_button("Save changes"):
                    primary_id = vehicle_options.get(primary_name_edit) if primary_name_edit != "None" else None
                    update_driver(
                        d["id"], name=name.strip(), employee_id=employee_id.strip() or None,
                        job_title=job_title.strip() or None, phone_number=phone_number.strip() or None,
                        company_name=company_name.strip() or None,
                        license_number=license_number.strip() or None,
                        license_category=license_category.strip() or None,
                        license_expiry=license_expiry, language=language,
                        primary_vehicle_id=primary_id,
                    )
                    authorized_ids_edit = [vehicle_options[n] for n in authorized_names_edit]
                    set_driver_authorized_vehicles(d["id"], authorized_ids_edit)
                    st.success("Saved")
                    st.rerun()

            toggle_label = "Deactivate driver" if d.get("active") else "Activate driver"
            if st.button(toggle_label, key=f"toggle_{d['id']}"):
                set_driver_active(d["id"], not d.get("active"))
                st.rerun()


# =====================================================================
# Vehicles
# =====================================================================

def render_vehicles_tab():
    st.subheader("Add a new vehicle")
    with st.form("add_vehicle_form", clear_on_submit=True):
        num = st.text_input("Vehicle number")
        odo = st.number_input("Current odometer reading", min_value=0.0, step=1.0)
        submitted = st.form_submit_button("Add vehicle")
        if submitted and num.strip():
            add_vehicle(num.strip(), current_odometer=odo)
            st.success("Vehicle added")
            st.rerun()

    st.subheader("Current vehicles")
    vehicles = get_vehicles(active_only=False)
    if not vehicles:
        st.info("No vehicles added yet.")
        return

    for v in vehicles:
        status = "🟢 Active" if v.get("active") else "🔴 Inactive"
        with st.expander(f"{v['vehicle_number']} — {status}"):
            with st.form(f"edit_vehicle_{v['id']}"):
                vehicle_number = st.text_input("Vehicle number", value=v.get("vehicle_number") or "")
                plate_number = st.text_input("Plate number", value=v.get("plate_number") or "")
                vehicle_type = st.text_input("Vehicle type", value=v.get("vehicle_type") or "")
                current_odometer = st.number_input(
                    "Current odometer reading (km)", min_value=0.0, step=1.0,
                    value=float(v.get("current_odometer") or 0),
                )
                st.caption("This is normally updated automatically when a trip ends. Only change it manually to correct a wrong starting value or fix a data issue.")
                if st.form_submit_button("Save changes"):
                    update_vehicle(
                        v["id"], vehicle_number=vehicle_number.strip(),
                        plate_number=plate_number.strip() or None,
                        vehicle_type=vehicle_type.strip() or None,
                        current_odometer=current_odometer,
                    )
                    st.success("Saved")
                    st.rerun()
            toggle_label = "Deactivate" if v.get("active") else "Activate"
            if st.button(toggle_label, key=f"veh_toggle_{v['id']}"):
                set_vehicle_active(v["id"], not v.get("active"))
                st.rerun()


# =====================================================================
# Destinations / Departments
# =====================================================================

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
            with st.expander(d["name"]):
                with st.form(f"edit_dest_{d['id']}"):
                    new_name = st.text_input("Name", value=d["name"], key=f"dest_name_{d['id']}")
                    if st.form_submit_button("Save"):
                        update_destination(d["id"], new_name.strip())
                        st.rerun()

    with col2:
        st.subheader("Entities / Departments")
        with st.form("add_dept_form", clear_on_submit=True):
            name = st.text_input("New entity/department")
            if st.form_submit_button("Add") and name.strip():
                add_department(name.strip())
                st.rerun()
        for d in get_departments():
            with st.expander(d["name"]):
                with st.form(f"edit_dept_{d['id']}"):
                    new_name = st.text_input("Name", value=d["name"], key=f"dept_name_{d['id']}")
                    if st.form_submit_button("Save"):
                        update_department(d["id"], new_name.strip())
                        st.rerun()
