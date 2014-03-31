import re
from operator import itemgetter
from itertools import chain
from dateutil.parser import *
from dateutil.tz import *
import requests
import redis

TICKET_URL_TEMPLATE = 'https://ticket.api.anchor.com.au/ticket/{0}'.format
TICKET_MESSAGE_URL_BASE = 'https://ticket.api.anchor.com.au/ticket_message'
WEB_TICKET_URL_TEMPLATE = 'https://rt.engineroom.anchor.net.au/Ticket/Display.html?id={_id}'.format

TICKET_UNSTALL_RE = re.compile(r'The ticket \d+ has not received a reply from the requestor for.*Get on the phone with the client right now', re.I)

CUSTOMER_NAME_CACHE_TTL = 7 * 24 * 60 * 60 # 1 week, in seconds

from distiller import Distiller


class RtTicketDistiller(Distiller):
	doc_type = 'rt'

	@classmethod
	def will_handle(url):
		return url.startswith( ('rt://', 'https://rt.engineroom.anchor.net.au/') )

	@staticmethod
	def clean_message(msg):
		fields_we_care_about = (
				'_id',
				'from_email',
				'from_realname',
				'content',
				'subject',
				'created',
				'private',
				)
		clean_msg = dict([ (k,v) for (k,v) in msg.iteritems() if k in fields_we_care_about ])

		# When we reply on a ticket, we get the ticket-wide subject if we don't specify a different Subject
		if clean_msg['subject'] == 'No Subject':
			clean_msg['subject'] = ''

		# Message body cleanup, attempt to nuke junk
		body_lines = clean_msg['content'].split('\n')
		body_lines = [ line.strip() for line in body_lines ]                     # Remove leading and trailing whitespace for later compaction
		body_lines = [ line for line in body_lines if not line.startswith('>') ] # Quoted lines
		body_lines = [ line for line in body_lines if not line == '' ]           # Empty lines
		body_lines = [ line for line in body_lines if line not in ('Hi,', 'Hello,') or len(line) > 20 ] # Greetings
		lines_beginning_with_thanks = [ line for line in body_lines if line.startswith('Thanks') and len(line) < 10 ] # Kill trailing platitudes
		if lines_beginning_with_thanks:
			body_lines = body_lines[:body_lines.index(lines_beginning_with_thanks[0])]
		if 'Regards,' in body_lines:                                             # Kill trailing platitudes
			body_lines = body_lines[:body_lines.index('Regards,')]
		if '--' in body_lines:                                                   # Kill signatures
			body_lines = body_lines[:body_lines.index('--')]

		# And put it all back together again
		clean_msg['content'] = '\n'.join(body_lines)

		# Sloppiness in the ticket API?
		if clean_msg['from_email'] is None:
			clean_msg['from_email'] = ''

		# Sloppiness in the ticket API?
		if clean_msg['from_realname'] is None:
			clean_msg['from_realname'] = ''

		# Kill quotemarks around names
		clean_msg['from_realname'] = clean_msg['from_realname'].strip("'\"")

		# Don't index the automated comment that gets added when a ticket unstalls itself
		if TICKET_UNSTALL_RE.search(clean_msg['content']):
			clean_msg['content'] = ''

		return clean_msg


	# Expect an URL of form:
	# https://rt.engineroom.anchor.net.au/Ticket/Display.html?id=152
	def tidy_url(self):
		"Turn the RT URL into an API URL"

		if self.url.startswith('rt://'):
			self.url = self.url.replace('rt://', 'https://rt.engineroom.anchor.net.au/Ticket/Display.html?id=')

		rt_url_match = re.match(r'https://rt\.engineroom\.anchor\.net\.au/Ticket/\w+\.html\?id=(\d+)', self.url)
		if rt_url_match is None:
			raise ValueError("This URL doesn't match our idea of an RT URL: %s" % self.url)
		ticket_number = rt_url_match.group(1)

		self.ticket_url = TICKET_URL_TEMPLATE(ticket_number)


	def blobify(self):

		# Customer Name cache
		try:
			cn_cache = redis.StrictRedis(host='localhost', port=6379, db=0)
			cn_key   = "customer_id:{0}".format
			cn_get   = lambda x: None if x is None else cn_cache.get(cn_key(x))  # Being a jackass, I <3 curry
		except:
			raise RuntimeError("Can't connect to local Redis server to cache customer details")


		# Prepare auth
		try:
			api_credentials = self.auth['anchor_api']
		except:
			raise RuntimeError("You must provide Anchor API credentials, please set API_AUTH_USER and API_AUTH_PASS")

		# Prep URL and headers for requests
		self.tidy_url()
		ticket_url   = self.ticket_url

		headers = {}
		headers['Accept'] = 'application/json'

		# Get ticket from API
		ticket_response = requests.get(ticket_url, auth=api_credentials, verify=True, headers=headers)
		try:
			ticket_response.raise_for_status()
		except:
			#debug("Couldn't get ticket from API, HTTP error %s, probably not allowed to view ticket" % ticket_response.status_code)
			if response.status_code == 404:
				self.enqueue_deletion()
			return

		# Mangle ticket until no good
		ticket = ticket_response.json() # FIXME: add error-checking
		if 'code' in ticket: # we got a 404 or 403 or something, probably redundant after the raise_for_status check
			#debug("Ticket API hates us? %s" % str(ticket) )
			return

		ticket_url         = WEB_TICKET_URL_TEMPLATE(**ticket) # Canonicalise the ticket URL, as merged tickets could have been accessed by multiple URLs
		ticket_number      = "{_id}".format(**ticket)
		ticket_subject     = ticket['subject']
		ticket_status      = ticket['status']
		ticket_queue       = ticket['queue']
		ticket_category    = ticket['category'] # Unlike some other fields, this can be None
		ticket_priority    = ticket['priority']
		ticket_lastupdated = ticket['lastupdated']
		customer_visible   = True if not ticket['private'] else False

		# XXX: Handle deleted and merged tickets now. Use indexer_url here and
		# call for the ticket's deletion.
		#  - Deleted tickets: Delete the URL
		#  - Merged tickets: When deleting we MUST act on distiller.url, not
		#    ticket_url that we got from the API (that's the ticket it was merged into)
		#  - What about tickets that have been merged and then deleted? We want to
		#    delete both distiller.url and ticket_url

		# Any residual deleted tickets are hidden from display later on,
		# but for now we should delete them when we spot them.
		if ticket_status == 'deleted':
			# XXX: Is this the correct URL to nuke? For A merged into B,
			# this will nuke B if it was also deleted. A should have been
			# deleted in the previous step.
			self.enqueue_deletion(url=ticket_url)
			print "Status=deleted, enqueued for deletion from index: {0}".format(ticket_url)
			return

		# This may be None if there's no Related Customer set
		customer_url = ticket['customer_url']
		customer_id  = customer_url.rpartition('/')[-1] if customer_url else None

		customer_name = None
		if customer_id:
			if cn_get(customer_id) is None:
				# We need to retrieve it from the customer API
				customer_response = requests.get(customer_url, auth=api_credentials, verify=True, headers=headers)
				if customer_response.status_code != 200:
					retrieved_name = '__NOT_FOUND__'
				else:
					customer = customer_response.json() # FIXME: add error-checking
					retrieved_name = customer.get('description', '__NOT_FOUND__') # more paranoia against the unexpected

				# Now stash it
				cn_cache.setex( cn_key(customer_id), CUSTOMER_NAME_CACHE_TTL, retrieved_name ) # Assume success, should only fail if TTL is invalid

			# Now make use of it
			maybe_customer_name = cn_get(customer_id)
			if maybe_customer_name != "__NOT_FOUND__":
				# Even if everything goes wrong and cn_key() gives us
				# None after hitting that customer API, it's okay.
				customer_name = maybe_customer_name

		# Get a real datetime object, let ElasticSearch figure out the rest
		ticket_lastupdated = parse(ticket_lastupdated)
		ticket_lastupdated = ticket_lastupdated.astimezone(tzutc())

		# Get associated messages from API
		messages_response  = requests.get(TICKET_MESSAGE_URL_BASE, params={'ticket_url': self.ticket_url}, auth=api_credentials, verify=True, headers=headers)
		try:
			messages_response.raise_for_status()
		except:
			#debug("Error getting Messages from API, got HTTP response {0}".format(ticket_response.status_code))
			return



		# Mangle messages until no good
		messages = messages_response.json() # FIXME: add error-checking
		messages = [ self.clean_message(x) for x in messages ]

		# We see git@bitts rollin', we hatin'
		messages = [ m for m in messages if not m['from_email'].startswith('git@bitts') ]

		# Pull out the first post, we'll use it for the excerpt
		# XXX: Blindly assumes the first post has the lowest numerical ID, check with dev team whether this is correct
		messages.sort(key=itemgetter('_id'))
		# Some messages are empty or otherwise useless, so ignore them
		messages = [ m for m in messages if m['subject'] or m['content'] or m['from_email'] ]

		# XXX: Incurs an explosion if we get a ticket with no messages lol
		first_post = messages[0].copy()
		# For some reason, the subject line sometimes appears to be empty. Not
		# sure if this is a problem with the ticket API.
		if not first_post['subject']:
			first_post['subject'] = ticket_subject
		first_post['content'] = '\n'.join( first_post['content'].split('\n')[:6] )
		ticket_excerpt = first_post['content'].encode('utf8')

		# Grab customer-presentable messages
		if customer_visible:
			public_messages = [ m for m in messages if not m['private'] ]

			# XXX: We have found non-private tickets without any customer-visible messages, like rt://8785
			if public_messages:
				public_first_post = public_messages[0]
				# For some reason, the subject line sometimes appears to be empty. Not
				# sure if this is a problem with the ticket API.
				if not public_first_post['subject']:
					public_first_post['subject'] = ticket_subject
				public_ticket_excerpt = public_first_post['content'].encode('utf8')
			else:
				public_ticket_excerpt = "No excerpt could be found for this ticket, please contact Anchor Support for assistance"

		# This is an empty list if the ticket has seen no actual communication (eg. internal-only tickets)
		contact_timestamps = [ parse(m['created']) for m in messages if not m['private'] ]


		# Put together our response. We have:
		# - ticket_url (string)
		# - ticket_subject (string)
		# - ticket_status (string)
		# - ticket_queue (string)
		# - ticket_category (string or None)
		# - ticket_priority (int)
		# - messages (iterable of dicts)
		# - public_messages (iterable of dicts)
		# - public_ticket_excerpt (string)

		all_message_lines = [ x for x in chain(*[ message['content'].split('\n') for message in messages ]) ]
		if customer_visible:
			public_all_message_lines = [ x for x in chain(*[ message['content'].split('\n') for message in public_messages ]) ]
		realnames         = list(set( [ x['from_realname'] for x in messages if x['from_realname'] != '' ] ))
		emails            = list(set( [ x['from_email']    for x in messages if x['from_email']    != '' ] ))

		blob = " ".join([
				ticket_number.encode('utf8'),
				ticket_subject.encode('utf8'),
				' '.join(realnames).encode('utf8'),
				' '.join(emails).encode('utf8'),
				' '.join(all_message_lines).encode('utf8'),
				])

		public_blob = None
		if customer_visible and public_all_message_lines: # Double-check for existence of real content
			public_blob = " ".join([
					ticket_number.encode('utf8'),
					ticket_subject.encode('utf8'),
					' '.join(realnames).encode('utf8'),
					' '.join(emails).encode('utf8'),
					' '.join(public_all_message_lines).encode('utf8'),
					])

		ticketblob = {
			'url':              ticket_url,
			'blob':             blob,
			'local_id':         ticket_number,
			'title':            ticket_subject, # printable as a document title
			'excerpt':          ticket_excerpt,
			'subject':          ticket_subject,
			'status':           ticket_status,
			'queue':            ticket_queue,
			'priority':         ticket_priority,
			'realname':         realnames,
			'email':            emails,
			'last_updated':     ticket_lastupdated,
			'customer_visible': customer_visible,
			}

		# Only set category if it's meaningful
		if ticket_category:
			ticketblob['category'] = ticket_category

		# Only set public_blob if we've got it
		if public_blob:
			ticketblob['public_blob'] = public_blob

		# Only set last_contact if it has meaning
		if contact_timestamps:
			ticketblob['last_contact'] = max(contact_timestamps).astimezone(tzutc())

		# Only set customer details if we have that metadata
		if customer_id:
			ticketblob['customer_id'] = customer_id

		if customer_name:
			ticketblob['customer_name'] = customer_name

		if customer_url:
			ticketblob['customer_url'] = customer_url

		maybe_customer_details = ' '.join(  [ x for x in (customer_name,customer_id) if x is not None ]  )
		if maybe_customer_details:
			ticketblob['customer'] = maybe_customer_details

		yield ticketblob
