from distil import *

distillers = [
	MoinMapDistiller ,
	RtTicketDistiller ,
	GollumDistiller ,
	ProvsysResourceDistiller ,
	ProvsysServersDistiller ,
	ProvsysVlansDistiller ,
	CustomerDistiller ,
	GenericHttpDistiller ,
	]

KNOWN_DOC_TYPES = [ 'provsys', 'docs', 'map', 'rt' ]
KNOWN_DOC_TYPES = [ d.doc_type for d in distillers ]


def get_distiller(url):
	'''Return a distiller that's suitable for the URL provided'''

	for distiller in distillers:
		if distiller.will_handle(url):
			return distiller(url)

#	if MoinMapDistiller.will_handle(url):
#		return MoinMapDistiller(url)
#
#	if RtTicketDistiller.will_handle(url):
#		return RtTicketDistiller(url)
#
#	if GollumDistiller.will_handle(url):
#		return GollumDistiller(url)
#
#	if ProvsysResourceDistiller.will_handle(url):
#		return ProvsysResourceDistiller(url)
#
#	if ProvsysServersDistiller.will_handle(url):
#		return ProvsysServersDistiller(url)
#
#	if ProvsysVlansDistiller.will_handle(url):
#		return ProvsysVlansDistiller(url)
#
#	if GenericHttpDistiller.will_handle(url):
#		return GenericHttpDistiller(url)

	raise LookupError("We don't have a module that can handle that URL: {0}".format(url))


def determine_doc_type(url):
	for distiller in distillers:
		if distiller.will_handle(url):
			return distiller.doc_type

#	if url.startswith('https://map.engineroom.anchor.net.au/'):
#		return "map"
#
#	if url.startswith('https://rt.engineroom.anchor.net.au/'):
#		return "rt"
#
#	if url.startswith('https://resources.engineroom.anchor.net.au/'):
#		return "provsys"
#
#	if url.startswith('https://docs.anchor.net.au/'):
#		return "docs"

	# Be explicit about this. Maybe should be "untyped"?
	# XXX: Actually, no, an unknown doctype is useless I think, force the
	# user to make decisions.  ES *needs* a doc_type, all documents of a
	# given type should have the same "shape".
	return None


# A list of hostnames/IPs and ports, passed straight to the ES constructor.
ELASTICSEARCH_NODES = [ "umad.anchor.net.au:9200" ]


# Not using "_all" because you might have other indices in the ES cluster, or have polluted your indices
# XXX: Should be possible to get rid of this, unify the indices into a single one. Only used by elasticsearch_backend.py
ELASTICSEARCH_SEARCH_INDEXES = ','.join( [ "umad_%s" % x for x in KNOWN_DOC_TYPES ] )

# How many hits do you want to display? ES doesn't easily offer pagination, and
# besides, results past the first page probably suck anyway.
MAX_HITS = 50
