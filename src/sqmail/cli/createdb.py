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

def addvfolder(cursor, name, query, parent):
	cursor.execute( \
		"insert into vfolders"\
		"  (name, query, parent)"\
		"  values ('"+name+"', '"+query+"', "+str(parent)+")");
	cursor.execute( \
		"select last_insert_id()")
	return cursor.fetchone()[0]

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

	cursor.execute ( \
		"create table vfolders"\
		"  (id integer not null primary key auto_increment,"\
		"  name text,"\
		"  query text,"\
		"  parent integer)");
		
	cursor.execute( \
		"create table addressbook"\
		"  (email text,"\
		"  realname text)");

	cursor.execute( \
		"create table aliases"\
		"  (name text,"\
		"  addresslist text)");
		
	print "Setting up..."

	cursor.execute( \
		"insert into settings"\
		"  (name, value)"\
		"  values ('idcounter', '1')");

	r = addvfolder("Received Messages", \
		"(readstatus = 'Read') or (readstatus = 'Unread')", \
		0)

	addvfolder("Messages from root", \
		"fromfield like '%root%'", \
		r)

	addvfolder("Deleted Messages", \
		"(readstatus = 'Deleted')", \
		0)

	addvfolder("Sent Messages", \
		"(readstatus = 'Sent')", \
		0)

	print "Disconnecting..."

	connection.close()
	print "\nDone."

# Revision History
# $Log: createdb.py,v $
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

