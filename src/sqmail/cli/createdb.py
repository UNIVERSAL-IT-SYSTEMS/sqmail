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

	setsetting(cursor, "vfolders", ["Received Messages", \
		"Deleted Messages", "Sent Messages", "root"])

	setsetting(cursor, "vfolder query Received Messages", \
		"(readstatus = 'Read') or (readstatus = 'Unread')")

	setsetting(cursor, "vfolder query Deleted Messages", \
		"(readstatus = 'Deleted')")

	setsetting(cursor, "vfolder query Sent Messages", \
		"(readstatus = 'Sent')")

	setsetting(cursor, "vfolder query root", \
		"(fromfield like '%root%')")
	setsetting(cursor, "vfolder parent root", "Received Messages")

	print "Disconnecting..."

	connection.close()
	print "\nDone."

# Revision History
# $Log: createdb.py,v $
# Revision 1.1  2001/01/09 11:41:24  dtrg
# Added the create-database CLI command.
#

