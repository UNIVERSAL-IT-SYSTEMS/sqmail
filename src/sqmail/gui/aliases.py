# Handles the aliases window.
# $Source: /cvsroot/sqmail/sqmail/src/sqmail/gui/aliases.py,v $
# $State: Exp $

import os.path
import string
import sys
import MimeWriter
import base64
import quopri
import cStringIO
import cPickle
import gtk
import smtplib
import time
import rfc822
import re
import gnome.mime
import sqmail.utils
import sqmail.message
import sqmail.gui.reader
import sqmail.gui.utils
import sqmail.gui.textviewer

class SQmaiLAliases:
	def __init__(self, reader):
		aliaseswin = reader.readglade("aliaseswin", self)
		self.widget = sqmail.gui.utils.WidgetStore(aliaseswin)
		self.cursor = sqmail.db.cursor()

		self.cursor.execute("SELECT name, addresslist FROM aliases")
		while 1:
			i = self.cursor.fetchone()
			if not i:
				break

			fp = cStringIO.StringIO(i[1])
			msglist = cPickle.load(fp)
			parent = self.widget.tree.insert_node(None, None, [i[0]], \
				is_leaf=0, expanded=1)
			self.widget.tree.node_set_row_data(parent, i[0])
			for j in msglist:
				node = self.widget.tree.insert_node(parent, None, [j], \
					is_leaf=0, expanded=1)
				self.widget.tree.node_set_row_data(node, j)

		self.widget.tree.set_reorderable(1)
		self.on_unselect(None, None, None)

	def on_close(self, obj):
		# Write the data back into the aliases table.
		self.cursor.execute("LOCK TABLES aliases WRITE")
		# Nuke all the existing aliases.
		self.cursor.execute("DELETE FROM aliases")
		# For each alias...
		for node in self.widget.tree.base_nodes():
			# Read the data out of the CTree...
			alias = self.widget.tree.node_get_row_data(node)
			msglist = []
			for node in node.children:
				msglist.append(self.widget.tree.node_get_row_data(node))
			print alias,"=",msglist
			fp = cStringIO.StringIO()
			cPickle.dump(msglist, fp)
			msglist = fp.getvalue()
			# ...and put it into the database.
			self.cursor.execute("INSERT INTO aliases" \
					     " (name, addresslist) VALUES " \
					     " ('"+sqmail.db.escape(alias)+"', " \
					     " '"+sqmail.db.escape(msglist)+"')")

		self.cursor.execute("UNLOCK TABLES")
		self.widget.aliaseswin.destroy()

	def on_new(self, obj):
		sel = self.widget.tree.selection
		name = ""
		if not sel:
			# Nothing is selected, so add a new top-level entry.
			node = self.widget.tree.insert_node(None, None, [name], \
				is_leaf=0, expanded=1)
		else:
			node = sel[0]
			# If a top-level entry is selected...
			if not node.parent:
				# Add a child to that entry.
				node = self.widget.tree.insert_node(node, None, [name])
			else:
				# Otherwise, add a sibling.
				node = self.widget.tree.insert_node(node.parent, node, [name])
		self.widget.tree.node_set_row_data(node, name)
		self.widget.tree.sort()
		self.widget.tree.select(node)

	def on_delete(self, obj):
		node = self.widget.tree.selection[0]
		self.widget.tree.remove_node(node)

	def on_select(self, obj, a, b):
		node = self.widget.tree.selection[0]
		name = self.widget.tree.node_get_row_data(node)
		self.widget.text.set_text(name)
		self.widget.text.set_sensitive(1)
		# We can only delete top-level nodes if they're empty.
		if (not node.parent and (len(node.children) != 0)):
			self.widget.deletebutton.set_sensitive(0)
		else:
			self.widget.deletebutton.set_sensitive(1)

	def on_unselect(self, obj, a, b):
		self.widget.text.set_text("")
		self.widget.text.set_sensitive(0)
		self.widget.deletebutton.set_sensitive(0)

	def on_text_activate(self, obj):
		node = self.widget.tree.selection[0]
		name = self.widget.text.get_text()
		self.widget.tree.node_set_row_data(node, name)
		self.widget.tree.node_set_text(node, 0, name)
		
# Revision History
# $Log: aliases.py,v $
# Revision 1.1  2001/02/02 20:05:14  dtrg
# Realised I had forgotten to add this file, totally breaking the rest of
# the system!
# First draft mail aliases support. The editor works reasonably well,
# although there are known problems in dragging addresses and the UI could
# be improved.
#
