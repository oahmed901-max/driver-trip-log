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
        st.error("This link is invalid or the driver is inactive. Please contact the supervisor.")
        return

    st.title(f"🚚 {driver['name']}")
    open_trip = get_open_trip(driver["id"])

    if open_trip:
        render_end_trip_form(open_trip)
    else:
        render_start_trip_form(driver)


def render_start_trip_form(driver):
    st.subheader("Start a new trip")
    vehicles = get_vehicles()
    if not vehicles:
        st.warning("No vehicles added yet. Please contact the supervisor.")
        return

    default_idx = 0
    if driver.get("primary_vehicle_id"):
        ids = [v["id"] for v in vehicles]
        if driver["primary_vehicle_id"] in ids:
            default_idx = ids.index(driver["primary_vehicle_id"])

    vehicle = st.selectbox(
        "Vehicle", vehicles, index=default_idx, format_func=lambda v: v["vehicle_number"]
    )
    st.metric("Current odometer reading", f"{vehicle['current_odometer']:,.0f} كم")

    if st.button("Start Trip", type="primary", use_container_width=True):
        trip = start_trip(driver["id"], vehicle["id"], vehicle["current_odometer"])
        if trip:
            st.success("Start Trip ✓")
            st.rerun()
        else:
            st.error("An error occurred while starting the trip. Please try again.")


def render_end_trip_form(trip):
    vehicle = get_vehicle(trip["vehicle_id"])
    st.subheader("End Current Trip")
    start_clock = trip["start_time"][11:16] if trip.get("start_time") else ""
    st.info(f"Vehicle: {vehicle['vehicle_number']} — Started at  {start_clock}")
    st.metric("Odometer reading at start", f"{trip['start_odometer']:,.0f}")

    end_km = st.number_input(
        "Current odometer reading", min_value=float(trip["start_odometer"]), step=1.0
    )

    destinations = get_destinations()
    dest_names = [d["name"] for d in destinations] + ["Other"]
    dest_choice = st.selectbox("Destination", dest_names)
    dest_id, dest_other = None, None
    if dest_choice == "Other":
        dest_other = st.text_input("Enter the destination")
    else:
        dest_id = next(d["id"] for d in destinations if d["name"] == dest_choice)

    departments = get_departments()
    dept_names = [d["name"] for d in departments] + ["Not specified"]
    dept_choice = st.selectbox("Entity / Department", dept_names)
    dept_id = None
    if dept_choice != "Not specified":
        dept_id = next(d["id"] for d in departments if d["name"] == dept_choice)

    person_name = st.text_input("Person's name (optional)")

    if st.button("End Trip", type="primary", use_container_width=True):
        try:
            close_trip(trip["id"], end_km, dest_id, dest_other, dept_id, person_name)
            distance = end_km - trip["start_odometer"]
            st.success(f"Trip recorded successfully — Distance: {distance} km ✓")
            st.rerun()
        except Exception as e:
            st.error(f" An error occurred while saving: {e}")
