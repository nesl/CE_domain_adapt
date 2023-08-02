import streamlit as st
from utils import list_detected_events, get_image_for_event, get_class_grouping, get_name_from_index
import json

from streamlit_extras.switch_page_button import switch_page


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


# Set up our initial variables
result_path = "data/ce_output.txt"
# AE FILES MUST BE SORTED IN ORDER OF CAM ID
ae_files = ["data/ae_cam0.txt", "data/ae_cam1.txt", "data/ae_cam2.txt"]
video_dir = "data"

# Get the events
events_to_check, ae_data, wb_data = list_detected_events(result_path, ae_files)
# Get the class mappings
class_mappings = json.load(open("data/class_mappings.json", "r"))


# Keep track of which page we are on
if "page" not in st.session_state:
    st.session_state.page = 0
def nextpage():
    if st.session_state.page >= len(events_to_check)-1:
        switch_page("time_constraints")
    else: 
        st.session_state.page += 1

def restart(): st.session_state.page = 0

def review(): switch_page("review")


# Create an empty container
display_placeholder = st.empty()
if st.button("Yes, it is correct"):
    nextpage()
# st.button("No, it is incorrect", on_click=review)
if st.button("No, it is incorrect"):
    review()




with display_placeholder.container():

    event_data = events_to_check[st.session_state.page]
    # Start getting images and object classes
    img, obj_classes = get_image_for_event(event_data[1][0], video_dir, wb_data)

    st.write("event name: {x} ".format(x=event_data[0]))

    img_display = st.image(img)

    # The textbox should describe grouping of classes
    st.subheader('Are the following claims correct?')
    class_groups = get_class_grouping(obj_classes)

    for class_key in class_groups.keys():
        st.write("There are {x} objects of type {y} within the red highlighted area.".format(x=class_groups[class_key], y=get_name_from_index(class_mappings, class_key)) )
    
    
        # display_placeholder.empty()

# Set up image display
# img_display = st.image()




