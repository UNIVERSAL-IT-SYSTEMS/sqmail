# VFolder abstraction.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/vfolder.py,v $
# $State: Exp $

import os
import rfc822
import string
import sqmail.db
import sqmail.message
import sqmail.utils
import cPickle
import cStringIO

def get_folder_list():
	l = sqmail.utils.getsetting("vfolders")
	if (l == None):
		print "WARNING: your database seems not to have been initialised correctly."
		print "(I can't seem to find the vfolder list.) I'm trying to work round this"
		print "but there may be other problems."
		l = []
	if ("" in l):
		print "WARNING: one or more vfolders have empty names. Replacing with randomly-"
		print "generated ones."
	for i in xrange(len(l)):
		if (l[i] == ""):
			l[i] = "(blank name "+str(i)+")"
	return l

def write_to_cache(vf):
	fp = open(os.path.expanduser("~/.sqmail.cache"), "w")
	cPickle.dump(vf, fp)
	fp.close()

def read_from_cache():
	try:
		fp = open(os.path.expanduser("~/.sqmail.cache"), "r")
	except IOError:
		return None
	vf = cPickle.load(fp)
	fp.close()
	return vf

def write_id(id):
	fp = open(os.path.expanduser("~/.sqmail.id"), "w")
	cPickle.dump(id, fp)
	fp.close()

def read_id():
	try:
		fp = open(os.path.expanduser("~/.sqmail.id"), "r")
		id = cPickle.load(fp)
		fp.close
	except IOError:
		id = None
	return id

def vfolder_add(name, query, parent):
	cursor = sqmail.db.cursor()
	print "Adding vfolder", name, "query", query
	cursor.execute("INSERT INTO vfolders (name, query, parent) values " \
			" ('%s', '%s', %d)" \
			% (sqmail.db.escape(name), sqmail.db.escape(query), parent))
	cursor.execute("SELECT LAST_INSERT_ID()")
	return int(cursor.fetchone()[0])
	
def vfolder_find(name):
	cursor = sqmail.db.cursor()
	cursor.execute("SELECT id FROM vfolders WHERE name = '%s'" \
			% sqmail.db.escape(name))
	i = cursor.fetchone()
	if i:
		return int(i[0])
	return None

def vfolder_get(id):
	# Check if it's a new-style vfolder.
	cursor = sqmail.db.cursor()
	cursor.execute("SELECT name, query, parent FROM vfolders"\
		       " WHERE id = %d" % id)
	i = cursor.fetchone()
	if i:
		return i
	return None

def vfolder_set(id, name, query, parent):
	cursor = sqmail.db.cursor()
	q = "UPDATE vfolders SET name='%s', query='%s', parent=%d WHERE id=%d"\
	    % (sqmail.db.escape(name), sqmail.db.escape(query), parent, id)
	print q
	cursor.execute(q)
	
def read_hierarchic_query(id, query):
	if not id:
		return query
	p = vfolder_get(id)[2]
	if (p == id):
		print "DANGER! Dastardly recursive loop found in vfolder", id+"."
		print "Terminating loop before your machine crashes."
		return query
	if not p:
		return query
	query = "((" + vfolder_get(p)[1] + ") and ("+query+"))"
	return read_hierarchic_query(p, query)
	
def read_allthatsleft_query(id):
	parent = vfolder_get(id)[2]
	l = get_folder_list()
	query = "1"
	for i in l:
		j = vfolder_get(i)
		if (j[2] == parent):
			q = j[1]
			if ((q != "") and (q != "1")):
				query = query+" and (not ("+q+"))"
	return query

