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
	cursor.execute("INSERT INTO vfolders" \
			" (name, query, parent) values " \
			" ('"+sqmail.db.escape(name)+"', "\
			" '"+sqmail.db.escape(query)+"', "\
			" "+str(parent)+")")
	cursor.execute("SELECT LAST_INSERT_ID()")
	return int(cursor.fetchone()[0])
	
def vfolder_find(name):
	cursor = sqmail.db.cursor()
	cursor.execute("SELECT id FROM vfolders" \
			" WHERE name = '"+sqmail.db.escape(name)+"'")
	i = cursor.fetchone()
	if i:
		return int(i[0])
	return None

def vfolder_get(id):
	# Check if it's a new-style vfolder.
	cursor = sqmail.db.cursor()
	cursor.execute("SELECT name, query, parent FROM vfolders"\
		       " WHERE id = "+str(id))
	i = cursor.fetchone()
	if i:
		return i
	return None

def vfolder_set(id, name, query, parent):
	cursor = sqmail.db.cursor()
	q = "UPDATE vfolders SET "\
	    " name = '"+sqmail.db.escape(name)+"', "\
	    " query = '"+sqmail.db.escape(query)+"', "\
	    " parent = "+str(parent)+" "\
	    "WHERE id = "+str(id)
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
				id = vfolder_add(name, query, parent)
		if id and query:
			self.id = id
			self.name = name
			self.query = query
			self.parent = parent
		elif id:
			self.id = id
			(self.name, self.query, self.parent) = \
				vfolder_get(id)
		else:
			self.id = None
			self.name = None
			self.query = query
			self.parent = None

		self.unread = None
		self.results = None

	def scan(self):
		cursor = sqmail.db.cursor()
		if not self.query:
			# An empty query means `all messages that are left'. We
			# need to find all the folders with the same parent as
			# this one, OR the queries together, and NOT the result.
			query = read_allthatsleft_query(self.id)
		else:
			query = self.query
		query = read_hierarchic_query(self.id, query)
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

	def clearcache(self):
		self.results = []
		
	def getquery(self):
		return self.query
	
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
		return not not self.results

	def purge(self):
		self.results = None

	def save(self):
		vfolder_set(self.id, self.name, self.query, self.parent)

	def getunread(self):
		if not self.results:
			self.scan()
		return self.unread
	
	def getresults(self):
		if not self.results:
			self.scan()
		return self.results

	def getlen(self):
		return len(self)

	def __len__(self):
		if not self.results:
			self.scan()
		return len(self.results)

	def __getitem__(self, index):
		if not self.results:
			self.scan()
		return self.results[index]

# Revision History
# $Log: vfolder.py,v $
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



