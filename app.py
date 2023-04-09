#!/usr/bin/env python

from flask import Flask, render_template, url_for, request, session

from db import Database, DatabaseMessage, DatabaseUser

import datetime
import dotenv
import flask
import flask_socketio
import functools
import os
import uuid

dotenv.load_dotenv()

app = Flask(__name__)

def generate_secret_key():
	secret_key_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "secret_key.txt")

	if not os.path.exists(secret_key_path):
		secret_key = str(uuid.uuid4())

		with open(secret_key_path, "w") as file:
			file.write(f"{secret_key}\n")
	else:
		with open(secret_key_path) as file:
			secret_key = file.read().rstrip("\n")

	app.config["SECRET_KEY"] = secret_key

generate_secret_key()

socketio = flask_socketio.SocketIO(app)

def authenticate_user(fn):
	@functools.wraps(fn)
	def wrapper(*args, **kwargs):
		if get_user() is None:
			flask.abort(401)

		return fn(*args, **kwargs)

	return wrapper

def authorize_socket_user(fn):
	@functools.wraps(fn)
	def wrapper(*args, **kwargs):
		if \
			get_user() is None or \
			(chat := get_socket_chat()) is None or not get_user().voted_for(chat):
			flask_socketio.disconnect()
		else:
			return fn(*args, **kwargs)

	return wrapper

def get_db():
	if "db" not in flask.g:
		flask.g.db = Database()

	return flask.g.db

def get_socket_chat():
	print(flask_socketio.rooms())
	chat_rooms = set(flask_socketio.rooms()) - {flask.request.sid}

	if len(chat_rooms) != 1:
		return

	return get_db().chat(next(iter(chat_rooms)))

def get_user():
	if "user" not in flask.g:
		if "user_id" not in flask.session:
			return

		flask.g.user = DatabaseUser(get_db(), flask.session["user_id"])

	return flask.g.user

@app.route("/")
def index():
	if get_user() is None:
		return flask.redirect(url_for("login"))
	else:
		return flask.render_template("index.html")

@app.route("/chats/<chat_id>/messages")
@authenticate_user
def chat_messages(chat_id):
	if (chat := get_db().chat(chat_id)) is None:
		flask.abort(404)

	return flask.jsonify([message.to_json() for message in chat.messages()])

@app.route("/users/me")
@authenticate_user
def my_user():
	return flask.jsonify(get_user().to_json())

@app.route('/login', methods=['GET','POST'])
def login():
	if flask.request.method == 'POST':
		error = None
		if get_db().user_by_username(flask.request.form['username']) == None:
			error = "User not found"
			return render_template('login.html', error=error)
		elif get_db().user_by_username(flask.request.form['username']).verify_password(flask.request.form['password']) == False:
			error = "Password is invalid"
			return render_template('login.html', error=error)
		else:
			user = flask.request.form['username']
			session["user_id"] = get_db().user_by_username(user).id
			return flask.redirect(url_for("index"))
	return flask.render_template("login.html")

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
			user = flask.request.form['username']
			session["user_id"] = get_db().user_by_username(user).id
			return flask.redirect(url_for("index"))
	else:
		return flask.render_template("sign_up.html")

@socketio.on("connect")
def on_connect(auth):
	if auth is None or not isinstance(chat_id := auth.get("chatID"), str):
		return False

	flask_socketio.join_room(chat_id)

@socketio.on("message")
@authorize_socket_user
def on_message(data):
	if isinstance(data, str):
		message = get_socket_chat().insert_message(get_user(), data, datetime.datetime.now())

		flask_socketio.emit("message_broadcast", message.to_json(), json=True, to=get_socket_chat().id)
	else:
		flask_socketio.emit("error", "Please provide a string with your message.")

@app.route("/chats", methods=["GET"])
def chats():
	return '[{"id":"1","name":"Hackathon", "votes": "22", "open": "false", "openDay": "MON 3-5pm"},{"id":"2","name":"Art orgy", "votes": "124", "open": "t", "openDay": "SAT 9pm-12am"},{"id":"3","name":"Engineering stuff", "votes": "21", "open": "t", "openDay": "TUE 1-3pm"}]'

@app.route("/chats/<id>", methods=["GET"])
def chat(id):
	print(id)
	if id == "1":
		return '{"id":"1","name":"Hackathon", "votes": "22", "open": "f", "openDay": "MON 3-5pm"}'
	if id == "2":
		return '{"id":"2","name":"Art orgy", "votes": "124", "open": "t", "openDay": "SAT 9pm-12am"}'
	return '{"id":"3","name":"Engineering stuff", "votes": "21", "open": "t", "openDay": "TUE 1-3pm"}'

if __name__ == "__main__":
	socketio.run(app, debug=True)
