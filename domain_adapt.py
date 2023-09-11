import os
from utils import get_image_for_frame_index, get_video_and_data, list_detected_events, \
    read_next_image, get_wb_coords, parse_ae, add_wb_to_video, \
    get_image_for_event, save_image, get_ordered_vicinal_events, get_image_for_wb_state,\
    save_relevant_track_images, get_class_grouping

# Import the languageCE files
import sys
# sys.path.append('../DistributedCE/detection/server_code')
# from LanguageCE.test_ce import build_ce1
from test_ce import build_ce1
import json


# Need to come up with some test cases:
#   - AE missing randomly
#   - AE present but time is off
#   - AE is present but misclassified, either from 
#       - non-event
#       - a random event which is prior or later, thus affecting detections.



# Get the times of every event occurring
def get_ae_times(events_to_check):

    event_ae_times = []
    # Iterate through each event
    for event_i, event in enumerate(events_to_check):
        # Get the max time 
        current_times = [x[0] for x in event[1]]
        event_occurrence_time = max(current_times)
        event_ae_times.append((event_i, event_occurrence_time))

    return event_ae_times

# Get the time of an AE which occurs closest to the detection time
def get_closest_ae_time(events_to_check, detected_time):

    # Get the list of AE times
    event_ae_times = get_ae_times(events_to_check)

    # Get the closest AE time
    #  This means closest AE that is just prior to detected_time
    closest_ae_diff = detected_time
    closest_ae_index = -1
    closest_ae_time = detected_time
    for ae_times in event_ae_times[::-1]:
        current_diff = detected_time - ae_times[1]
        #  Check if time is smaller AND still close to the event
        if current_diff < closest_ae_diff and current_diff >= -100:
            closest_ae_diff = current_diff
            closest_ae_index = ae_times[0]
            closest_ae_time = ae_times[1]
    
    return closest_ae_index, closest_ae_time, event_ae_times

# Get the AEs which are relevant
#  This also puts them in reverse order
def get_ordered_relevant_detected_aes(events_to_check, detected_time):

    # Get the closest AE time and all ae_times
    closest_ae_index, closest_ae_time, event_ae_times = \
        get_closest_ae_time(events_to_check, detected_time)

    # Sort the event_ae_times in descending time order
    event_ae_times = sorted(event_ae_times, key=lambda x : -x[1])

    # Based on the closest AE time, determine which AEs are still relevant
    relevant_ae_times = [(x[0], x[1]) for x in event_ae_times if x[1] <= closest_ae_time]

    relevant_aes = [events_to_check[x[0]] for x in relevant_ae_times]
    
    return relevant_aes, relevant_ae_times


# Find vicinal events within a period of time
# def get_vicinal_events_within_time(lower_bound, upper_bound, ordered_vicinal_events):
    
#     vicinal_events_within_range = []
#     # Iterate through the list of events
#     for vicinal_event in ordered_vicinal_events:
        
#         event_time = vicinal_event[0]["time"]
#         if lower_bound < event_time and event_time < upper_bound:
#             vicinal_events_within_range.append(vicinal_event)

#     return vicinal_events_within_range


# Find vicinal events within a period of time
def get_vicinal_events_within_time(lower_bound, upper_bound, unconfirmed_vicinal_events):
    
    vicinal_events_within_range = []

    # Iterate through every wb:
    for wb_name in unconfirmed_vicinal_events.keys():
        # iterate through every wb event 
        for wb_event in unconfirmed_vicinal_events[wb_name]:
            if lower_bound < wb_event[0] and wb_event[0] < upper_bound:
                vicinal_events_within_range.append(wb_event)

    return vicinal_events_within_range


# Get watchbox name from cam and wb id
def get_wb_name(wb_data, cam_id, wb_id):
    wb_name = ""

    for wb_key in wb_data.keys():
        if wb_data[wb_key]["cam_id"] == cam_id and wb_data[wb_key]["watchbox_id"] == wb_id:
            wb_name = wb_key

    return wb_name

