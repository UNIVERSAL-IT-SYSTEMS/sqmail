# CLI utility that lists the contents of a vfolder.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/cli/scan.py,v $
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

frommsg = None
tomsg = None
lastmsg = None
vfname = None
currentmsg = None
mboxfile = None

def usage():
	print "Syntax: " + sys.argv[0] + " scan [options] vfolder"
	print "  --from <n>         Start listing from message #n"
	print "  --to <n>           Stop listing at message #n"
	print "  --last <n>         Only show last n messages"
	print "  --export <file>    Emit the message to the named mbox file"
	
def parseargs():
	global frommsg, tomsg, lastmsg, vfname, mboxfile
	try:
		opts, args = getopt.getopt(sys.argv[2:], "hl:f:t:e:", \
			["help", "last=", "from=", "to=", "export="])
	except getopt.error:
		usage()
		sys.exit(2)

	for o, a in opts:
		if (o in ("-h", "--help")):
			usage()
			sys.exit()
		if (o in ("-l", "--last")):
			lastmsg = int(a)
		if (o in ("-f", "--from")):
			frommsg = int(a)
		if (o in ("-t", "--to")):
			tomsg = int(a)
		if (o in ("-e", "--export")):
			mboxfile = open(a, "a")
	
	if (lastmsg != None):
		if (frommsg != None) or (tomsg != None):
			print "Syntax error: can't specify --last with --from or --to"
			sys.exit(2)

	if (len(args) == 0):
		vfname = ""
	elif (len(args) == 1):
		vfname = args[0]
	else:
		usage()
		sys.exit(2)


def SQmaiLScan():	
	global frommsg, tomsg, lastmsg, vfname, mboxfile
	parseargs()

	db = sqmail.db.db
	if (vfname == ""):
		# Cached results only
		vf = sqmail.vfolder.read_from_cache()
		if not vf:
			print "Unable to load results cache --- no previous query."
			sys.exit(1)
		currentmsg = sqmail.vfolder.read_id()
	else:
		if (vfname[0] == ":"):
			# Manual SQL query
			vfname = vfname[1:]
			vf = sqmail.vfolder.VFolder(query=vfname)
		elif (vfname[0] == "="):
			# Preconfigured vfolder by ID
			vfnum = int(vfname[1:])
			try:
				vf = sqmail.vfolder.VFolder(id=vfnum)
				vfname = vf.getname()
			except KeyError:
				print "No vfolder with that ID is available."
				sys.exit(1)
		else:
			# Preconfigured vfolder by name
			try:
				vf = sqmail.vfolder.VFolder(name=vfname)
			except KeyError:
				print "No vfolder of that name is available."
				sys.exit(1)

		vf.scan()
		sqmail.vfolder.write_to_cache(vf)
		currentmsg = 0
		sqmail.vfolder.write_id(currentmsg)

	if (len(vf) == 0):
		print "The vfolder contains no messages."
		sys.exit(0)

	if (lastmsg != None):
		tomsg = len(vf)-1
		frommsg = tomsg-lastmsg
		if (frommsg < 0):
			print "Warning: you asked for the last %d messages, but there are only %d" % (lastmsg, len(vf))
			print "available."
			frommsg = 0
	else:
		if (tomsg == None):
			tomsg = len(vf)-1
		if (frommsg == None):
			frommsg = 0
		if (frommsg > tomsg):
			print "Warning: FROM is greater than TO. Silly."
			i = tomsg
			tomsg = frommsg
			frommsg = i
		if (frommsg < 0):
			print "Warning: message numbers below zero are meaningless."
			tomsg = 0
		if (tomsg >= len(vf)):
			print "Warning: you asked for messages up to %d, but there are only %d" % (frommsg, len(vf))
			print "available."
			tomsg = len(vf)

	dayago = time.time() - (24.0*60.0*60.0)
	for i in range(tomsg-frommsg+1):
		o = vf[i+frommsg]
		if (o[5] < dayago):
			t = time.strftime("%m/%d", time.localtime(o[5]))
		else:
			t = time.strftime("%H:%M", time.localtime(o[5]))
		print "% 4d%c%c %-5s %-19s %s" % (i+frommsg, \
			32+11*((i+frommsg)==currentmsg), \
			32+46*(o[1] == "Unread"), \
			t, o[3], o[4])

		if mboxfile:
			msg = sqmail.message.Message(vf[i][0])
			date = time.gmtime(msg.getdate())
			fromfield = msg.getfrom() + "  " + time.asctime(date)
			mboxfile.write("From  ")
			mboxfile.write(fromfield)
			mboxfile.write("\n")
			mboxfile.write(msg.getheaders())
			mboxfile.write("X-SQmaiL-Annotation: ")
			mboxfile.write(msg.getannotation())
			mboxfile.write("\nX-SQmaiL-ReadStatus: ")
			mboxfile.write(msg.getreadstatus())
			mboxfile.write("\n\n")
			mboxfile.write(msg.getbody())
			mboxfile.write("\n\012\012")
			


# Revision History
# $Log: scan.py,v $
# Revision 1.6  2001/05/23 10:22:01  dtrg
# Fixed some fairly stupid getopt bugs.
#
# Revision 1.5  2001/03/07 12:23:17  dtrg
# Checks for empty vfolders.
#
# Revision 1.4  2001/03/05 20:44:41  dtrg
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
# Revision 1.3  2001/01/18 18:50:06  dtrg
# Forgot to get it to emit the ReadStatus field.
#
# Revision 1.2  2001/01/16 20:13:48  dtrg
# Added the ability to export all messages being listed to an mbox file.
#
# Revision 1.1  2001/01/08 14:58:55  dtrg
# Added the scan CLI command.
