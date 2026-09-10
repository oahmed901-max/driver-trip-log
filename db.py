import secrets as pysecrets
import streamlit as st
from supabase import create_client


@st.cache_resource
def get_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# ---------- Drivers ----------

def get_driver_by_token(token):
    sb = get_client()
    res = sb.table("drivers").select("*").eq("unique_token", token).eq("active", True).execute()
    return res.data[0] if res.data else None


def get_drivers():
    sb = get_client()
    return sb.table("drivers").select("*").order("created_at", desc=True).execute().data


def add_driver(name, employee_id=None):
    sb = get_client()
    token = pysecrets.token_urlsafe(12)
    res = sb.table("drivers").insert({
        "name": name,
        "employee_id": employee_id,
        "unique_token": token,
    }).execute()
    return res.data[0] if res.data else None


def set_driver_active(driver_id, active):
    sb = get_client()
    sb.table("drivers").update({"active": active}).eq("id", driver_id).execute()


# ---------- Vehicles ----------

def get_vehicles(active_only=True):
    sb = get_client()
    q = sb.table("vehicles").select("*").order("vehicle_number")
    if active_only:
        q = q.eq("active", True)
    return q.execute().data


def get_vehicle(vehicle_id):
    sb = get_client()
    res = sb.table("vehicles").select("*").eq("id", vehicle_id).execute()
    return res.data[0] if res.data else None


def add_vehicle(vehicle_number, current_odometer=0, plate_number=None, vehicle_type=None):
    sb = get_client()
    res = sb.table("vehicles").insert({
        "vehicle_number": vehicle_number,
        "plate_number": plate_number,
        "vehicle_type": vehicle_type,
        "current_odometer": current_odometer,
    }).execute()
    return res.data[0] if res.data else None


def set_vehicle_active(vehicle_id, active):
    sb = get_client()
    sb.table("vehicles").update({"active": active}).eq("id", vehicle_id).execute()


# ---------- Destinations / Departments ----------

def get_destinations():
    sb = get_client()
    return sb.table("destinations").select("*").eq("active", True).order("name").execute().data


def add_destination(name):
    sb = get_client()
    sb.table("destinations").insert({"name": name}).execute()


def get_departments():
    sb = get_client()
    return sb.table("departments").select("*").eq("active", True).order("name").execute().data


def add_department(name):
    sb = get_client()
    sb.table("departments").insert({"name": name}).execute()


# ---------- Trips ----------

def get_open_trip(driver_id):
    sb = get_client()
    res = (
        sb.table("trips")
        .select("*")
        .eq("driver_id", driver_id)
        .eq("status", "active")
        .is_("end_odometer", "null")
        .order("start_time", desc=True)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def start_trip(driver_id, vehicle_id, start_odometer):
    sb = get_client()
    res = sb.table("trips").insert({
        "driver_id": driver_id,
        "vehicle_id": vehicle_id,
        "start_odometer": start_odometer,
    }).execute()
    return res.data[0] if res.data else None


def close_trip(trip_id, end_odometer, destination_id, destination_other, department_id, person_name):
    sb = get_client()
    return sb.rpc("close_trip", {
        "p_trip_id": trip_id,
        "p_end_odometer": end_odometer,
        "p_destination_id": destination_id,
        "p_destination_other": destination_other,
        "p_department_id": department_id,
        "p_person_name": person_name,
    }).execute()


def get_trips():
    sb = get_client()
    res = (
        sb.table("trips")
        .select("*, drivers(name), vehicles(vehicle_number), destinations(name), departments(name)")
        .order("start_time", desc=True)
        .execute()
    )
    return res.data
