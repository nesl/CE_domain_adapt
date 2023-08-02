import streamlit as st
from streamlit_extras.switch_page_button import switch_page
import time
from utils import get_image_for_frame_index, get_video_and_data, list_detected_events, \
    read_next_image, get_wb_coords, parse_ae, add_wb_to_video
from streamlit_javascript import st_javascript

# This is how we hide the sidebar navigation
st.set_page_config(initial_sidebar_state="collapsed")
st.markdown(
    """
<style>
    [data-testid="collapsedControl"] {
        display: none
    }
    [class="stVideo"] {
        width: 1000px;
    }
</style>
""",
    unsafe_allow_html=True,
)


def draw_rect(vidsize, wb_coords):

    size_ratio = vidsize / 1920

    top_pos = -420 + int(wb_coords[0]*size_ratio)
    left_pos = int(wb_coords[1] * size_ratio)
    width = int(wb_coords[2] * size_ratio)
    height = int(wb_coords[3] * size_ratio)

    print(top_pos)
    print(left_pos)
    print(width)
    print(height)

    rect_markdown = """
        <div style="position:absolute; top: {}px; left: {}px; width: {}px; height: {}px; border: 2px solid red; pointer-events: none;">
        </div>
    
    """.format(top_pos, left_pos, width, height)


    st.markdown(rect_markdown, unsafe_allow_html=True)



# wrapper for caching event data
@st.cache_data
def get_events(result_path, ae_files):
    return list_detected_events(result_path, ae_files)


st.title('Determining Correct Time of Events')

# Get event data
result_path = "data/ce_output.txt"
# AE FILES MUST BE SORTED IN ORDER OF CAM ID
ae_files = ["data/ae_cam0.txt", "data/ae_cam1.txt", "data/ae_cam2.txt"]


# Get the events, and be sure to cache
events_to_check, ae_data, wb_data = get_events(result_path, ae_files)

# So now we need to have a slider which "plays" a video
video_name = "cam0"
video_path = "data/" + video_name + ".mp4"
result_path = "data/result.mp4"
# Let's just take an event of interest
event_of_interest = events_to_check[0]
ae_of_interest = ae_data[event_of_interest[0]][1]

index = 0
event_time = event_of_interest[1][index][0]

model, comp_size = parse_ae(ae_of_interest, index)

# Add a watchbox to our video
wb_coords = get_wb_coords(wb_data, event_of_interest[1][0])
# add_wb_to_video(video_path, wb_coords, result_path)


# Open and play the video
video_file = open(video_path, "rb")
video_bytes = video_file.read()
st.video(video_bytes)


# Draw the rectangle
vidsize = 704
draw_rect(vidsize, wb_coords)



# TODOS:
#  Still have to show user when event occurs (e.g. time of occurrence) and 
#   allow them to fill out a form for times.
