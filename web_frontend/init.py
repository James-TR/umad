# vim: set fileencoding=utf8
import sys
import os
import re
import cStringIO
import cgi
from optparse import OptionParser
from operator import itemgetter

from bottle import route, request, response, template, static_file, run, view, default_app

from dateutil.parser import *
from dateutil.tz import *

from elasticsearch_backend import *


VERSION_STRING = 'no version string found'
DEBUG = False
def debug(msg, force_debug=False):
	if DEBUG or force_debug:
		sys.stderr.write(str(msg) + '\n')
		sys.stderr.flush()

UMAD_INDEXER_URL = os.environ.get('UMAD_INDEXER_URL', 'https://umad-indexer.anchor.net.au/')


def highlight_document_source(url):
	# Valid values are kept in umad.css
	# - highlight-miku
	# - highlight-luka
	# - highlight-portal-orange
	# - highlight-portal-blue
	# - highlight-lavender
	# - highlight-red
	# - highlight-coral
	# - highlight-orange
	#
	# We return a 2-element dict containing a pretty_name and css_class
	if url.startswith('https://map.engineroom.anchor.net.au/'):
		return ('Map',      'highlight-miku')
	if url.startswith('https://rt.engineroom.anchor.net.au/'):
		return ('RT',       'highlight-lavender')
	if url.startswith('https://resources.engineroom.anchor.net.au/'):
		return ('Provsys',  'highlight-portal-blue')
	if url.startswith('https://docs.anchor.net.au/'):
		return ('Docs',   'highlight-orange')
	if url.startswith('https://customer.api.anchor.com.au/customers/'):
		return ('Customer', 'highlight-pink')
	if url.startswith('https://domains.anchor.com.au/'):
		return ('Domain', 'highlight-portal-orange')

	return ('DEFAULT', '')



@route('/umad-opensearch.xml')
def serve_opensearch_definition():
	opensearch_template = '''<?xml version="1.0" encoding="UTF-8"?>
<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">
  <ShortName>{{shortname}}</ShortName>
  <Description>{{description}}</Description>
  <Tags>{{tags}}</Tags>
  <Contact>{{contact}}</Contact>
  <Url type="text/html" 
       template="{{search_root}}?q={searchTerms}&amp;count={count?}"/>
  <Url type="application/opensearchdescription+xml" 
       rel="self" 
       template="{{search_root}}umad-opensearch.xml"/>
  <Image type="image/x-icon" 
         height="16" 
         width="16">{{search_root}}static/img/badapple16.ico</Image>
  <Image type="image/png" 
         height="64" 
         width="64">{{search_root}}static/img/badapple64.png</Image>
</OpenSearchDescription>'''

	search_root = '{0}://{1}/'.format(request['wsgi.url_scheme'], request['HTTP_HOST'])
	opensearch_description = template(opensearch_template,
		shortname='UMAD? ({0})'.format(request['SERVER_NAME']),
		description='Ask about Anchor and ye shall receive.',
		tags='anchor provsys rt tickets map wiki moin gollum docs',
		contact='barney.desmond@anchor.net.au',
		search_root=search_root)

	response.content_type = 'application/opensearchdescription+xml'
	return opensearch_description


@route('/static/<filepath:path>')
def server_static(filepath):
	static_path = os.path.join( os.getcwd(), 'static' )
	return static_file(filepath, root=static_path)

