# VFolder abstraction.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/vfolder.py,v $
# $State: Exp $

"""Classes and Functions related to VFolders

Includes the objects Query, QueryException, VFQuery, UserQuery, and
VFolder.

"""

import os
import rfc822
import string, re
from sqmail import db, message, utils, sequences
import cPickle
import cStringIO


def vfolder_find(name):
	cursor = db.cursor()
	cursor.execute("SELECT id FROM vfolders WHERE name = %s", name)
	i = cursor.fetchone()
	if i:
		return int(i[0])
	return None

def get_folder_list():
	l = utils.getsetting("vfolders")
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
	cursor = db.cursor()
	cursor.execute("INSERT INTO vfolders (name, query, parent) values "
				   " (%s, %s, %s)", [name, query, parent])
	cursor.execute("SELECT LAST_INSERT_ID()")
	return int(cursor.fetchone()[0])

def vfolder_find(name):
	cursor = db.cursor()
	cursor.execute("SELECT id FROM vfolders WHERE name = '%s'" \
			% db.escape(name))
	i = cursor.fetchone()
	if i:
		return int(i[0])
	return None

def vfolder_get(id):
	# Check if it's a new-style vfolder.
	cursor = db.cursor()
	cursor.execute("SELECT name, query, parent FROM vfolders"\
		       " WHERE id = %d" % id)
	i = cursor.fetchone()
	if i:
		return i
	return None



class QueryException(Exception):
	pass

class Query:
	"""Simple class representing VFolder Query

	Wrapper around self.qstring.  This just helps avoid a lot of
	query+" AND "+query type stuff below.

	"""
	max_query_length = 10000

	def __init__(self, qstring):
		"""qstring is the actual SQL query string"""
		if len(qstring) > self.max_query_length:
			error_string = ("Query length over %d.  Cycle created?" %
							self.max_query_length)
			raise QueryException(error_string)
		self.qstring = qstring

	def __str__(self): return self.qstring
	def __add__(self, x): return self.qstring + x
	def __radd__(self, x): return x + self.qstring
	def __len__(self): return len(self.qstring)


class VFQuery(Query):
	"""Use for the actual SQL queries

	These queries are on the headers,sequence_data.  Use
	UserQuery.ExpandToVFQuery to get a VFQuery.

	self.qstring is the part of the query that goes after "WHERE ..."

	self.seqdict is a dictionary of sequences.  If a sequence name is
	a key, then it needs to be quantified over.

	"""
	def __init__(self, qstring):
		self.seqdict = {}
		self.qschema = None
		Query.__init__(self, qstring)
	
	def quoteseqname(self, seqname):
		"""Returns one word version of sequence name"""
		seqname = string.replace(seqname, " ", "_")
		seqname = string.replace(seqname, "-", "M")
		seqname = string.replace(seqname, "+", "P")
		return seqname

	def setqschema(self):
		"""Set the query schema strings and argument list

		It is meant to be used like: cursor.execute(qschema % foo),
		where foo is a column name, so any % in the qstring should be
		quoted.

		"""
		joinstringlist = []
		for seqname in self.seqdict.keys():
			joinstringlist.append("LEFT JOIN sequence_data AS sd%s ON"
								  " headers.id = sd%s.id AND sd%s.sid ="
								  "'%s'" %
								  ((self.quoteseqname(seqname),)*3 +
								   (seqname,)))
		self.qschema = string.join(["SELECT %s FROM headers"] +
								   joinstringlist +
								   ["WHERE",
									string.replace(self.qstring, "%", "%%")])

	def count(self, addendum = ""):
		"""Returns the number of messages matching the query

		addendum will be added to the qschema at the end"""
		cursor = db.cursor()
		if not self.qschema: self.setqschema()
		cursor.execute((self.qschema % "COUNT(*)") + " " + addendum)
		return cursor.fetchone()[0]

	def countunread(self):
		"""Returns number of unread messages"""
		return self.count("AND readstatus = 'Unread'")
		
	def selectcolumns(self, columns, ordering):
		"""Returns the specified columns with fetchall() on query"""
		cursor = db.cursor()
		if not self.qschema: self.setqschema()
		print "executing: ",(self.qschema % columns)+" ORDER BY "+ordering
		cursor.execute((self.qschema % columns) + " ORDER BY " + ordering)
		return cursor.fetchall()

	def binaryop(self, vfquerylist, opstring, default):
		"""Used for defining And and Or"""
		if not vfquerylist:
			return VFQuery(default)
		qstringlist, seqdict = [], {}
		for arg in (self,) + vfquerylist:
			qstringlist.append(arg.qstring)
			seqdict.update(arg.seqdict)
		vfq = VFQuery("(" + string.join(qstringlist, " "+opstring+" ") + ")")
		vfq.seqdict = seqdict
		return vfq

	def And(*vfqueries):
		"""Return vfquery conjunction of given vfqueries"""
		return vfqueries[0].binaryop(vfqueries[1:], "AND", "1")

	def Or(*vfqueries):
		"""Return vfquery disjunction of given vfqueries"""
		return vfqueries[0].binaryop(vfqueries[1:], "OR", "0")

	def Not(self):
		"""Return vfquery negation of self"""
		vfq = VFQuery("(NOT " + self.qstring + ")")
		vfq.seqdict = self.seqdict.copy()
		return vfq

	def reckon_sequences(self, foldername):
		"""Changes self to exclude/include folder related sequences

		Also sets self.qstringnoseq and self.seqdictnoseq as the
		previous versions of self.qstring and self.seqdict in case we
		want to know what would happen without the overrides.

		"""
		self.qstringnoseq = self.qstring
		self.seqdictnoseq = self.seqdict.copy()
		inseq, outseq = "+"+foldername, "-"+foldername
		quoteinseq, quoteoutseq = map(self.quoteseqname, [inseq, outseq])
		self.qstring = ("(sd%s.sid IS NOT NULL OR "
						"(%s AND sd%s.sid IS NULL))" %
						(quoteinseq, self.qstringnoseq, quoteoutseq))
		self.seqdict[inseq] = self.seqdict[outseq] = 1

	def no_sequences(self):
		"""Return a VFQuery like self but ignore folder sequences"""
		vfq = VFQuery(self.qstringnoseq)
		vfq.seqdict = self.seqdictnoseq.copy()
		return vfq


