import datetime
from dateutil.tz import *

import elasticsearch

from localconfig import *


# XXX: This mechanism does not define ordering of distiller classes in the
# list. Might this be a problem when it comes to iterating the distillers and
# calling will_handle()?

# XXX: Is the ordering in distil/__init__.py honoured for our purposes? No, it
# appears to be alpha-ordered when iterated.

import inspect
import distil
distillers = [ x[1] for x in inspect.getmembers(distil, inspect.isclass) ]


KNOWN_DOC_TYPES = { d.doc_type for d in distillers }


# A list of hostnames/IPs and ports, passed straight to the ES constructor.
ELASTICSEARCH_NODES = [ "umad1.syd1.anchor.net.au:9200", "umad2.syd1.anchor.net.au:9200", "umad3.syd1.anchor.net.au:9200" ]



def get_distiller(url):
	'''Return a distiller that's suitable for the URL provided'''

	for distiller in distillers:
		if distiller.will_handle(url):
			return distiller(url)

	raise LookupError("We don't have a module that can handle that URL: {0}".format(url))


def determine_doc_type(url):
	"""We return None if no matches are found, caller to deal with it"""
	for distiller in distillers:
		if distiller.will_handle(url):
			return distiller.doc_type





es = elasticsearch.Elasticsearch(ELASTICSEARCH_NODES)
indices = elasticsearch.client.IndicesClient(es)

class InvalidDocument(Exception): pass

def add_to_index(document):
	key = document['url']

	doc_type = determine_doc_type(key)
	if doc_type is None:
		raise LookupError("We don't have a module that can handle that URL: {0}".format(url))

	index_name = "umad_%s" % doc_type

	# Sanity check the document. Our minimal requirement for the document
	# is that it has a 'blob' and 'url' key, but ES will support much
	# richer arbitrary fields.
	if 'url' not in document:
		raise InvalidDocument("The document MUST have a 'url' field, cannot add to index: {0}".format(document))
	if 'blob' not in document:
		raise InvalidDocument("The document MUST have a 'blob' field, cannot add to index: {0}".format(document))

	# Pass the document's type along as extra metadata, for the renderer's
	# benefit.
	document['doc_type'] = doc_type

	# Get the current time in UTC and set `last_indexed` on the document
	document['last_indexed'] = datetime.datetime.now(tzutc())

	es.index(
		index = index_name,
		doc_type = doc_type,
		id = key,
		body = document
	)

	return


# Useful for cleaning up mistakes when docs get indexed incorrectly, eg.:
# >>> import elasticsearch_backend
# >>> elasticsearch_backend.delete_from_index('https://docs.anchor.net.au/some/obsolete/page')
def delete_from_index(url):
	doc_type = determine_doc_type(url)
	index_name = "umad_%s" % doc_type
	#print "Index type is {0}".format(index_name)

	try:
		es.delete(
			index = index_name,
			doc_type = doc_type,
			id = url
		)
	except elasticsearch.exceptions.NotFoundError as e:
		pass

	return


def valid_search_query(search_term):
	"Return True/False as to whether the query is valid"
	# XXX: This could probably just be "_all" for the index.
	test_results = indices.validate_query(index="_all", q=search_term)
	return test_results[u'valid']

def type_boost(doctype, boost_factor):
	return { "boost_factor": boost_factor, "filter": { "type": { "value": doctype } } }

def linear_deweight_for_age(scale='28d'):
	# We can mix this in for RT tickets and any documents with a "last_updated" field.
	# The default decay factor is 0.5, meaning that the score is halved for every 28 days of age.
	return { "gauss": { "last_updated": { "scale": scale } } }

