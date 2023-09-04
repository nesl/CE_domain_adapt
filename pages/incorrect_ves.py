import streamlit as st
from utils import get_image_for_event, get_class_grouping, get_name_from_index
import json

from streamlit_extras.switch_page_button import switch_page
from domain_adapt import find_closest_aes, save_image, \
    match_and_add_ves, verify_ve_intervals, get_tracking_info, save_track_data_to_label

# This is how we hide the sidebar navigation
st.set_page_config(initial_sidebar_state="collapsed")
st.markdown(
    """
<style>
    [data-testid="collapsedControl"] {
        display: none
    }
</style>
""",
    unsafe_allow_html=True,
)


st.markdown("# Identifying Missed Constraints")





# # Set up our initial variables
# result_path = "data/ce_output.txt"
# # AE FILES MUST BE SORTED IN ORDER OF CAM ID
# ae_files = ["data/ae_cam0.txt", "data/ae_cam1.txt", "data/ae_cam2.txt"]
# video_dir = "data"

# # Get the events
# events_to_check, ae_data, wb_data = list_detected_events(result_path, ae_files)
# # Get the class mappings
# class_mappings = json.load(open("data/class_mappings.json", "r"))

unconfirmed_vicinal_events = st.session_state["unconfirmed_vicinal_events"]
ce_obj = st.session_state["ce_obj"]
detected_time = st.session_state["detected_time"]
class_mappings = st.session_state["class_mappings"]
ae_statuses = find_closest_aes(st.session_state["confirmed_vicinal_events"], ce_obj, detected_time)
st.session_state["ae_statuses"] = ae_statuses
confirmed_vicinal_events = st.session_state["confirmed_vicinal_events"]
video_dir = st.session_state["video_dir"]
wb_data = st.session_state["wb_data"]

# Get the events we need to verify
events_to_verify = verify_ve_intervals(ae_statuses, detected_time, \
        unconfirmed_vicinal_events, confirmed_vicinal_events)

# Keep track of which page we are on
if "page" not in st.session_state:
    st.session_state.page = 0
def nextpage():

    if st.session_state.page >= len(events_to_verify)-1:
        track_data = get_tracking_info(st.session_state["confirmed_vicinal_events"])
        save_track_data_to_label(track_data, st.session_state["ae_files"], video_dir)
        switch_page("video_review")
    else: 
        st.session_state.page += 1

def restart(): st.session_state.page = 0

def review(): switch_page("review")


# Create an empty container
display_placeholder = st.empty()
if st.button("Yes, it is correct"):

    wb_name = st.session_state["wb_query"][2]
    wb_time = st.session_state["wb_query"][0]

    # Every time we correct something, we need to redo the confirmed vicinal events
    # Use the match and add ves...
    confirmed_vicinal_events = match_and_add_ves(unconfirmed_vicinal_events, confirmed_vicinal_events,\
        wb_name, wb_time)

    st.session_state["confirmed_vicinal_events"] = confirmed_vicinal_events

    nextpage()
# st.button("No, it is incorrect", on_click=review)
if st.button("No, it is incorrect"):

    print("do nothing...")

    # review()




with display_placeholder.container():

    wb_query = events_to_verify[st.session_state.page]
    st.session_state["wb_query"] = wb_query

    img, objects = get_image_for_event(wb_query, video_dir, wb_data)
    # Show image here...
    # save_image("results/x.jpg", img)
    img_display = st.image(img)

    st.subheader('Are the following claims correct?')
    class_groups = get_class_grouping(objects)

    for class_key in class_groups.keys():
        st.write("There are {x} objects of type {y} within the red highlighted area.".format(\
            x=class_groups[class_key], y=get_name_from_index(class_mappings, class_key)) )
    if len(class_groups.keys()) == 0: #Empty item
        st.write("There are no objects within the red highlighted area.")


    
    # After everything is done
    # track_data = get_tracking_info(confirmed_vicinal_events)
    # save_track_data_to_label(track_data, ae_files, video_dir)
    # save_relevant_track_images("data/training", video_dir, "da_confirmed.json")


