# VFolder abstraction.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/vfolder.py,v $
# $State: Exp $

"""Classes and Functions related to VFolders

The vfolders table can be created with:

CREATE TABLE vfolders
   (id INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT,
    name TEXT,
    size INTEGER UNSIGNED,
    unread INTEGER UNSIGNED,
	curmsg INTEGER UNSIGNED,
	curmsgpos INTEGER UNSIGNED,
    query TEXT,
    children TEXT);

id is a unique integer identifying the vfolder.
name is some text describing it, which doesn't have to be unique.
size is the number of messages in the folder
unread is the number of unread messages in the folder
curmsg is the id of the current message
curmsgpos is the position of the current message (e.g. 3rd, 5th)
query is the query the user types in the gui
children is a string of folder ids separated by spacse (e.g. "5 37 12")

Most of these should be kept in tight sync with the database.  curmsg
and curmsgpos however are less important (they aren't modified by
incoming mail in the background for instance) and can be saved once
per session.

"""

import string
import sqmail.db
import sqmail.sequences
import sqmail.queries


class VFolderException(Exception):
	pass

class VFolder:
	"""Virtual Folders are what the user manipulates as folders"""
	def __init__(self, id, name, size, unread,
				 curmsg, curmsgpos, querystring, childids):
		"""Construct vfolder

		Do not call this constructor directly (that is why it is hard
		to use), instead use a method of VFolderManager.

		self.dependencies is a dictionary of vfolders (indexed by id)
		that the current folder depends on.  It should not include
		itself.

		"""
		self.id = id
		self.name = name
		self.size = size
		self.unread = unread
		self.curmsg = curmsg
		self.curmsgpos = curmsgpos
		self.uquery = sqmail.queries.UserQuery(querystring, self)
		self.childids = childids

		self.dependencies = None
		self.vfquery = None
		self.cquery = sqmail.queries.CacheQuery("", self)

	def scan(self, msgid, range):
		"""Return scan listings in range about msgid

		If range is positive, the scan will return range messages
		after or equal to msgid, if available.  If range is negative,
		try to return -range messages before msgid.

		"""
		if msgid is None: msgid = 0
		columns = ("headers.id,readstatus,fromfield,"
				   "realfromfield,subjectfield,unix_timestamp(date)")
		if range < 0:
			beforeid = list(self.cquery.selectcolumns(columns,
							"AND sequence_data.id < %d" % msgid,
							"sequence_data.id DESC", -range))
			beforeid.reverse()
			return beforeid
		return self.cquery.selectcolumns(columns,
							 "AND sequence_data.id >= %d" % msgid,
                             "sequence_data.id", range)

	def rebuildindex(self):
		"""Clear caching sequence and rebuild, update size and unread

		First, if the folder does not have a vfquery, set it.  Then
		use it to determine which messages should be put into the
		caching sequence.  Because we cannot use an insert to put rows
		into a table mentioned in the select which the insert uses, we
		must add the messages to a temporary table, and then copy them
		back.

		"""
		if not self.vfquery: self.getvfquery()
		cachesid = self.getcacheseq().getsid()
		selstr = self.vfquery.qschema % ("%d,headers.id" % cachesid)
		sqmail.db.execute("DELETE FROM sequence_data WHERE sid = %s", cachesid)
		sqmail.db.execute("INSERT INTO sequence_temp (sid, id) " + selstr)
		sqmail.db.execute("INSERT INTO sequence_data (sid, id) "
						  "SELECT sid,id FROM sequence_temp")
		sqmail.db.execute("DELETE FROM sequence_temp WHERE 1")

	def getvfquery(self, force = None):
		"""Expand self.uquery into self.vfquery and return result"""
		if force or self.vfquery is None:
			self.vfquery = self.uquery.ExpandToVFQuery(self)
			self.vfquery.setqschema()
		return self.vfquery

	def getdependencies(self, force = None):
		"""Return dependencies dictionary, building vfquery if necessary"""
		if force or self.dependencies is None:
			self.dependencies = self.getvfquery().folderdeps.copy()
			del self.dependencies[self.id]
		return self.dependencies

	def getsize(self, forcequery = None):
		"""Return number of messages, querying if not available

		If forcequery is "table", try to read the result from the
		vfolders table instead of recomputing it from scratch.

		"""
		if forcequery == "table":
			self.size = self._getattr("size")
		elif forcequery or self.size is None:
			self.setsize(self.cquery.count())
		return self.size

	def getunread(self, forcequery = None):
		"""Return number of unread messages, querying if necessary"""
		if forcequery == "table":
			self.unread = self._getattr("unread")
		elif forcequery or self.unread is None:
			self.setunread(self.cquery.countunread())
		return self.unread

	def getcurmsg(self):
		"""Return current message id"""
		return self.curmsg

	def getcurmsgpos(self, forcequery = None):
		"""Return position of current message, setting table if necessary

		If curmsg is None, this should be None too, and no query will
		be forced.

		"""
		if not forcequery and self.curmsgpos: return self.curmsgpos
		if not self.curmsgpos and not self.getcurmsg(): return None

		if self.getcurmsg(): cmp = self.cquery.count("AND headers.id <= %d" %
													 self.getcurmsg())
		else: cmp = None
		self.setcurmsgpos(cmp)
		return cmp

	def getuquerystr(self):
		return str(self.uquery)
	
	def getname(self):
		return self.name

	def _getattr(self, attribute):
		"""Read attribute from vfolders table"""
		return sqmail.db.fetchone("SELECT " + attribute + " FROM vfolders "
								  "WHERE id = %s", self.id)[0]

	def _setattr(self, attribute, value):
		"""Update the vfolders table by setting attribute to value"""
		sqmail.db.execute("UPDATE vfolders SET " + attribute +
						  " = %s WHERE id = %s", (value, self.id))

	def setname(self, name):
		self.name = name
		self._setattr("name", name)

	def setsize(self, size):
		self.size = size
		self._setattr("size", size)

	def setunread(self, unread):
		self.unread = unread
		self._setattr("unread", unread)

	def setcurmsg(self, curmsg):
		self.curmsg = curmsg
		self._setattr("curmsg", curmsg)

	def setcurmsgpos(self, curmsgpos):
		self.curmsgpos = curmsgpos
		self._setattr("curmsgpos", curmsgpos)

	def setuquery(self, uquerystr):
		"""Set uquery from string, recurse on folders which depend on self"""
		self.uquery = sqmail.queries.UserQuery(uquerystr, self)
		for depender in get_what_depends_on_recursive(self):
			depender.recalculate_all()
		self._setattr("query", uquerystr)

	def recalculate_all(self):
		"""Recompute all of the folder's information from query

		Rebuild self.vfquery and the caching sequence, and reset the
		size and number of unread messages.  Then update dependencies.

		"""
		self.getvfquery(1)
		self.rebuildindex()
		self.getsize(1)
		self.getunread(1)
		self.getdependencies(1)
		list_vfolders_by_dep(1)

	def _changebyone(self, attribute, opstr):
		"""helper function for increment/decrement methods

		The folder information in memory does not have to be in sync
		with the database for these to work.

		"""
		sqmail.db.execute("UPDATE vfolders SET %s = %s %s 1 WHERE id = %d" %
						  (attribute, attribute, opstr, self.id))

	def increment_size(self):
		self.size = self.size + 1
		self._changebyone("size", "+")

	def increment_unread(self):
		self.unread = self.unread + 1
		self._changebyone("unread", "+")

	def decrement_size(self):
		self.size = self.size - 1
		self._changebyone("size", "-")

	def decrement_unread(self):
		self.unread = self.unread - 1
		self._changebyone("unread", "-")

	def setquery(self, querystring):
		"""Set query string and recompute index, size, and unread"""
		self.uquery = sqmail.queries.UserQuery(querystring)
		self._setattr("query", querystring)
		self.rebuildindex()
		self.getsize()
		self.getunread()

	def addchildid(self, id, position = None):
		"""Add id to folder's children at position"""
		if not position: position = len(self.childids)
		self.childids.insert(position, id)
		self._updatechildren()

	def deletechildid(self, position):
		"""Remove the child at position, starting with 0"""
		del self.childids[position]
		self._updatechildren()

	def _updatechildren(self):
		"""Save self.childids to database"""
		sqmail.db.execute("UPDATE vfolders SET children = %s WHERE id = %s",
						  (string.join(map(lambda x: "%d" % x,
										   self.childids)), self.id))

	def getchildren(self):
		"""Return list of VFolder children"""
		return map(get_by_id, self.childids)

	def getparents(self):
		"""Return list of vfolders which have self as a child"""
		return filter(lambda x, s = self: s.id in x.childids, list_vfolders())

	def getsiblings(self):
		"""Get sibling VFolders, including any half brothers and sisters."""
		sibs_and_me = []
		for parent in self.getparents():
			sibs_and_me.extend(parent.getchildren())
		return filter(lambda x, s=self: x is not s, sibs_and_me)
		
	def getposseq(self):
		"""Return the override sequence which forces messages in

		The sequence name will be, e.g, "+43" if the folder's id is
		43.  Similarly, the negative sequence will be "-43".  If the
		sequence does not exist, this creates it.

		"""
		name = "FolderOverrideIn:" + str(self.id)
		return (sqmail.sequences.get_by_name(name) or
				sqmail.sequences.create_sequence(name))

	def getnegseq(self):
		"""Return the override sequence which forces messages out"""
		name = "FolderOverrideOut:" + str(self.id)
		return (sqmail.sequences.get_by_name(name) or
				sqmail.sequences.create_sequence(name))

	def getcacheseq(self):
		"""Return the sequence used to cache query results or None"""
		name = "FolderCache:" + str(self.id)
		return (sqmail.sequences.get_by_name(name) or
				sqmail.sequences.create_sequence(name))

	def processmsg(self, sqmsg):
		"""Process new sqmail message.  True if message added.

		This should be called after the message has been given an id
		and saved to the database.  processmsg updates size, unread,
		and the cacheing sequence.

		"""
		if self.vfquery.containsid(sqmsg.id):
			self.getcacheseq().addid(sqmsg.id)
			self.increment_size()
			if sqmsg.readstatus == "Unread":
				self.increment_unread()
			return 1
		else: return None

	def addmsgid(self, id):
		"""Force an message by id to folder

		First remove the message from the negative sequence.  Then, if
		the message still doesn't show up in the query, add it to
		the positive override sequence.

		"""
		self.getnegseq().deleteid(id)
		if not self.vfquery.count(" AND headers.id = %d" % id):
			self.getposseq().addid(id)

	def deletemsgid(self, id):
		"""Remove a message by id from folder, see self.addid"""
		self.getposseq().deleteid(id)
		if self.vfquery.count(" AND headers.id = %d" % id):
			self.getnegseq().addid(id)
			
	def movemsgid(self, id, dest_vf):
		"""Move a message from current vfolder to another"""
		self.deletemsgid(id)
		dest_vf.addmsgid(id)