class UserQuery(Query):
	"""Query that the user types into the query box

	These are not SQL at all, but look similar to queries on the
	headers table.  It is possible to ask about sequence_data
	types also.

	"""
	def ExpandToVFQuery(self, vf):
		"""Expand self into full VFQuery, relative to vfolder vf

		Follows three rules:

		0.  If the string is empty, return the always false query.
		
		1.  Replace forms like VFOLDER:foobar or VFOLDER:"foobar" (use
		the latter if folder name contains spaces) for their
		correspending VFQuery strings.  As special cases,
		VFOLDER:children is replaced by the disjunction of all the
		children's queries, and VFOLDER:notsiblings is replaced by the
		disjunction of the negations of all the folders which share a
		parent with the original folder, except of course for the
		original folder.

		2. Add a bit of SQL so that messages in the sequence named
		+foobar will always be in folder foobar and messages in the
		-foobar sequence will never be.  (One message shouldn't be
		in both the +foobar and -foobar sequences.)

		"""
		self.vf = vf
		if not string.strip(self.qstring): return VFQuery("0")
		vfq = self.macroexpand(self.qstring)
		vfq.reckon_sequences(vf.name)
		return vfq

	def macroexpand(self, s):
		"""Replace instances like VFOLDER:foobar"""
		vf_regexp = re.compile('VFOLDER:(\\w+)|VFOLDER:"(.+?)"',
							   re.I | re.M | re.S)
		seqdict = {}
		while 1:
			match = vf_regexp.search(s)
			if not match: break
			vfq = self.find_vfqrepl(match.group(1) or match.group(2))
			seqdict.update(vfq.seqdict)
			s = s[:match.start(0)] + vfq.qstring + s[match.end(0):]
		finalvfq = VFQuery(s)
		finalvfq.seqdict = seqdict
		return finalvfq

	def find_vfqrepl(self, foldername):
		"""Returns vfquery that VFOLDER:foldername represents"""
		lowercase = string.lower(foldername)
		if lowercase == "notsiblings":  # Disjoin negations of child vfqs
			siblings = map(lambda x: x.vfquery, self.vf.getsiblings())
			if siblings: return apply(VFQuery.Or, siblings).Not()
			else: return VFQuery("1")
		elif lowercase == "children":
			children = map(lambda x: x.vfquery, self.vf.getchildren())
			if children: return apply(VFQuery.Or, children)
			else: return VFQuery("0")
		else:
			vf = vfolder_find(foldername)
			if not vf: raise QueryException("Can't find folder "+foldername+
											" in query from "+self.vf.name)
			else: return VFolder(vf).vfquery



