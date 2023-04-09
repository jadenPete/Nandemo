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

@app.route('/sign_up', methods=['GET','POST'])
def sign_up():
	if flask.request.method == 'POST':
		error = None
		if flask.request.form['password_check'] != flask.request.form['password']:
			error = "Password did not match"
			return flask.render_template("sign_up.html", error=error)
		elif get_db().create_user(flask.request.form['username'],flask.request.form['first_name'],flask.request.form['last_name'],flask.request.form['password'])==None:
			error = "Username is invalid, please choose another username."
		return flask.render_template('sign_up.html', error = error)
	else:
		return flask.render_template('sign_up.html')

@app.route('/', methods=['POST','GET'])
def index():
	if flask.request.method == 'POST':
		return flask.redirect('/sign_up')
	return flask.render_template('index.html')