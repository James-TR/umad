import re
import requests
from bs4 import BeautifulSoup

WIKIWORD_RE = re.compile(r'([a-z]+)([A-Z])')

from distiller import Distiller

class MoinMapDistiller(Distiller):
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

		# The non-printable version of the page shows valid status codes on redirect, rather than a 200
		response = requests.head(url, auth=wiki_credentials, verify='AnchorCA.pem', allow_redirects=False)
		# Don't index redirects, pages not found, or pages we aren't authorised to view
		if response.status_code in (301, 403, 404):
			self.enqueue_deletion()
			return

		# Once we know the page is valid, grab the printable version of the page
		response = requests.get(url, auth=wiki_credentials, params={'action':'print'}, verify='AnchorCA.pem')

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

		# Get the parts of the content we care about
		page = BeautifulSoup(response.text)
		content = page.find_all('div', id='content')[0]
		inc_duplicates = [ line.text.strip() for line in content.find_all(re.compile("^p|^li|^h[\d]+|^a")) ]

		# Remove empty & duplicate lines
		inc_duplicates = [line for line in inc_duplicates if line ]
		page_lines = []
		for line in inc_duplicates:
			if line not in page_lines:
				page_lines.append(line)

		# Try to find a suitable title - either the first <h1>, or if that doesn't exist, from the URI
		title = ' '.join([ WIKIWORD_RE.sub(r'\1 \2', x) for x in page_name.split('/') ])
		excerpt = None
		if page_lines and content.find('h1'):
			title = content.find('h1').text

			# If the first line of the page is the same as the title, don't add it into the blob and excerpt
			if page_lines[0].replace(' ','').endswith(title.replace(' ', '')):
				del(page_lines[0])

			# Try and find an exciting excerpt, this is complete and utter guesswork
			excerpt = '\n'.join(page_lines[:10])

		# Content is now considered tidy
		blob = '\n'.join([title] + page_lines)

		# Allow for title keyword searching
		map_rough_title_chunks  = set(page_name.split('/'))
		map_rough_title_chunks |= set([ WIKIWORD_RE.sub(r'\1 \2', x) for x in map_rough_title_chunks ])

		# Get last updated time
		page_info = page.find('p', id='pageinfo').text
		date_string = re.search(r'(\d+-\d+-\d+ \d+:\d+:\d+)', page_info).group(0)
		last_updated = self.parse_date_string(date_string)

		# Good to go now
		document = {}
		document['url']  = url
		document['blob'] = blob
		document['local_id'] = ' '.join(map_rough_title_chunks)
		document['title']    = title
		document['last_updated']  = last_updated
		if excerpt:
			document['excerpt'] = excerpt

		yield document
