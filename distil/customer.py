import re
from dateutil.parser import *
from dateutil.tz import *
import requests

from distiller import Distiller

CUSTOMER_TENANCIES_URL = 'https://customer.api.anchor.com.au/customer-tenancies'


def blobify_contact(c):
	# A contact-dict is:
	# - contact_id <type 'int'>
	# - contact_name <type 'unicode'>
	# - contact_email <type 'unicode'>
	# - contact_phone_numbers <type 'dict'>
	#     - <type 'unicode'>  -->  <type 'unicode'>
	contact_details = []
	if c['contact_email']:
		contact_details.append(c['contact_email'])
	contact_details += [ x for x in c['contact_phone_numbers'].values()]

	if contact_details:
		return u"{1} ({0})".format(', '.join(contact_details), c['contact_name'])

	return c['contact_name']


def clean_contact(contact_dict):
	# - city <type 'unicode'>
	# - _type <type 'unicode'>
	# - last_name <type 'unicode'>
	# - address1 <type 'unicode'>
	# - address2 <type 'unicode'>
	# - primary_customers_url <type 'unicode'>
	# - alternative_customers_url <type 'unicode'>
	# - first_name <type 'unicode'>
	# - billing_customers_url <type 'unicode'>
	# - state <type 'unicode'>
	# - postcode <type 'unicode'>
	# - _url <type 'unicode'>
	# - country <type 'unicode'>
	# - phone_numbers <type 'dict'>
	# - _id <type 'int'>
	# - email <type 'unicode'>

	# XXX: find some pathologically broken customers to test this against,
	# eg. None for some name fields, etc.
	contact = {}
	contact['contact_id']    = contact_dict['_id']
	contact['contact_name']  = u"{first_name} {last_name}".format(**contact_dict)
	contact['contact_email'] = contact_dict['email']

	# Phone numbers seem to be retarded, it's a dict of unicode=>{unicode|dict}
	# Populated values have a unicode value, while empty entries have an (empty) dict
	contact['contact_phone_numbers'] = dict((k,v.replace(' ', '')) for k,v in contact_dict['phone_numbers'].iteritems() if type(v) is not dict)

	# - contact_id <type 'int'>
	# - contact_name <type 'unicode'>
	# - contact_email <type 'unicode'>
	# - contact_phone_numbers <type 'dict'>
	#     - <type 'unicode'>  -->  <type 'unicode'>
	return contact