class VFolderManagerClass:
	"""Find, create, destroy, and inspect dependencies between vfolders

	There should only be one instance of this class.  When created, it
	reads the contents of the vfolders table into memory.
	
	"""
	def __init__(self):
		self.vfolderids = {}
		self.vfolders_by_dep = None
		for row in sqmail.db.fetchall("SELECT id,name,size,unread,curmsg,"
									  "curmsgpos,query,children "
									  "FROM vfolders"):
			vf = VFolder(row[0], row[1], row[2], row[3], row[4], row[5],
						 row[6], map(int, string.split(row[7])))
			self.vfolderids[vf.id] = vf

	def get_by_name(self, name):
		"""Return first vfolder with name, or none otherwise"""
		for vf in self.vfolderids.values():
			if vf.name == name: return vf
		return None

	def get_by_id(self, id):
		"""Return vfolder with given id, or None if none"""
		if self.vfolderids.has_key(id):
			return self.vfolderids[id]
		else: return None

	def create_vfolder(self, name, parentid, query = "", children = []):
		"""Create a vfolder with the given name/parent and update database"""
		sqmail.db.execute("INSERT INTO vfolders (name, query, children) "
						  "VALUES (%s, %s, %s)",
						  (name, query, string.join(map(str, children))))
		id = sqmail.db.fetchone("SELECT LAST_INSERT_ID()")[0]
		vf = VFolder(id, name, None, None, None, None, query, children)
		self.vfolderids[vf.id] = vf
		self.vfolderids[parentid].addchildid(id)
		return vf

	def list_vfolders(self):
		"""Return list of vfolders in no particular order"""
		return self.vfolderids.values()

	def get_what_depends_on(self, dependee):
		"""Return list of vfolders that depend upon vfolder dependee"""
		deps = []
		for depender in self.list_vfolders():
			if depender.getdependencies().has_key(dependee.id):
				deps.append(depender)
		return deps

	def get_what_depends_on_recursive(self, dependee):
		"""Return list of vfolders that depend sooner or later on folder

		This function isn't very fast, and could be rewritten if speed
		is an issue.  The output is returned in dependency order, as
		in list_vfolders_by_dep.  It includes dependee.

		"""
		olddepdict, depdict = {}, { dependee.id: dependee }
		while olddepdict != depdict:
			olddepdict.update(depdict)
			for oldfold in olddepdict.values():
				for depender in self.get_what_depends_on(oldfold):
					depdict[depender.id] = depender
		return filter(lambda vf, d = depdict: d.has_key(vf.id),
					  self.list_vfolders_by_dep())

	def list_vfolders_by_dep(self, forcecalculation = None):
		"""Return list of vfolders in order by dependency

		In the resulting list of vfolders, no vfolder in the list
		should depend on a vfolder after it.  Thus, when updating all
		folders, they can be only done once in this order.

		"""
		if forcecalculation or not self.vfolders_by_dep:
			origin, destination = self.list_vfolders(), []
			while 1:
				for vf in origin:
					for depender in vf.getdependencies().values():
						if depender not in destination: break
					else:
						origin.remove(vf)
						destination.append(vf)
						break
				else: break
			if origin:
				print "Circular Folder dependencies!"
				destination.extend(origin)
			self.vfolders_by_dep = destination
		return self.vfolders_by_dep

	def filter_incoming(self, sqmsg):
		"""Update vfolder listings with new message

		Goes through all the vfolders and updates their messages
		caches, and size, and unread numbers.  Then for each vfolder
		which was updated, it sticks its id in a sequence named
		"UpdatedVFolders" so that any running SQmaiL instance will
		know what to check for.

		"""
		seq = (sqmail.sequences.get_by_name("UpdatedVFolders") or
			   sqmail.sequences.create_sequence("UpdatedVFolders"))
		for vf in self.list_vfolders_by_dep():
			if vf.processmsg(sqmsg): seq.addid(vf.id)
			

# Warning, this is active code, so vfolder should not be imported if
# the database is not set up correctly.

VFolderManager = VFolderManagerClass()

# For convenience, bind VFolderManager methods to functions with
# global (module) scope.  Thus you can call vfolder.get_by_id
# instead of vfolder.VFolderManager.get_by_sid

for methodname in filter(lambda x: not x[0]=="_",
						 dir(VFolderManagerClass)):
	globals()[methodname] = eval("VFolderManager."+methodname)



# Revision History
# $Log: vfolder.py,v $
# Revision 1.19  2001/06/08 04:38:16  bescoto
# Multifile diff: added a few convenience functions to db.py and sequences.py.
# vfolder.py and queries.py are largely new, they are part of a system that
# caches folder listings so the folder does not have to be continually reread.
# createdb.py and upgrade.py were changed to deal with the new folder formats.
# reader.py was changed a bit to make it compatible with these changes.
#
# Revision 1.18  2001/06/01 19:26:39  bescoto
# Modifications to be compatible with new sequences, couple of bug fixes
#
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
