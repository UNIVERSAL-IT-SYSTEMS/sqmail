"""Define sequence type and related functions

The relevant tables in the sqmail database can be created by:

CREATE TABLE sequence_data
   (sid INTEGER UNSIGNED NOT NULL,
    id INTEGER UNSIGNED NOT NULL,
    UNIQUE INDEX sidid (sid, id));

CREATE TABLE sequence_temp
   (sid INTEGER UNSIGNED NOT NULL,
    id INTEGER UNSIGNED NOT NULL,
    UNIQUE INDEX sidid (sid, id));

CREATE TABLE sequence_descriptions
   (sid INTEGER UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name TEXT NOT NULL,
    misc LONGBLOB);

"""

import sqmail.db
import string


class SequenceException(Exception):
	"""Sequence exception - if something goes wrong with a sequence"""
	pass

class Sequence:
	"""A sequence is a set of messages
	
	A sequence is basically an attribute that can either apply or not
	to a message.  They differ from, for instance, a query in that
	whether or not a message is in a sequence is a sui generis fact,
	while whether or not a message is in a query is determined by a
	rule which depends on other facts about a message.  Thus sequences
	are good for arranging messages into groups which can't be
	determined by the message itself (unread, draft, important, etc).

	Right now sequences are stored in a big table which just lists the
    pairs (sequence id, message id).

	The name of each sequence, and possibly other information, is
	stored in a different table than the data pairs.

	"""
	def __init__(self, sid, name):
		"""Sequence constructor

		Only the sequence manager should ever call this constructor
		directly.  sid is the sequence id.  It is a non-negative
		4 byte integer.

		"""
		self.sid = sid
		self.name = name

	def addid(self, id):
		"""Given a message id, add it to the sequence"""
		sqmail.db.execute("INSERT INTO sequence_data (sid, id) VALUES "
						  "(%s, %s)", (self.sid, id))

	def checkid(self, id):
		"""Returns true if message id is in sequence"""
		return sqmail.db.execute("SELECT id FROM sequence_data WHERE "
								 "(sid = %s and id = %s)", (self.sid, id))

	def addmessage(self, sqmsg):
		"""Add an SQmaiL message to the sequence"""
		self.addid(sqmsg.getid())

	def deleteid(self, id):
		"""Removes the message id from the sequence"""
		sqmail.db.execute("DELETE FROM sequence_data WHERE "
						  "(sid = %s AND id = %s)", (self.sid, id))

	def deleteids(self, idlist):
		"""Remove a list of message ids from the sequence"""
		slist = ["0"] + map(lambda id: "id = %d" % id, idlist)
		sqmail.db.execute("DELETE FROM sequence_data WHERE sid = %d AND "
						  "(%s)" % (self.sid, string.join(slist, " OR ")))

	def list(self):
		"""Return list of message ids in sequence.  May be long."""
		return map(lambda x: x[0],
				   sqmail.db.fetchall("SELECT id FROM sequence_data WHERE "
									  "sid = %s", self.sid))
	def getname(self):
		return self.name

	def getsid(self):
		return self.sid

	def clear(self):
		"""Removes all the messages in sequence"""
		sqmail.db.execute("DELETE FROM sequence_data WHERE "
						  "sid = %s", self.sid)

	def getalias(self):
		"""Returns SQL alias for sequence

		SQmaiL sometimes try to query taking into account multiple
		sequences at once.  When this happens, it must join several
		copies of the sequence table together, and they must be named
		differently.  getalias() returns the alias of the sequence
		table used to query about this sequence in particular

		"""
		return "sd"+str(self.sid)


class SequenceManagerClass:
	"""Find, create, and destroy sequences

	There should only be once instance of this class.  When created,
	it reads information about the various sequences.  Sequences
	should be located, created, and destroyed only through the manager.

	"""
	def __init__(self):
		"""Read all info from sequence_descriptions table"""
		self.sequences_by_name = {}
		self.sequences_by_sid = {}
		for row in sqmail.db.fetchall("SELECT sid, name FROM "
									  "sequence_descriptions"):
			sid, name = row[0], row[1]
			seq = Sequence(sid, name)
			self.sequences_by_name[name] = seq
			self.sequences_by_sid[sid] = seq

	def listsequences(self):
		"""Return a list of all the available sequences"""
		return self.sequences_by_id.values()

	def get_by_sid(self, sid):
		"""Return a sequence with the given sid or None"""
		if self.sequences_by_sid.has_key(sid):
			return self.sequences_by_sid[sid]
		else: return None

	def get_by_name(self, name):
		"""Return a sequence with the given name or None"""
		if self.sequences_by_name.has_key(name):
			return self.sequences_by_name[name]
		else: return None

	def get_seqs_containing_id(self, id):
		"""Return a list of sequences containing the message id"""
		return map(lambda x: self.get_by_sid(x[0]),
				   sqmail.db.fetchall("SELECT sid FROM sequence_data "
									  "WHERE id = %s", id))

	def deleteidfromall(self, id):
		"""Delete a message id from all sequences"""
		sqmail.db.execute("DELETE FROM sequence_data WHERE id = %s", id)

	def seq_sid_to_name(self, sid):
		"""Return the name of the sequence with specified sid, or None"""
		seq = self.get_by_sid(sid)
		if not seq: return None
		else: return seq.getname()

	def seq_name_to_id(self, name):
		"""Return the sid of the sequence with specified name, or None"""
		seq = self.get_by_name(name)
		if not seq: return None
		else: return seq.getsid()

	def delete_sequence(self, sequence):
		"""Remove all trace of the specified sequence"""
		sequence.clear()
		sqmail.db.execute("DELETE FROM sequence_descriptions WHERE "
						  "sid = %s", sequence.sid)
		del self.sequences_by_name[sequence.getname()]
		del self.sequences_by_sid[sequence.getsid()]
		sequence.name = sequence.sid = None

	def create_sequence(self, name):
		"""Returns a new sequence with specified name"""
		sqmail.db.execute("INSERT into sequence_descriptions (name) "
						  "VALUES (%s)", name)
		sid = sqmail.db.fetchone("SELECT LAST_INSERT_ID()")[0]
		seq = Sequence(sid, name)
		self.sequences_by_sid[sid] = seq
		self.sequences_by_name[name] = seq
		return seq


# Warning, this is active code, so sequences should not be imported if
# the database is not ready.

SequenceManager = SequenceManagerClass()

# For convenience, bind SequenceManager methods to functions with
# global (module) scope.  Thus you can call sequences.get_by_sid
# instead of sequences.SequenceManager.get_by_sid

for methodname in filter(lambda x: not x[0]=="_",
						 dir(SequenceManagerClass)):
	globals()[methodname] = eval("SequenceManager."+methodname)
