"""
Copyright (c) 2020 Ryan Krueger. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Ryan Krueger, Jesse Michael Han, Daniel Selsam
"""

from flask import Flask

app = Flask(__name__)

from app import routes
