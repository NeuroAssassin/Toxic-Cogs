# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""
from app import app
from app.home import blueprint
from flask import render_template, redirect, url_for, session, request, jsonify
from jinja2 import TemplateNotFound
import websocket
import json

@blueprint.route('/index')
def index():
    
    #if not current_user.is_authenticated:
    #    return redirect(url_for('base_blueprint.login'))
    return render_template('index.html')

@blueprint.route('/commands')
def commands():
    if not session.get("id"):
        return redirect(url_for('base_blueprint.login'))
    
    data = app.commanddata
    prefix = app.variables.get("prefix", ["[p]"])

    return render_template("commands.html", cogs=[k['name'] for k in data], data=data, prefixes=prefix)

@blueprint.route('/credits')
def credits():
    try:
        return render_template("credits.html")
    except TemplateNotFound:
        return render_template('page-404.html'), 404

@blueprint.route('/changetheme', methods=['POST'])
def changetheme():
    obj = request.json
    if "iswhite" in obj:
        session['iswhitetheme'] = obj['iswhite']
    if "sidebarcolor" in obj:
        session['sidebarcolor'] = obj['sidebarcolor']
    return jsonify({"success": True})

@blueprint.route('/gettheme', methods=['GET'])
def gettheme():
    return jsonify({"iswhitetheme": session.get('iswhitetheme', False), "sidebarcolor": session.get('sidebarcolor', 'primary')})

@blueprint.route('/<template>')
def route_template(template):

    if not session.get("id"):
        return redirect(url_for('base_blueprint.login'))

    try:

        return render_template(template + '.html')

    except TemplateNotFound:
        return render_template('page-404.html'), 404
    
    except:
        return render_template('page-500.html'), 500
