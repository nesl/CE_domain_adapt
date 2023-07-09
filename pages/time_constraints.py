import streamlit as st
from streamlit_extras.switch_page_button import switch_page
import time
from utils import get_image_for_frame_index, get_video_and_data, check_missed_events, \
    read_next_image, draw_wb_coords, parse_ae
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

# wrapper for caching event data
@st.cache_data
def get_events(result_path, ae_files):
    return check_missed_events(result_path, ae_files)

# # Update slider values
def increment_slider(max_frames):
    if st.session_state["vslider"] < max_frames:
        st.session_state.vslider += 1
    else:
        pass
    return

# # # Update slider values
# def increment_slider2():
#     if st.session_state["vslider"] < 1000:
#         st.session_state.vslider += 1
#     else:
#         pass
#     return


st.title('Determining Correct Time of Events')


# Get event data
result_path = "data/ce_output.txt"
# AE FILES MUST BE SORTED IN ORDER OF CAM ID
ae_files = ["data/ae_cam0.txt", "data/ae_cam1.txt", "data/ae_cam2.txt"]


# Get the events, and be sure to cache
events_to_check, ae_data, wb_data = get_events(result_path, ae_files)

# So now we need to have a slider which "plays" a video
video_path = "data/cam0.mp4"
# Let's just take an event of interest
event_of_interest = events_to_check[0]
ae_of_interest = ae_data[event_of_interest[0]][1]

index = 0
event_time = event_of_interest[1][index][0]

model, comp_size = parse_ae(ae_of_interest, index)

# Get the total number of frames
total_frames, vidcap = get_video_and_data(video_path)

# Option for playing video
value1 = st.slider('Starting Time Index', 0, total_frames, value=event_time, key="vslider")
img1 = get_image_for_frame_index(vidcap, value1)
st.subheader('Please use the slider to determine when the video starts')




display_placeholder = st.empty()

st.subheader("Find when there are {x} objects of type {y} within the highlighted region".format(x=comp_size, y=model))
st.write("Our system detected this event at time {x}".format(x=event_time))

play = True
if st.button("Play"):
    play = True
if st.button("Pause"):
    play = False

#  This basically keeps replacing the image
previous_time = time.time()
while True:
    with display_placeholder.container():

        value1 += 1
        img1 = read_next_image(vidcap)
        img1 = draw_wb_coords(img1, wb_data, event_of_interest[1][0])
        img_display = st.image(img1)
        time_to_sleep = max(0, 1/30 - (time.time()-previous_time))
        st.write("current frame: {x}".format(x=value1))
        # increment_slider(total_frames)
        time.sleep(time_to_sleep)
        




        