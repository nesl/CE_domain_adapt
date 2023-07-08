import streamlit as st
from utils import check_missed_events, get_image_for_frame, get_class_grouping



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
events_to_check, ae_data, wb_data = check_missed_events(result_path, ae_files)


# Create an empty container
display_placeholder = st.empty()

with display_placeholder.container():
    # Start getting images and object classes
    for event_data in events_to_check:
        img, obj_classes = get_image_for_frame(event_data[1][0], video_dir, wb_data)

        img_display = st.image(img)

        # The textbox should describe grouping of classes
        st.subheader('Are the following claims correct?')
        class_groups = get_class_grouping(obj_classes)

        for class_key in class_groups.keys():
            st.write("There are {x} objects of type {y}".format(x=class_groups[class_key], y=class_key) )
        
    
        display_placeholder.empty()

# Set up image display
# img_display = st.image()




