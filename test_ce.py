from LanguageCE.ce_builder import sensor_event_stream, watchbox, \
    complexEvent, Event, OR, AND, GEN_PERMUTE, SEQUENCE_TIMED, SET_TIMED, HOLDS, SET, SEQUENCE
import time
import os
import cv2
import numpy as np

import json
import socket
import threading
# import argparse

import traceback

# data_file = open("complex_results.json", "r")
# json_results = json.load(data_file)
# data_file.close()

def get_data(frame_index):
    data = []
    
    for x in json_results:
        if x['time'] == frame_index:
            data.append(x)
    return data


# Send data - encode it 
def sendMessage(message, addr, sock):
    # Turn the message into bytes
    message = str(message).encode()
    print("sending to " + str(addr))
    sock.sendto(message, addr)



def build_ce1(class_mappings):
    # CE1
    # First, initialize our complex event
    ce1 = complexEvent(class_mappings)
    ce_structure = []
    # Set up our watchboxes
    ce1.addWatchbox(name="bridgewatchbox0", region_id='2', positions=[200,1,1919,1079], classes=['rec_vehicle'], watchbox_id=0)
    ce1.addWatchbox(name="bridgewatchbox1", region_id='2', positions=[213,274,772,772], classes=['rec_vehicle'], watchbox_id=1)
    ce1.addWatchbox(name="bridgewatchbox2", region_id='2', positions=[816,366,1200,725], classes=['rec_vehicle'], watchbox_id=2)
    ce1.addWatchbox(name="bridgewatchbox3", region_id='2', positions=[1294,290,1881,765], classes=['rec_vehicle'], watchbox_id=3)
    ce1.addWatchbox(name="bridgewatchbox4", region_id='1', positions=[413,474,1072,772], classes=['tank'], watchbox_id=0)
    ce1.addWatchbox(name="bridgewatchbox5", region_id='0', positions=[1,1,1919,1079], classes=['rec_vehicle'], watchbox_id=0)

    # Now we set up the atomic events

    # First, fource vehicles show up in camera 0
    vehicles_head_to_bridge = Event("bridgewatchbox5.composition(at=0, model='rec_vehicle').size==4 and bridgewatchbox5.composition(at=1, model='rec_vehicle').size!=4")

    # Next, four vehicles approach the bridge from one side
    vehicles_approach_bridge = Event("bridgewatchbox0.composition(at=0, model='rec_vehicle').size==4 and bridgewatchbox0.composition(at=1, model='rec_vehicle').size!=4")

    # Next, we have two vehicles on either side of the bridge
    vehicles_plant_bombs = Event( "bridgewatchbox1.composition(at=0, model='rec_vehicle').size==2 and bridgewatchbox3.composition(at=0, model='rec_vehicle').size==2" )

    # And we have more than 4 vehicles in cam2
    tanks_present = Event( "bridgewatchbox4.composition(at=0, model='tank').size>=4" )

    # Then we have two vehicles exit watchbox 3
    vehicles_leave = Event( "bridgewatchbox3.composition(at=1, model='rec_vehicle').size==2 and bridgewatchbox3.composition(at=0, model='rec_vehicle').size==0" )

    # head_then_approach = SET_TIMED(vehicles_head_to_bridge, vehicles_approach_bridge, 8000)
    # ev_holds = HOLDS(vehicles_head_to_bridge, 32)

    # And finally we add these events together
    # ce_structure = ce1.addEvents([SEQUENCE(vehicles_head_to_bridge, vehicles_approach_bridge), SEQUENCE(tanks_present, vehicles_plant_bombs, GEN_PERMUTE(vehicles_leave, "size"))])
    ce_structure = ce1.addEvents([vehicles_head_to_bridge, vehicles_approach_bridge, AND(tanks_present, vehicles_plant_bombs), GEN_PERMUTE(vehicles_leave, "size")])
    # ce_structure = ce1.addEvents([vehicles_approach_bridge, vehicles_plant_bombs, GEN_PERMUTE(vehicles_leave, "size")])

    return ce1, ce_structure

