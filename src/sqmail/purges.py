# Purge abstraction.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/purges.py,v $
# $State: Exp $

import os
import rfc822
import string
import sqmail.db
import cPickle
import cStringIO
import mimetools
import multifile
import types

def load_purge(name):
	cursor = sqmail.db.cursor()
	cursor.execute("SELECT active, vfolder, condition FROM purges WHERE "\
		"name = \""+sqmail.db.escape(name)+"\"")
	return cursor.fetchone()
	
def save_purge(name, active, vfolder, condition):
	cursor = sqmail.db.cursor()
	cursor.execute("SELECT COUNT(name) FROM purges WHERE name = \""+sqmail.db.escape(name)+"\"")
	if cursor.fetchone()[0]:
		cursor.execute("UPDATE purges SET "\
			+"name=\""+sqmail.db.escape(name)+"\", "\
			+"active="+str(active)+", "\
			+"vfolder="+str(vfolder)+", "\
			+"condition=\""+sqmail.db.escape(condition)+"\" "\
			+"WHERE name=\""+sqmail.db.escape(name)+"\"")
	else:
		cursor.execute("INSERT INTO purges (name, active, vfolder, condition) VALUES "\
			+"(\""+sqmail.db.escape(name)+"\", "\
			+str(active)+", "\
			+str(vfolder)+", "\
			+"\""+sqmail.db.escape(condition)+"\")")

def delete_purge(name):
	cursor = sqmail.db.cursor()
	cursor.execute("SELECT COUNT(name) FROM purges WHERE name = \""+sqmail.db.escape(name)+"\"")
	if cursor.fetchone()[0]:
		cursor.execute("DELETE FROM purges WHERE "
			+"name=\""+sqmail.db.escape(name)+"\"")
	else:
		raise KeyError

def enumerate():
	cursor = sqmail.db.cursor()
	list = []
	cursor.execute("SELECT name FROM purges")
	while 1:
		name = cursor.fetchone()
		if not name:
			break
		list.append(name[0])
	list.sort()
	return list

class Purge:
	def __init__(self, name, active=0, vfolder=None, condition=None):
		if condition:
			self.name = name
			self.active = active
			self.vfolder = vfolder
			self.condition = condition
		else:
			self.name = name
			i = load_purge(name)
			if i:
				self.active, self.vfolder, self.condition = i
			else:
				raise KeyError
		self.query = None
	
	def save(self):
		save_purge(self.name, self.active, self.vfolder, self.condition)

	def delete(self):
		delete_purge(self.name)

	def load_query(self):
		if self.vfolder:
			vf = sqmail.vfolder.VFolder(self.vfolder)
			self.query = vf.gethierarchicquery()
		else:
			self.query = "1"

	def count_matching(self):
		if not self.query:
			self.load_query()
		cursor = sqmail.db.cursor()
		cursor.execute("SELECT COUNT(*) FROM headers WHERE ("\
			+self.query+") AND ("+self.condition+")")
		return cursor.fetchone()[0]

	def count_total(self):
		if not self.query:
			self.load_query()
		cursor = sqmail.db.cursor()
		cursor.execute("SELECT COUNT(*) FROM headers WHERE ("\
			+self.query+")")
		return cursor.fetchone()[0]
	
	def purge_now(self):
		if not self.query:
			self.load_query()
		if not self.active:
			return None
		cursor = sqmail.db.cursor()

		# Count messages.

		total = self.count_total()

		# Actually delete them.

		cursor.execute("LOCK TABLES headers WRITE, bodies WRITE")
		idlist = []
		count = 0
		cursor.execute("SELECT id FROM headers WHERE ("\
			+self.query+") AND ("+self.condition+")")
		while 1:
			id = cursor.fetchone()
			if not id:
				break
			idlist.append(str(int(id[0])))
			count = count + 1
		if (count > 0):
			idlist = "((id=" + string.join(idlist, ") OR (id=") + "))"
		else:
			idlist = "0"

		cursor.execute("DELETE FROM headers WHERE "+idlist)
		cursor.execute("DELETE FROM bodies WHERE "+idlist)
		# Why doesn't this work?
		#count = cursor.fetchone()[0]

		cursor.execute("UNLOCK TABLES")
		
		return (count, total)

# Revision History
# $Log: purges.py,v $
# Revision 1.2  2001/06/15 09:34:36  dtrg
# Changed a str(x) to a str(int(x))... Python's habit of putting L after
# longs is confused MySQL.
#
# Revision 1.1  2001/03/01 19:55:38  dtrg
# Completed the command-line based purges system. Hesitantly applied it to
# my own data. Nothing catastrophic has happened yet.
#
