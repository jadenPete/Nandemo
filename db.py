import argon2
import dataclasses
import datetime
import os
import psycopg2
import uuid

class Database:
	def __init__(self):
		self.conn = psycopg2.connect(
			f"dbname={os.environ['DB_NAME']} user={os.environ['DB_USER']} password={os.environ['DB_PASSWORD']}"
		)

		self.conn.autocommit = True

		self.cur = self.conn.cursor()
		self.cur.execute(
			"""
CREATE TABLE IF NOT EXISTS users (
	id UUID PRIMARY KEY,
	username TEXT NOT NULL UNIQUE,
	first_name TEXT NOT NULL,
	last_name TEXT NOT NULL,
	password TEXT NOT NULL
);"""
		)

		self.cur.execute(
			"""
CREATE TABLE IF NOT EXISTS chats (
	id UUID PRIMARY KEY,
	name TEXT NOT NULL,
	meeting_time TIME WITH TIME ZONE NOT NULL,
	proposer_user_id UUID NOT NULL REFERENCES users(id)
);"""
		)

		self.cur.execute(
			"""
CREATE TABLE IF NOT EXISTS messages (
	id UUID PRIMARY KEY,
	chat_id UUID NOT NULL REFERENCES chats(id),
	user_id UUID NOT NULL REFERENCES users(id),
	content TEXT NOT NULL,
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL
);"""
		)

		self.cur.execute(
			"""
CREATE TABLE IF NOT EXISTS votes (
	user_id UUID NOT NULL REFERENCES users(id),
	chat_id UUID NOT NULL REFERENCES chats(id),
	PRIMARY KEY (user_id, chat_id)
);"""
		)

		self.password_hasher = argon2.PasswordHasher()

	@staticmethod
	def generate_uuid():
		return str(uuid.uuid4())

	def chat(self, id_):
		""" Retrieves a chat by its ID, returning its corresponding DatabaseChat object. """

		self.cur.execute("SELECT FROM chats WHERE id = %s;", (id_,))

		if self.cur.rowcount > 0:
			return DatabaseChat(self, id_)

	def create_user(self, username, first_name, last_name, password):
		""" Attempts to create a user.

		If a user already exists with the provided username, returns None.
		Otherwise, returns the newly created DatabaseUser instance.
		 """

		try:
			id_ = self.__class__.generate_uuid()
			hashed = self.password_hasher.hash(password)

			self.cur.execute(
				"INSERT INTO users VALUES (%s, %s, %s, %s, %s)",
				(id_, username, first_name, last_name, hashed)
			)
		except psycopg2.errors.UniqueViolation:
			return

		return DatabaseUser(self, id_)

	def ordered_chats(self):
		"""
		Returns a list of chats' corresponding DatabaseChat objects sorted by descending vote count.
		"""

		self.cur.execute(
			"""
SELECT id
FROM chats
LEFT JOIN votes ON chat_id = id
GROUP BY id
ORDER BY COUNT(user_id) DESC;"""
		)

		return [DatabaseChat(self, row[0]) for row in self.cur.fetchall()]

	def user_by_username(self, username):
		""" Retrieves a user by their username.

		Returns a corresponding DatabaseUser object if the user was found.
		Otherwise, returns None.
		"""

		self.cur.execute("SELECT id FROM users WHERE username = %s;", (username,))

		if self.cur.rowcount > 0:
			return DatabaseUser(self, self.cur.fetchone()[0])