def build_ce2(class_mappings):

    ce2 = complexEvent(class_mappings)
    # Set up our watchboxes
    ce2.addWatchbox("bridgewatchbox0 = watchbox(camera_id='2', positions=[1,1,1919,1079], classes=['rec_vehicle'], watchbox_id=0)")
    ce2.addWatchbox("bridgewatchbox1 = watchbox(camera_id='2', positions=[213,274,772,772], classes=['rec_vehicle'], watchbox_id=1)")
    ce2.addWatchbox("bridgewatchbox2 = watchbox(camera_id='2', positions=[816,366,1200,725], classes=['rec_vehicle'], watchbox_id=2)")
    ce2.addWatchbox("bridgewatchbox3 = watchbox(camera_id='2', positions=[1294,290,1881,765], classes=['rec_vehicle'], watchbox_id=3)")
    ce2.addWatchbox("roadwatchbox1 = watchbox(camera_id='0', positions=[213,274,1750,765], classes=['rec_vehicle'], watchbox_id=0)")
    ce2.addWatchbox("roadwatchbox2 = watchbox(camera_id='1', positions=[1294,274,1881,765], classes=['tank'], watchbox_id=0)")

    # Now we set up the atomic events

    # First, four recce vehicles move in formation through camera1
    vehicle_move = Event("roadwatchbox1.composition(at=0, model='rec_vehicle').size==4 and roadwatchbox1.composition(at=1, model='rec_vehicle').size<4")

    # Then in camera3, four vehicles approach the bridge from one side
    vec_approach_bridge = Event("bridgewatchbox0.composition(at=0, model='rec_vehicle').size==4 and bridgewatchbox0.composition(at=1, model='rec_vehicle').size<4")

    # Next, we have two vehicles on either side of the bridge
    rec_on_either_side = Event("bridgewatchbox1.composition(at=0, model='rec_vehicle').size==2 and bridgewatchbox3.composition(at=0, model='rec_vehicle').size==2")

    # In camera2, observe tanks moving toward the bridge (e.g. entering wb then leaving)
    tanks_exit_bridge = Event("roadwatchbox2.composition(at=1, model='tank').size>0 and roadwatchbox2.composition(at=0, model='tank').size==0")

    # Either ev21 occurred first, then ev23 within X frames (3 minutes = 5400 frames), or the other way around
    rec_first = WITHIN(rec_on_either_side, tanks_exit_bridge, 5400)
    tank_first = WITHIN(tanks_exit_bridge, rec_on_either_side, 5400) 

    # And finally we add these events together
    #  In this case, we do not enforce a strict sequence, because tanks_exit_bridge can occur before or after rec_on_either_side
    #  We do however enforce the time constraint that one or the other occurs within a certain time
    ce_structure = ce2.addEventSequence([vehicle_move, vec_approach_bridge, rec_on_either_side, tanks_exit_bridge, OR(tank_first, rec_first)], no_enforce_sequence=True )

    return ce2, ce_structure


