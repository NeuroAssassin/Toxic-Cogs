# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""
from redbot.core import data_manager
from flask import Flask, url_for, session
from flask_session import Session
from importlib import import_module
from os import path
from cryptography import fernet
from io import StringIO
import base64
import threading
import time
import websocket
import json
import sys

# In case the dashboard cog isn't loaded
global defaults
defaults = {
    'botname': 'Red Discord Bot',
    'botavatar': 'https://cdn.discordapp.com/icons/133049272517001216/a_aab012f3206eb514cac0432182e9e9ec.gif?size=1024',
    'botinfo': 'Hello, welcome to the Red Discord Bot dashboard!  Here you can see basic information, commands list and even interact with your bot!  Unfortunately, this dashboard is not connected to any bot currently, so none of these features are available.  If you are the owner of the bot, please load the dashboard cog from Toxic Cogs.',
    'owner': 'Cog Creators'
}

global running
running = True

global url
url = "ws://localhost:"

global app
app = None

def update_thread():
    def update_variables():
        global app
        ws = websocket.WebSocket()
        try:
            ws.connect(url)
        except ConnectionRefusedError:
            ws.close()
            return

        request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "DASHBOARDRPC__GET_VARIABLES",
            "params": []
        }
        try:
            ws.send(json.dumps(request))
        except ConnectionResetError:
            print("Connection reset")
            ws.close()
            return
            
        try:
            result = json.loads(ws.recv())
        except ConnectionResetError:
            print("Connection reset")
            ws.close()
            return
        if 'error' in result:
            if result['error']['code'] == -32601:
                app.variables = {}
                ws.close()
                return
            print(result['error'])
            ws.close()
            return
        if result['result'].get("disconnected", False):
            # Dashboard cog unloaded, disconnect
            app.variables = {}
            ws.close()
            return
        app.variables = result['result']
        app.variables["disconnected"] = False
        ws.close()

    while running:
        update_variables()
        time.sleep(5)

def register_blueprints(app):
    for module_name in ('base', 'home'):
        module = import_module('app.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)

def apply_themes(app):
    """
    Add support for themes.

    If DEFAULT_THEME is set then all calls to
      url_for('static', filename='')
      will modfify the url to include the theme name

    The theme parameter can be set directly in url_for as well:
      ex. url_for('static', filename='', theme='')

    If the file cannot be found in the /static/<theme>/ location then
      the url will not be modified and the file is expected to be
      in the default /static/ location
    """
    @app.context_processor
    def override_url_for():
        return dict(url_for=_generate_url_for_theme)

    def _generate_url_for_theme(endpoint, **values):
        if endpoint.endswith('static'):
            themename = values.get('theme', None) or \
                app.config.get('DEFAULT_THEME', None)
            if themename:
                theme_file = "{}/{}".format(themename, values.get('filename', ''))
                if path.isfile(path.join(app.static_folder, theme_file)):
                    values['filename'] = theme_file
        return url_for(endpoint, **values)

def add_constants(app):
    @app.context_processor
    def inject_variables():
        if not app.variables:
            return dict(**defaults)
        return dict(**app.variables)

def create_app(host, port, rpcport, instance, selenium=False):
    global url
    global app
    url += str(rpcport)
    
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)

    app = Flask(__name__, static_folder='base/static')
    app.variables = {}
    app.config.from_object(__name__)
    app.config['SESSION_TYPE'] = 'filesystem'
    app.secret_key = secret_key
    app.rpcport = rpcport

    # I cheat
    stdout = StringIO()
    sys.stdout = stdout

    try:
        data_manager.load_basic_configuration(instance)
    except (SystemExit, KeyError):
        sys.stdout = sys.__stdout__
        raise RuntimeError("Invalid instance name.  Please provide a correct one")
    finally:
        sys.stdout = sys.__stdout__
        del stdout

    p = data_manager.cog_data_path(raw_name="Dashboard")
    app.config['SESSION_FILE_DIR'] = str(p)
    
    Session(app)
    if selenium:
        app.config['LOGIN_DISABLED'] = True
    register_blueprints(app)
    apply_themes(app)
    add_constants(app)

    ut = threading.Thread(target=update_thread, daemon=True)
    ut.start()

    app.run(host=host, port=port)