@route('/heartbeat')
def heartbeat():
	response.content_type = 'text/plain; charset=UTF-8'

	search_term = '*'
	count = MAX_HITS

	VERSION_STRING = 'no version string found'
	if os.path.exists('RUNNING_VERSION'):
		with open('RUNNING_VERSION', 'r') as f:
			VERSION_STRING = f.readline().strip()

	template_dict = {}
	template_dict['searchterm'] = search_term
	template_dict['hits'] = []
	template_dict['hit_limit'] = 0
	template_dict['valid_search_query'] = True
	template_dict['doc_types_present'] = set()
	template_dict['version_string'] = VERSION_STRING
	template_dict['umad_indexer_url'] = UMAD_INDEXER_URL

	results = search_index(search_term, max_hits=count)
	result_docs = results['hits']
	template_dict['hit_limit'] = results['hit_limit']

	# Clean cruft
	result_docs = [ x for x in result_docs if not x['id'].startswith('https://ticket.api.anchor.com.au/') ]
	result_docs = [ x for x in result_docs if not x['id'].startswith('provsys://') ]

	# Sort
	result_docs.sort(key=itemgetter('score'), reverse=True)
	for doc in result_docs:
		if doc['type'] == 'rt' and doc['other_metadata'].get('status') == 'deleted': continue

		hit = {}
		hit['id'] = doc['id']
		hit['score'] = "{0:.2f}".format(doc['score'])

		if doc['highlight'].get('excerpt'):
			hit['extract'] = doc['highlight'].get('excerpt')[0]
		elif doc['highlight'].get('blob'):
			hit['extract'] = doc['highlight'].get('blob')[0]
		else:
			hit['extract'] = cgi.escape(doc['blob'][:200])

		if 'last_updated' in doc['other_metadata']:
			pretty_last_updated = parse(doc['other_metadata']['last_updated']).astimezone(tzlocal()).strftime('%Y-%m-%d %H:%M')
			doc['other_metadata']['last_updated_sydney'] = pretty_last_updated

		hit['highlight_class'] = highlight_document_source(doc['id'])[1]
		if hit['highlight_class']:
			template_dict['doc_types_present'].add(highlight_document_source(doc['id']))

		hit['other_metadata'] = doc['other_metadata']
		hit['other_metadata'] = dict((k,v) for k,v in hit['other_metadata'].iteritems() if v is not None)

		template_dict['hits'].append(hit)

	rendered_html = template('mainpage', template_dict).encode('utf8')


	# Perform analysis, comrade!
	output = []


	# Each source should have at least one document in them.
	# When searching for everything, check that we have buttons for every source
	num_sources = len(KNOWN_DOC_TYPES)
	num_source_buttons = rendered_html.count('btn btn-default doc-type')

	if num_sources != num_source_buttons:
		output.append( "✘ Some buttons are missing!  The buttons that should be shown are: {}".format(', '.join(KNOWN_DOC_TYPES)) )
	else:
		output.append( "✔ Correct number of buttons shown for {} document sources".format(num_sources) )


	# Each source should have a minimum of MAX_HITS results returned.
	# Check that we get at least that many results.
	expected_results = num_sources * count
	min_results      = num_sources

	match = re.search(r'Display limited to <strong><span id="hitcount">(\d+)</span> results', rendered_html)
	if match: num_results = int(match.group(1))
	else:     num_results = 0

	if not match: output.append( "✘ Failure while parsing page, couldn't find 'Display limited to etc...' in the source" )
	else:         output.append( "✔ A number of results is being reported" )

	if num_results < min_results: output.append( "✘ Reporting {} results, not even one for each doctype, something is wrong".format(num_results) )
	else:                         output.append( "✔ Reporting {} results, that's at least one for each doctype ({})".format(num_results, min_results) )

	if num_results < expected_results: output.append( "✘ Not enough results. Expected at least {}, but only {} reported".format(expected_results, num_results) )
	else:                              output.append( "✔ Reported number of results ({}) matches expectations".format(expected_results) )

	# Check if we got the expected number of results shown on the page
	# XXX: Does this work for domains?
	counted_hits = rendered_html.count('div class="hitlink"')
	if counted_hits != num_results: output.append( "✘ Reported {} results but only counted {} result cards".format(num_results, counted_hits) )
	else:                           output.append( "✔ Reported result count of {} appears to be correct".format(num_results) )

	if all( [ x.startswith("✔") for x in output ] ):
		return "OK"

	failure_lines = [ x for x in output if not x.startswith("✔") ]
	first_failure = [ str(x) for x in failure_lines[:1] ]
	return "WOW SUCH FAIL VERY SAD: {}".format( ''.join(first_failure) ).replace('OK','**')