# Get all vicinal events
def get_all_vicinal_events(ae_files, wb_data):

    # Create the unconfirmed vicinal event dict
    unconfirmed_vicinal_events = {}

    # print(wb_data)

    # Iterate through each file
    for ae_filepath in ae_files:

        cam_id = int(ae_filepath.split("ae_cam")[1][0])

        with open(ae_filepath, "r") as f:
            # Read every line
            for line in f.readlines():
                line_data = eval(line)
                
                # If there's a vicinal event
                if line_data["vicinal_events"]:
                    vicinal_event_data = line_data["vicinal_events"][0]

                    
                    # Go through each result
                    for entry in vicinal_event_data["results"]:
                        # Get the wb name
                        current_wb_id = entry["watchboxes"][0]

                        frame = line_data["frame_index"]
                        cam_name = "cam" + str(cam_id)
                        wb_name = get_wb_name(wb_data, cam_id, current_wb_id)
                        track_data = line_data["tracks"]
                        ve_data = (frame, cam_name, wb_name, track_data)

                        # Add to our vicinal events
                        if wb_name not in unconfirmed_vicinal_events:
                            unconfirmed_vicinal_events[wb_name] = [ve_data]
                        else:
                            unconfirmed_vicinal_events[wb_name].append(ve_data)

    for wb_key in unconfirmed_vicinal_events.keys():
        # Order the keys
        # sorted_times = sorted(list(unconfirmed_vicinal_events[wb_key].keys()))
        # Now sort the vicinal events under each watchbox
        # unconfirmed_vicinal_events[wb_key] = [unconfirmed_vicinal_events[wb_key][x] for x in sorted_times]

        unconfirmed_vicinal_events[wb_key] = sorted(unconfirmed_vicinal_events[wb_key], key= lambda x : x[0])

    return unconfirmed_vicinal_events




# Determine which aes have occurred, or partially occurred
#   based on the known vicinal events
def find_closest_aes(known_vicinal_events, ce_obj, latest_time):

    ae_statuses = ce_obj.find_closest_aes(known_vicinal_events, latest_time=latest_time)
    return ae_statuses



# Match and vicinal events to a known set of vicinal events
def match_and_add_ves(all_detected_vicinal_events, known_vicinal_events, wb_name, time):
    
    if wb_name not in all_detected_vicinal_events:
        return known_vicinal_events

    for vicinal_event in all_detected_vicinal_events[wb_name]:
        # If time matches
        if vicinal_event[0] == time:

            # Add this entry to the known vicinal events
            if wb_name in known_vicinal_events:

                # Ignore cases where we already added this
                if vicinal_event in known_vicinal_events[wb_name]:
                    break

                known_vicinal_events[wb_name].append(vicinal_event)
            else:
                known_vicinal_events[wb_name] = [vicinal_event]
            
            # Now, sort this particular entry by ascending time
            known_vicinal_events[wb_name] = sorted(known_vicinal_events[wb_name], \
                                                key=lambda y : y[0])
    
    return known_vicinal_events



# Get lower and upper time bounds for an ae
#  detected_time is the CE detection time
def get_time_bounds(ae_statuses, detected_time):

    missing_intervals = []  # pairs of [lower bound, upper bound]

    # Create a list of times, with -1 meaning missing events
    event_times = [detected_time] + [x[2] for x in ae_statuses] + [0]
    ae_names = [None] + [x[0] for x in ae_statuses] + [None]
    
    event_tup = [-1, -1]
    current_missed_aes = []
    crossed_missing_event = False
    for time_i, time  in enumerate(event_times):

        # event actually detected
        if time != -1:
            # If upper bound is present and we crossed a missing event
            #   then save lower bound and update the list
            #  If no upper bound is present, save upper bound
            if event_tup[1] == -1:
                event_tup[1] = time
            elif event_tup[1] != -1 and crossed_missing_event:
                event_tup[0] = time
                missing_intervals.append((current_missed_aes, event_tup))
                crossed_missing_event = False
                current_missed_aes = []
                event_tup = [-1, time]
            elif event_tup[1] != -1:
                event_tup[1] = time
        else:  #event not detected
            crossed_missing_event = True
            if ae_names[time_i]:
                current_missed_aes.append(ae_names[time_i])

    return missing_intervals
            