def build_hit(doc):
	source = doc['_source']
	# Highlight data is only present if the highlighter found something relevant.
	# Fake it up if necessary so the later code can make clean assumptions.
	if not 'highlight' in doc:
		doc['highlight'] = {}
	hit = {
		'id':             doc['_id'],
		'score':          doc['_score'],
		'type':           doc['_type'],
		'blob':           source['blob'],
		'other_metadata': source,
		'highlight':      doc['highlight']
	}
	if 'url' in hit['other_metadata']:
		del(hit['other_metadata']['url'])
	if 'blob' in hit['other_metadata']:
		del(hit['other_metadata']['blob'])

	# A hit looks like this:
	# {
	#     'other_metadata':
	#         {
	#             u'url':      u'http://www.imdb.com/title/tt1319708/',
	#             u'customer': u'Hyron',
	#             u'blob':     u"I didn't ask for this",
	#             u'name':     u'Deus Ex: Human Revolution'
	#         },
	#     'score': 0.095891505000000002,
	#     'type':  u'quote_page',
	#     'id':    u'http://www.imdb.com/title/tt1319708/',
	#     'blob':  u"I didn't ask for this",
	#     'highlight':
	#         {
	#             u'blob':    [ u"list", u"of", u"highlighted", u"blob", u"fragments" ],
	#             u'excerpt': [ u"singleton list of the excerpt, highlighted up" ],
	#         }
	# }

	return hit


def search_index(search_term, max_hits=0):
	all_hits = []

	# Perform one query for each backend, because we might have tainted indices that we
	# don't want to touch.
	for backend in KNOWN_DOC_TYPES:
		q_dict = {
			"query": {
				"function_score": {
					"functions": [
						# This is a dummy boost, as ES complains if there are no functions to run.
						{ "boost_factor": 1.0 },
						# Goal: Provsys ranks highest, then new gollum docs, then old Map wiki, then RT tickets.
						type_boost('provsys', 3.0),
						type_boost('gollum',  2.0),
						type_boost('map',     1.8),
						# Funnel pages are low-value
						{ "boost_factor": 0.5, "filter": { "query": { "query_string": { "query": "url:(Funnel AND Sales)" } } } },
						# CSR Procedures are especially useful
						{ "boost_factor": 2.5, "filter": { "query": { "query_string": { "query": "url:\"CustomerService/Procedures\"" } } } },
					],
					"query": {
						"query_string": {
							"query": search_term,
							"default_operator": "and",
							"fields": [ "title^1.5", "customer_name", "blob" ]
						}
					},
					"score_mode": "multiply"
				}
			},
			"highlight": {
				"pre_tags": [ "<strong>" ],
				"post_tags": [ "</strong>" ],
				# Pre-escape the highlight fragments treating them as HTML content, then slap our highlighting tags on
				"encoder": "html",
				"fragment_size": 200,
				"fields": {
					"blob": {},
					"excerpt": {
						# Don't break down excerpt fields, they're ready-to-consume
						"number_of_fragments": 1
					}
				}
			}
		}

		if backend == 'rt':
			# We *should* be able to mix this in with a filter so that it only applies to rt documents,
			# but that doesn't seem to work and all the non-rt shards complain.
			q_dict['query']['function_score']['functions'].append(linear_deweight_for_age())
			# Searching for RT ticket numbers is highly appropriate.
			q_dict['query']['function_score']['query']['query_string']['fields'].append("local_id^3")

		idx_name = "umad_{0}".format

		# Don't freak out if some indices don't exist yet.
		try:
			if max_hits:
				results = es.search(index=idx_name(backend), body=q_dict, size=max_hits)
			else:
				results = es.search(index=idx_name(backend), body=q_dict) # ES defaults to 10
		except elasticsearch.NotFoundError as e:
			continue

		docs = results['hits']['hits']
		hits = [ build_hit(doc) for doc in docs ]

		all_hits += hits

	# Would be nice to turn this section into yields, lose the hit_limit if we can get away without it
	return {'hits':all_hits, 'hit_limit':max_hits}


def get_from_index(url):
	doc_type = determine_doc_type(url)
	index_name = "umad_%s" % doc_type

	args = [index_name, url]
	return es.get(index=index_name, id=url)
