"""Command line client

Using the client you can send python commands to a running SQmaiL gui
instance.  The code for actually opening the sockets is in
sqmail/client.py; this code is mostly for parsing the command line and
possibly providing a python-interpreter like interface.

"""

import sys
import sqmail.client
import getopt
import code
import cStringIO
import traceback
import string

def invalidparams():
	print """
Syntax: %s client [-s] [-e expression]...[-e expression]
                  [filename]...[filename]

    -e expression     Cause SQmaiL to execute expression
	filename          Read file filename and execute
	-s                Read commands from stdin and execute
	<no arguments>    Read commands from terminal like python interpreter

SQmaiL client is not meant as a substitute for the python interpreter
or for running large files --- it is best used for sending small
commands or for use in debugging.  If you want the client to print (on
the client's end) some result, use the function client_return, as in:

$ SQmaiL client -e "client_return(2+2)"
4
"""
	sys.exit(2)

def parseargs(arglist):
	"""Return triple representing arguments

	First member of triple is 1 if -s found, 0 otherwise.  The second
	and third members are lists containing the expressions and
	filenames respectively to evaluate.

	"""
	try: opts, filenames = getopt.getopt(arglist, "se:")
	except getopt.error: invalidparams()

	sfound = 0
	expressions = []
	for optpair in opts:
		if optpair[0]=="-s": sfound = 1
		elif optpair[0]=="-e": expressions.append(optpair[1])
	return (sfound, expressions, filenames)

def interpreter():
	"""Mimic a (poor) version of python's interpreter"""

	print """SQmaiL client interpreter.

All commands are actually executed by the server.  Use
client_return(foo) to print foo on the client side."""

	# Try to read prompts and get readline support
	try: sys.ps1
	except AttributeError: sys.ps1 = ">>> "
	try: sys.ps2
	except AttributeError: sys.ps2 = "... "
	try: import readline
	except: pass

	while 1:
		try: codestring = readcommand()
		except EOFError:  # User pressed Control-D
			print
			sys.exit(0)
		if codestring:
			result = sqmail.client.send(codestring)
			if result: print result

def readcommand():
	"""Read one code block from terminal

	Used by interpreter() to figure out when the user is done adding
	to a statement.  Returns the text of the command if a command was
	successfully entered, or None if some exception or other caused us
	to reset.

	"""
	s = raw_input(sys.ps1)
	while 1:
		try: codeobj = code.compile_command(s)
		except SyntaxError, OverflowError:
			exceptstringfile = cStringIO.StringIO()
			traceback.print_exc(None, exceptstringfile)
			print exceptstringfile.getvalue()
			return None
		if codeobj: return s
		s = s + "\n" + raw_input(sys.ps2)

def SQmaiLClient():
	"""Called by main SQmaiL executable"""

	sfound, expressions, filenames = parseargs(sys.argv[2:])

	execstrings = []
	if sfound: execstrings.append(sys.stdin.read())
	execstrings.extend(expressions)
	for fn in filenames:
		fp = open(fn, "r")
		execstrings.append(fp.read())
		fp.close()

	if execstrings:
		print string.join(map(sqmail.client.send, execstrings), "\n"),
	else: interpreter()