# Go through the corresponding camera file, and get all data and times
#   for a particular track.
def get_tracking_info(confirmed_vicinal_events):

    tracked_ids_per_cam = {}  # camera : ids
    # Iterate through each confirmed vicinal event, and get
    #   the track IDs for every camera
    for wb_name in confirmed_vicinal_events.keys():
        for event in confirmed_vicinal_events[wb_name]:
            cam_name = event[1]
            track_ids = list(event[3].keys())

            # Then, we begin adding to our dict
            if cam_name not in tracked_ids_per_cam:
                tracked_ids_per_cam[cam_name] = track_ids
            else: # We have to add to the dict
                for track_id in track_ids:
                    tracked_ids_per_cam[cam_name].append(track_id)
                # Get the unique set
                tracked_ids_per_cam[cam_name] = list(set(tracked_ids_per_cam[cam_name]))
    
    return tracked_ids_per_cam

# Grab all the bounding boxes and images for the given tracks and cameras
#  Be sure to actually test this by marking the bboxes on the images
def save_track_data_to_label(tracked_ids_per_cam, ae_files, video_dir):
    
    # Keep track of tracks and bboxes
    cam_frames_and_bboxes = {}  # cam_id : [{'frame_index': time, 'tracks': track_data which includes bboxes and preds]...]

    # So we first iterate through one camera's files
    for cam_name in tracked_ids_per_cam.keys():
        tracked_ids = tracked_ids_per_cam[cam_name]
        current_ae_file = [af for af in ae_files if cam_name in af][0]
        
        # Open the ae file, and go through it line by line
        lines = []
        with open(current_ae_file, "r") as af:
            lines = af.readlines()
        
        for line in lines:
            line_data = eval(line)
            tracks_data = list(line_data["tracks"].keys())
            # Check if any tracked ids are in the line data's tracks
            if any([x in tracked_ids for x in tracks_data]):
                # This may be a problem - we are saving all bbox data for this frame
                #  even if not confirmed by the user
                entry_to_add = line_data
                entry_to_add.pop("vicinal_events")
                if cam_name not in cam_frames_and_bboxes:
                    cam_frames_and_bboxes[cam_name] = [entry_to_add]
                else:
                    cam_frames_and_bboxes[cam_name].append(entry_to_add)
    
    # Save the cam_frames_and_bboxes to a file
    filepath = video_dir + "/da_confirmed.json"
    with open(filepath, "w") as wp:
        json.dump(cam_frames_and_bboxes, wp)



# To make things really simple, this is the algorithm:
#   Go through each AE in reverse, starting from closest AE to CE detection time:
#      Go through each watchbox state in the atomic event, and make sure
#        it occurs and is on time.  We restrict the search area to being between
#        the next AE/CE detection time, and just after the previous watchbox or AE event.
#      If it isn't found, then it means the previous AE was probably not correct.
#      And this process would then continue.

#  Note - verifying if something is correct is easy.
#     So when we go through several possible AEs (e.g. an OR'd statement),
#     we should verify as many events as we can (in terms of watchbox states)
#        which change upon every vicinal event - this is according to the bounds.
#     Then, given those watchbox states, we can identify which AEs
#       are most likely, and start requesting the user to look for those.
#     Once an AE is determined with certainty, then we move on.
#      By moving on, we seek the next "necessary" event, meaning that
#       we ignore other events which were optional (e.g. in OR)

#  Note - we need to eval if the corrected watchbox states results
#    in a necessary AE


# So here's how we split up the domain adapt functions...
#   # Basically we need 4 pages:
#   One for starting the user session and initializing variables
#    THis is where we intialize everything and grab all unconfirmed events
#       We have to pass a bunch of variables, including the unconfirmed events
def initialize_labelling_data(result_path, ae_files, detected_time):

     # Get the events
    events_to_check, ae_programs, wb_data = list_detected_events(result_path, ae_files)

    # Get relevant AEs based on the detection time
    relevant_aes, relevant_ae_times = get_ordered_relevant_detected_aes(events_to_check, detected_time)

    return relevant_aes, ae_programs, wb_data

