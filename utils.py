import os
import cv2

# Parse the CE results for a particular take.
#  Example ce_file: "results/CE1_smoke_50_True_True_True/364/ce_output.txt"
def parse_ce_results_for_file(ce_file):

    # Parse detection event log
    with open(ce_file, "r") as rfile:

        # Get the header information
        atomic_events = eval(rfile.readline())
        watchbox_information = eval(rfile.readline())

        event_data = []

        # Now iterate through each line and get each atomic event
        while True:

            line = rfile.readline()
            if not line:
                break

            # Make sure that we only save the events which actually occurred
            #  e.g. result is True
            ce_data = eval(line)
            if ce_data["complex_event"]["result"]:
                event_data.append(ce_data)


    return atomic_events, watchbox_information, event_data
        



# Opens an AE file, and gets the bounding box information for a set of tracks
#   at a given time
def get_obj_data_for_tracks(watchbox_event, ae_files):

    # Get the ae file with the corresponding camera
    camid = "cam" + str(watchbox_event["camid"])
    ae_filepath = [x for x in ae_files if camid in x][0]

    # Get the frame index we want
    frame_index = watchbox_event["time"]
    # Get the track ids of interest
    track_ids_of_interest = watchbox_event["track_ids"]

    # Get track data
    last_seen_data = {}

    # Open the ae file and get the bounding boxes for objects at this time.
    with open(ae_filepath, "r") as af:

        line_of_interest = ""
        while True:
            
            line = af.readline()
            if not line:
                break
            
            line_data = eval(line)

            # Check if any of the current detected track ids match
            for track_id in line_data["tracks"].keys():
                if track_id in track_ids_of_interest:
                    last_seen_data[track_id] = line_data["tracks"][track_id]

            
            # The frames match!
            #   So we break here.
            if line_data["frame_index"] == frame_index: 
                break # Break since we found the data

    return last_seen_data, camid, frame_index



# First, get the CE results for a particular take
#  result_path: e.g. "DistributedCE/detection/ce_results/CE1_smoke_50_True_True_True/378"
def check_missed_events(result_filepath, ae_files):


    # open and parse the results of our CE detection
    overall_atomic_events, watchbox_information, event_data = \
        parse_ce_results_for_file(result_filepath)

    
    # This is of the form [(ae_name, [(time, camera, wbname, obj_data), ...])]
    events_to_check = []

    # Now, generate images using the watchboxes for an image, 
    #   and describe what we detected.

    # So first, for each complex event happening, we need to
    #  identify the atomic events, and for each we need to identify 
    #  which watchbox it occurred in and what time.
    for multi_atomic_event in event_data:
        # Get the atomic events
        atomic_events = multi_atomic_event["complex_event"]["ae_list"]


        # Now iterate through each atomic event
        for atomic_event_name in atomic_events:
            
            # Get the atomic event information
            ae_to_add = (atomic_event_name, [])
            atomic_event_data = None
            for x_i, x in enumerate(multi_atomic_event["atomic_event"]):
                if atomic_event_name in x:
                    atomic_event_data = x[atomic_event_name]

            # Now, iterate through each element, and get the time, track ids, and camid
            for watchbox_event in atomic_event_data:
                last_seen_data, cam_id, frame_index = \
                    get_obj_data_for_tracks(watchbox_event, ae_files)
                
                ae_to_add[1].append((frame_index, cam_id, \
                    watchbox_event["wb_name"], last_seen_data))
            
            events_to_check.append(ae_to_add)
    
    return events_to_check, overall_atomic_events, watchbox_information


# Get the total number of frames in this video
def get_video_and_data(video_path):

    vidcap = cv2.VideoCapture(video_path)
    frames = vidcap.get(cv2.CAP_PROP_FRAME_COUNT)
    return int(frames), vidcap


# Parse the AE function to see what we should be looking for.
#  The index tells us in a multi-watchbox AE which one we should look at
def parse_ae(ae_text, index):

    # Now, get the model and size data
    ae_split = ae_text.split("composition")[1:]
    ae_split = [x.split("self.watchboxes") for x in ae_split]
    ae_split = [x[0] for x in ae_split]

    ae_text_of_interest = ae_split[index]

    # Get the model and size
    model = ae_text_of_interest.split("model='")[1].split("')")[0]
    comp_size = ae_text_of_interest.split(".size")[1][2:].split(" ")[0]
    
    return model, comp_size

        

