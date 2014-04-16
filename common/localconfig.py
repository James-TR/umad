from distil import *


# >>> Make your edits BELOW here <<<
distillers = [
	MoinMapDistiller ,
	RtTicketDistiller ,
	GollumDistiller ,
	ProvsysResourceDistiller ,
	ProvsysServersDistiller ,
	ProvsysVlansDistiller ,
	CustomerDistiller ,
	DomainDistiller ,
	# This is a demo Distiller
	#NewtypeDistiller ,
	]

# A list of hostnames/IPs and ports, passed straight to the ES constructor.
ELASTICSEARCH_NODES = [ "umad1.syd1.anchor.net.au:9200", "umad2.syd1.anchor.net.au:9200", "umad3.syd1.anchor.net.au:9200" ]

# >>> Make your edits ABOVE here <<<


KNOWN_DOC_TYPES = { d.doc_type for d in distillers }

def get_distiller(url):
	'''Return a distiller that's suitable for the URL provided'''

	for distiller in distillers:
		if distiller.will_handle(url):
			return distiller(url)

	raise LookupError("We don't have a module that can handle that URL: {0}".format(url))


def determine_doc_type(url):
	for distiller in distillers:
		if distiller.will_handle(url):
			return distiller.doc_type

	# Be explicit about returning None. Maybe it should be "untyped"..?
	return None

	# XXX: Actually, no, an unknown doctype is useless I think, force the
	# user to make decisions.  ES *needs* a doc_type, all documents of a
	# given type should have the same "shape".


# Not using "_all" because you might have other indices in the ES cluster, or have polluted your indices
# XXX: Should be possible to get rid of this, unify the indices into a single one. Only used by elasticsearch_backend.py
ELASTICSEARCH_SEARCH_INDEXES = ','.join( [ "umad_%s" % x for x in KNOWN_DOC_TYPES ] )

# How many hits do you want to display of each doctype? ES doesn't easily offer
# pagination, and besides, results past the first page probably suck anyway.
MAX_HITS = 50