#   One for confirming vicinal events
#     with a button for 'needs to be edited'
#     This is where we do part 1.5 and get the new ae statuses
#        if the CE still isn't satisfied, we move on.
#   Note - there are two versions of this:
#     one where we go through the wb states critical to the AE
#     and another where we go through wb states within an interval.
def grab_aes(relevant_aes, ae_programs, wb_data):

    # Track the recognized vicinal events
    #  Data is {wb_name: {time : event}}
    unconfirmed_vicinal_events = {}

    # Data is {ae_name : [(camera, composition, wb_coords) ... ]}
    search_ae_data = {}


    # Iterate backwards from last AE (by default this is already sorted in reverse)
    for ae_i, ae_event in enumerate(relevant_aes):

        # Get watchbox data for this atomic event
        current_event_name = ae_event[0]
        current_event_data = ae_event[1]
        ae_program_for_event = ae_programs[current_event_name][1]

        search_ae_data[current_event_name] = []

        #  Now, iterate through each watchbox state relevant to this AE
        for wb_event_i, wb_event in enumerate(current_event_data):

            # Get the time for this watchbox event
            wb_event_time = wb_event[0]
            wb_camera = wb_event[1]
            # Parse the AE to get some data
            wb_composition = parse_ae(ae_program_for_event, wb_event_i)
            # Get the watchbox coordinates for this event
            wb_coords = get_wb_coords(wb_data, current_event_data[wb_event_i])

            search_entry = (wb_camera, wb_composition, wb_coords)

            search_ae_data[current_event_name].append(search_entry)

            # THIS IS PART OF THE "MISSED CE CHECK"
            # NOTE - THIS IS  NOT NEEDED HERE...
            # Get the image for this watchbox and save it
            # img, objects = get_image_for_event(wb_event, video_dir, wb_data)
            # save_image("results/x.jpg", img)

            
            # By default, we add each wb event
            wb_name = wb_event[2]
            if wb_name not in unconfirmed_vicinal_events:
                unconfirmed_vicinal_events[wb_name] = {}
            unconfirmed_vicinal_events[wb_name][wb_event_time] = wb_event

        # Now update our upper and lower bound ae times
        # upper_bound_ae_time = relevant_ae_times[ae_i][1]
        # lower_bound_ae_time = 0 if ae_i==len(relevant_ae_times)-1 else relevant_ae_times[ae_i+1][1]
            
    # Now, update our the known vicinal events so that it is easier to index
    #  Basically, each list of times must be ordered in ascending order
    for wb_key in unconfirmed_vicinal_events.keys():
        # Order the keys
        sorted_times = sorted(list(unconfirmed_vicinal_events[wb_key].keys()))
        # Now sort the vicinal events under each watchbox
        unconfirmed_vicinal_events[wb_key] = [unconfirmed_vicinal_events[wb_key][x] for x in sorted_times]

    return unconfirmed_vicinal_events, search_ae_data


# 2nd part of verifying by vicinal events
def verify_aes(unconfirmed_vicinal_events, ce_obj, detected_time):

    events_to_verify = []

    ae_statuses = find_closest_aes(unconfirmed_vicinal_events, ce_obj, detected_time)
    
    print(ae_statuses)
    confirmed_vicinal_events = {}
    for status in ae_statuses:
        wb_queries = status[3]
        for wb_query in wb_queries:
            
            events_to_verify.append(wb_query)
            
            # img, comp = get_image_for_wb_state(wb_query, "data", ce_obj.watchboxes, class_mappings)
            
            # # Show image here...
            # save_image("results/x.jpg", img)

            # # Get user input here
            # # user_label = input()
            # # if user_label == "correct":
                
            # # Get the time and watchbox name
            # event_wb_name = wb_query[1][0]
            # event_time = wb_query[1][1]

            # # WE ALLOW THE USER TO CORRECT IT HERE, WHICH CHANGES THE WB_QUERY
            # #  And creates a new entry for additional sampling

            # confirmed_vicinal_events = match_and_add_ves(unconfirmed_vicinal_events, confirmed_vicinal_events,\
            #      event_wb_name, event_time)

    return events_to_verify
    # return confirmed_vicinal_events

