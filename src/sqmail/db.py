# Database abstraction.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/db.py,v $
# $State: Exp $

import sys
import os
import utils
import getpass
import MySQLdb
import pickle
import string

__prefs = None
__connection = None

def stdin_asker():
	host = utils.getfield("Host to connect to?", "localhost")
	username = utils.getfield("User name?", getpass.getuser())
	passwd = getpass.getpass()
	dbname = utils.getfield("Database name?", "sqmail")
	return {"host":host, "user":username, "pass":passwd, "db":dbname};

def writeprefs():
	global __prefs
	try:
		fp = open(os.path.expanduser("~/.sqmail"), "w")
		pickle.dump(__prefs, fp)
		fp.close()
		os.chmod(os.path.expanduser("~/.sqmail"), 0600)
	except IOError:
		print "Unable to write back preferences"

def readprefs():
	global __prefs
	try:
		fp = open(os.path.expanduser("~/.sqmail"), "r")
		__prefs = pickle.load(fp)
		fp.close()
	except IOError:
		return None

def loadprefs():
	global __prefs
	if (__prefs == None):
		readprefs()
		if (__prefs == None):
			__prefs = stdin_asker()
			writeprefs()

def db():
	return MySQLdb

def connect():
	global __prefs
	global __connection
	if not __connection:
		loadprefs()
		__connection = MySQLdb.connect(db=__prefs["db"], host=__prefs["host"], \
			user=__prefs["user"], passwd=__prefs["pass"])
	return __connection
		
def cursor():
	global __connection
	if not __connection:
		connect()
	return __connection.cursor()

def lock(cursor):
	cursor.execute("LOCK TABLES settings WRITE, headers WRITE, bodies WRITE")

def unlock(cursor):
	cursor.execute("UNLOCK TABLES")

def getnewid(cursor):
	cursor.execute("SELECT value FROM settings WHERE name = 'idcounter'")
	id = cursor.fetchone()[0]
	cursor.execute("UPDATE settings SET value = value + 1 WHERE name = 'idcounter'")
	return int(id)

def escape(str):
	if not str:
		return ""
	str = string.replace(str, "\\", "\\\\")
	str = string.replace(str, "\n", "\\n")
	str = string.replace(str, "\r", "\\r")
	str = string.replace(str, "\t", "\\t")
	str = string.replace(str, "'", "\\'")
	str = string.replace(str, '"', '\\"')
	return str

def execute(command, argtuple = None):
	"""Get a cursor and run command on it.  Returns of cursor.execute"""
	print "Executing: ", command, argtuple
	c = cursor()
	if argtuple: return c.execute(command, argtuple)
	else: return c.execute(command)

def fetchall(query, argtuple = None):
	"""Get a cursor, run query, and return results of cursor() fetchall."""
	print "Fetchall: ", query, argtuple
	c = cursor()
	if argtuple: c.execute(query, argtuple)
	else: c.execute(query)
	return c.fetchall()

def fetchone(query, argtuple = None):
	"""Same as fetchall but only return one row"""
	print "Fetchone: ", query, argtuple
	c = cursor()
	if argtuple: c.execute(query, argtuple)
	else: c.execute(query)
	return c.fetchone()

# Revision History
# $Log: db.py,v $
# Revision 1.4  2001/06/08 04:38:16  bescoto
# Multifile diff: added a few convenience functions to db.py and sequences.py.
# vfolder.py and queries.py are largely new, they are part of a system that
# caches folder listings so the folder does not have to be continually reread.
# createdb.py and upgrade.py were changed to deal with the new folder formats.
# reader.py was changed a bit to make it compatible with these changes.
#
# Revision 1.3  2001/06/01 19:26:59  bescoto
# Defined a few convenience functions
#
# Revision 1.2  2001/03/09 10:58:42  dtrg
# getnewid() was returning the new id as a string. Eeek.
#
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#


