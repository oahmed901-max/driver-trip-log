import streamlit as st
from driver_view import render_driver_view
from supervisor_view import render_supervisor_view

st.set_page_config(page_title="driver-trip-log", page_icon="🚚", layout="centered")

params = st.query_params
token = params.get("d")

if token:
    render_driver_view(token)
else:
    render_supervisor_view()
