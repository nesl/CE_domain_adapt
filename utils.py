import os
import cv2
from tqdm import tqdm
import json

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
        

# Add data to json file
#  Format of file:
#   {
#       "review_time": [5, ...]    # Measured in time.time
#       "vreview_time": [10, ...]
#       "annotate_time": [7, ...]
#       "total_time": [60]
# }
def add_metrics_to_json_file(metrics_filepath, type, time):

    # If this filepath doesn't exist yet, make it
    data = {}
    if not os.path.exists(metrics_filepath):
        with open(metrics_filepath, 'w') as fp:
            pass
    else:
        # Open and append
        with open(metrics_filepath, "r") as f:
            data = json.load(f)

        if type not in ["review_time", "vreview_time", "annotate_time", "total_time"]:
            print("NOT ALLOWED TYPE")
            asdf
    
    # Now, go to the type:
    if type not in data:
        data[type] = [time]
    else:
        data[type].append(time)
    
    # Now, save the file
    with open(metrics_filepath, "w") as f:
        json.dump(data, f)




# Sample and save videos
def sample_and_save_videos(to_annotate_path, video_dir, subsample_val):

    # If there's already stuff here, then skip
    if os.listdir(to_annotate_path):
        return

    # Get all the video filepaths
    video_files = os.listdir(video_dir)
    video_files = [os.path.join(video_dir, x) for x in video_files]
    video_files = [x for x in video_files if ".mp4" in x]

    # Iterate through each file
    for vfilepath in video_files:

        # Open the file and get every subsample_val frame
        num_frames, vidcap = get_video_and_data(vfilepath)

        # print(num_frames)

        # Loop until we're out of video frames
        for frame_index in tqdm(range(0, num_frames, subsample_val)):
            # Read in image

            vidcap.set(cv2.CAP_PROP_POS_FRAMES,frame_index)
            ret, image_to_save = vidcap.read()

            # If we have a frame
            if ret:
                # if frame_index % subsample_val == 1:
                image_filename = str(len(os.listdir(to_annotate_path)))+".jpg"
                save_path = os.path.join(to_annotate_path, image_filename)
                save_image(save_path, image_to_save)
            else:
                break

        # Release video
        vidcap.release()




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


# For all AE files, pull up all the vicinal events
#  The result is a list of [()] IDK yet
def get_ordered_vicinal_events(ae_files):

    # First, iterate through each ae file and get its vicinal events
    vicinal_event_dict = {x:[] for x in ae_files}
    for ae_file in ae_files:
        with open(ae_file, "r") as af:
            while True:
                # Read a line
                line = af.readline()
                if not line:
                    break

                # Check if there's a vicinal event
                line_data = eval(line)
                vicinal_event = line_data["vicinal_events"]
                if vicinal_event:
                    vicinal_event_dict[ae_file].append(vicinal_event)
                    vicinal_event.append(line_data["tracks"])
    
    # Then we merge the lists such that all vicinal events are in order
    vicinal_event_sequence = []
    # This var keeps track of the current index in each ae_file until all vicinal events
    #  are added.
    vicinal_event_tracker = {x:0 for x in ae_files}
    while True:

        # we only break once all items are added - in other words
        #   when the event tracker is all -1
        if all([x < 0 for x in vicinal_event_tracker.values()]):
            break

        # We iterate through each dict, and if we can add it, then we do so
        #  and check if it has reached the end.
        earliest_vicinal_event_time = None
        earliest_vicinal_event_key = None
        earliest_tracked_index = None
        for ae_key in vicinal_event_tracker:
            current_tracked_index = vicinal_event_tracker[ae_key]
            if current_tracked_index == -1:
                continue  # skip this if it is completed.
            current_tracked_time = vicinal_event_dict[ae_key][current_tracked_index][0]["time"]

            if not earliest_vicinal_event_time:  # If this is empty, fill it with the event
                earliest_vicinal_event_time = current_tracked_time
                earliest_vicinal_event_key = ae_key
            elif current_tracked_time < earliest_vicinal_event_time:
                earliest_vicinal_event_time = current_tracked_time
                earliest_vicinal_event_key = ae_key

        # Now, make sure to add the current vicinal event
        index_of_interest = vicinal_event_tracker[earliest_vicinal_event_key]
        vicinal_event_sequence.append(vicinal_event_dict[earliest_vicinal_event_key][index_of_interest])
        vicinal_event_tracker[earliest_vicinal_event_key] += 1
        # If we have added everything, set the tracker to -1
        if vicinal_event_tracker[earliest_vicinal_event_key] >= len(vicinal_event_dict[earliest_vicinal_event_key]):
            vicinal_event_tracker[earliest_vicinal_event_key] = -1
        

    return vicinal_event_sequence




