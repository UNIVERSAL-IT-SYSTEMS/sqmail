"""Code for SQmaiL server - listen at socket and eval code

The socket basically accepts a connection, waits for some incoming
data, and runs it.  Usually an empty string will be sent back, but if
there is an exception, the traceback will be sent, and if there the
client_return(object) function is called, the object will be coerced
to a string and sent back.

To start listening, create an instance of the Server object, and run
Server.loop() periodically.

"""

import socket
import select
import os
import stat
import time
import sys
import cStringIO
import string
import traceback

# This is kind of a hack but I wanted the client_return function to be
# visible to the client, so it needs something to modify within the
# global namespace
global returnlist

class ServerException(Exception):
	pass

class Server:
	"""Establish socket and eval incoming code

	First open a socket for listening.  When loop() is called, accept
	any new connections, and eval all incoming data on any accepted
	connection as python code.  If there is an exception or traceback,
	send this and the result back on the same socket connection, and
	close that connection.  loop() is meant to be called within the
	sqmail's mainloop.
	
	"""
	def __init__(self):
		self.connections = []
		self.socket = self.getsocket()
		if not self.socket:
			raise ServerException("getsocket() unable to get proper socket")

	def getsocket(self):
		"""Return a socket ready to .accept() connections

		The socketfile name is .sqmail-socket.pid in the /usr/tmp
		directory, or the directory specified in os.environ['TMPDIR'] if
		available.  If the file already exists and can't be erased, or if
		the socket cannot be opened, return None.

		"""
		if os.environ.has_key('TMPDIR'): dir = os.environ['TMPDIR']
		else: dir = "/usr/tmp"
		self.sockname = os.path.join(dir, ".sqmail-socket.%d.%d" %
									 (os.getuid(), os.getpid()))
		try:
			try:
				os.stat(self.sockname)
				try: os.unlink(self.sockname)
				except os.error: return
			except: pass
			s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			s.bind(self.sockname)
			os.chmod(self.sockname, 0600)
			s.listen(1)
		except socket.error: return
		return s

	def loop(self):
		"""Look for sockets and evaluate any data coming in on one.

		This can be called from an event loop.  It returns 1 just in
		case a null value would cause it to be ejected from the loop.

		"""
		global returnlist
		returnlist = []

		if select.select([self.socket], [], [], 0)[0]:
			conn = self.socket.accept()[0]
			codeobj = compile(conn.recv(1048576), "<string>", "exec")
			try: exec codeobj in globals()
			except SystemExit: raise
			except:
				stringfile = cStringIO.StringIO()
				traceback.print_exc(None, stringfile)
				client_return(stringfile.getvalue())
			conn.send(string.join(returnlist, "\n"))
			conn.close()
		return 1

	def stop(self):
		"""Shut down server and remove socket"""
		self.socket.close()
		os.unlink(self.sockname)
		

def client_return(object):
	"""The client can use this to return a string to itself
	
	object is coerced into a string and the result will be
	sent back to the client.
	
	"""
	global returnlist
	returnlist.append(str(object))
