#!/usr/bin/env python

from db import Database, DatabaseMessage, DatabaseUser

import datetime
import dotenv
import flask
import flask_socketio
import functools
import os
import uuid

dotenv.load_dotenv()

app = flask.Flask(__name__)

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

socketio = flask_socketio.SocketIO(app, json=flask.json)

class CustomJSONProvider(flask.json.provider.DefaultJSONProvider):
	@staticmethod
	def default(obj):
		if isinstance(obj, DatabaseMessage):
			return {
				"id": obj.id,
				"chatID": obj.chat_id,
				"userID": obj.user_id,
				"content": obj.content,
				"timestamp": datetime.timedelta(
					hours=obj.timestamp.hour,
					minutes=obj.timestamp.minute,
					seconds=obj.timstamp.seconds
				).total_seconds()
			}

		return super().default(obj)

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

		return fn(*args, **kwargs)

	return wrapper

def get_db():
	if "db" not in flask.g:
		flask.g.db = Database()

	return flask.g.db

def get_socket_chat():
	chat_rooms = set(flask_socketio.rooms()) - {flask.request.sid}

	if len(chat_rooms) != 1:
		return

	return get_db().chat(next(iter(chat_rooms)))

def get_user():
	context = flask.session if "sid" in flask.session else flask.g

	if "user" not in context:
		# TODO: Replace this once Phillip and Raven finish writing their authentication code
		context.user = DatabaseUser(get_db(), "4f35714b-171e-45f9-bf2e-6a92cdfb6f72")

	return context.user

@app.route("/")
@authenticate_user
def index():
	return flask.render_template("index.html")

@app.route("/chats/<chat_id>/messages")
@authenticate_user
def chat_messages(chat_id):
	if (chat := get_db().chat(chat_id)) is None:
		flask.abort(404)

	return flask.jsonify(chat.messages())

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

@socketio.on("connect")
def on_connect(auth):
	if auth is None or not isinstance(chat_id := auth.get("chatID"), str):
		return False

	flask_socketio.join_room(chat_id)

@socketio.on("message")
def on_message(data):
	if isinstance(data, str):
		message = get_socket_chat().insert_message(get_user(), data, datetime.datetime.now())

		flask_socketio.emit("message_broadcast", message, json=True, to=get_socket_chat().id)
	else:
		flask_socketio.emit("error", "Please provide a string with your message.")

if __name__ == "__main__":
	socketio.run(app, debug=True)
