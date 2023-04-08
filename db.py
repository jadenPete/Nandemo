import argon2
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
	def _generate_uuid():
		return str(uuid.uuid4())

	def create_user(self, username, first_name, last_name, password):
		""" Attempts to create a user.

		If a user already exists with the provided username, returns None.
		Otherwise, returns the newly created DatabaseUser instance.
		 """

		try:
			id_ = self.__class__._generate_uuid()
			hashed = self.password_hasher.hash(password)

			self.cur.execute(
				"INSERT INTO users VALUES (%s, %s, %s, %s, %s)",
				(id_, username, first_name, last_name, hashed)
			)
		except psycopg2.errors.UniqueViolation:
			return

		return DatabaseUser(self, id_)

	def user_by_username(self, username):
		""" Retrieves a user by their username.

		Returns a corresponding DatabaseUser object if the user was found.
		Otherwise, returns None.
		"""

		self.cur.execute("SELECT id FROM users WHERE username = %s;", (username,))

		if self.cur.rowcount > 0:
			return DatabaseUser(self, self.cur.fetchone()[0])

class DatabaseUser:
	def __init__(self, db, id_):
		self.db = db
		self.id = id_

	def verify_password(self, password):
		""" Verifies the users the password with one provided upon login.

		Returns True if the password is correct and False otherwise.
		"""

		self.cur.execute("SELECT password FROM users WHERE id = %s;", (self.id,))

		if self.cur.rowcount == 0:
			return

		try:
			self.db.password_hasher.verify(self.cur.fetchone()[0], password)
		except argon2.exceptions.VerifyMismatchError:
			return False

		return True
