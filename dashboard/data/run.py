# -*- encoding: utf-8 -*-
"""
License: Commercial
Copyright (c) 2019 - present AppSeed.us
"""

from app import create_app
import argparse

parser = argparse.ArgumentParser(description="Argument parser for Red Discord Bot Dashboard - Client")
parser.add_argument("--port", dest="port", type=int, default=42356)
parser.add_argument("--rpc-port", dest="rpcport", type=int, default=6133)

args = vars(parser.parse_args())

create_app("0.0.0.0", args['port'], args['rpcport'])