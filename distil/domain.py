import requests
from opensrs import OpenSRS
import json
import datetime


from distiller import Distiller
from distil.opensrs import OpenSRSHTTPException

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
			server = 'https://domains.anchor.com.au:55443'
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

	def blobify(self):
		url = self.url
		name = url.split('/')[-1]
		try:
			domain = self.get_info(name)
		except OpenSRSHTTPException as e:
			self.enqueue_deletion()
			return

		# Put together our response. We have:
		# - name                  <str>
		# - url                   <str>
		# - customer_id           <int>
		# - customer_name         <unicode>
		# - created               <datetime>
		# - updated               <datetime>
		# - expiry                <datetime>
		# - owner_contact         <dict> of <str>
		# - au_registrant_info    <dict> of <str>

		if 'registry_createdate' in domain:
			created = self.parse_date_string(domain['registry_createdate'])
		else:
			created = None

		if 'registry_updatedate' in domain:
			updated = self.parse_date_string(domain['registry_updatedate'])
		else:
			updated = None

		if 'registry_expiredate' in domain:
			expiry   = self.parse_date_string(domain['registry_expiredate'])
		else:
			expiry = self.parse_date_string(domain['expiredate'])

		tld_data = domain['tld_data']

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
		blob = " ".join([ name,
		u"{first_name} {last_name} ({org_name}) {email}".format(**owner_contact).encode('utf8'),
		"Expiry:", expiry.strftime('%Y-%m-%d'),
		"Nameservers:", ", ".join(nameservers)
		])

		# Customer details default to none, until we can set them to useful values
		customer_id = None
		customer_name = None

		if domain['affiliate_id'] != 'None':
			customer_id = int(domain['affiliate_id'])

			# Grab the customer name
			try: api_credentials = self.auth['anchor_api']
			except: raise RuntimeError("You must provide Anchor API credentials, please set API_AUTH_USER and API_AUTH_PASS")

			customer_url = 'https://customer.api.anchor.com.au/customers/{}'.format(customer_id)
			customer_response = requests.get(customer_url, auth=api_credentials, verify=True, headers=self.accept_json)
			try:
				customer_response.raise_for_status()
				customer = customer_response.json()
				customer_name = customer['description']
				blob += (' {0} {1} ').format(customer_name, customer_id)
			except:
				print ("Indexing {0}: couldn't get customer {1} from API, HTTP error {2}, probably not allowed to view customer".format(name, customer_id, customer_response.status_code))

		domainblob = {
			'name':             name,
			'customer_name':    customer_name,
			'blob':             blob,
			'url':              url,
			'local_id':         name,
			'customer_id':      customer_id,
			'expiry':           expiry,
			'owner_contact':    owner_contact,
			'nameservers':      nameservers,
			}

		# Not always present
		if created is not None: domainblob['created'] = created
		if updated is not None: domainblob['updated'] = updated

		if tld_data:
			if 'au_registrant_info' in tld_data:
				au_data = tld_data['au_registrant_info']
				au_info = {}

				if 'registrant_name' in au_data:
					au_info['name'] = au_data['registrant_name']
				else:
					au_info['name'] = au_data.get('eligibility_name')

				if 'registrant_id' in au_data:
					au_info['id']      = au_data['registrant_id']
				else:
					au_info['id'] = au_data.get('eligibility_id')

				if 'registrant_id_type' in au_data:
					au_info['id_type']      = au_data['registrant_id_type']
				else:
					au_info['id_type'] = au_data.get('eligibility_id_type')

				au_info['type']    = au_data.get('eligibility_type')
				domainblob['au_registrant'] = "{name} ({id_type}: {id} - {type})".format(**au_info).encode('utf8')
			else:
				for key in tld_data:
					domainblob[key] = tld_data[key]

		# Only add the extra contact fields into the domainblob if they
		# actually exist. "Empty" fields will have u'None' in them.
		if tech_contact:    domainblob['tech_contact']    = u"{first_name} {last_name} ({org_name}) {email}".format(**tech_contact).encode('utf8')
		if admin_contact:   domainblob['admin_contact']   = u"{first_name} {last_name} ({org_name}) {email}".format(**admin_contact).encode('utf8')
		if billing_contact: domainblob['billing_contact'] = u"{first_name} {last_name} ({org_name}) {email}".format(**billing_contact).encode('utf8')

		yield domainblob
