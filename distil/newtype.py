# XXX: This is an example Distiller subclass, you should make a copy and edit
# it to implement your own new doctype.

# Feel free to import whatever libraries you need to get the job done
import sys
import os
from random import sample, choice

# You need to keep this, as you're subclassing Distiller
from distiller import Distiller


# Need to mangle your data a bit more? Feel free to drop some utility functions
# out here in the module. If we were being strict about our OO we'd make them
# static methods inside the class, but to be honest it's just uglier than it
# needs to be, and more typing. Stay pragmatic, just put 'em here.

def get_workdays(staff):
	# This just returns some mocked-up additional data
	return sample( ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], 3)

# This is a mock implementation of a hypothetical remote data store with an API
def retrieve_newtypes(nickname=None, *args, **kwargs):
	newtypes = {}
	newtypes['yuki'] = { 'name': "Yuki", 'age': "16", 'favourite_colour': "blue",  'u_type': "Gothic" }
	newtypes['tomo'] = { 'name': "Tomo", 'age': "17", 'favourite_colour': "black", 'u_type': "Chinese" }
	newtypes['nao']  = { 'name': "Nao",  'age': "20", 'favourite_colour': "red",   'u_type': "Traditional" }
	if not nickname:
		return sample(newtypes.values(), len(newtypes))
	return [ choice(newtypes) ]


# Pick your own name for the Distiller, following Python's usual CapWords pattern
class NewtypeDistiller(Distiller):

	# This string should be short and sweet, and unambiguous. [a-z_]+
	doc_type = 'newtype'

	@classmethod
	def will_handle(klass, url):
		# UMAD uses prefix matching to select an appropriate Distiller
		# for a given URL. Try to be as specific as possible, in case
		# other Distillers are working close by.
		return url.startswith('http://newtype/common/prefix/for/all/newtypes/')


	# This is the heavy lifter, it all happens here. blobify is called, and
	# may return multiple documents either via an iterator (recommended) or
	# list.
	#
	# If something goes wrong, you can return None (nothing to do) or raise
	# an exception (something blew up, we're giving up).
	#
	# As a convenience, various methods and attributes are made available
	# by the base Distiller class. Call `self.enqueue_reindex` if you need
	# to enqueue a URL for (re)indexing, and `self.enqueue_deletion` to
	# flag a URL for deletion (eg. you discover that an existing document
	# has disappeared and needs to expunged from the index.
	#
	# `self.auth` is a dictionary of authentication credentials that can be
	# passed to the `requests` HTTP library (or used in other creative
	# ways). `self.accept_json` is suitable for passing as the `headers`
	# parameter to `requests.get` and its siblings.
	def blobify(self):

		# This is the starting point for every distiller, take the
		# supplied URL then do with it what you will.
		url = self.url

		# The final path component is always their nickname, so grab that
		nickname = url.rpartition('/')[-1]

		# The base Distiller class can supply credentials for you, it's
		# a 2-tuple of (user,pass).
		newtype_credentials = self.auth['newtype']

		# Get the data from our hypothetical API endpoint
		for newtype in retrieve_newtypes(auth=newtype_credentials, headers=self.accept_json):
			# Each newtype is a dict, pull out the data we want and
			# form a clean document.
			document = {}

			# Because a single URL can return multiple documents,
			# each document sends along its own URL. Newtype is
			# 1-to-1, so we pass through what we were given.
			document['url'] = url

			# The title is displayed in search results if present,
			# otherwise we fall back to the URL.
			document['title'] = nickname

			# local_id is a preferentially weighted identifier
			# that's unique within each doctype, allowing for
			# direct "keyed" search lookups.
			document['local_id'] = nickname

			# Find out what days they're at work.
			workdays = get_workdays(nickname)

			# The blob is a machine-relevant chunk of text, it's
			# what we search against by default. It's keyword-rich
			# with minimal noise.
			document['blob'] = " ".join(newtype.values()+workdays)

			# The excerpt is a nicely composed human-targeted
			# summary of the document. If present, it will be
			# displayed in search results, in preference to the
			# blob.
			document['excerpt'] = "{name} is {age}. His favourite colour is {favourite_colour}, and he works on {0}/{1}/{2}, in {u_type} uniform.".format(*workdays, **newtype)

			# Finally, send off the finished document for indexing.
			yield document