# Get an image for a particular frame index
def get_image_for_frame_index(vidcap, frame_index):

    #  Start reading data 
    vidcap.set(cv2.CAP_PROP_POS_FRAMES,frame_index)
    return read_next_image(vidcap)

# Read the next image
def read_next_image(vidcap):
    _, image_to_draw = vidcap.read()
    # Convert from bgr to rgb
    image_to_draw = cv2.cvtColor(image_to_draw, cv2.COLOR_BGR2RGB)

    return image_to_draw


# Get the watchbox coordinates and draw it over the image
def draw_wb_coords(image_to_draw, wb_data, event_to_check):
    # First, get the watchbox coordinates
    wb_coords = wb_data[event_to_check[2]]["positions"]
    # Draw the watchbox
    cv2.rectangle(image_to_draw, (wb_coords[0], wb_coords[1]), \
        (wb_coords[2], wb_coords[3]), (0, 0, 255), 3)
    return image_to_draw

    
# We also need to grab images at a given frame index
#  (2163, 'cam0', 'bridgewatchbox5', {36: {'bbox_data': [305.64, 531.76, 333.87, 543.84], 'prediction': 1}, 37: {'bbox_data': [42.21, 551.0, 71.59, 565.2], 'prediction': 1}, 38: {'bbox_data': [224.01, 521.07, 251.96, 533.43], 'prediction': 1}, 40: {'bbox_data': [5.59, 524.0, 35.61, 537.0], 'prediction': 1}})
def get_image_for_event(event_to_check, video_dir, wb_data):

    # First, get the full video filepaths
    video_filepaths = [x for x in os.listdir(video_dir) if ".mp4" in x]
    video_filepaths = [os.path.join(video_dir, x) for x in video_filepaths]

    # Open the correct video, and move to the frame.
    vpath = [x for x in video_filepaths if event_to_check[1] in x][0]
    frame_of_interest = event_to_check[0]

    #  Start reading data 
    vidcap = cv2.VideoCapture(vpath)
    success,image = vidcap.read()
    vidcap.set(cv2.CAP_PROP_POS_FRAMES,frame_of_interest)
    _, image_to_draw = vidcap.read()
    # while success:
    #     success,image = vidcap.read()
    #     if count == frame_of_interest:
    #         image_to_draw = image
    #         break
    #     count += 1

    # Now we draw on the image.

    image_to_draw = draw_wb_coords(image_to_draw, wb_data, event_to_check)
    # Now, draw all the objects
    obj_classes = {}
    for obj_track in event_to_check[3].keys():
        bbox_data = event_to_check[3][obj_track]["bbox_data"]
        bbox_data = [int(x) for x in bbox_data]
        obj_classes[obj_track] = event_to_check[3][obj_track]["prediction"]

        # Draw the bounding boxes
        cv2.rectangle(image_to_draw,  (bbox_data[0], bbox_data[1]), \
            (bbox_data[2], bbox_data[3]), (0, 255, 255), 1)
        fontScale = 0.5
        color = (255, 153, 255)
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = 2
        image_to_draw = cv2.putText(image_to_draw, str(obj_track), (bbox_data[0], bbox_data[1]), font, 
                        fontScale, color, thickness, cv2.LINE_AA)

    # Convert from bgr to rgb
    image_to_draw = cv2.cvtColor(image_to_draw, cv2.COLOR_BGR2RGB)

    return image_to_draw, obj_classes
        

# Get class composition
def get_class_grouping(obj_classes):
    class_counts = {}
    for track_id in obj_classes.keys():
        class_type = obj_classes[track_id]
        if class_type not in class_counts:
            class_counts[class_type] = 1
        else:
            class_counts[class_type] += 1
    return class_counts


# Get class name from index
def get_name_from_index(class_mappings, index):

    name = ""
    for x in class_mappings.keys():
        if class_mappings[x] == index:
            name = x
    return name


# We also need to do some interpretation of our language
#   e.g. go from "wb1.composition" to "are there 5 recce vehicles in wb1?"
