import flask
import logging

from werkzeug.middleware.proxy_fix import ProxyFix
from pathlib import Path
from orchestration_logic.LidFlow import LidFlow
from orchestration_logic.orchestration_crate import Orchestration_crate
from orchestration_logic.orchestration_types import OrchestrationData
from globus_sdk import LocalGlobusConnectPersonal
from flow_config import *

from apply_template import apply_template


app = flask.Flask(__name__)
# IMPORTANT: the commented code below is required if we're running behind a proxy (e.g.: nginx) - it should not be
# uncommented otherwise
# app.wsgi_app = ProxyFix(
#     app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
# )


# Tie in gunicorn logger
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_logger.handlers)
app.logger.setLevel(logging.INFO)
info = app.logger.info


@app.route('/')
def index():
    return flask.render_template('index.html', title='Title', text='This is the home page')


# Serve static files - this is only for development, nginx will serve these in production
@app.route('/static/<path:filespec>')
def static_files(filespec):
    return flask.send_from_directory('static', filespec)

@app.route('/static/favicon/<path:filespec>')
def static_favicon(filespec):
    return flask.send_from_directory('static/favicon', filespec)


# Example POST REST endpoint
@app.route('/LiD/', methods=['POST'])
def execute_LiD_flow():

    # Grab endpoint details for transfers
    local_gcp = LocalGlobusConnectPersonal()
    ep_id = local_gcp.endpoint_id

    # Using locally defined config, could be passed in as a parameter in json body
    config = {
        "endpoints": endpoints,
        "data_paths": data_paths,
        "intermediate_paths": intermediate_paths,
        "LP_configuration": LP_configuration,
        "run_label": run_label,
        "run_tags": run_tags
    }
    # Edit config to include dymamic gcp endpoint
    config["LP_configuration"]["orchestration_node"] = ep_id

    # Execute the gladier flow
    lid_flow = LidFlow(endpoints=endpoints, 
                       data_paths=data_paths, 
                       intermediate_paths=intermediate_paths, 
                       LP_configuration=LP_configuration, 
                       run_label=run_label, 
                       run_tags=run_tags)
    lid_flow.run()
    lid_flow.monitor_run()
    lid_flow.monitor_transfer()
    orchestration_data: OrchestrationData = lid_flow.get_data()
    orchestration_crate = Orchestration_crate(lid_flow, 
                                              orchestration_data, 
                                              (Path.cwd() / "orchestration_crate"), 
                                              config['run_label'], 
                                              config['run_tags'])
    orchestration_crate.build_crate()
    orchestration_crate.clean_up()

    apply_template("generated_versions/LiD/")

    # Serialize orchestration data for testing
    # lid_flow.serrialize_data() # Serialize orchestration data for testing
    # oCrate = Orchestration_crate(None, None, (Path.cwd() / "working_crate"), run_label, run_tags, True)
    # oCrate.deserialize_data() # Using local data for testing
    # oCrate.build_crate()
    # oCrate.create_publication() # Not working or tested

    # Do something with query params
    # info(flask.request.args.to_dict())

    # Do something with the body if it's json






    if flask.request.is_json:
        info(flask.request.json)

    return flask.jsonify(flask.request.args)
