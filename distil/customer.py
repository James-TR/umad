import sys
import os
import re
from urllib import urlencode
from operator import itemgetter
from itertools import chain
import json
# dateutil is a useful helper library, you may need to install the
# `python-dateutil` package especially
from dateutil.parser import *
from dateutil.tz import *
# Fuck urllib2, that's effort. You may need to `pip install requests`.
# http://docs.python-requests.org/en/latest/index.html
import requests

class MissingAuth(Exception): pass


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


# XXX: This'd be nicer if it yielded instead of returning, I think that'll be acceptable in the places it's consumed
def get_contacts(contact_list):
	# Prepare auth
	auth_user = os.environ.get('API_AUTH_USER')
	auth_pass = os.environ.get('API_AUTH_PASS')
	if not auth_user or not auth_pass:
		raise MissingAuth("You must provide Anchor API credentials, please set API_AUTH_USER and API_AUTH_PASS")

	# Prep URL and headers for requests
	headers = {}
	headers['Accept'] = 'application/json'

	contacts = []
	for contact_url in contact_list:
		contact_response = requests.get(contact_url, auth=(auth_user,auth_pass), verify=True, headers=headers)
		try:
			contact_response.raise_for_status()
		except:
			raise FailedToRetrieveCustomer("Couldn't get customer from API, HTTP error %s, probably not allowed to view customer" % contact_response.status_code)

		contact = clean_contact(contact_response.json())
		contacts.append(contact)

	return contacts




def blobify(distiller):
	url = distiller.url
	# Note to self: yield'ing is cool. Either yield, return None, or raise
	# an exception. The latter is some other poor schmuck's problem.

	# Prepare auth
	auth_user = os.environ.get('API_AUTH_USER')
	auth_pass = os.environ.get('API_AUTH_PASS')
	if not auth_user or not auth_pass:
		raise MissingAuth("You must provide Anchor API credentials, please set API_AUTH_USER and API_AUTH_PASS")

	# Prep URL and headers for requests
	headers = {}
	headers['Accept'] = 'application/json'

	customer_response = requests.get(url, auth=(auth_user,auth_pass), verify=True, headers=headers)
	try:
		customer_response.raise_for_status()
	except:
		raise FailedToRetrieveCustomer("Couldn't get customer from API, HTTP error %s, probably not allowed to view customer" % customer_response.status_code)

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
	primary_contacts     = get_contacts(customer['primary_contact_url_list'])
	billing_contacts     = get_contacts(customer['billing_contact_url_list'])
	alternative_contacts = get_contacts(customer['alternative_contact_url_list'])

	# Put together our response. We have:
	# - customer_id           <int>
	# - customer_name         <unicode>
	# - customer_url          <unicode>
	# - primary_contacts      <list> of <contact-dict>
	# - billing_contacts      <list> of <contact-dict>
	# - alternative_contacts  <list> of <contact-dict>

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

	if primary_contacts:
		primary_contacts_blob = u"Primary contacts: {0}".format(', '.join([ blobify_contact(x) for x in primary_contacts ])).encode('utf8')
		customerblob['primary_contacts'] = primary_contacts_blob
		customerblob['blob'] += '\n' + primary_contacts_blob
	if billing_contacts:
		billing_contacts_blob = u"Billing contacts: {0}".format(', '.join([ blobify_contact(x) for x in billing_contacts ])).encode('utf8')
		customerblob['billing_contacts'] = billing_contacts_blob
		customerblob['blob'] += '\n' + billing_contacts_blob
	if alternative_contacts:
		technical_contacts_blob = u"Technical contacts: {0}".format(', '.join([ blobify_contact(x) for x in alternative_contacts ])).encode('utf8')
		customerblob['technical_contacts'] = technical_contacts_blob
		customerblob['blob'] += '\n' + technical_contacts_blob

	yield customerblob
