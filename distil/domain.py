from dateutil.parser import *
from dateutil.tz import *
import requests
from opensrs import OpenSRS
import json
import datetime


from distiller import Distiller

class DomainDistiller(Distiller):
	doc_type = 'domain'

	@classmethod
	def will_handle(klass, url):
		return url.startswith('https://domains.anchor.com.au/')

	def query(self, action, object, attributes):
		"""Everything sent to OpenSRS has the following components:
			action - the name of the action (ie. sw_register, name_suggest, etc)
			object - the object type to operate on (ie. domain, trust_service)
			attrs - a data struct to construct the attributes from (see example)
			extra_items - any extra top level items (ie. registrant_ip)
		"""

		if attributes.get('domain', '').endswith(".au"):
			server = 'https://anchor.opensrs.net:55443'
			try:
				username, private_key = self.auth['openhrs']
			except:
				raise RuntimeError("You must provide OpenHRS credentials, please set OPENHRS_AUTH_USER and OPENHRS_AUTH_KEY")
			# The OpenSRS library doesn't support arbitary server URLs, like our OpenHRS instance, so we hardcode it here.
			# There's no test server for OpenHRS, either.
			opensrs = OpenSRS(username, private_key, server)
		else:
			try:
				username, private_key = self.auth['opensrs']
			except:
				raise RuntimeError("You must provide OpenSRS credentials, please set OPENSRS_AUTH_USER and OPENSRS_AUTH_KEY")
			opensrs = OpenSRS(username, private_key, test=False)

		if opensrs:
			post_data = opensrs.post(action, object, attributes)
			return post_data

	def get_domain_list(self):
		"""Gets a list of all domains listed in OpenSRS. Does not differenciate between active/expired"""
		now = datetime.datetime.now()
		exp_from = "%04d-%02d-%02d" % (now.year-1, now.month, now.day)
		exp_to = "%04d-%02d-%02d" % (now.year+15, now.month, now.day)
		domain_list = []
		for extension in ['.com', '.au']:
			result = self.query('get_domains_by_expiredate', 'domain', { 'exp_from' : exp_from, 'exp_to' : exp_to, 'limit' : 100000, 'page' : 1, 'domain': extension})
			[ domain_list.append(x['name']) for x in result['attributes']['exp_domains'] ]
		return domain_list

	def get_info(self, domain):
		""" From http://opensrs.com/docs/apidomains/get_domain_type_all_info_xml.htm """
		info = self.query('get', 'domain', { 'domain': domain, 'type': 'all_info',})
		return info['attributes']

	def parse_date_string(self, date_string):
		datetime = parse(date_string)
		if datetime.tzinfo is None:
			datetime = datetime.replace(tzinfo=tzutc())
		return datetime.astimezone(tzlocal()).strftime('%Y-%m-%d')

	def blobify(self):
		url = self.url
		name = url.split('/')[-1]
		domain = self.get_info(name)

		# Put together our response. We have:
		# - name                  <str>
		# - url                   <str>
		# - customer_id           <int>
		# - customer_name         <unicode>
		# - created               <str>
		# - updated               <str>
		# - expiry                <str>
		# - owner_contact         <dict> of <str>
		# - au_registrant_info    <dict> of <str>

		created     = self.parse_date_string(domain['registry_createdate'])
		updated     = self.parse_date_string(domain['registry_updatedate'])
		expiry      = self.parse_date_string(domain['registry_expiredate'])
		tld_data    = domain['tld_data']

		# OpenSRS is a piece of shit
		if tld_data == 'None': tld_data = None

		# All domains have an owner, but the other fields vary by TLD.
		owner_contact = domain['contact_set']['owner']
		# If not present they get None, which'll be dealt with later.
		tech_contact    = domain['contact_set'].get('tech')
		admin_contact   = domain['contact_set'].get('admin')
		billing_contact = domain['contact_set'].get('billing')

		nameservers = [ x['name'] for x in domain['nameserver_list'] ]

		# Create the blob
		blob = name

		if domain['affiliate_id'] != 'None':
			customer_id = int(domain['affiliate_id'])

			# Grab the customer name
			try: api_credentials = self.auth['anchor_api']
			except: raise RuntimeError("You must provide Anchor API credentials, please set API_AUTH_USER and API_AUTH_PASS")

			customer_url = 'https://customer.api.anchor.com.au/customers/{}'.format(customer_id)
			customer_response = requests.get(customer_url, auth=api_credentials, verify=True, headers=self.accept_json)
			# XXX: Do we really want to die here?
			try: customer_response.raise_for_status()
			except: raise RuntimeError("Couldn't get customer {0} from API, HTTP error {1}, probably not allowed to view customer".format(customer_id, customer_response.status_code))

			customer = customer_response.json()
			customer_name = customer['description']
			blob += (' {} {} ').format(customer_name, str(customer_id))
		else:
			customer_id = None
			customer_name = None

		blob += " ".join([ 
			u"{first_name} {last_name} ({org_name}) {email}".format(**owner_contact).encode('utf8'),
			"Expiry:", expiry.encode('utf8'),
			"Nameservers:", ", ".join(nameservers)
			])

		domainblob = {
			'name':             name,
			'customer_name':    customer_name,
			'blob':             blob,
			'url':              url,
			'local_id':         name,
			'customer_id':      customer_id,
			'created':          created,
			'updated':          updated,
			'expiry':           expiry,
			'owner_contact':    owner_contact,
			'nameservers':      nameservers,
			}

		if tld_data:
			for key in tld_data:
				domainblob[key] = tld_data[key]

		# Only add the extra contact fields into the domainblob if they actually exist
		if tech_contact:    domainblob['tech_contact']    = tech_contact
		if admin_contact:   domainblob['admin_contact']   = admin_contact
		if billing_contact: domainblob['billing_contact'] = billing_contact

		yield domainblob