class DatabaseChat:
	def __init__(self, db, id_):
		self.db = db
		self.id = id_

	def insert_message(self, user, content, timestamp):
		""" Inserts a message posted by a particular user and including a timestamp.

		Returns a DatabaseMessage object corresponding to the inserted message.
		"""

		message_id = Database.generate_uuid()

		self.db.cur.execute(
			"INSERT INTO messages VALUES (%s, %s, %s, %s, %s)",
			(message_id, self.id, user.id, content, timestamp)
		)

		user_json = user.to_json()

		return DatabaseMessage(
			message_id,
			self.id,
			user.id,
			user_json["first_name"],
			user_json["last_name"],
			content,
			timestamp
		)

	def messages(self):
		"""
		Returns a list of messages' corresponding DatabaseMessage objects sorted by timestamp for
		the chat.
		"""

		self.db.cur.execute(
			"""
SELECT messages.id, chat_id, user_id, first_name, last_name, content, timestamp
FROM messages
JOIN users ON user_id = users.id
WHERE chat_id = %s
ORDER BY timestamp;""",
			(self.id,)
		)

		return [DatabaseMessage(*row) for row in self.db.cur.fetchall()]

	def to_json(self, user):
		self.db.cur.execute(
			"""
SELECT name, meeting_time, COUNT(user_id)
FROM chats
LEFT JOIN votes ON chat_id = id
WHERE id = %s
GROUP BY id;""",
			(self.id,)
		)

		name, meeting_time, vote_count = self.db.cur.fetchone()

		self.db.cur.execute(
			"SELECT FROM votes WHERE user_id = %s AND chat_id = %s;",
			(user.id, self.id)
		)

		return {
			"id": self.id,
			"name": name,
			"meetingTime":
				# We shouldn't assume the server is in the same timezoneas the client
				(meeting_time.hour * 60 + meeting_time.minute) * 60 + meeting_time.second,

			# Don't hardcode these
			"meetingDuration": 60 * 60 * 2,
			"formatedMeetingDuration": "2 hours",
			"voteCount": vote_count,
			"voted": self.db.cur.rowcount > 0
		}

@dataclasses.dataclass
class DatabaseMessage:
	id: str
	chat_id: str
	user_id: str
	user_first_name: str
	user_last_name: str
	content: str
	timestamp: datetime.datetime

	def to_json(self):
		return {
			"id": self.id,
			"chatID": self.chat_id,
			"userID": self.user_id,
			"userFirstName": self.user_first_name,
			"userLastName": self.user_last_name,
			"content": self.content,
			"timestamp": int(self.timestamp.timestamp())
		}

class DatabaseUser:
	def __init__(self, db, id_):
		self.db = db
		self.id = id_

	def create_chat(self, name, meeting_time):
		""" Creates a chat.

		Returns a corresponding DatabaseChat object.
		"""

		chat_id = self.db.generate_uuid()

		self.db.cur.execute(
			"INSERT INTO chats VALUES (%s, %s, %s, %s)",
			(chat_id, name, meeting_time, self.id)
		)

		return DatabaseChat(self.db, chat_id)

	def delete_vote(self, chat):
		""" Unvotes for a chat.

		Returns True if the chat was already voted for by the user and False otherwise.
		"""

		self.db.cur.execute(
			"DELETE FROM votes WHERE user_id = %s AND chat_id = %s;",
			(self.id, chat.id)
		)

		return self.db.cur.rowcount > 0

	def to_json(self):
		self.db.cur.execute(
			"SELECT username, first_name, last_name FROM users WHERE id = %s;",
			(self.id,)
		)

		username, first_name, last_name = self.db.cur.fetchone()

		return {
			"id": self.id,
			"username": username,
			"first_name": first_name,
			"last_name": last_name
		}

	def verify_password(self, password):
		""" Verifies the users the password with one provided upon login.

		Returns True if the password is correct and False otherwise.
		"""

		self.db.cur.execute("SELECT password FROM users WHERE id = %s;", (self.id,))

		try:
			self.db.password_hasher.verify(self.db.cur.fetchone()[0], password)
		except argon2.exceptions.VerifyMismatchError:
			return False

		return True

	def vote(self, chat):
		""" Votes for a chat.

		Returns False if the chat was already voted for by the user and True otherwise.
		"""

		self.db.cur.execute("INSERT INTO votes VALUES (%s, %s);", (self.id, chat.id))

		return self.db.cur.rowcount > 0

	def voted_for(self, chat):
		""" Returns True if the user voted for a particular chat and False otherwise. """

		self.db.cur.execute(
			"SELECT FROM votes WHERE user_id = %s AND chat_id = %s;",
			(self.id, chat.id)
		)

		return self.db.cur.rowcount > 0
