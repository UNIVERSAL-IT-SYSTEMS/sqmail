# CLI utility that displays an individual message.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/cli/show.py,v $
# $State: Exp $

import sys
import string
import time
import getpass
import mailbox
import sqmail.db
import sqmail.message
import sqmail.vfolder
import getopt
import os.path
import cPickle
import time
import types

currentmsg = None
attachment = None
saveattachment = None
nomime = 0

def usage():
	print "Syntax: " + sys.argv[0] + " show [options] [msgnumber]"
	print "  --nomime           Don't attempt to MIME decode"
	print "  --attachment <id>  Show attachment (defaults to first text/plain)"
	print "  --save <filename>  Save attachment, don't display it"
	print "msgnumber can be n or p for the next or previous message."
	
def parseargs():
	global currentmsg, attachment, saveattachment, nomime
	try:
		opts, args = getopt.getopt(sys.argv[2:], "ha:s:", \
			["help", "attachment:", "save:"])
	except getopt.GetoptError:
		usage()
		sys.exit(2)

	for o, a in opts:
		if (o in ("-h", "--help")):
			usage()
			sys.exit()
		elif (o in ("-n", "--nomime")):
			nomime = 1
		elif (o in ("-a", "--attachment")):
			attachment = a
		elif (o in ("-s", "--save")):
			saveattachment = a
	
	if (len(args) == 1):
		if (args[0] == "n"):
			currentmsg = "Next"
		elif (args[0] == "p"):
			currentmsg = "Prev"
		else:
			currentmsg = int(args[0])
	elif (len(args) != 0):
		usage()
		sys.exit(2)

def mimelist(data, count):
	for i in range(len(data)):
		if (data[i][3] != ""):
			print "%s: %s (%s; %d bytes)" % (data[i][3], data[i][0], data[i][1], len(data[i][2]))
			count[0] = count[0] + 1
		if (type(data[i][2]) == types.ListType):
			mimelist(data[i][2], count)

def mimefindtype(d, t):
	for i in range(len(d)):
		if (d[i][1] == t):
			return d[i]
		if (type(d[i][2]) == types.ListType):
			v = mimefindtype(d[i][2], t)
			if (v != None):
				return v
	return None

def mimefindid(d, t):
	for i in range(len(d)):
		if (d[i][3] == t):
			return d[i]
		if (type(d[i][2]) == types.ListType):
			v = mimefindid(d[i][2], t)
			if (v != None):
				return v
	return None

def mimedisplay(d):
	global saveattachment
	if saveattachment:
		print "Saving attachment %s (%s; %d bytes)" % (d[0], d[1], len(d[2]))
		fp = open(saveattachment, "w")
		fp.write(d[2])
		fp.close
	else:
		print "Displaying attachment %s (%s; %d bytes)" % (d[0], d[1], len(d[2]))
		if (d[1] == "text/plain"):
			print "-"*78
			print d[2]
			print "-"*78
		else:
			print "(Unable to display non-text/plain attachment)"

def SQmaiLShow():	
	global currentmsg
	global attachment
	global nomime
	parseargs()

	db = sqmail.db.db
	vf = sqmail.vfolder.read_from_cache()
	i = sqmail.vfolder.read_id()
	if not vf:
		print "You have to scan first."
		sys.exit()

	if (currentmsg == "Next"):
		currentmsg = i + 1
	elif (currentmsg == "Prev"):
		currentmsg = i - 1
	elif (currentmsg == None):
		currentmsg = i

	if (i < 0):
		print "Negative message numbers are meaningless."
		sys.exit()
	if (i > len(vf)):
		print "No more messages."
		sys.exit()
	sqmail.vfolder.write_id(currentmsg)

	msg = sqmail.message.Message(vf[currentmsg][0])
	msg.markread()
	print "Message #%d (%d) from %s (%s)" % (currentmsg, vf[currentmsg][0], \
		vf[currentmsg][3], vf[currentmsg][4])
	print "Arrived at:",
	print time.asctime(time.localtime(vf[currentmsg][5]))
	print "Subject: %s" % (msg.getsubject())

	if not nomime:
		try:
			decoded = msg.mimedecode()
		except sqmail.message.MIMEDecodeAbortException:
			print "ERROR: MIME decode failed!"
			nomime = 1
	
	if nomime:
		print "-"*78
		while 1:
			i = msg.readline()
			if (i == ""):
				break
			print i[:-1]
		print "-"*78
		return

	sections = len(decoded)
	if (sections > 1):
		print "%d sections." % (len(decoded))
	print
	if attachment:
		attachment = mimefindid(decoded, attachment)
		if not attachment:
			print "Attachment not found. Valid attachments:"
		else:
			mimedisplay(attachment)
	else:
		attachment = mimefindtype(decoded, "text/plain")
		if not attachment:
			print "Warning: message does not contain a text/plain attachment. Trying HTML instead."
			attachment = mimefindtype(decoded, "text/html")
		if not attachment:
			print "Warning: message does not contain a text/html attachment either. You'll"
			print "have to do this manually."
		else:
			mimedisplay(attachment)
		
	print "\nAvailable attachments:"
	count = [0]
	mimelist(decoded, count)
	if (count[0] == 0):
		print "(None.)"
	#print msg.getheaders()
	#print msg.getbody()

# Revision History
# $Log: show.py,v $
# Revision 1.2  2001/03/05 20:44:41  dtrg
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
# Revision 1.1  2001/01/08 15:34:28  dtrg
# Added the show CLI command.
#