class VFolder:
	def __init__(self, id=None, name=None, query=None, parent=None):
		if (not id and not query and not name):
			raise RuntimeError("Can't create a VFolder instance without at least one of id, name and query")
		if name and not id:
			id = vfolder_find(name)
			if not id:
				if query:
					id = vfolder_add(name, query, parent)
				else:
					raise KeyError
		if id and query:
			self.id = id
			self.name = name
			self.query = query
			self.parent = parent
		elif id:
			self.id = id
			i = vfolder_get(id)
			if not i:
				raise KeyError
			(self.name, self.query, self.parent) = i
		else:
			self.id = None
			self.name = None
			self.query = query
			self.parent = None

		self.unread = None
		self.results = None
		self.total = None

	def count(self):
		cursor = sqmail.db.cursor()
		query = self.gethierarchicquery()
		print "Counting", self.name
		try:
			cursor.execute("SELECT COUNT(*) FROM headers WHERE "+query+" AND readstatus='Unread'")
			self.unread = cursor.fetchone()[0]
			cursor.execute("SELECT COUNT(*) FROM headers WHERE "+query)
			self.total = cursor.fetchone()[0]
		except sqmail.db.db().OperationalError:
			print "SQL syntax error in folder", self.name
		print self.unread,"/", self.total

	def scan(self):
		cursor = sqmail.db.cursor()
		query = self.gethierarchicquery()
		try:
			cursor.execute("SELECT COUNT(*) FROM headers WHERE "+query+" AND readstatus='Unread'")
			self.unread = cursor.fetchone()[0]
			cursor.execute("SELECT id,readstatus,fromfield,realfromfield,subjectfield,unix_timestamp(date) FROM headers WHERE "+query+" ORDER BY date")
		except sqmail.db.db().OperationalError:
			print "SQL syntax error in folder", self.name
			self.results = []
		else:
			self.results = []
			while 1:
				d = cursor.fetchone()
				if not d:
					break

				self.results.append(list(d))
		self.total = len(self.results)

	def clearcache(self):
		self.results = []
		self.total = None
		
	def getquery(self):
		return self.query
	
	def gethierarchicquery(self):
		if not self.query:
			# An empty query means `all messages that are left'. We
			# need to find all the folders with the same parent as
			# this one, OR the queries together, and NOT the result.
			query = read_allthatsleft_query(self.id)
		else:
			query = self.query
		query = read_hierarchic_query(self.id, query)
		return query

	def setquery(self, query):
		self.query = query
		self.unread = None
		self.results = None
	
	def getname(self):
		return self.name

	def setname(self, name):
		self.name = name
		self.unread = None
		self.results = None

	def getparent(self):
		return self.parent

	def setparent(self, parent):
		self.parent = parent
		self.unread = None
		self.results = None

	def getcounted(self):
		return (self.total != None)

	def save(self):
		vfolder_set(self.id, self.name, self.query, self.parent)

	def getunread(self):
		if (self.total == None):
			self.count()
		return self.unread
	
	def getresults(self):
		if (self.results == None):
			self.scan()
		return self.results

	def __len__(self):
		if (self.total == None):
			self.count()
		return self.total
	getlen = __len__

	def __getitem__(self, index):
		if (self.results == None):
			self.scan()
		return self.results[index]

# Revision History
# $Log: vfolder.py,v $
# Revision 1.13  2001/03/13 19:28:23  dtrg
# Doesn't load message headers until you select the folder; this improves
# speed and memory consumption considerably (because it's not keeping huge
# numbers of message headers around).
#
# Revision 1.12  2001/03/12 10:34:26  dtrg
# Forgot to escape some constant strings being passed to the SQL server.
#
# Revision 1.11  2001/03/09 10:34:14  dtrg
# When you do str(i) when i is a long, Python returns a string like "123L".
# This really upsets the SQL server. So I've rewritten large numbers of the
# SQL queries to use % syntax, which doesn't do that.
#
# Revision 1.10  2001/03/07 12:25:44  dtrg
# Prevented some longs from being sent to the SQL server, and fixed a logic
# bug in the vfolder constructor code.
#
# Revision 1.9  2001/03/05 20:44:41  dtrg
# Lots of changes.
# * Added outgoing X-Face support (relies on netppm and compface).
# * Rearrange the FileSelector code now I understand about bound and unbound
# method calls.
# * Put in a workaround for the MimeReader bug, so that when given a message
# that triggers it, it fails cleanly and presents the user with the
# undecoded message rather than eating all the core and locking the system.
# * Put some sanity checking in VFolder so that attempts to access unknown
# vfolders are trapped cleanly, rather than triggering the
# create-new-vfolder code and falling over in a heap.
#
# Revision 1.8  2001/02/27 16:35:31  dtrg
# Fixed a nasty little bug that caused it to think that empty vfolders were
# never counted, causing the background counting routine to keep trying
# indefinitely.
#
# Revision 1.7  2001/02/23 19:50:26  dtrg
# Lots of changes: added the beginnings of the purges system, CLI utility
# for same, GUI utility & UI for same, plus a CLI vfolder lister.
#
# Revision 1.6  2001/02/15 19:34:16  dtrg
# Many changes. Bulletproofed the send box, so it should now give you
# (reasonably) user-friendly messages when something goes wrong; rescan a
# vfolder when you leave it, so the vfolder list is kept up-to-date (and in
# the background, too); added `unimplemented' messages to a lot of
# unimplemented buttons; some general tidying.
#
# Revision 1.5  2001/01/25 20:55:06  dtrg
# Woohoo! Vfolder styling now works (mostly, except backgrounds). Also added
# background vfolder counting to avoid that nasty delay on startup or
# whenever you fetch new mail.
#
# Revision 1.4  2001/01/22 11:47:44  dtrg
# create-database turned out not to be working (a simple syntax bug plus I
# forgot to emit a new-style vfolders setting). Fixed. Also added some
# bulletproofing to protect against this sort of problem.
#
# Revision 1.3  2001/01/19 20:37:23  dtrg
# Changed the way vfolders are stored in the database.
#
# Now they're stored in a seperate table, vfolders, and referenced by id.
# This means that finally you can have two vfolders with the same name (very
# handy in a tree scenario). The system's also slightly less fragile.
#
# WARNING! The current code will not work with previous versions of the
# database. You will need to do "SQmaiL upgrade" to automatically convert
# your data.
#
# Revision 1.2  2001/01/16 20:13:12  dtrg
# Fixed small bug that was preventing on-the-fly queries from the scan CLI
# from working.
#
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#



