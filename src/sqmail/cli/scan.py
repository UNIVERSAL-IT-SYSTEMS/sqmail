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

def usage():
	print "Syntax: " + sys.argv[0] + " scan [options] vfolder"
	print "  --from <n>         Start listing from message #n"
	print "  --to <n>           Stop listing at message #n"
	print "  --last <n>         Only show last n messages"
	
def parseargs():
	global frommsg, tomsg, lastmsg, vfname
	try:
		opts, args = getopt.getopt(sys.argv[2:], "hl:f:t:", \
			["help", "last=", "from=", "to="])
	except getopt.GetoptError:
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
	global frommsg, tomsg, lastmsg, vfname
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
		else:
			# Preconfigured vfolder
			vf = sqmail.vfolder.VFolder(name=vfname)

		vf.scan()
		sqmail.vfolder.write_to_cache(vf)
		currentmsg = 0
		sqmail.vfolder.write_id(currentmsg)

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

# Revision History
# $Log: scan.py,v $
# Revision 1.1  2001/01/08 14:58:55  dtrg
# Added the scan CLI command.
#

