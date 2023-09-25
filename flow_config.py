from pathlib import Path

# Configuration for LidFlow as top level attributes (we could easily move this to a config file)
# Customizable attributes for re-execution by readers? # TODO
endpoints = {
    "FT_UUID": "5612672e-1ead-11ee-abf1-63e0d97254cd",
    "ST_UUID": "105a24f4-2a94-11ee-8801-056a4e394379",
    "LD_UUID": "21968ff8-29c4-11ee-87ff-056a4e394379",
    "DS_UUID": "d6215ec8-244a-11ee-80c1-a3018385fcef"
}

# Data paths for the actual test and validation data
data_paths = {
    "validation_path": "/home/ubuntu/LiD_Datastore/validation.txt",
    "data_path": "/home/ubuntu/LiD_Datastore/input_data.txt"
}

# Intermediate paths for data transfer between LPAPs
intermediate_paths = {
    "validation_dest_path": "/home/ubuntu/statistics_lpap/input/validation.txt",
    "DS_FT_dest": "/home/ubuntu/fastText_lpap/input/input_data.txt",
    "DS_LD_dest": "/home/ubuntu/langdetect_lpap/input/input_data.txt",
    "FT_ST_dest": "/home/ubuntu/statistics_lpap/input/fastText_predictions.txt",
    "LD_ST_dest": "/home/ubuntu/statistics_lpap/input/langdetect_predictions.txt",
    "FT_output_path": "/home/ubuntu/fastText_lpap/output/fastText_predictions.txt",
    "LD_output_path": "/home/ubuntu/langdetect_lpap/output/langdetect_predictions.txt"
}

# LivePub name/subcrate path & orchestration node UUID
# TODO change article_name to subcrate_path -> will need to change in LPAPs 
LP_configuration = {
    "orchestration_node": "None",
    "article_name": f"{Path.cwd()}/sub_crates"
}

# Run label and tags for the flow
run_label = "LiDFlow run"
run_tags = ["LID", "Orchestration", "Test"]