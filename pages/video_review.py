import streamlit as st
import os
from streamlit_extras.switch_page_button import switch_page
import time
# from utils import get_image_for_frame_index, get_video_and_data, check_missed_events, \
#     read_next_image, draw_wb_coords, get_wb_coords, parse_ae
from utils import get_image_for_frame_index, get_video_and_data, \
    draw_wb_coords, get_class_grouping, save_image, convert_from_bgr, add_metrics_to_json_file
from domain_adapt import find_closest_aes, get_time_bounds, reorganize_video_search


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

# # wrapper for caching event data
# @st.cache_data
# def get_events(result_path, ae_files):
#     return check_missed_events(result_path, ae_files)

# # # Update slider values
# def increment_slider(max_frames):
#     if st.session_state["vslider"] < max_frames:
#         st.session_state.vslider += 1
#     else:
#         pass
#     return

# # # Update slider values
# def increment_slider2():
#     if st.session_state["vslider"] < 1000:
#         st.session_state.vslider += 1
#     else:
#         pass
#     return


st.title('Verify from video')

unconfirmed_vicinal_events = st.session_state["unconfirmed_vicinal_events"]
ce_obj = st.session_state["ce_obj"]
detected_time = st.session_state["detected_time"]
class_mappings = st.session_state["class_mappings"]
ae_statuses = find_closest_aes(st.session_state["confirmed_vicinal_events"], ce_obj, detected_time)
st.session_state["ae_statuses"] = ae_statuses
confirmed_vicinal_events = st.session_state["confirmed_vicinal_events"]
video_dir = st.session_state["video_dir"]
wb_data = st.session_state["wb_data"]
search_ae_data = st.session_state["search_ae_data"]

missing_intervals = get_time_bounds(ae_statuses, detected_time)
segments_to_annotate = reorganize_video_search(search_ae_data, missing_intervals, video_dir)


# Keep track of which page we are on
if "page3" not in st.session_state:
    st.session_state.page3 = 0
def nextpage():

    # First, save the timing
    add_metrics_to_json_file(st.session_state["timing_metrics_file"], \
        "vreview_time", time.time() - st.session_state["st"])

    if st.session_state.page3 >= len(segments_to_annotate)-1:
        switch_page("image_label")
    else: 
        st.session_state.page3 += 1
def restart(): st.session_state.page3 = 0
def review(): switch_page("review")


# Create an empty container
if st.button("I found the event!"):

    # When the event is found, we save the current image to a file
    annotation_dir = st.session_state["to_annotate_path"] # os.path.join(video_dir, "to_annotate")
    num_current_files = len(os.listdir(annotation_dir))
    save_filepath = os.path.join(annotation_dir, str(num_current_files)+".jpg")
    
    # Save image to that folder
    save_image(save_filepath, convert_from_bgr(st.session_state["current_image"]))

    nextpage()
# st.button("No, it is incorrect", on_click=review)
if st.button("I can't find this!"):

    nextpage()



# Stuff to annotate
current_segment = segments_to_annotate[st.session_state.page3]
#  (video_filepath, time_interval, watchbox, composition)
video_path = current_segment[0]
time_interval = current_segment[1]
watchbox = current_segment[2]
comp = current_segment[3]

# Get the total number of frames
total_frames, vidcap = get_video_and_data(video_path)
st.session_state["st"] = time.time()
# Option for playing video
value1 = st.slider('Starting Time Index', time_interval[0], time_interval[1], value=time_interval[0], key="vslider")
img1 = get_image_for_frame_index(vidcap, value1)
img_draw = img1.copy()
st.subheader('Please use the slider to determine when the video starts')


display_placeholder = st.empty()

st.subheader("Find when the number of {x} objects {y} within the highlighted region".format(\
    x=comp[0], y=comp[2]))
st.write("Ignore cases where there are no objects at all.")
# st.write("Our system detected this event at time {x}".format(x=event_time))



#  This basically keeps replacing the image
# previous_time = time.time()
# while True:
with display_placeholder.container():

    # if play:

    # value1 += 1
    # img1 = read_next_image(vidcap)
    # wb_coords = get_wb_coords(wb_data, event_of_interest[1][0])
    img1_drawn = draw_wb_coords(img_draw, watchbox)
    st.session_state["current_image"] = img1
    img_display = st.image(img1_drawn)

    # time_to_sleep = max(0, 1/30 - (time.time()-previous_time))
    st.write("current frame: {x}".format(x=value1))

        




        