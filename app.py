#!/usr/bin/env python

from .db import Database
import dotenv
import flask

dotenv.load_dotenv()

app = flask.Flask(__name__)

def get_db():
	if "db" not in flask.g:
		flask.g.db = Database()

	return flask.g.db

@app.route("/")
def index():
	return flask.render_template("index.html")
