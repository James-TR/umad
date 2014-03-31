import re
import requests

TITLE_RE           = re.compile(r'<<Title(\((.*)\))?>>')
NON_TITLE_MACRO_RE = re.compile(r'<<(?!Title[(>])')
WIKIWORD_RE        = re.compile(r'([a-z]+)([A-Z])')
REDIRECT_RE        = re.compile(r'#redirect\b', re.I)

from distiller import Distiller

class MoinMapDistiller(Distiller):
	""" XXX: Might be more sensible to treat Map pages like Gollum pages, and just
	         let the HTML-to-Markdown processor have at it.
	"""

	doc_type = 'map'

	@classmethod
	def will_handle(klass, url):
		return url.startswith('https://map.engineroom.anchor.net.au/')

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
		response = requests.get(url, auth=wiki_credentials, params={'action':'raw'}, verify='AnchorCA.pem')
		try:
			response.raise_for_status()
		except:
			#debug("Error getting page from map wiki, got HTTP response {0}".format(response.status_code))
			if response.status_code == 404:
				self.enqueue_deletion()
			return

		# An example URL:  https://map.engineroom.anchor.net.au/PoP/SYD1/NetworkPorts
		#
		# url      = https://map.engineroom.anchor.net.au/PoP/SYD1/NetworkPorts
		# local_id = PoP/SYD1/NetworkPorts
		# map      = PoP/SYD1/NetworkPorts
		# title    = syd1 Network Port Allocations

		# Get the page name as according to Moin
		page_name = url.replace('https://map.engineroom.anchor.net.au/', '')
		if page_name == '': # Special case for the home page
			page_name = 'ClueStick'

		# Get the content
		page_lines = [ line.strip() for line in response.content.split('\n') ]
		page_lines = [ line for line in page_lines if line ]

		# XXX: what if the page is empty? Might break a whole bunch of assumptions below this point.

		if page_lines:
			if REDIRECT_RE.match(line):
				# Null document, don't index it
				return
				# Alternatively, enqueue a deletion?
				# self.enqueue_deletion()

		# Discard all lines beginning with one of: (keep line if all checks are not-hit)
		#  - Comment (#)
		#  - Table tags (||)
		page_lines = [ line for line in page_lines if  all( [ not line.startswith(x) for x in ['#', '||'] ] )  ]


		# Try to find a suitable title
		lines_starting_with_title_macro = [ line for line in page_lines[:3] if line.startswith('<<Title') ]
		lines_starting_with_equals_sign = [ line for line in page_lines[:3] if line.startswith('=') ]

		title = None
		if lines_starting_with_title_macro:
			title_line = lines_starting_with_title_macro[0]
			title_match = TITLE_RE.match(title_line)
			if not title_match.group(2):
				title=None
			else:
				title = TITLE_RE.sub(r'\2', title_line).strip('"\'')
		elif lines_starting_with_equals_sign:
			title_line = lines_starting_with_equals_sign[0]
			title = title_line.strip('= ')
			page_lines.remove(title_line)

		if not title: # Either got left with an empty string, or still None
			path_components = page_name.split('/')
			title = ' '.join([ WIKIWORD_RE.sub(r'\1 \2', x) for x in path_components ])


		# Strip all lines that are just macros
		page_lines = [ line for line in page_lines if not NON_TITLE_MACRO_RE.match(line) ]

		# Content is now considered tidy
		blob = '\n'.join(page_lines)

		# Try and find an exciting excerpt, this is complete and utter guesswork
		excerpt = '\n'.join(page_lines[:10])

		# Allow for title keyword searching
		map_rough_title_chunks  = set(page_name.split('/'))
		map_rough_title_chunks |= set([ WIKIWORD_RE.sub(r'\1 \2', x) for x in map_rough_title_chunks ])

		# Good to go now
		document = {}
		document['url']  = url
		document['blob'] = blob
		document['local_id'] = ' '.join(map_rough_title_chunks)
		document['title']    = title
		document['excerpt']  = excerpt

		yield document
