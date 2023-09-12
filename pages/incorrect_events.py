import streamlit as st
from utils import get_image_for_wb_state, get_class_grouping, \
    get_name_from_index, convert_from_bgr, add_metrics_to_json_file
import time
import json
import os
from streamlit_extras.switch_page_button import switch_page
from domain_adapt import find_closest_aes, save_image, \
    match_and_add_ves, verify_aes

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
video_dir = st.session_state["video_dir"]

# Get the events we need to verify
events_to_verify = verify_aes(unconfirmed_vicinal_events, ce_obj, detected_time)

# No events can be verified
if not events_to_verify:
    # Move on.
    switch_page("incorrect_ves")

# Keep track of which page we are on
if "page1" not in st.session_state:
    st.session_state.page1 = 0
def nextpage():

    # First, save the timing
    add_metrics_to_json_file(st.session_state["timing_metrics_file"], \
        "review_time", time.time() - st.session_state["st"])


    if st.session_state.page1 >= len(events_to_verify)-1:
        ae_statuses = find_closest_aes(st.session_state["confirmed_vicinal_events"], ce_obj, detected_time)
        st.session_state["ae_statuses"] = ae_statuses
        switch_page("incorrect_ves")
    else: 
        st.session_state.page1 += 1

def restart(): st.session_state.page1 = 0

def review(): switch_page("review")


# Create an empty container
display_placeholder = st.empty()
if st.button("Yes, it is correct"):

    # This is correct, so move on but first add to our confiremd vicinal events
    # Get the time and watchbox name
    event_wb_name = st.session_state["wb_query"][1][0]
    event_time = st.session_state["wb_query"][1][1]
    # WE ALLOW THE USER TO CORRECT IT HERE, WHICH CHANGES THE WB_QUERY
    #  And creates a new entry for additional sampling
    confirmed_vicinal_events = match_and_add_ves(unconfirmed_vicinal_events, st.session_state["confirmed_vicinal_events"],\
            event_wb_name, event_time)
    st.session_state["confirmed_vicinal_events"] = confirmed_vicinal_events

    nextpage()
# st.button("No, it is incorrect", on_click=review)
if st.button("No, it is incorrect"):

    # When the event is found, we save the current image to a file
    annotation_dir = st.session_state["to_annotate_path"] # os.path.join(video_dir, "to_annotate")
    num_current_files = len(os.listdir(annotation_dir))
    save_filepath = os.path.join(annotation_dir, str(num_current_files)+".jpg")
    
    # Save image to that folder
    save_image(save_filepath, st.session_state["current_image"])
    # print(st.session_state.page1)
    nextpage()




with display_placeholder.container():

    wb_query = events_to_verify[st.session_state.page1]
    st.session_state["wb_query"] = wb_query

    img_drawn, comp, img_orig = get_image_for_wb_state(wb_query, video_dir, ce_obj.watchboxes, class_mappings)
    st.session_state["current_image"] = img_orig
    # Show image here...
    # save_image("results/x.jpg", img)
    img_display = st.image(img_drawn)
    st.session_state["st"] = time.time()

    st.subheader('Are the following claims correct?')
    class_groups = get_class_grouping(comp)

    for class_key in class_groups.keys():
        class_name = get_name_from_index(class_mappings, class_key)
        if class_name:
            st.write("There are {x} objects of type {y} overlapping with the red highlighted area.".format(\
                x=class_groups[class_key], y= class_name))
    if len(class_groups.keys()) == 0: #Empty item
        st.write("There are no objects overlapping with the red highlighted area.")


    # display_placeholder.empty()

    # Get user input here
    # user_label = input()
    # if user_label == "correct":
        
    
    


    # event_data = events_to_check[st.session_state.page]
    # # Start getting images and object classes
    # img, obj_classes = get_image_for_event(event_data[1][0], video_dir, wb_data)

    # st.write("event name: {x} ".format(x=event_data[0]))

    # img_display = st.image(img)

    # # The textbox should describe grouping of classes
    # st.subheader('Are the following claims correct?')
    # class_groups = get_class_grouping(obj_classes)

    # for class_key in class_groups.keys():
    #     st.write("There are {x} objects of type {y} within the red highlighted area.".format(x=class_groups[class_key], y=get_name_from_index(class_mappings, class_key)) )
    
    
        # display_placeholder.empty()

# Set up image display
# img_display = st.image()




