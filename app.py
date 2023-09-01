import flask
from werkzeug.middleware.proxy_fix import ProxyFix
import logging

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


# Example POST REST endpoint
@app.route('/test/', methods=['POST'])
def test():
    # Do something with query params
    info(flask.request.args.to_dict())

    # Do something with the body if it's json
    if flask.request.is_json:
        info(flask.request.json)

    return flask.jsonify(flask.request.args)
