"""Define sequence type and related functions

The relevant tables in the sqmail database can be created by:

CREATE TABLE sequence_data (sid VARCHAR(40) NOT NULL, id INTEGER NOT NULL,
    INDEX sidid (sid,id));
CREATE TABLE sequence_descriptions (sid VARCHAR(40) NOT NULL PRIMARY KEY,
    description text);

"""

from sqmail import db, message

sid_length = 40

class SequenceException(Exception):
	"""Sequence exception - if something goes wrong with a sequence"""
	pass


class Sequence:
	"""A sequence is a set of messages
	
	A sequence is basically an attribute that can either apply or not
	to a message.  They differ from, for instance, a query in that whether
	or not a message is in a sequence is a sui generis fact, while whether
	or not a query returns a message is determined by a rule which depends
	on other facts about a message.  Thus sequences are good for arranging
	messages into groups which can't be determined by the message itself
	(unread, draft, important, etc).

	Right now sequences are stored in a big table which just pairs
	messages to the sequence(s) its in.

	Sequences may (or may not) also have descriptions, which are
	stored in another table.

	"""
	def __init__(self, sid):
		"""Sequence constructor

		sid is the sequence id.  It should be a string at most sid_length
		long.  sid's may or may not be case sensitive.

		self.description is 0 if sequence it's unknown if sequence has
		description.  It's None if sequence has no description.

		"""
		global sid_length

		if len(sid) > sid_length:
			raise SequenceException("Sequence id too long")
		else: self.sid = sid
		self.cursor = None
		self.description = 0

	def getcursor(self):
		if not self.cursor:
			self.cursor = db.cursor()
		return self.cursor

	def AddMessageID(self, id):
		"""Given a message id, add it to the sequence"""
		cursor = self.getcursor()
		cursor.execute("INSERT INTO sequence_data VALUES (%s, %s)",
					   (self.sid, id))

	def CheckID(self, id):
		"""Returns true if message id is in sequence"""
		cursor = self.getcursor()
		cursor.execute("SELECT id FROM sequence_data WHERE " +
					   "(sid = %s AND id = %s)" % (self.sid, id))
		return cursor.fetchone()[0]

	def AddMessage(self, sqmsg):
		"""Add an SQmaiL message to the sequence"""
		self.AddMessageID(sqmsg.getid())

	def DeleteID(self, id):
		"""Removes the message id from the sequence"""
		cursor = self.getcursor()
		cursor.execute("DELETE FROM sequence_data WHERE (sid = %s AND id = %s)",
					   (self.sid, id))

	def GetIDs(self):
		"""Return list of message ids in sequence.  May be long."""
		cursor = self.getcursor()
		cursor.execute("SELECT id FROM sequence_data WHERE sid = %s",
					   self.sid)
		return map(lambda x: x[0], cursor.fetchall())

	def GetDescription(self):
		"""Return description of sequence

		A description is just a string associated with a sequence.
		You can use it to describe what a sequence does, etc.

		"""
		if self.description is None: return None
		if self.description: return self.description

		cursor = self.getcursor()
		cursor.execute("SELECT description FROM sequence_descriptions WHERE sid = %s",
					   self.sid)
		selectrow = cursor.fetchone()
		if not selectrow: self.description = None
		else: self.description = selectrow[0]
		return self.description
		
	def createdescriptionrow(self):
		"""Adds description row for sequence"""
		self.cursor.execute("INSERT INTO sequence_descriptions (sid) VALUES (%s)",
							self.sid)

	def SetDescription(self, description):
		"""Set sequence description"""
		self.description = description
		cursor = self.getcursor()
		cursor.execute("SELECT sid FROM sequence_descriptions WHERE sid = %s",
					   self.sid)
		if not cursor.fetchall(): self.createdescriptionrow()
		cursor.execute("UPDATE sequence_descriptions SET description = %s WHERE sid = %s",
					   (description, self.sid))

	def DeleteDescription(self):
		"""Removes any description of the sequence"""
		self.description = None
		cursor = self.getcursor()
		cursor.execute("DELETE FROM sequence_descriptions where sid = %s",
					   self.sid)


def ListSequences():
	"""Return a list with all non-empty sequences in it"""
	cursor = db.cursor()
	cursor.execute("SELECT DISTINCT sid FROM sequence_data")
	return map(lambda x: x[0], cursor.fetchall())

def GetSequencesContainingID(id):
	"""Returns list of sequence ids containing given message id"""
	cursor = db.cursor()
	cursor.execute("SELECT sid FROM sequence_data WHERE id = %s", id)
	return map(lambda x: x[0], cursor.fetchall())

def DeleteIDFromAll(id):
	"""Deletes message id from all sequences"""
	db.cursor().execute("DELETE FROM sequence_data WHERE id = %s", id)