# Type 2: verify vicinal events occurring within intervals
def verify_ve_intervals(ae_statuses, detected_time, \
        unconfirmed_vicinal_events, confirmed_vicinal_events):

    # For any ae_status which is missing, we check its upper and lower bound ae time
    missing_intervals = get_time_bounds(ae_statuses, detected_time)
    events_to_verify = []  # Format of (cam name, time, tracks)

    # Now, if the watchbox state at the time of the detected AE is incorrect,
    #  We have to establish which vicinal events are correct
    for interval in missing_intervals:
        time_intervals = interval[1]
        lower_bound_ae_time = time_intervals[0]
        upper_bound_ae_time = time_intervals[1]
        
        events_to_check = get_vicinal_events_within_time(lower_bound_ae_time, upper_bound_ae_time, unconfirmed_vicinal_events)
        # Iterate through each vicinal event and verify it
        for ve_i, vicinal_event in enumerate(events_to_check):

            events_to_verify.append(vicinal_event)

            # First, get the time, then the camera
            # ev_time = vicinal_event[0]["time"]
            # cam_str = "cam" + str(vicinal_event[0]["camera_id"])
            # wb_name = [y for y,x in wb_data.items() if x["watchbox_id"] \
            #         == vicinal_event[0]["results"][0]["watchboxes"][0]][0]

            # wb_event = (ev_time, cam_str, wb_name, vicinal_event[1])
            # Now, we can get the image for this vicinal event and save it
            # img, objects = get_image_for_event(vicinal_event, video_dir, wb_data)
            # # save_image("results/y.jpg", img)

            # wb_name = vicinal_event[2]
            # wb_time = vicinal_event[0]

            # # Every time we correct something, we need to redo the confirmed vicinal events
            # # Use the match and add ves...
            # confirmed_vicinal_events = match_and_add_ves(unconfirmed_vicinal_events, confirmed_vicinal_events,\
            #     wb_name, wb_time)
    
    # Now, get all the data for all the bboxes for the confirmed items and their tracks
    # track_data = get_tracking_info(confirmed_vicinal_events)
    # save_track_data_to_label(track_data, ae_files, video_dir)
    # save_relevant_track_images("data/training", video_dir, "da_confirmed.json")

    # return confirmed_vicinal_events
    return events_to_verify

#   Another for scrolling through a video
#     and naming the bounds, and a button for 'needs to be edited'
#       based on which events must still be annotated.
#    This is where we do part 2 and get the new ae statuses
#       if the CE still isn't satisfied, we move on.



#   Once the above two are finalized, we have a list of images to be annotated
#     and then we have the user annotate that list of images.
#      This basically generates two things:
#         - a list of confirmed events (which can be used for training)
#         - a list of user annotations (which are combined with track data)
#      This is we show part 3, at least for the intervals we missed.



# Remove redundant elements from list1 given list2
def remove_reundant_events(event_list1, event_list2):

    result_dict = {}
    # Iterate through every elements of eventlist1
    for wb_name in event_list1.keys():
        current_entry = event_list1[wb_name]
        # print(wb_name)
        # print(len(event_list1[wb_name]))
        for ve in current_entry:

            ve_matched = False
            # Check if the ve matches in event_list2
            if wb_name in event_list2.keys():
                event_list2_times = [x[0] for x in event_list2[wb_name]]
                if ve[0] in event_list2_times:
                    ve_matched = True
            if not ve_matched:  # No match, so add to our result dict
                if wb_name not in result_dict:
                    result_dict[wb_name] = [ve]
                else:
                    result_dict[wb_name].append(ve)
    
    # # Iterate through result_dict
    # for wb_name in result_dict.keys():
    #     print(wb_name)
    #     print(len(result_dict[wb_name]))
    return result_dict






# This reorganizes the ae search into a list of
#  (video_filepath, time_interval, watchbox, composition)
def reorganize_video_search(search_ae, missing_intervals, video_dir):

    video_segments_to_annotate = []

    # Iterate through each interval, and figure out what is missing
    for missing_data in missing_intervals:
        missing_aes = []
        for ae_list in missing_data[0]:
            missing_aes += ae_list
        interval = missing_data[1]

        # iterate through each missing ae
        for missing_ae in missing_aes:

            # Skip if it's a non-ae name (like 'and')
            if missing_ae not in search_ae.keys():
                continue

            # Otherwise, find all data for this ae
            data_for_ae = search_ae[missing_ae]
            # Iterate through each data segment
            for data_item in data_for_ae:
                cam_name = data_item[0]
                vfilepath = [x for x in os.listdir(video_dir) if ".mp4" in x]
                vfilepath = [x for x in vfilepath if cam_name in x][0]
                vfilepath = os.path.join(video_dir, vfilepath)

                comp = data_item[1]


                if "==0" in comp[2]:
                    continue  # SKip all 0 cases

                wb_bbox = data_item[2]

                annotation_tup = (vfilepath, interval, wb_bbox, comp)
                video_segments_to_annotate.append(annotation_tup)

    return video_segments_to_annotate




