import os
import sqmail.utils
import sqmail.db
import sqmail.preferences
import urllib
import string
import cPickle
import cStringIO
import thread
import threading

__picon_lock = threading.RLock()

# Return the picon for a particular email address, fetching it off the net if
# need be.

def get_picon_xpm(email):
	cursor = sqmail.db.cursor()

	# Chop the user part of the email address if we've been told to.

	if sqmail.preferences.get_omitpiconsuser():
		i = string.find(email, "@")
		email = "+"+email[i:]

	# Is the email address in the database?

	#cursor.execute("LOCK TABLES picons WRITE")
	cursor.execute("SELECT image FROM picons WHERE email='%s'" \
		% sqmail.db.escape(email))
	i = cursor.fetchone()
	if (i != None):
		#cursor.execute("UNLOCK TABLES")
		#__picon_lock.release()
		fp = cStringIO.StringIO(i[0])
		return cPickle.load(fp)

	# No. Need to query the remote server. First set the proxy.

	if (sqmail.preferences.get_usepiconsproxy()):
		os.environ["http_proxy"] = "http://%s:%d" % \
			(sqmail.preferences.get_piconsproxyserver(), \
			sqmail.preferences.get_piconsproxyport())
		print os.environ["http_proxy"]
	else:
		try:
			del os.environ["http_proxy"]
		except KeyError:
			pass

	# Now open the HTTP connection and read in the image.

	i = string.find(email, "@")
	user = email[:i]
	host = email[i+1:]
	i = sqmail.preferences.get_piconsserver() + \
		"/" + host + "/" + user + \
		"/users+usenix+misc+domains+unknown/up/single/xpm"
	print "Picons: Fetching", i
	try:
		fp = urllib.urlopen(i)
	except IOError, e:
		print "Picons: I/O error:", e
		#__picon_lock.release()
		#cursor.execute("UNLOCK TABLES")
		return None
	image = sqmail.utils.load_xpm(fp)
	if not image:
		print "Picons: I/O error: didn't understand reply from server"
		#__picon_lock.release()
		#cursor.execute("UNLOCK TABLES")
		return None

	# Cache the image.

	fp = cStringIO.StringIO()
	cPickle.dump(image, fp)
	cursor.execute("INSERT IGNORE INTO picons (email, image) VALUES ('%s', '%s')" \
		% (sqmail.db.escape(email), sqmail.db.escape(fp.getvalue())))
	#__picon_lock.release()
	#cursor.execute("UNLOCK TABLES picons")
	return image

# Return statistics on the picon cache.

def get_picon_stats():
	#__picon_lock.acquire()
	cursor = sqmail.db.cursor()
	#cursor.execute("LOCK TABLES picons WRITE")
	cursor.execute("SELECT COUNT(*) FROM picons")
	#cursor.execute("UNLOCK TABLES")
	#__picon_lock.release()
	return int(cursor.fetchone()[0])

# Purge the cache.

def flush():
	#__picon_lock.acquire()
	cursor = sqmail.db.cursor()
	print "Flushing picons cache..."
	#cursor.execute("LOCK TABLES picons WRITE")
	cursor.execute("TRUNCATE picons")
	#cursor.execute("UNLOCK TABLES")
	#__picon_lock.release()
	print "Done."

# Start background lookup thread.

__thread = None
__lock = None
__queue = []
def start_thread():
	global __thread, __lock, __queue
	__lock = threading.Lock()
	__lock.acquire()
	__thread = threading.Thread(target=thread_func, name="Picons background fetcher")
	__thread.setDaemon(1)
	__thread.start()

def thread_func():
	global __thread, __lock, __queue
	while 1:
		while (__queue == []):
			print "Picons: nothing to do, waiting"
			__lock.acquire()
		address = __queue.pop(0)
		get_picon_xpm(address)
		print "Picons: all done for", address

# Queue an address for background fetching.

def queue_address(email):
	global __thread, __lock, __queue
	if not sqmail.preferences.get_usepicons():
		return
	if __thread:
		# Check to see if the fetcher thread has died --- it has a
		# tendency to.
		if (__thread not in threading.enumerate()):
			start_thread()
		__queue.append(email)
		try:
			__lock.release()
		except thread.error:
			# An error here means the lock's already released.
			pass

