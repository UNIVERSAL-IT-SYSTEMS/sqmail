"""Classes and functions related to queries

Includes class definitions for the QueryException, Query, VFQuery,
UserQuery, and CachedQuery objects.

"""

import re
import string
import sqmail.db
import sqmail.vfolder

class QueryException(Exception):
	pass


class Query:
	"""Simple class representing VFolder Query

	self.qstring is the part of the query that goes after "WHERE ..."

	If this query is the query of a vfolder, self.vf is that folder.

	self.vfolderdeps is a dictionary (indexed by id) of the vfolders
	that the query depends on.  So if one of those vfolders is
	changed, the vfquery should be reexamined.

	self.seqdict is a dictionary of sequences.  If a sequence sid is
	a key, then it needs to be quantified over.

	"""
	max_query_length = 10000

	def __init__(self, qstring, vf = None, seqdict = None, folderdeps = None):
		"""qstring is the actual SQL query string"""
		if len(qstring) > self.max_query_length:
			error_string = ("Query length over %d.  Cycle created?" %
							self.max_query_length)
			raise QueryException(error_string)
		self.qstring = qstring
		self.vf = vf
		self.qschema = None
		if folderdeps: self.folderdeps = folderdeps
		elif vf: self.folderdeps = { vf.id: vf }
		else: self.folderdeps = {}
		if seqdict is None: self.seqdict = {}
		else: self.seqdict = seqdict

	def __str__(self): return self.qstring
	def __add__(self, x): return self.qstring + x
	def __radd__(self, x): return x + self.qstring
	def __len__(self): return len(self.qstring)

	def add_folderdeps(self, folderlist):
		"""Add list of vfolders to self.folderdeps"""
		for vf in folderlist:
			self.folderdeps[vf.id] = vf

	def copy(self):
		"""Return a non-identical query with similar fields"""
		q = Query(self.qstring)
		q.vf = self.vf
		q.qschema = self.qschema
		q.folderdeps = self.folderdeps.copy()
		q.seqdict = self.seqdict.copy()

	def count(self, addendum = ""):
		"""Returns the number of messages matching the query

		addendum will be added to the qschema at the end.  This uses a
		select to count the messages in the sequence, so use the
		numbers in the vfolder table instead if they are up to date.
		
		"""
		if not self.qschema: self.setqschema()
		return sqmail.db.fetchone((self.qschema % "COUNT(*)") +
								  " " + addendum)[0]

	def countunread(self):
		"""Returns number of unread messages matching query"""
		return self.count("AND readstatus='Unread'")

	def containsid(self, msgid):
		"""True if query matches msgid"""
		return self.count("AND headers.id = %d" % msgid)

	def selectcolumns(self, columns, addendum = "", ordering = None,
					  limit = None):
		"""Return specified columns with fetchall

		ordering is a field position.  If None, then result is not
		explicitly ordered.  limit is either a number n or a pair
		(m,n), meaning respectively to get the first n or to skip the
		first m and deliver the n.

		"""
		if ordering: orderstring = " ORDER BY " + ordering
		else: orderstring = ""

		if not limit: limitstring = ""
		elif type(limit) is type(1): limitstring = " LIMIT %d" % limit
		else: limitstring = " LIMIT %d,%d" % (limit[0], limit[1])

		return sqmail.db.fetchall((self.qschema % columns) + " " +
								  addendum + orderstring + limitstring)

class VFQuery(Query):
	"""Use for the actual SQL queries

	These queries are on the headers,sequence_data.  Use
	UserQuery.ExpandToVFQuery to get a VFQuery.

	"""
	def setqschema(self):
		"""Set the query schema strings and argument list

		It is meant to be used like: cursor.execute(qschema % foo),
		where foo is a column name, so any % in the qstring should be
		quoted.

		"""
		joinstringlist = []
		for seq in self.seqdict.values():
			s = ("LEFT JOIN sequence_data AS %s ON headers.id = %s.id "
				 "AND %s.sid = %d" % ((seq.getalias(),)*3 +
									  (seq.getsid(),)))
			joinstringlist.append(s)
		self.qschema = string.join(["SELECT %s FROM headers"] +
								   joinstringlist +
								   ["WHERE",
									string.replace(self.qstring, "%", "%%")])

	def reckon_sequences(self, vf):
		"""Changes self to exclude/include folder related sequences

		Also sets self.qstringnoseq and self.seqdictnoseq as the
		previous versions of self.qstring and self.seqdict in case we
		want to know what would happen without the overrides.

		"""
		self.qstringnoseq = self.qstring
		self.seqdictnoseq = self.seqdict.copy()
		inseq, outseq = vf.getposseq(), vf.getnegseq()
		self.qstring = ("(%s.sid IS NOT NULL OR (%s AND %s.sid IS NULL))" %
						(inseq.getalias(), self.qstringnoseq,
						 outseq.getalias()))
		self.seqdict[inseq.sid] = inseq
		self.seqdict[outseq.sid] = outseq

	def no_sequences(self):
		"""Return a VFQuery like self but ignore folder sequences"""
		vfq = VFQuery(self.qstringnoseq)
		vfq.seqdict = self.seqdictnoseq.copy()
		vfq.folderdeps = self.folderdeps.copy()
		return vfq


