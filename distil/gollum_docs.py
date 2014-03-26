import os
import requests
from lxml import html

# Plaintext-ify all the junk we get
import html2text

JUNK_CONTENT = []
JUNK_CONTENT.append('  * Search\n\n  * Home\n  * All\n  * Files\n  * New\n  * Upload\n  * Rename\n  * Edit\n  * History')
JUNK_CONTENT.append('  * Search\n\n  * Home\n  * All\n  * New\n  * Upload\n  * Rename\n  * Edit\n  * History') # womble stole the precious thing (Files)

from distiller import Distiller

class GollumDistiller(Distiller):

	def tidy_url(self):
		"This is a hack that destroys query parameters"
		# Question marks aren't disallowed in the fragment identifier (I seem to recall)
		self.url = self.url.partition('#')[0].partition('?')[0]

	def blobify(self):
		self.tidy_url()
		url = self.url

		# Prepare auth
		try:
			wiki_credentials = self.auth['mapwiki']
		except:
			raise RuntimeError("You must provide Map wiki credentials, please set MAPWIKI_USER and MAPWIKI_PASS")

		# Grab the page
		response = requests.get(url, auth=wiki_credentials)
		try:
			response.raise_for_status()
		except:
			# Delete the page from the index if it doesn't exist
			if response.status_code == 404:
				self.enqueue_deletion()
			raise RuntimeError("Error getting page from gollum docs, got HTTP response {0} with error: {1}".format(response.status_code, response.reason) )

		# An example URL:  https://docs.anchor.net.au/system/anchor-wikis/Namespaces
		#
		# url      = https://docs.anchor.net.au/system/anchor-wikis/Namespaces
		# local_id = system/anchor-wikis/Namespaces
		# docs     = system/anchor-wikis/Namespaces
		# title    = Fetch from   <!-- --- title: THIS IS THE TITLE -->

		doc_tree = html.fromstring(response.text)
		content = html2text.html2text(response.text)
		# We could probably do this with lxml and some XPath, but meh
		for JUNK in JUNK_CONTENT:
			content = content.replace(JUNK, '')

		# XXX: We're assuming here that all pages across all wikis are in a single index and namespace
		# XXX: What if the page is empty? Might break a whole bunch of assumptions below this point.

		# Get the page name
		page_name = url.replace('https://docs.anchor.net.au/', '')

		# Get the content
		page_lines = [ line.strip() for line in content.split('\n') ]

		# Kill empty lines and clean out footer
		page_lines = [ line for line in page_lines if line ]
		if page_lines[-1] == 'Delete this Page': del(page_lines[-1])
		if page_lines[-1].startswith('Last edited by '): del(page_lines[-1])
		# Kill residue from conversion
		page_lines = [ line for line in page_lines if line != '!toc' ]

		# Local identifier will be the URL path components
		# Foo/Bar/Baz-is-da-best  =>  Foo Bar Baz is da best
		local_id = page_name.replace('/', ' ').replace('-', ' ')

		# Pull the title from the HTML
		title_list = doc_tree.xpath('//title/text()')
		if title_list:
			title = title_list[0]
			# Slashes in titles aren't very useful, we'll break on spaces instead later
			title = title.replace('/', ' / ')
			# If we have a real document title, roll it into the local_id for searchability goodness
			local_id += " " + ' '.join(title.split())
		else:
			title = local_id


		# If we get this title, it means that the page doesn't exist.
		# It was probably deleted, so go ahead and nuke it.
		if title == 'Create a new page':
			self.enqueue_deletion()
			return

		# The homepage of each repo is called Home, let's have something slightly more useful
		if title == 'Home':
			title = local_id

		# Content is now considered tidy
		blob = '\n'.join([title]+page_lines)

		# Try and find an exciting excerpt, this is complete and utter guesswork
		excerpt = '\n'.join(page_lines[:10])

		# Good to go now
		document = {}
		document['url']  = url
		document['blob'] = blob
		document['local_id'] = local_id
		document['title']    = title
		document['excerpt']  = excerpt

		for key in document:
			print u"{0}\n\t{1}\n".format(key, document[key][:400]).encode('utf8')


		yield document
