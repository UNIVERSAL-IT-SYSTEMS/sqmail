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
	return sqmail.utils.getsetting("vfolders")

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

def read_hierarchic_query(name, query):
	if not name:
		return query
	p = sqmail.utils.getsetting("vfolder parent "+name)
	if (p == name):
		print "DANGER! Dastardly recursive loop found in vfolder", name+"."
		print "Terminating loop before your machine crashes."
		return query
	if not p:
		return query
	query = "((" + sqmail.utils.getsetting("vfolder query "+p, "1") + \
		") and ("+query+"))"
	return read_hierarchic_query(p, query)
	
def read_allthatsleft_query(name):
	parent = sqmail.utils.getsetting("vfolder parent "+name)
	l = get_folder_list()
	query = "1"
	for i in l:
		if (sqmail.utils.getsetting("vfolder parent "+i) == parent):
			q = sqmail.utils.getsetting("vfolder query "+i)
			if ((q != "") and (q != "1")):
				query = query+" and (not ("+q+"))"
	return query

class VFolder:
	def __init__(self, name=None, query=None, parent=None):
		if (not name and not query):
			raise RuntimeError("Can't create a VFolder instance without at least one of name and query")
		if name and query:
			self.name = name
			self.query = query
			self.parent = parent
		elif name:
			self.name = name
			self.query = sqmail.utils.getsetting("vfolder query "+name)
			self.parent = sqmail.utils.getsetting("vfolder parent "+name)
		else:
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
			query = read_allthatsleft_query(self.name)
		else:
			query = self.query
		query = read_hierarchic_query(self.name, query)
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

	def setparent(self, parent):
		self.parent = parent
		self.unread = None
		self.results = None

	def save(self):
		sqmail.utils.setsetting("vfolder query "+self.name, self.query)
		sqmail.utils.setsetting("vfolder parent "+self.name, self.parent)

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
# Revision 1.2  2001/01/16 20:13:12  dtrg
# Fixed small bug that was preventing on-the-fly queries from the scan CLI
# from working.
#
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#