class CacheQuery(Query):
	"""Represent query of cached messages in a sequence

	A CacheQuery should return the same messages as a VFQuery, but
	the CacheQuery will be faster, and often much faster, because it
	only needs to retrieve the messages in a certain sequence and thus
	does not need to examine every single message.

	"""
	def __init__(self, qstring, vf):
		"""Init - ignore qstring, set everything from vf

		vf is the folder that this query is supposed to cache.  The
		rest of the state of the query can be set from this, so
		qstring is ignored.  (It is provided for compatibility with
		Query.__init__.)
		
		"""
		self.cacheseq = seq = vf.getcacheseq()
		Query.__init__(self, "(%s.sid IS NOT NULL)" % seq.getalias(),
					   vf, { seq.sid: seq }, { vf.id : vf})
		self.qschema = ("SELECT %s FROM sequence_data,headers WHERE "
						"headers.id = sequence_data.id AND "
						"sequence_data.sid = %d" % ("%s", seq.getsid()))


class UserQuery(Query):
	"""Query that the user types into the query box

	These are not SQL at all, but look similar to queries on the
	headers table.  It is possible to ask about sequence_data
	types also.

	"""
	def ExpandToVFQuery(self, vf):
		"""Expand self into full VFQuery, relative to vfolder vf

		Follows three rules:

		0.  If the string is empty, return the always false query.
		
		1.  Replace forms like VFOLDER:foobar or VFOLDER:"foobar" (use
		the latter if folder name contains spaces) for their
		correspending VFQuery strings.  As special cases,
		VFOLDER:children is replaced by the disjunction of all the
		children's queries, and VFOLDER:siblings is replaced by the
		disjunction of all the folders which share a parent with the
		original folder, except of course for the original folder.

		2. Add a bit of SQL so that messages in the sequence named
		+foobar will always be in folder foobar and messages in the
		-foobar sequence will never be.  (One message shouldn't be
		in both the +foobar and -foobar sequences.)

		"""
		if not string.strip(self.qstring): return VFQuery("0")

		self.finalvfq = VFQuery("(%s)" % self.qstring, vf)
		self._macroexpand()
		self.finalvfq.reckon_sequences(vf)
		return self.finalvfq

	def _setregexps(self):
		"""Sets necessary regular expressions if not set already"""
		try: self.vf_re
		except AttributeError:
			self.vf_re = re.compile('VFOLDER:(\\w+)|VFOLDER:"(.+?)"',
									re.I | re.M | re.S)
			self.vfi_re = re.compile('VFOLDERID:([0-9]+)', re.I | re.M | re.S)

	def _macroexpand(self):
		"""Replace macros in self.finalvfq.qstring, return when done

		Update self.finalvfq by replacing macros.  Go through each
		regular expression one by one, and return when none of them
		match any more.

		"""
		self._setregexps()
		while 1:
			# Replace macros like "VFOLDER:foo"
			match = self.vf_re.search(self.finalvfq.qstring)
			if match:
				self._vfqmacrorepl(self._find_namerepl(match.group(1)
													   or match.group(2)),
								   match.start(0), match.end(0))
				continue
			# Replace macros like "VFOLDERID:234"
			match = self.vfi_re.search(self.finalvfq.qstring)
			if match:
				self._vfqmacrorepl(sqmail.vfolder.get_by_id(
					int(match.group(1))), match.start(0), match.end(0))
				continue
			break

	def _vfqmacrorepl(self, query, startpos, endpos):
		"""Update self.finalvfq by substituting one query at pos

		In finalvfq.qstring, replace [startpos:endpos] with new vfq.
		Both VFQueries and CachedQueries should work.
		""" 
		self.finalvfq.seqdict.update(query.seqdict)
		self.finalvfq.folderdeps.update(query.folderdeps)
		self.finalvfq.qstring = (self.finalvfq.qstring[:startpos]+
								 query.qstring+
								 self.finalvfq.qstring[endpos:])

	def _find_namerepl(self, foldername):
		"""Returns vfquery that VFOLDER:foldername represents"""
		lowercase = string.lower(foldername)
		if lowercase == "siblings":
			return apply(qor, map(lambda x: x.cquery, self.vf.getsiblings()))
		elif lowercase == "children":
			return apply(qor, map(lambda x: x.cquery, self.vf.getchildren()))
		elif lowercase == "parents":
			return apply(qand, map(lambda x: x.cquery, self.vf.getparents()))
		else:
			vf = sqmail.vfolder.get_by_name(foldername)
			if not vf: raise QueryException("Can't find folder "+foldername+
											" in query from "+self.vf.name)
			else: return vf.cquery



def _binaryop(querylist, opstring, default):
	"""helper function used by qand and qor"""
	qstringlist, seqdict, folderdeps = [], {}, {}
	for query in querylist:
		qstringlist.append(query.qstring)
		seqdict.update(query.seqdict)
		folderdeps.update(query.folderdeps)
	if not querylist: vfq = VFQuery(default)
	else: vfq = VFQuery("(%s)" % string.join(qstringlist, " "+opstring+" "))
	vfq.seqdict = seqdict
	vfq.folderdeps = folderdeps
	return vfq

def qand(*queries):
	"""Return vfquery conjunction of given queries"""
	return _binaryop(queries, "AND", "1")

def qor(*queries):
	"""Return vfquery disjunction of given queries"""
	return _binaryop(queries, "OR", "0")

def qnot(query):
	"""Return vfquery negation of given query"""
	vfq = VFQuery("(NOT %s)" % query.qstring)
	vfq.seqdict = query.seqdict.copy()
	vfq.folderdeps = query.folderdeps.copy()
	return vfq