# We need to get our list of AEs and their times which they were detected.
def domain_adapt(result_path, ae_files, detected_time, video_dir, ce_obj, class_mappings):

   
    relevant_aes, ae_programs, wb_data = initialize_labelling_data(result_path, ae_files, detected_time)
    
    #  Get all vicinal events ordered by time
    # Remember - this returns a pair of 
    # [{'camera_id': X, 'results': [], 'time': X}, tracked objects]
    # ordered_vicinal_events = get_ordered_vicinal_events(ae_files)

    # # Check the later and previous AEs
    # upper_bound_ae_time = detected_time
    # lower_bound_ae_time = relevant_ae_times[0][1]

    ###########
    # PART 1: Break down AE information into a series of vicinal_events
    #   What this really does is load all the watchbox events into 
    #     unconfirmed_vicinal_events.
    ########### 
    unconfirmed_vicinal_events, search_ae = grab_aes(relevant_aes, ae_programs, wb_data)
    

    ######
    # PART 1.5: Decide which AEs still need to be confirmed.
    #   First, we decide which AEs have occurred based on the unconfirmed_vicinal_events
    #      Clearly, all of them will have, but we are going to go through and user verify them.
    #    Then, we will create a new variable, called confirmed_vicinal_events
    #      where we will store all the events which the user actually verified.
    ######

    # print(unconfirmed_vicinal_events)
    # print("\n\n")

    # Decide which AEs have been confirmed
    # confirmed_vicinal_events = verify_aes(unconfirmed_vicinal_events, ce_obj, detected_time)
    
   
    # confirmed_vicinal_events = {}
    # Check which AEs are missing
    # ae_statuses = find_closest_aes(confirmed_vicinal_events, ce_obj, detected_time)


    #########
    # PART 2: If any atomic event is missed, verify watchbox states of vicinal events
    #          for the times that we should be looking for (e.g. incorrect AEs)
    #########
    # confirmed_vicinal_events = verify_ve_intervals(ae_statuses, detected_time, \
    #     unconfirmed_vicinal_events, confirmed_vicinal_events)
    

    ##########
    # PART 3:  Now, based on the ae_statuses, figure out what intervals we still need
    #          to look at.
    ##########

    confirmed_vicinal_events = {}
    ae_statuses = find_closest_aes(confirmed_vicinal_events, ce_obj, detected_time)
    missing_intervals = get_time_bounds(ae_statuses, detected_time)

    segments_to_annotate = reorganize_video_search(search_ae, missing_intervals, video_dir)
    data = segments_to_annotate[0]
    object_comp = data[3]
    out_data = get_class_grouping(object_comp)
    print(out_data)
    asdf
    
    # Now, for every missing interval, request the user to look at that interval
    for interval in missing_intervals:
        print("Do something here...")
        # Also have a func for drawing bboxes
        #   and matching them to existing bboxes, which get attached to tracks.
        print(vicinal_event)
        # user_confirmed_bboxes.append()
        asdf

        # Basically allow the user to scroll through a video and click a button
        #  which save the images for later annotation.



if __name__=='__main__':

    result_path = "data/ce_output.txt"
    # AE FILES MUST BE SORTED IN ORDER OF CAM ID
    ae_files = ["data/ae_cam0.txt", "data/ae_cam1.txt", "data/ae_cam2.txt"]

    CE_detection_time = 18000
    video_dir = "data"

    # Open our config file
    # with open("../DistributedCE/detection/server_code/configs/local.json", "r") as f:
    #     server_config = json.load(f)
    # class_mappings = server_config["class_mappings"]
    class_mappings = {"rec_vehicle": 1, "tank": 0}

    # Get the CE we are interested in
    ce_obj, ce_structure = build_ce1(class_mappings)

    domain_adapt(result_path, ae_files, CE_detection_time, video_dir, ce_obj, class_mappings)






# Side note
#   - you may end up missing an intermediate wb state (e.g. wb@1, wb@2)