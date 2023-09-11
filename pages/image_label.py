import streamlit as st
import os
from pages.streamlit_img_label import st_img_label
from pages.streamlit_img_label.manage import ImageManager, ImageDirManager
from utils import add_metrics_to_json_file
import time
from streamlit_extras.switch_page_button import switch_page

# This is how we hide the sidebar navigation
st.set_page_config(initial_sidebar_state="expanded")
st.markdown(
    """
<style>
    [data-testid="collapsedControl"] {
        display: True
    }
</style>
""",
    unsafe_allow_html=True,
)

def run(img_dir, labels):
    
    st.set_option("deprecation.showfileUploaderEncoding", False)
    # print("Here")
    idm = ImageDirManager(img_dir)

    # Check if we need to refresh
    if "labelled_dirs" not in st.session_state:
        st.session_state["labelled_dirs"] = []

    if "files" not in st.session_state and img_dir not in st.session_state["labelled_dirs"] :
        # print("restarting...")
        st.session_state["files"] = idm.get_all_files()
        st.session_state["annotation_files"] = idm.get_exist_annotation_files()
        st.session_state["image_index"] = 0
        st.session_state["labelled_dirs"].append(img_dir)
    elif img_dir not in st.session_state["labelled_dirs"]:
        # print("restarting...")
        st.session_state["files"] = idm.get_all_files()
        st.session_state["annotation_files"] = idm.get_exist_annotation_files()
        st.session_state["image_index"] = 0
        st.session_state["labelled_dirs"].append(img_dir)
    else:
        # print("OTHERWISE...")
        idm.set_all_files(st.session_state["files"])
        idm.set_annotation_files(st.session_state["annotation_files"])
    
    def refresh():
        st.session_state["files"] = idm.get_all_files()
        st.session_state["annotation_files"] = idm.get_exist_annotation_files()
        st.session_state["image_index"] = 0

    def switching_beginning():
        switch_page("test")

    def next_image():
        # print("next")
        st.session_state["st"] = time.time()
        image_index = st.session_state["image_index"]
        if image_index < len(st.session_state["files"]) - 1:
            st.session_state["image_index"] += 1
        else:
            st.warning('This is the last image. Click below to go back to beginning.')
            # This is the last image, so go back to the beginning
                   


    def previous_image():
        st.session_state["st"] = time.time()
        image_index = st.session_state["image_index"]
        if image_index > 0:
            st.session_state["image_index"] -= 1
        else:
            st.warning('This is the first image.')

    def next_annotate_file():
        # print("next")
        st.session_state["st"] = time.time()
        image_index = st.session_state["image_index"]
        next_image_index = idm.get_next_annotation_image(image_index)
        if next_image_index:
            st.session_state["image_index"] = idm.get_next_annotation_image(image_index)
        else:
            st.warning("All images are annotated.")
            next_image()

    def go_to_image():
        # print("go")
        st.session_state["st"] = time.time()
        file_index = st.session_state["files"].index(st.session_state["file"])
        st.session_state["image_index"] = file_index

    # Sidebar: show status
    n_files = len(st.session_state["files"])
    n_annotate_files = len(st.session_state["annotation_files"])
    st.sidebar.write("Total files:", n_files)
    st.sidebar.write("Total annotate files:", n_annotate_files)
    st.sidebar.write("Remaining files:", n_files - n_annotate_files)

    if st.button("Back to beginning..."):
        switch_page("test")     

    st.sidebar.selectbox(
        "Files",
        st.session_state["files"],
        index=st.session_state["image_index"],
        on_change=go_to_image,
        key="file",
    )
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.button(label="Previous image", on_click=previous_image)
    with col2:
        st.button(label="Next image", on_click=next_image)
    st.sidebar.button(label="Next need annotate", on_click=next_annotate_file)
    st.sidebar.button(label="Refresh", on_click=refresh)

    # Main content: annotate images
    img_file_name = idm.get_image(st.session_state["image_index"])
    img_path = os.path.join(img_dir, img_file_name)
    im = ImageManager(img_path)
    
    img = im.get_img()
    resized_img = im.resizing_img()
    resized_rects = im.get_resized_rects()
    rects = st_img_label(resized_img, box_color="red", rects=resized_rects)

    def annotate():

        # First, save the timing
        add_metrics_to_json_file(st.session_state["timing_metrics_file"], \
            "annotate_time", time.time() - st.session_state["st"])

        im.save_annotation()
        image_annotate_file_name = img_file_name.split(".")[0] + ".xml"
        if image_annotate_file_name not in st.session_state["annotation_files"]:
            st.session_state["annotation_files"].append(image_annotate_file_name)
        next_annotate_file()

    if rects:
        st.button(label="Save", on_click=annotate)
        preview_imgs = im.init_annotation(rects)

        

        for i, prev_img in enumerate(preview_imgs):
            prev_img[0].thumbnail((200, 200))
            col1, col2 = st.columns(2)
            with col1:
                col1.image(prev_img[0])
            with col2:
                default_index = 0
                if prev_img[1]:
                    default_index = labels.index(prev_img[1])

                select_label = col2.selectbox(
                    "Label", labels, key=f"label_{i}", index=default_index
                )
                im.set_annotation(i, select_label)

if __name__ == "__main__":


    if "st" not in st.session_state:
        # print("start")
        st.session_state["st"] = time.time()

    # custom_labels = ["", "dog", "cat"]
    custom_labels = st.session_state["class_mappings"]
    custom_labels = list(custom_labels.keys())

    # Images to annotate
    annotation_dir = st.session_state["to_annotate_path"]
    # image_dir = os.path.join(data_dir, "to_annotate")


    run(annotation_dir, custom_labels)