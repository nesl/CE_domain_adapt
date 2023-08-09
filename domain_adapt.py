import os
from utils import get_image_for_frame_index, get_video_and_data, list_detected_events, \
    read_next_image, get_wb_coords, parse_ae, add_wb_to_video, \
    get_image_for_event, save_image, get_ordered_vicinal_events


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
def get_vicinal_events_within_time(lower_bound, upper_bound, ordered_vicinal_events):
    
    vicinal_events_within_range = []
    # Iterate through the list of events
    for vicinal_event in ordered_vicinal_events:
        
        event_time = vicinal_event[0]["time"]
        if lower_bound < event_time and event_time < upper_bound:
            vicinal_events_within_range.append(vicinal_event)

    return vicinal_events_within_range


    


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



# We need to get our list of AEs and their times which they were detected.
def domain_adapt(result_path, ae_files, detected_time, video_dir):

    # Get the events
    events_to_check, ae_programs, wb_data = list_detected_events(result_path, ae_files)

    # Get relevant AEs based on the detection time
    relevant_aes, relevant_ae_times = get_ordered_relevant_detected_aes(events_to_check, detected_time)

    # Get all vicinal events ordered by time
    # Remember - this returns a pair of 
    # [{'camera_id': X, 'results': [], 'time': X}, tracked objects]
    ordered_vicinal_events = get_ordered_vicinal_events(ae_files)

    # Check the later and previous AEs
    upper_bound_ae_time = detected_time
    lower_bound_ae_time = relevant_ae_times[0][1]


    # Need some variable for tracking the events which were correctly detected
    # And the times they were detected
    #  List of (ae_name, time)
    known_aes = []

    ###########
    # PART 1: Check if the atomic event was recognized properly
    ########### 

    # Iterate backwards from last AE (by default this is already sorted in reverse)
    for ae_i, ae_event in enumerate(relevant_aes):

        # Get watchbox data for this atomic event
        current_event_name = ae_event[0]
        current_event_data = ae_event[1]
        ae_program_for_event = ae_programs[current_event_name][1]

        # print(current_event_name)
        # print(upper_bound_ae_time)
        # print(lower_bound_ae_time)


        
        #  Now, iterate through each watchbox state relevant to this AE
        for wb_event_i, wb_event in enumerate(current_event_data):



            # Get the time for this watchbox event
            wb_event_time = wb_event[0]
            # Parse the AE to get some data
            wb_composition = parse_ae(ae_program_for_event, wb_event_i)
            # Get the watchbox coordinates for this event
            wb_coords = get_wb_coords(wb_data, current_event_data[wb_event_i])


            # THIS IS PART OF THE "MISSED CE CHECK"
            # Get the image for this watchbox and save it
            img, objects = get_image_for_event(wb_event, video_dir, wb_data)
            save_image("results/x.jpg", img)


        # Save this ae to our known AEs
        known_aes.append((current_event_name, relevant_ae_times[ae_i]))

        # Now update our upper and lower bound ae times
        upper_bound_ae_time = relevant_ae_times[ae_i][1]
        lower_bound_ae_time = 0 if ae_i==len(relevant_ae_times)-1 else relevant_ae_times[ae_i+1][1]
            



    ######
    # PART 1.5: Decide which AEs still need to be confirmed.
    #   This also includes AEs which did not occur on time
    ######


    print(known_aes)
    asdf


    #########
    # PART 2: If any atomic event is missed, verify watchbox states of vicinal events
    #          for the times that we should be looking for (e.g. incorrect AEs)
    #########

    # Now, if the watchbox state at the time of the detected AE is incorrect,
    #  We have to establish which vicinal events are correct
    events_to_check = get_vicinal_events_within_time(lower_bound_ae_time, upper_bound_ae_time, ordered_vicinal_events)
    # Iterate through each vicinal event and verify it
    for ve_i, vicinal_event in enumerate(events_to_check):

        # First, get the time, then the camera
        ev_time = vicinal_event[0]["time"]
        cam_str = "cam" + str(vicinal_event[0]["camera_id"])
        wb_name = [y for y,x in wb_data.items() if x["watchbox_id"] \
                == vicinal_event[0]["results"][0]["watchboxes"][0]][0]

        wb_event = (ev_time, cam_str, wb_name, vicinal_event[1])

        # Now, we can get the image for this vicinal event and save it
        img, objects = get_image_for_event(wb_event, video_dir, wb_data)



    # Things we still have to do:
    #   - Figure out how to 'confirm' an atomic event
    #   - Evaluate a 'confirmed' atomic event
    #   - Move on to the next atomic event
    
        


        

    # print(events_to_check)
    # print(events_to_check[-1])
    # event_of_interest = events_to_check[-1][0]
    # print(ae_data[event_of_interest])



result_path = "data/ce_output.txt"
# AE FILES MUST BE SORTED IN ORDER OF CAM ID
ae_files = ["data/ae_cam0.txt", "data/ae_cam1.txt", "data/ae_cam2.txt"]

CE_detection_time = 18000
video_dir = "data"

domain_adapt(result_path, ae_files, CE_detection_time, video_dir)