def build_ce3(class_mappings):

    ce3 = complexEvent(class_mappings)
    # Set up our watchboxes
    
    ce3.addWatchbox("rwatchbox1 = watchbox(camera_id='1', positions=[213,274,772,772], classes=['rec_vehicle'], watchbox_id=1)")
    ce3.addWatchbox("rwatchbox2 = watchbox(camera_id='1', positions=[750,366,1200,725], classes=['tank'], watchbox_id=2)")
    ce3.addWatchbox("rwatchbox3 = watchbox(camera_id='1', positions=[1210,290,1750,765], classes=['rec_vehicle'], watchbox_id=3)")
    # Need one watchbox object per type of object
    ce3.addWatchbox("rwatchbox0 = watchbox(camera_id='1', positions=[1,1,1919,1079], classes=['rec_vehicle', 'tank'], watchbox_id=0)")
    ce3.addWatchbox("r0watchbox0 = watchbox(camera_id='0', positions=[1,1,1919,1079], classes=['rec_vehicle', 'tank'], watchbox_id=0)")

    # 3.1 -  recce vehicles in opposite watchbox
    recce_in_opposite_wb = Event("rwatchbox1.composition(at=0, model='rec_vehicle').size==2 and rwatchbox3.composition(at=0, model='rec_vehicle').size==2")

    # 3.0 - recce vehicles and tanks present in camera, for either camera id 1 or camera id 0
    all_in_cam0 = Event("r0watchbox0.composition(at=0, model='rec_vehicle').size>=4 and r0watchbox0.composition(at=0, model='tank').size>=4")
    all_in_cam1 = Event("rwatchbox0.composition(at=0, model='rec_vehicle').size>=4 and rwatchbox0.composition(at=0, model='tank').size>=4")

    # 3.2 - tanks in middle watchbox.
    tank_in_middle = Event("rwatchbox2.composition(at=0, model='tank').size>=4")

    # The above events can occur in any order
    ce_structure = ce3.addEventSequence([recce_in_opposite_wb, tank_in_middle, OR(all_in_cam1, all_in_cam0)], no_enforce_sequence=True)

    return ce3, ce_structure


# import argparse


# parser = argparse.ArgumentParser(description='Edge Processing Node')
# parser.add_argument('--ce', type=int, help='Determines which CE we want to capture')
# parser.add_argument('--server_port', type=int, help='Determines which CE we want to capture')
# parser.add_argument('--result_dir', type=str, help='this is where we will output our json')
# # parser.add_argument('--debug_output', type=str, help='this is where we will output debug data')
# args = parser.parse_args()
# SERVER_ADDR = ("127.0.0.1", args.server_port)


# if __name__=='__main__':

#     try:
#         complexEventObj = None
#         ce_structure = []
#         if args.ce == 1:
#             complexEventObj, ce_structure = build_ce1()
        
#             complexEventObj.result_dir = args.result_dir
        
#             # Our bounding boxes are as follows:
#             watchboxes = {
#                 2: [ [1,1,1919,1079, 1], [213,274,772,772,1], [816,366,1200,725,1], [1294,290,1881,765,1]],
#                 1: [ [413,274,1072,772, 0] ],
#                 0: [ [1,1,1919,1079, 1] ]
#             }
#             complexEventObj.config_watchboxes = watchboxes

#         elif args.ce == 2:

#             complexEventObj, ce_structure =  build_ce2()
#             complexEventObj.result_dir = args.result_dir

#             watchboxes = {
#                 2: [ [1,1,1919,1079,1], [213,274,772,772,1], [816,366,1200,725,1], [1294,290,1881,765,1]],
#                 1: [ [1294,274,1881,765, 0] ],
#                 0: [ [1,1,1919,1079, 1] ]
#             }
#             complexEventObj.config_watchboxes = watchboxes

#         elif args.ce == 3:

#             complexEventObj, ce_structure =  build_ce3()
#             complexEventObj.result_dir = args.result_dir

#             # Our bounding boxes are as follows:
#             watchboxes = {
#                 1: [ [1,1,1919,1079, 0], [213,274,772,772,1], [750,366,1200,725,0], [1210,290,1750,765,1], [1,1,1919,1079,1] ],
#                 0: [ [1,1,1919,1079, 0], [1,1,1919,1079, 1] ]
#             }
#             complexEventObj.config_watchboxes = watchboxes
            


#     except Exception as e:
#         print(traceback.format_exc())
#         input()
    
    
#     # # Set up our server
#     server_listen_thread = threading.Thread(target=server_listen, \
#         args=(complexEventObj,ce_structure,))
#     server_listen_thread.start()

#     if incoming_data:
#         #### RUN OUR EVALUATION ON THE EVENT ANYTIME WE GET NEW DATA
#         ce1.update(incoming_data)

#         event_occurred, results = ce1.evaluate()
#         if event_occurred:

#             for result in results:
#                 print("Event %s has changed to %s at frame %d" %(result[0], str(result[1]), frame_index))

    
    