# First, get the CE results for a particular take
#  result_path: e.g. "DistributedCE/detection/ce_results/CE1_smoke_50_True_True_True/378"
def list_detected_events(result_filepath, ae_files):


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

# Get the total number of frames in this video
def get_video_total_frames(video_path):

    vidcap = cv2.VideoCapture(video_path)
    frames = vidcap.get(cv2.CAP_PROP_FRAME_COUNT)
    vidcap.release()
    return int(frames)


# Add a watchbox to a video
def add_wb_to_video(video_path, wb_coords, save_path):

    # Get the total number of frames
    total_frames, vidcap = get_video_and_data(video_path)
    width = int(vidcap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(vidcap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc('F','M','P','4'), 30, (width, height))

    for i in tqdm(range(total_frames)):
        # Iterate through entire video file, and save it
        img1 = read_next_image(vidcap)
        img1 = draw_wb_coords(img1, wb_coords)
        out.write(img1)
    out.release()
    vidcap.release()



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
    operation = ae_text_of_interest.split(".size")[1]#.split(" ")[0]
    # Get rid of any alpha character after
    operation_final = ""
    for x in operation:
        if not x.isalpha():
            operation_final += x
    comp_size = ae_text_of_interest.split(".size")[1][2:].split(" ")[0]
    
    # Make sure comp_size is all numeric
    comp_size = ''.join([x for x in comp_size if x.isnumeric()])
    
    return model, comp_size, operation_final

        

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

def convert_from_bgr(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def get_wb_coords(wb_data, event_to_check):
    # First, get the watchbox coordinates
    wb_coords = wb_data[event_to_check[2]]["positions"]
    return wb_coords

# Get the watchbox coordinates and draw it over the image
def draw_wb_coords(image_to_draw, wb_coords):
    
    # Draw the watchbox
    cv2.rectangle(image_to_draw, (wb_coords[0], wb_coords[1]), \
        (wb_coords[2], wb_coords[3]), (0, 0, 255), 3)
    return image_to_draw


# Save the image
def save_image(filepath, img):
    cv2.imwrite(filepath, img)


# We also need to grab images at a given frame index
#  (2163, 'cam0', 'bridgewatchbox5', {36: {'bbox_data': [305.64, 531.76, 333.87, 543.84], 'prediction': 1}, 37: {'bbox_data': [42.21, 551.0, 71.59, 565.2], 'prediction': 1}, 38: {'bbox_data': [224.01, 521.07, 251.96, 533.43], 'prediction': 1}, 40: {'bbox_data': [5.59, 524.0, 35.61, 537.0], 'prediction': 1}})
def get_image_for_wb_state(wb_state, video_dir, watchboxes, class_mappings):

    cam_name = wb_state[1][4]

    # First, get the full video filepaths
    video_filepaths = [x for x in os.listdir(video_dir) if ".mp4" in x]
    video_filepaths = [os.path.join(video_dir, x) for x in video_filepaths]

    # Open the correct video, and move to the frame.
    vpath = [x for x in video_filepaths if cam_name in x][0]
    frame_of_interest = wb_state[1][1]

    #  Start reading data 
    vidcap = cv2.VideoCapture(vpath)
    success,image = vidcap.read()
    vidcap.set(cv2.CAP_PROP_POS_FRAMES,frame_of_interest)
    _, img_out = vidcap.read()
    # while success:
    #     success,image = vidcap.read()
    #     if count == frame_of_interest:
    #         image_to_draw = image
    #         break
    #     count += 1

    # Now we draw on the image.
    image_to_draw = img_out.copy()
    # Get the wb coords and draw the image
    wb_coords = watchboxes[wb_state[1][0]].positions
    image_to_draw = draw_wb_coords(image_to_draw, wb_coords)

    # Now, draw all the objects
    obj_classes = {}
    for obj_track in wb_state[1][2]:

        # First, get the class of interest
        class_of_interest = class_mappings[wb_state[0][0]]
        bbox_data = wb_state[1][2][obj_track]
        bbox_data = [int(x) for x in bbox_data]
        obj_classes[obj_track] = wb_state[1][3][obj_track]

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

    return image_to_draw, obj_classes, img_out

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
    _, img_out = vidcap.read()
    # while success:
    #     success,image = vidcap.read()
    #     if count == frame_of_interest:
    #         image_to_draw = image
    #         break
    #     count += 1

    # Now we draw on the image.

    # Get the wb coords and draw the image
    image_to_draw = img_out.copy()
    wb_coords = get_wb_coords(wb_data, event_to_check)
    image_to_draw = draw_wb_coords(image_to_draw, wb_coords)

    # Now, draw all the objects
    obj_classes = {}
    for obj_track in event_to_check[3].keys():
        bbox_data = event_to_check[3][obj_track]["bbox_data"]
        bbox_data = [int(x) for x in bbox_data]
        obj_classes[obj_track] = event_to_check[3][obj_track]["prediction"]

        # Draw the bounding boxes
        # cv2.rectangle(image_to_draw,  (bbox_data[0], bbox_data[1]), \
        #     (bbox_data[2], bbox_data[3]), (0, 255, 255), 1)
        fontScale = 0.5
        color = (255, 153, 255)
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = 2
        # image_to_draw = cv2.putText(image_to_draw, str(obj_track), (bbox_data[0], bbox_data[1]), font, 
        #                 fontScale, color, thickness, cv2.LINE_AA)

    # Convert from bgr to rgb
    image_to_draw = cv2.cvtColor(image_to_draw, cv2.COLOR_BGR2RGB)

    return image_to_draw, obj_classes, img_out
        

# Save all images for the given cam/frame ids
def save_relevant_track_images(save_dir, video_dir, track_json_file):

    # first, if the save dir doesn't exist then make it
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)

    # Get the corresponding video files
    video_filepaths = [x for x in os.listdir(video_dir) if ".mp4" in x]
    video_filepaths = [os.path.join(video_dir, x) for x in video_filepaths]

    
    # Now, open the track json file
    track_data = None
    track_json_filepath = video_dir + "/" + track_json_file
    with open(track_json_filepath, "r") as tf:
        track_data = json.load(tf)
    
    # Iterate through every camera in the track json file
    for cam_name in track_data.keys():

        vf_of_interest = [x for x in video_filepaths if cam_name in x][0]
        #  Start reading data 
        vidcap = cv2.VideoCapture(vf_of_interest)
        success,image = vidcap.read()

        # Now, we go through every entry of this cam
        #  And save the corresponding image
        for entry in tqdm(track_data[cam_name]):
            
            frame_index = entry["frame_index"]
            vidcap.set(cv2.CAP_PROP_POS_FRAMES,frame_index)
            _, img_to_save = vidcap.read()

            # image filename
            img_filename = track_json_file.split(".json")[0] + "_" + \
                cam_name + "_frame_" + str(frame_index) + ".jpg"
            filepath = save_dir + "/" + img_filename

            # Now add the bboxes for debugging
            # for id in entry["tracks"]:
                
            #     bbox_data = entry["tracks"][id]["bbox_data"]
            #     bbox_data = [int(x) for x in bbox_data]
            #     print(bbox_data)
            #      # Draw the bounding boxes
            #     cv2.rectangle(img_to_save,  (bbox_data[0], bbox_data[1]), \
            #         (bbox_data[2], bbox_data[3]), (0, 255, 255), 1)


            save_image(filepath, img_to_save)




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