class VFolder:
	"""Virtual Folders are what the user manipulates as folders

	There are two kinds of queries that a VFolder works with.  The
	first is pure SQL and is what is actually used to pick the messages
	out of the database.  The second is called a "user query", and is what
	the user specifies as the criteria for picking out messages in a
	vfolder.  User queries may contain certain key words like
	"INFOLDER:Drafts" which are expanded to the query used to determine
	which messages are in the Drafts folder.

	"""
	def __init__(self, id=None, name=None, uquery=None, parent=None):
		if (not id and not uquery and not name):
			raise RuntimeError("Can't create a VFolder instance without" +
							   " at least one of id, name and query string")
		if name and not id:
			id = vfolder_find(name)
			if not id:
				if uquery:
					id = vfolder_add(name, uquery, parent)
				else:
					raise KeyError
		if id and uquery:
			self.id = id
			self.name = name
			self.uquery = UserQuery(uquery)
			self.parent = parent
		elif id:
			self.id = id
			i = vfolder_get(id)
			if not i:
				raise KeyError
			self.name, self.parent = i[0], i[2]
			self.uquery = UserQuery(i[1])
			self.vfquery = self.uquery.ExpandToVFQuery(self)
		else:
			self.id = None
			self.name = None
			self.uquery = UserQuery(uquery)
			self.parent = None

		self.unread = None
		self.results = None
		self.total = None
		self.whole_query = None

	def count(self):
		"""Set self.unread and self.total"""
		try:
			self.total = self.vfquery.count()
			self.unread = self.vfquery.countunread()
		except (db.db().OperationalError, QueryException), exception:
			print "SQL syntax error counting folder", self.name
			print exception

	def scan(self):
		"""Set self.results and self.total"""
		columns = ("headers.id,readstatus,fromfield,"
				   "realfromfield,subjectfield,unix_timestamp(date)")
		try:
			self.unread = self.vfquery.countunread()
			self.results = self.vfquery.selectcolumns(columns, "date")
		except (db.db().OperationalError, QueryException), exception:
			print "SQL syntax error scanning folder", self.name
			print exception
			self.results = []
		self.total = len(self.results)

	def clearcache(self):
		self.results = []
		self.total = None
		
	def getuquerystr(self):
		return str(self.uquery)
	
	def setuquery(self, querystring):
		self.uquery = UserQuery(querystring)
		self.unread = None
		self.results = None
	
	def getname(self):
		return self.name

	def setname(self, name):
		self.name = name
		self.unread = None
		self.results = None

	def getchildren(self):
		"""Returns list of VFolder children"""
		cursor = db.cursor()
		cursor.execute("SELECT id FROM vfolders WHERE parent=%s", self.id)
		return map(VFolder,
				   reduce(lambda x,y: x+[y[0]], cursor.fetchall(), []))

	def getparent(self):
		return self.parent

	def getparents(self):
		"""In case a folder can later have multiple parents"""
		return [VFolder(self.parent)]

	def getsiblings(self):
		"""Get sibling VFolders, including any half brothers and sisters."""
		cursor = db.cursor()
		cursor.execute("SELECT vf1.id FROM vfolders AS vf0, vfolders AS vf1 "
					   "WHERE vf0.id=%s AND vf0.parent=vf1.parent AND "
					   "NOT (vf1.id=%s)", (self.id, self.id))
		return map(VFolder,
				   reduce(lambda x,y: x+[y[0]], cursor.fetchall(), []))
		
	def setparent(self, parent):
		self.parent = parent
		self.unread = None
		self.results = None

	def getcounted(self):
		return (self.total != None)

	def save(self):
		"""Saves the folder settings in database"""
		cursor = db.cursor()
		cursor.execute("UPDATE vfolders SET name=%s, query=%s, parent=%s "
					   "WHERE id=%s", (self.name, self.uquery,
									   self.parent, self.id))

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

	def AddMsgID(self, id):
		"""Add an message by id to folder

		First remove the message from the negative sequence.  Then, if
		the message still doesn't show up in the query, add it to
		the positive override sequence.
		"""
		sequences.Sequence("-" + self.name).DeleteID(id)
		if not self.vfquery.count(" AND headers.id = %d" % id):
			sequences.Sequence("+" + self.name).AddMessageID(id)

	def RemoveMsgID(self, id):
		"""Remove a message by id from folder, see AddMsgID"""
		sequences.Sequence("+" + self.name).DeleteID(id)
		if self.vfquery.count(" AND headers.id = %d" % id):
			sequences.Sequence("-" + self.name).AddMessageID(id)
			
	def MoveMsgID(self, id, dest_vf):
		"""Move a message from current vfolder to another"""
		self.RemoveMsgID(id)
		dest_vf.AddMsgID(id)



# Revision History
# $Log: vfolder.py,v $
# Revision 1.17  2001/05/26 19:19:56  bescoto
# *** empty log message ***
#
# Revision 1.16  2001/05/26 18:15:48  bescoto
# Reorganization of vfolder and query structure.  Added adding/removing
# individual messages of folders through use of override sequences.
# Queries now support recursive macro substitution e.g. VFOLDER:foo
#
# Revision 1.14  2001/04/19 18:24:16  dtrg
# Added the ability to change the readstatus of a message. Also did some
# minor tweaking to various areas.
#
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
