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

# Revision History
# $Log: db.py,v $
# Revision 1.2  2001/03/09 10:58:42  dtrg
# getnewid() was returning the new id as a string. Eeek.
#
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#


