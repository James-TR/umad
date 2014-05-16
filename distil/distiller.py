import os
import requests
from dateutil.parser import *
from dateutil.tz import *

class Distiller(object):
	def __init__(self, url, indexer_url='https://umad-indexer.anchor.net.au/'):
		self.url         = url
		self.indexer_url = indexer_url

		self.auth = {}
		if os.environ.get('MAPWIKI_USER') and os.environ.get('MAPWIKI_PASS'):
			self.auth['mapwiki'] = (os.environ.get('MAPWIKI_USER'), os.environ.get('MAPWIKI_PASS'))
		if os.environ.get('API_AUTH_USER') and os.environ.get('API_AUTH_PASS'):
			self.auth['anchor_api'] = (os.environ.get('API_AUTH_USER'), os.environ.get('API_AUTH_PASS'))
		if os.environ.get('OPENSRS_AUTH_USER') and os.environ.get('OPENSRS_AUTH_KEY'):
			self.auth['opensrs'] = (os.environ.get('OPENSRS_AUTH_USER'), os.environ.get('OPENSRS_AUTH_KEY'))
		if os.environ.get('OPENHRS_AUTH_USER') and os.environ.get('OPENHRS_AUTH_KEY'):
			self.auth['openhrs'] = (os.environ.get('OPENHRS_AUTH_USER'), os.environ.get('OPENHRS_AUTH_KEY'))

		# This is mock data, it's provided as a functional example of
		# how the Distiller class can fulfil external dependencies for
		# its subclasses.
		self.auth['newtype'] = ('demoUser', 'demoPass')

		self.accept_json = {'Accept':"application/json"}

		self.docs = self.blobify()

	@staticmethod
	def debug(msg=''):
		pass # uncomment the following line to enable debug output
		print msg

	def enqueue_reindex(self, url=None):
		# Reindex thyself
		if url is None:
			return requests.get(self.indexer_url, params={'url':self.url}, verify=True)
		# Reindex something else
		return requests.get(self.indexer_url, params={'url':url}, verify=True)

	def enqueue_deletion(self, url=None):
		# Delete yourself
		if url is None:
			return requests.delete(self.indexer_url, params={'url':self.url}, verify=True)
		# Delete some other document
		return requests.delete(self.indexer_url, params={'url':url}, verify=True)

	def blobify(self):
		# Once implemented, blobify is typically a generator, thus
		# turning self.docs into an iteratori that yields dicts. It's
		# also acceptable for blobify to return a list of dicts.
		raise NotImplementedError("Distiller plugins must implement blobify()")

	def parse_date_string(self, date_string):
		datetime = parse(date_string)
		if datetime.tzinfo is None:
			datetime = datetime.replace(tzinfo=tzutc())
		return datetime.astimezone(tzlocal()).strftime('%Y-%m-%dT%H:%M:%S')
