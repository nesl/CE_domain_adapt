
import os 

# Add ce annotation time to this
def obtain_metric_data(exp_path):

    metrics_path = os.path.join(exp_path, "time_metrics.json")
    metric_data = None
    with open(metrics_path, "r") as f:
        metric_data = eval(f.read())

    return metric_data



# Carla annotations - adapted and baseline
# train_dir = "/media/brianw/Elements/icra_data/carla_annotated/adapt"
# train_dir = "/media/brianw/Elements/icra_data/carla_annotated/baseline"
# train_dir = "annotated/soartech_annotated/adapt"

train_dir = "annotated/soartech_annotated/baseline"
train_dir = "annotated/soartech_annotated/adapt"
# train_dir = "annotated/carla_annotated/baseline"
# train_dir = "annotated/carla_annotated/adapt"


ce_total_times = []
num_required_annotations = []

annotate_time = []
review_time = []

# Go through each experimental folder
for exp_dir in os.listdir(train_dir):
    # Get the experimental dir path
    exp_dir_path = os.path.join(train_dir, exp_dir)

    metric_data = obtain_metric_data(exp_dir_path)  
    ce_total_times.append(metric_data["total_time"][0])
    if "annotate_time" in metric_data:
        num_required_annotations.append(len(metric_data["annotate_time"]))
        annotate_time.extend(metric_data["annotate_time"])
    if "review_time" in metric_data:
        review_time.extend(metric_data["review_time"])

# Calculate average metrics
ce_avg_time = sum(ce_total_times) / len(ce_total_times)
print(ce_avg_time)
avg_num_annotations = sum(num_required_annotations) / len(num_required_annotations)
print(avg_num_annotations)
avg_review_time = sum(review_time) / len(review_time)
avg_annotate_time = sum(annotate_time) / len(annotate_time)
print(avg_annotate_time)
print(annotate_time)
print(sorted(annotate_time))

