import streamlit as st
import pandas as pd
import numpy as np
import os
import time

from domain_adapt import initialize_labelling_data, grab_aes, \
    get_all_vicinal_events, remove_reundant_events
from utils import sample_and_save_videos, add_metrics_to_json_file
from test_ce import build_ce1

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

# Here, we need to initialize a bunch of data

result_path = "data/ce_output.txt"
parent_name = "out"  # Change this to whatever the ce/iteration folder is
annotation_type = "baseline" # either 'baseline' or 'adapt'
subsample_frames = 500 # Every 50 frames, or roughly 5 seconds

saved_annotations_path = os.path.join("annotated", annotation_type, parent_name)
to_annotate_path = os.path.join("to_annotate", annotation_type, parent_name)
# Make all directories
if not os.path.exists("annotated"):
    os.mkdir("annotated")
if not os.path.exists("to_annotate"):
    os.mkdir("to_annotate")
if not os.path.exists("annotated/"+annotation_type):
    os.mkdir("annotated/"+annotation_type)
if not os.path.exists("to_annotate/"+annotation_type):
    os.mkdir("to_annotate/"+annotation_type)
if not os.path.exists(saved_annotations_path):
    os.mkdir(saved_annotations_path)
if not os.path.exists(to_annotate_path):
    os.mkdir(to_annotate_path)


# AE FILES MUST BE SORTED IN ORDER OF CAM ID
ae_files = ["data/ae_cam0.txt", "data/ae_cam1.txt", "data/ae_cam2.txt"]
detected_time = 18000
video_dir = "data"
class_mappings = {"rec_vehicle": 1, "tank": 0}

# Get the CE we are interested in
ce_obj, ce_structure = build_ce1(class_mappings)


# Start keeping track of some general metrics, like timing
st.session_state["timing_metrics_file"] = os.path.join(saved_annotations_path, "time_metrics.json")


if annotation_type == "baseline":

    st.session_state["to_annotate_path"] = saved_annotations_path
    st.session_state["saved_annotations_path"] = saved_annotations_path
    st.session_state["video_dir"] = video_dir
    st.session_state["class_mappings"] = class_mappings

    # Load in all the necessary data
    sample_and_save_videos(saved_annotations_path, video_dir, subsample_frames)
    st.session_state["ce_annotation_starttime"] = time.time()
    # Then, go straight to labelling
    switch_page("image_label")


else: # Our adapt method

    st.session_state["result_path"] = result_path
    st.session_state["ae_files"] = ae_files
    st.session_state["detected_time"] = detected_time
    st.session_state["video_dir"] = video_dir
    st.session_state["class_mappings"] = class_mappings
    st.session_state["ce_obj"] = ce_obj
    st.session_state["to_annotate_path"] = to_annotate_path
    st.session_state["saved_annotations_path"] = saved_annotations_path

    # First, initialize data before we move forward
    relevant_aes, ae_programs, wb_data = \
        initialize_labelling_data(result_path, ae_files, detected_time)
    st.session_state["relevant_aes"] = relevant_aes
    st.session_state["ae_programs"] = ae_programs
    st.session_state["wb_data"] = wb_data

    # Then, get all the AEs we need to check
    unconfirmed_vicinal_events, search_ae_data = grab_aes(relevant_aes, ae_programs, wb_data)
    unconfirmed_vicinal_events2 = get_all_vicinal_events(ae_files, wb_data)
    unconfirmed_vicinal_events2 = remove_reundant_events(unconfirmed_vicinal_events2, unconfirmed_vicinal_events)

    st.session_state["unconfirmed_vicinal_events"] = unconfirmed_vicinal_events
    st.session_state["unconfirmed_vicinal_events2"] = unconfirmed_vicinal_events2
    st.session_state["search_ae_data"] = search_ae_data
    st.session_state["confirmed_vicinal_events"] = {}





    st.title('Preface/Briefing Page')

    # Basically we need 3 pages:
    #   One for confirming vicinal events
    #     with a button for 'needs to be edited'
    #   Another for scrolling through a video
    #     and naming the bounds, and a button for 'needs to be edited'
    #       based on which events must still be annotated.
    #   Once the above two are finalized, we have a list of images to be annotated
    #     and then we have the user annotate that list of images.
    #      This basically generates two things:
    #         - a list of confirmed events (which can be used for training)
    #         - a list of user annotations (which are combined with track data)

    st.session_state["ce_annotation_starttime"] = time.time()

    if st.button('Determing Incorrect Events'):
        switch_page("incorrect_events")
    if st.button('Determing Incorrect Events2'):
        switch_page("incorrect_ves")
    if st.button('Video checker'):
        switch_page("video_review")
    if st.button('Image annotations'):
        switch_page("image_label")




# Todos:
#  Add timing functionality and image counting functionality
#    e.g. like how much time 'image checking' takes vs 'image annotation'
#  Also need to figure out the baseline (maybe just video review but with all events)

# Count:
#   - how many images reviewed
#   - how many images annotated
# Time:
#   - time spent on review, including video
#   - time spend on annotation
#   - Time spend during the entire process for a single CE
# Record for every example, and update the same file