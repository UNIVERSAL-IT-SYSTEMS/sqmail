# Assorted utilities.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/utils.py,v $
# $State: Exp $

import os
import sys
import string
import rfc822
import sqmail.db
import cStringIO
import cPickle

def getfield(prompt, default):
        sys.stdout.write(prompt)
        sys.stdout.write(" [")
        sys.stdout.write(default)
        sys.stdout.write("]: ")
        sys.stdout.flush()
        value = sys.stdin.readline()
        value = value[0:-1]
        if (value == ""):
                value = default
        return value

__settings = {}
def getsetting(name, default=None):
	global __settings
	if (__settings.has_key(name)):
		return __settings[name]
	cursor = sqmail.db.cursor()
	cursor.execute("SELECT value FROM settings WHERE name = '%s'" % name)
	value = cursor.fetchone()
	if not value:
		return default
	fp = cStringIO.StringIO(value[0])
	value = cPickle.load(fp)
	__settings[name] = value
	return value

def setsetting(name, value):
	global __settings
	__settings[name] = value
	fp = cStringIO.StringIO()
	cPickle.dump(value, fp)
	cursor = sqmail.db.cursor()
	value = sqmail.db.escape(fp.getvalue())
	cursor.execute("SELECT COUNT(*) FROM settings WHERE name = '%s'" % name)
	if (cursor.fetchone()[0] == 0):
		cursor.execute("INSERT INTO settings (name, value) VALUES ('%s', '%s')" \
			% (name, value))
	else:
		cursor.execute("UPDATE settings SET value = '%s' WHERE " \
			"name = '%s'" % (value, name))

def parse_mimeheader(s):
	if not s:
		return []
	list = []
	if (";" in s):
		i = string.index(s, ";")
		s = s[i:]
	else:
		return [s]
		
	while (s[:1] == ';'):
		s = s[1:]
		if (";" in s):
			end = string.index(s, ";")
		else:
			end = len(s)
		f = s[:end]
		if ("=" in f):
			i = string.index(f, "=")
			f = string.lower(string.strip(f[:i])) + "=" + \
				string.strip(f[i+1:])
		list.append(string.strip(f))
		s = s[end:]
	return list
	
def get_mime_param(list, name):
	name = string.lower(name) + "="
	n = len(name)
	for p in list:
		if (p[:n] == name):
			return rfc822.unquote(p[n:])
	return None

def load_xpm(fp):
	pixdata = []
	if (fp.readline()[:-1] != "/* XPM */"):
		return None
	for i in fp.readlines():
		i = string.split(i, '"')
		if (len(i) == 3):
			pixdata.append(i[1])
	if (pixdata == []):
		return None
	return pixdata
	
# Revision History
# $Log: utils.py,v $
# Revision 1.3  2001/03/09 20:36:19  dtrg
# First draft picons support.
#
# Revision 1.2  2001/03/09 10:34:14  dtrg
# When you do str(i) when i is a long, Python returns a string like "123L".
# This really upsets the SQL server. So I've rewritten large numbers of the
# SQL queries to use % syntax, which doesn't do that.
#
# Revision 1.1  2001/01/05 17:27:48  dtrg
# Initial version.
#




