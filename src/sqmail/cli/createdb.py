# CLI utility that creates a new database.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/cli/createdb.py,v $
# $State: Exp $

import sys
import string
import time
import getpass
import cPickle
import cStringIO
import sqmail.db
import sqmail.utils

import MySQLdb
db = MySQLdb

def setsetting(cursor, name, value):
	fp = cStringIO.StringIO()
	cPickle.dump(value, fp)
	cursor.execute( \
		"insert into settings"\
		"  (name, value)"\
		"  values ('"+name+"', '"+\
			sqmail.db.escape(fp.getvalue())+"')");

def SQmaiLCreateDB():
	dbname = "sqmail"
	username = getpass.getuser()

	print "Warning! This program will create a SQmaiL database, possibly deleting"
	print "the old one, which may have hundreds of megabytes of mail in it. Here"
	print "be dragons."

	host = sqmail.utils.getfield("\nHost to connect to:", "localhost")
	passwd = getpass.getpass("Root administrator password: ")

	try:
		connection = db.connect(user="root", host=host, passwd=passwd)
		cursor = connection.cursor()
	except db.OperationalError:
		print "\nThe password was not recognised."
		print "\nI need administrator access to create the SQmaiL database. Once that"
		print "has been done, I no longer need it. Contact your administrator and"
		print "try again."
		sys.exit()

	dbname = sqmail.utils.getfield("What do you want to call the database?", dbname)

	exists = 1
	try:
		cursor.execute("use "+dbname)
	except db.OperationalError:
		exists = 0

	if (exists == 1):
		print "\nA database of that name already exists. If you want, I can delete it"
		print "for you so you can create a new, empty one. You will lose all data in"
		print "this database. If you are sharing your SQL server with other people,"
		print "then be very, very careful."
		value = sqmail.utils.getfield("\nTo delete the database type YES.", "no")
		if (value != "YES"):
			print "\nAborted. Good move."
			sys.exit()

		print "\nDeleting database..."
		cursor.execute("drop database "+dbname)
		print

	username = sqmail.utils.getfield("Which user do you want to own the database?", username)
	userpasswd = getpass.getpass("And the user's password? ")

	print "\nCreating database..."

	cursor.execute("create database "+dbname)

	print "Setting permissions..."

	cursor.execute("grant all privileges on "+dbname+".* to "+username)

	print "Reconnecting as "+username+"..."

	connection.close()
	connection = db.connect(host=host, user=username, passwd=userpasswd, db=dbname)
	cursor = connection.cursor()

	print "Creating tables..."

	cursor.execute( \
		"create table settings"\
		"  (name text,"\
		"  value text)");

	cursor.execute( \
		"create table headers"\
		"  (id integer not null primary key,"\
		"  tofield text,"\
		"  fromfield text,"\
		"  realfromfield text,"\
		"  ccfield text,"\
		"  subjectfield text,"\
		"  date datetime not null,"\
		"  annotation text,"\
		"  readstatus enum ('Read', 'Unread', 'Deleted', 'Sent') not null)");
	cursor.execute( \
		"create table bodies"\
		"  (id integer not null primary key,"\
		"  header longtext,"\
		"  body longtext)");
	setsetting(cursor, "message data version", "0.3")

	cursor.execute("""
            CREATE TABLE vfolders
                (id INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT,
                 name TEXT,
                 size INTEGER UNSIGNED,
                 unread INTEGER UNSIGNED,
                 curmsg INTEGER UNSIGNED,
                 curmsgpos INTEGER UNSIGNED,
                 query TEXT,
                 children TEXT)""")
	cursor.execute("INSERT INTO vfolders (name, query, children) "
				   "VALUES ('/', '1', '')")
	setsetting(cursor, "vfolder data version", "0.3")
		
	cursor.execute( \
		"create table addressbook"\
		"  (email text,"\
		"  realname text)");

	cursor.execute( \
		"create table aliases"\
		"  (name text,"\
		"  addresslist text)");
	setsetting(cursor, "aliases data version", "0.3")
		
	cursor.execute( \
		"CREATE TABLE purges"\
		"  (active TINYINT,"\
		"  name TEXT,"\
		"  vfolder INTEGER,"\
		"  condition TEXT)");

	cursor.execute( \
		"CREATE TABLE picons"\
		"  (email VARCHAR(128) PRIMARY KEY NOT NULL,"\
		"  image TEXT)");
	setsetting(cursor, "purges data version", "0.2")

	# Add sequence tables
	cursor.execute("""CREATE TABLE sequence_data
                      (sid INTEGER UNSIGNED NOT NULL,
                       id INTEGER UNSIGNED NOT NULL,
                       UNIQUE INDEX sidid (sid, id))""")
	cursor.execute("""CREATE TABLE sequence_temp
                      (sid INTEGER UNSIGNED NOT NULL,
                       id INTEGER UNSIGNED NOT NULL,
                       UNIQUE INDEX sidid (sid, id))""")
	cursor.execute("""CREATE TABLE sequence_descriptions
                      (sid INTEGER UNSIGNED NOT NULL
                           AUTO_INCREMENT PRIMARY KEY,
                       name TEXT NOT NULL,
                       misc LONGBLOB)""")
	setsetting(cursor, "sequences data version", "0.0")

	cursor.execute( \
		"insert into settings"\
		"  (name, value)"\
		"  values ('idcounter', '1')");

	from sqmail import vfolder
	rootid = vfolder.get_by_name("/").id
	vfolder.create_vfolder("Received Messages", rootid,
						   "(readstatus = 'Read') or (readstatus = 'Unread')")
	vfolder.create_vfolder("Messages from root", rootid,
						   "fromfield like '%root%'")
	vfolder.create_vfolder("Deleted Messages", rootid,
						   "(readstatus = 'Deleted')")
	vfolder.create_vfolder("Sent Messages", rootid,
						   "(readstatus = 'Sent')")

	print "Disconnecting..."

	connection.close()
	print "\nDone."

# Revision History
# $Log: createdb.py,v $
# Revision 1.7  2001/08/06 20:45:47  bescoto
# Changed SQmaiLCreateDB() to make the new version of the vfolder table (v0.3)
# now expected by the rest of SQmaiL.
#
# Revision 1.6  2001/06/08 04:38:16  bescoto
# Multifile diff: added a few convenience functions to db.py and sequences.py.
# vfolder.py and queries.py are largely new, they are part of a system that
# caches folder listings so the folder does not have to be continually reread.
# createdb.py and upgrade.py were changed to deal with the new folder formats.
# reader.py was changed a bit to make it compatible with these changes.
#
# Revision 1.5  2001/05/26 18:22:29  bescoto
# Now adds sequence_data and sequence_descriptions tables
#
# Revision 1.4  2001/05/01 18:23:42  dtrg
# Added the Debian package building stuff. Now much easier to install.
# Some GUI tidying prior to the release.
# Did some work on the message DnD... turns out to be rather harder than I
# thought, as you can't have a CTree do its own native DnD and also drag
# your own stuff onto it at the same time.
#
# Revision 1.3  2001/01/22 11:47:45  dtrg
# create-database turned out not to be working (a simple syntax bug plus I
# forgot to emit a new-style vfolders setting). Fixed. Also added some
# bulletproofing to protect against this sort of problem.
#
# Revision 1.2  2001/01/19 20:37:23  dtrg
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
# Revision 1.1  2001/01/09 11:41:24  dtrg
# Added the create-database CLI command.
#