@route('/')
@view('mainpage')
def search():
	# Fetch environment
	global VERSION_STRING
	VERSION_STRING = 'no version string found'
	if os.path.exists('RUNNING_VERSION'):
		with open('RUNNING_VERSION', 'r') as f:
			VERSION_STRING = f.readline().strip()

	q     = request.query.q     or ''
	count = request.query.count or MAX_HITS
	# Some people are weird, yo
	try: count = int(count)
	except: count = MAX_HITS

	debug(u"Search term: {0}, with count of {1}".format(q, count).encode('utf8'))

	# Fill up a dictionary to pass to the templating engine. It expects the searchterm and a list of document-hits
	template_dict = {}
	template_dict['searchterm'] = q
	template_dict['hits'] = []
	template_dict['hit_limit'] = 0
	template_dict['valid_search_query'] = True
	template_dict['doc_types_present'] = set()

	template_dict['version_string']   = VERSION_STRING
	template_dict['umad_indexer_url'] = UMAD_INDEXER_URL


	if q:
		# ES is case insensitive, but our query mangling below isn't.  Lets just lowercase it all now before searching
		search_term = q.lower()

		# If the query is prefixed with doctype:, then only return results of _type:doctype
		# eg: customer: Anchor
		if search_term.split(':')[0] in KNOWN_DOC_TYPES:
			search_term = '_type:' + search_term.replace(':', ' ', 1)

		# Pre-query validity check
		template_dict['valid_search_query'] = valid_search_query(search_term)
		if not template_dict['valid_search_query']:
			# Bail out early
			return template_dict

		# Search nao
		results = search_index(search_term, max_hits=count)
		result_docs = results['hits']
		template_dict['hit_limit'] = results['hit_limit']

		# Clean out cruft, because our index is dirty right now
		result_docs = [ x for x in result_docs if not x['id'].startswith('https://ticket.api.anchor.com.au/') ]
		result_docs = [ x for x in result_docs if not x['id'].startswith('provsys://') ]

		# Sort all results before presentation
		result_docs.sort(key=itemgetter('score'), reverse=True)
		for doc in result_docs:
			# doc is a dictionary with keys:
			#     id		str
			#     score		number
			#     type		str
			#     blob		str
			#     other_metadata	dict
			#     highlight		dict

			# Don't display deleted RT tickets, bail out early.
			if doc['type'] == 'rt' and doc['other_metadata'].get('status') == 'deleted':
				continue

			# Elasticsearch pre-escapes HTML for us, before applying its highlight tags.
			# We then pass this extract to the renderer, directing it not to escape HTML.
			hit = {}
			hit['id'] = doc['id']
			hit['score'] = "{0:.2f}".format(doc['score'])

			# ES always returns a highlight dict now, though it may be empty.
			# Test for presence of blob and excerpt, and use them.
			#
			# I've mixed feelings on how to present the highlight fragments. Google
			# appears to present just one. We always get a list of highlights (up to 5),
			# and could provide a couple of fragments like so:
			#
			#     extract = '&hellip;<br/>'.join(highlights)
			#
			# But, it's difficult to identify the breaks visually so I'm sticking
			# with 1st-fragment for now.
			if doc['highlight'].get('excerpt'): # None (False) if not present, or empty list (False), or populated list (True)
				hit['extract'] = doc['highlight'].get('excerpt')[0]
			elif doc['highlight'].get('blob'): # None (False) if not present, or empty list (False), or populated list (True)
				hit['extract'] = doc['highlight'].get('blob')[0]
			else:
				hit['extract'] = cgi.escape(doc['blob'][:200])

			if 'last_updated' in doc['other_metadata']:
				pretty_last_updated = parse(doc['other_metadata']['last_updated']).astimezone(tzlocal()).strftime('%Y-%m-%d %H:%M')
				doc['other_metadata']['last_updated_sydney'] = pretty_last_updated

			hit['highlight_class'] = highlight_document_source(doc['id'])[1]
			if hit['highlight_class']:
				template_dict['doc_types_present'].add(highlight_document_source(doc['id']))

			# Any other keys that the backend might provide
			hit['other_metadata'] = doc['other_metadata']
			# Filter out any metadata keys with a value of None
			# (we've seen this on RT tickets' "Category" field).
			hit['other_metadata'] = dict((k,v) for k,v in hit['other_metadata'].iteritems() if v is not None)

			# More About Escaping, we have:
			#
			# highlight_class: CSS identifier(?), used as an HTML attribute, please keep this sane and not requiring escaping; let renderer escape it
			# id:              A URL, used as HTML and as an attribute; let renderer escape it
			# score:           Numeric string
			# type:            Simple text string
			# extract:         Arbitrary text, used as HTML; we escape it
			# other_metadata:  Arbitrary text, let the renderer escape it

			template_dict['hits'].append(hit)

	return template_dict


# For encapsulating in a WSGI container
application = default_app()


def main(argv=None):
	if argv is None:
		argv = sys.argv

	parser = OptionParser()
	parser.add_option("--verbose", "-v", dest="debug", action="store_true", default=False,       help="Log exactly what's happening")
	parser.add_option("--bind", "-b",    dest="bind_host",                  default='localhost', help="Hostname/IP to listen on, [default: %default]")
	parser.add_option("--port", "-p",    dest="bind_port", type="int",      default=8080,        help="Port number to listen on, [default: %default]")
	(options, search_terms) = parser.parse_args(args=argv)

	global DEBUG
	DEBUG = options.debug

	global VERSION_STRING
	if os.path.exists('RUNNING_VERSION'):
		with open('RUNNING_VERSION', 'r') as f:
			VERSION_STRING = f.readline().strip()
	debug("Using version string {0}".format(VERSION_STRING))

	run(host=options.bind_host, port=options.bind_port, debug=True)

	return 0

if __name__ == "__main__":
	sys.exit(main())

