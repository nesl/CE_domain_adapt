import os
import xml.etree.ElementTree as ET
import json
import shutil
from tqdm import tqdm

# def parse_xml(xml_path, class_mappings):
#     tree = ET.parse(xml_path)
#     root = tree.getroot()

#     annotation_data = []

#     # Get each object
#     for item in root.findall('object'):

#         class_id = item.find('name').text
#         class_id = class_mappings[class_id]

#         boundingboxinfo = item.find('bndbox')
#         x1 = boundingboxinfo.find('xmin').text
#         y1 = boundingboxinfo.find('ymin').text
#         x2 = boundingboxinfo.find('xmax').text
#         y2 = boundingboxinfo.find('ymax').text

#         current_entry = (class_id, int(x1), int(y1), int(x2), int(y2))
#         annotation_data.append(current_entry)
    

#     return annotation_data


def extract_info_from_xml(xml_file, ce_dir):
    root = ET.parse(xml_file).getroot()
    
    # Initialise the info dict 
    info_dict = {}
    info_dict['bboxes'] = []

    # Parse the XML Tree
    for elem in root:
        # Get the file name 
        if elem.tag == "filename":
            info_dict['filename'] = ce_dir + "_" + elem.text
            
        # Get the image size
        elif elem.tag == "size":
            image_size = []
            for subelem in elem:
                image_size.append(int(subelem.text))
            
            info_dict['image_size'] = tuple(image_size)
        
        # Get details of the bounding box 
        elif elem.tag == "object":
            bbox = {}
            for subelem in elem:
                if subelem.tag == "name":
                    bbox["class"] = subelem.text
                    
                elif subelem.tag == "bndbox":
                    for subsubelem in subelem:
                        bbox[subsubelem.tag] = int(subsubelem.text)            
            info_dict['bboxes'].append(bbox)
    
    return info_dict


def convert_to_yolov5(info_dict, class_name_to_id_mapping, dataset_dir):
    print_buffer = []
    
    # For each bounding box
    for b in info_dict["bboxes"]:
        try:
            class_id = class_name_to_id_mapping[b["class"]]
        except KeyError:
            print("Invalid Class. Must be one from ", class_name_to_id_mapping.keys())
        
        # Transform the bbox co-ordinates as per the format required by YOLO v5
        b_center_x = (b["xmin"] + b["xmax"]) / 2 
        b_center_y = (b["ymin"] + b["ymax"]) / 2
        b_width    = (b["xmax"] - b["xmin"])
        b_height   = (b["ymax"] - b["ymin"])
        
        # Normalise the co-ordinates by the dimensions of the image
        image_w, image_h, image_c = info_dict["image_size"]  
        b_center_x /= image_w 
        b_center_y /= image_h 
        b_width    /= image_w 
        b_height   /= image_h 
        
        #Write the bbox details to the file 
        print_buffer.append("{} {:.3f} {:.3f} {:.3f} {:.3f}".format(class_id, b_center_x, b_center_y, b_width, b_height))
        
    # Name of the file which we have to save 
    save_file_name = os.path.join(dataset_dir, info_dict["filename"].replace("jpg", "txt"))
    
    # Save the annotation to disk
    print("\n".join(print_buffer), file= open(save_file_name, "w"))



# Go through an experimental folder, and get all the data we need
def obtain_training_data(exp_dir_path, class_mappings, dataset_dir, exp_dir):
    # List all the files and images which have annotations
    annotation_names = [x for x in os.listdir(exp_dir_path) if ".xml" in x]
    annotation_names = [x.split(".xml")[0] for x in annotation_names]

    
    # Make an images and labels directory
    dataset_img_dir = os.path.join(dataset_dir, "images")
    if not os.path.exists(dataset_img_dir):
        os.mkdir(dataset_img_dir)
    dataset_txt_dir = os.path.join(dataset_dir, "labels")
    if not os.path.exists(dataset_txt_dir):
        os.mkdir(dataset_txt_dir)

    
    # Now, iterate through each annotation, and parse the xml
    for annotation_name in tqdm(annotation_names):
        # Get the xml path
        xml_path = os.path.join(exp_dir_path, annotation_name + ".xml")
        # Get the image path
        img_path = os.path.join(exp_dir_path, annotation_name + ".jpg")
        
        xml_data = extract_info_from_xml(xml_path, exp_dir)
        convert_to_yolov5(xml_data, class_mappings, dataset_txt_dir)

        # Move the image to the dataset dir as well
        img_name = exp_dir + "_" + annotation_name + ".jpg"
        destination_imgpath = os.path.join(dataset_img_dir, img_name)
        shutil.copyfile(img_path, destination_imgpath)




# Locate where our annotations are

# Carla annotations - adapted and baseline
ce_type = "soartech"
# train_dir = "/media/brianw/Elements/icra_data/carla_annotated/adapt"
# train_dir = "/media/brianw/Elements/icra_data/carla_annotated/baseline"
# train_dir = "annotated/soartech_annotated/adapt"
train_dir = "annotated/soartech_annotated/baseline"

import argparse

config_file = "configs/local_soartech.json"
dataset_dir = "datasets/soartech"
if ce_type == "carla":
    config_file = "configs/local_carla.json"
    dataset_dir = "datasets/carla"

# Make dataset dir
if not os.path.exists(dataset_dir):
    os.mkdir(dataset_dir)

with open(config_file, "r") as f:
    config = json.load(f)
class_mappings = config["class_mappings"]

# Go through each experimental folder
for exp_dir in os.listdir(train_dir):
    # Get the experimental dir path
    exp_dir_path = os.path.join(train_dir, exp_dir)

    obtain_training_data(exp_dir_path, class_mappings, dataset_dir, exp_dir)
    # print(exp_dir_path)
    # asdf