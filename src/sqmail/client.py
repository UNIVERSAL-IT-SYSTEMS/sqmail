import sys
import os
import socket
import stat

class ClientException(Exception):
	pass

def getsocknamelist(directory):
	"""Sees if a filename is appropriate to check for being a socket

	The socket should start with .sqmail-socket.%d. where %d is the
	uid of the current user.  It should also be owned by the user -
	that way another user shouldn't be able to mess up the client by
	adding spurious sockets.

	"""
	uid = os.getuid()
	prefix = ".sqmail-socket.%d." % uid
	socknames = []

	filelist = os.listdir(directory)
	for file in filelist:
		sockstat = os.stat(os.path.join(directory, file))
		if (sockstat[stat.ST_UID] == uid and
			file[:len(prefix)] == prefix and
			stat.S_ISSOCK(sockstat[stat.ST_MODE])):
			socknames.append(os.path.join(directory, file))
	return socknames

def getsocket():
	"""Returns active socket

	Tries sockets whose name is given by setsocknamelist until it
	finds one that is listening, or raises Exception if none are found.

	"""
	if os.environ.has_key('TMPDIR'): directory = os.environ['TMPDIR']
	else: directory = "/usr/tmp"
	socknamelist =  getsocknamelist(directory)
	
	s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	for sockname in socknamelist:
		try:
			s.connect(sockname)
			break
		except socket.error: continue
	else: raise ClientException("Unable to open socket")
	return s

def send(inputstring):
	"""Send string to server, return result"""
	s = getsocket()
	s.send(inputstring)
	result = s.recv(1048576)
	s.close()
	return result

