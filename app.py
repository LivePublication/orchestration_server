import contextlib
import datetime
import subprocess
from os import path

import numpy as np
import flask
import logging

import requests
from bs4 import BeautifulSoup
from celery import shared_task, current_task, Task
from celery.result import AsyncResult
import celery.signals
from markupsafe import Markup, escape
from werkzeug.middleware.proxy_fix import ProxyFix
from pathlib import Path

from celeryapp.celeryapp import celery_init_app
from orchestration_logic.LidFlow import LidFlow
from orchestration_logic.orchestration_crate import Orchestration_crate
from orchestration_logic.orchestration_types import OrchestrationData
from globus_sdk import LocalGlobusConnectPersonal
from flow_config import *

from apply_template import apply_template


app = flask.Flask(__name__)
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)
app.config.from_mapping(
    CELERY=dict(
        broker_url="redis://localhost",
        result_backend="redis://localhost",
        task_ignore_result=True,
    ),
)
celery_app = celery_init_app(app)

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


@app.route('/start_flow', methods=['POST'])
def start_flow():
    # Check there's not already a task running (for now)
    tasks = requests.get('http://localhost:5555/api/tasks').json()
    started_tasks = [k for k, v in tasks.items() if v['state'] in ['PENDING', 'RECEIVED', 'STARTED']]

    if len(started_tasks):
        info(f'Already started task {started_tasks[0]}')
        return flask.jsonify({
            'status': 'Already started',
            'task_id': started_tasks[0]
        })
    else:
        result = run_flow.delay()
        info(f'Started task {result.id}')
        return flask.jsonify({
            'status': 'Task started',
            'task_id': result.id
        })


@app.route('/flow_status/<id>', methods=['GET'])
def flow_status(id: str):
    # result = AsyncResult(id)

    # Retrieve task state from flower API
    status = requests.get(f'http://localhost:5555/api/task/info/{id}').json()
    submit_time = datetime.datetime.fromtimestamp(status['received'])
    # start_time = datetime.datetime.fromtimestamp(status['started'])
    # This is probably the most recent update - only valid if the task has finished/errored
    end_time = datetime.datetime.fromtimestamp(status['timestamp'])

    # Elapsed time (complete vs. in progress)
    if status['state'] in ['SUCCESS', 'FAILURE', 'REVOKED']:
        elapsed_time = datetime.datetime.now() - end_time
    else:
        elapsed_time = datetime.datetime.now() - submit_time

    # Return state
    return flask.jsonify({
        'status': status['state'],
        'start_time': submit_time.strftime('%X %x'),
        'time_elapsed': str(elapsed_time),
    })


@shared_task(ignore_result=True)
def run_flow():
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
                       run_tags=run_tags)  # Create flow object. Note: The LidFlow class will be abstracted to somthing more generic in the future
    lid_flow.run()                         # Run flow, authenticate with globus
    lid_flow.monitor_run()                 # Wait untill Globus reports the flow as complete
    lid_flow.monitor_transfer()            # Wait untill LPAP transfers to orchestration server are complete
    orchestration_data: OrchestrationData = lid_flow.get_data()  # Create the orchestration data object, contains all data we need to build the orchestration crate
    orchestration_crate = Orchestration_crate(lid_flow,
                                              orchestration_data,
                                              (Path.cwd() / "orchestration_crate"),
                                              config['run_label'],
                                              config['run_tags'])   # Create orchestration crate object
    orchestration_crate.build_crate()      # Finally, build the orchestration crate
    orchestration_crate.clean_up()         # Remove local temp directories and files

    apply_template("generated_versions/LiD/" + config['run_label'] + "/") # Very simple 'applciation' of quarto template to the orchestration crate


@app.route('/render/<id>/', methods=['GET'])
def render_paper(id):
    try:
        # TODO: hard coded repo for now
        folder = 'generated_versions/LiD/V1'
        if not path.isdir(folder):
            info(f'Folder {folder} does not exist')
            raise FileNotFoundError(f'Folder {folder} does not exist')

        # Run quarto
        index_file = path.join(folder, 'index.qmd')
        if not path.isfile(index_file):
            info(f'No index.qmd file in {folder}')
            raise FileNotFoundError(f'No index.qmd file in {folder}')

        render_file = path.join(folder, 'paper_render.html')

        with contextlib.chdir(folder):
            info(f'Rendering {index_file} to {render_file}')
            subprocess.check_call(['quarto', 'render', path.basename(index_file),
                                   '--to', 'html', '--output', path.basename(render_file),
                                   '--execute'])

        # Wrap html in layout
        with open(render_file, 'r', encoding='utf-8') as f:
            html = f.read()

        soup = BeautifulSoup(html, 'html.parser')

        head = ''.join(str(c) for c in soup.head.contents)
        header = ''.join(str(c) for c in soup.header.contents)
        body = soup.find(id='quarto-content')

        return flask.render_template('quarto_paper.html',
                               title='Live Publications',
                               head=Markup(head),
                               header=Markup(header),
                               content=Markup(body),)
    except FileNotFoundError as e:
        logging.error(e)
        flask.abort(404)


@app.route('/render/<id>/<path:filespec>')
def paper_files(id, filespec):
    """Serve files (libraries and artefacts) from a paper"""
    _filespec = escape(filespec)

    try:
        # TODO: hardcoded for now
        repo_dir = 'generated_versions/LiD/V1'

        return flask.send_from_directory(repo_dir, _filespec)
    except FileNotFoundError:
        flask.abort(404)


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
                       run_tags=run_tags)  # Create flow object. Note: The LidFlow class will be abstracted to somthing more generic in the future
    lid_flow.run()                         # Run flow, authenticate with globus
    lid_flow.monitor_run()                 # Wait untill Globus reports the flow as complete
    lid_flow.monitor_transfer()            # Wait untill LPAP transfers to orchestration server are complete
    orchestration_data: OrchestrationData = lid_flow.get_data()  # Create the orchestration data object, contains all data we need to build the orchestration crate
    orchestration_crate = Orchestration_crate(lid_flow, 
                                              orchestration_data, 
                                              (Path.cwd() / "orchestration_crate"), 
                                              config['run_label'], 
                                              config['run_tags'])   # Create orchestration crate object
    orchestration_crate.build_crate()      # Finally, build the orchestration crate
    orchestration_crate.clean_up()         # Remove local temp directories and files

    apply_template("generated_versions/LiD/" + config['run_label'] + "/") # Very simple 'applciation' of quarto template to the orchestration crate

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