class CustomerDistiller(Distiller):
	doc_type = 'customer'

	@classmethod
	def will_handle(klass, url):
		return url.startswith('https://customer.api.anchor.com.au/customers/')


	def get_contacts(self, contact_list):
		# Prepare auth
		try: api_credentials = self.auth['anchor_api']
		except: raise RuntimeError("You must provide Anchor API credentials, please set API_AUTH_USER and API_AUTH_PASS")

		for contact_url in contact_list:
			contact_response = requests.get(contact_url, auth=api_credentials, verify=True, headers=self.accept_json)

			try: contact_response.raise_for_status()
			except: raise RuntimeError("Couldn't get contact from customer API, HTTP error {0}, probably not allowed to view customer".format(contact_response.status_code))

			contact = clean_contact(contact_response.json())
			yield contact


	def get_tenancies(self, customer_id):
		# Prepare auth
		try: api_credentials = self.auth['anchor_api']
		except: raise RuntimeError("You must provide Anchor API credentials, please set API_AUTH_USER and API_AUTH_PASS")

		tenancies_response = requests.get(CUSTOMER_TENANCIES_URL, params={'customer_id':customer_id}, auth=api_credentials, verify=True, headers=self.accept_json)

		try: tenancies_response.raise_for_status()
		except: raise RuntimeError("Couldn't search tenancies in customer API, HTTP error {0}, probably not allowed to view customer".format(tenancies_response.status_code))

		tenancies_list = tenancies_response.json()
		return [ tenancy['tenancy_id'] for tenancy in tenancies_list ]


	def blobify(self):
		url = self.url

		# Prepare auth
		try: api_credentials = self.auth['anchor_api']
		except: raise RuntimeError("You must provide Anchor API credentials, please set API_AUTH_USER and API_AUTH_PASS")

		# Validate the URL format and extract the intended customer ID
		customer_url_match = re.match(r'https://customer\.api\.anchor\.com\.au/customers/(\d+)$', url)
		if customer_url_match is None:
			raise ValueError("This URL doesn't match our idea of a customer URL: {0}".format(url))
		supplied_customer_id = int(customer_url_match.group(1))

		customer_response = requests.get(url, auth=api_credentials, verify=True, headers=self.accept_json)
		try: customer_response.raise_for_status()
		except: raise RuntimeError("Couldn't get customer from API, HTTP error {0}, probably not allowed to view customer".format(customer_response.status_code))

		customer = customer_response.json() # FIXME: add error-checking
		# - _id                          <type 'int'>
		# - _type                        <type 'unicode'>
		# - _url                         <type 'unicode'>
		# - description                  <type 'unicode'>
		# - invoices_url                 <type 'unicode'>
		# - partner_customer_url         <type 'unicode'>
		# - alternative_contact_url_list <type 'list'> of <type 'unicode'> URLs
		# - billing_contact_url_list     <type 'list'> of <type 'unicode'> URLs
		# - primary_contact_url_list     <type 'list'> of <type 'unicode'> URLs

		customer_id          = customer['_id']
		customer_name        = customer['description']
		customer_url         = customer['_url'] # probably not necessary, can the URL ever change?
		functional_url       = 'https://system.netsuite.com/app/common/search/ubersearchresults.nl?quicksearch=T&searchtype=Uber&frame=be&Uber_NAMEtype=KEYWORDSTARTSWITH&Uber_NAME=cust:{0}'.format(customer_id)
		primary_contacts     = self.get_contacts(customer['primary_contact_url_list'])
		billing_contacts     = self.get_contacts(customer['billing_contact_url_list'])
		alternative_contacts = self.get_contacts(customer['alternative_contact_url_list'])
		tenancies            = self.get_tenancies(customer_id)

		# Handle merged customers by calling our enqueue_deletion method.
		# supplied_customer_id is what we were given in the URL.
		# customer_id is       is what the customer API gave us, which may be different.
		#
		# Merged customers will have a different customer_id after the API redirects us.
		if customer_id != supplied_customer_id:
			self.enqueue_deletion()
			print "Customer merge detected, {0} into {1}, enqueued for deletion from index: {2}".format(supplied_customer_id, customer_id, self.url)

		# Put together our response. We have:
		# - customer_id           <int>
		# - customer_name         <unicode>
		# - customer_url          <unicode>
		# - primary_contacts      <list> of <contact-dict>
		# - billing_contacts      <list> of <contact-dict>
		# - alternative_contacts  <list> of <contact-dict>
		# - tenancies             <list> of <unicode>

		blob = " ".join([
			str(customer_id),
			customer_name.encode('utf8'),
			])

		# XXX: This should possibly be improved by collapsing all contacts into a
		# single list, with roles tagged on.
		customerblob = {
			'url':              customer_url,
			'blob':             blob,
			'local_id':         customer_id,
			'title':            customer_name,
			'customer_id':      customer_id,
			'customer_name':    customer_name,
			'functional_url':   functional_url,
			#'last_updated':     customer_lastupdated,
			}

		primary_contacts_joined = ', '.join([ blobify_contact(x) for x in primary_contacts ])
		if primary_contacts_joined:
			primary_contacts_blob = u"Primary contacts: {0}".format(primary_contacts_joined).encode('utf8')
			customerblob['primary_contacts'] = primary_contacts_blob
			customerblob['blob'] += '\n' + primary_contacts_blob
		billing_contacts_joined = ', '.join([ blobify_contact(x) for x in billing_contacts ])
		if billing_contacts_joined:
			billing_contacts_blob = u"Billing contacts: {0}".format(billing_contacts_joined).encode('utf8')
			customerblob['billing_contacts'] = billing_contacts_blob
			customerblob['blob'] += '\n' + billing_contacts_blob
		technical_contacts_joined = ', '.join([ blobify_contact(x) for x in alternative_contacts ])
		if technical_contacts_joined:
			technical_contacts_blob = u"Technical contacts: {0}".format(technical_contacts_joined).encode('utf8')
			customerblob['technical_contacts'] = technical_contacts_blob
			customerblob['blob'] += '\n' + technical_contacts_blob

		if tenancies:
			tenancies_joined = u', '.join(tenancies)
			tenancies_blob = "OpenStack tenancies: {0}".format(tenancies_joined).encode('utf8')
			customerblob['tenancies'] = tenancies
			customerblob['blob'] += '\n' + tenancies_blob

		yield customerblob
