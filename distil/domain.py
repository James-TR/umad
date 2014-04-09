from dateutil.parser import *
from dateutil.tz import *
import requests
from opensrs import OpenSRS
import json
import datetime


from distiller import Distiller

def pretty_print(text):
	print json.dumps(text, sort_keys=True, indent=4, separators=(',', ': '))


class DomainDistiller(Distiller):
	doc_type = 'domain'

	@classmethod
	def will_handle(klass, url):
		return url.startswith('https://domains.anchor.com.au/')

	def pretty_print(self, text):
		print json.dumps(text, sort_keys=True, indent=4, separators=(',', ': '))

	@classmethod
	def query(klass, action, object, attributes):
		"""Everything sent to OpenSRS has the following components:
	        action - the name of the action (ie. sw_register, name_suggest, etc)
	        object - the object type to operate on (ie. domain, trust_service)
	        attrs - a data struct to construct the attributes from (see example)
	        extra_items - any extra top level items (ie. registrant_ip)
		"""

		if attributes.has_key('domain') and attributes['domain'].split('.')[-1] == "au":
			server = 'https://anchor.opensrs.net:55443'
			username = 'anchorhrs'
			private_key = '458c081f0dc4188d0b0098b1820cf14429bb6f4b6a3a58e86af689e54729dd5257f60c047960e45304e733961a2a44e19e43a1f098471f87'
			# The OpenSRS library doesn't support arbitary server URLs, like our OpenHRS instance, so we hardcode it here.  
			# There's no test server for OpenHRS, either.
			opensrs = OpenSRS(username, private_key, server)	
		else:
			username = 'anchor'
			private_key = '1c2de3c188264817832a2d6d71a207dbe48e2cc969aafea9058da06e2e4caebaead24d20533833e1303d776b29df6fcac40a4108d1dc2fa6'
			opensrs = OpenSRS(username, private_key, test=False)

		if opensrs:
			post_data = opensrs.post(action, object, attributes)
			return post_data
	
	@classmethod
	def get_domain_list(klass):
		"""Gets a list of all domains listed in OpenSRS. Does not differenciate between active/expired"""
		now = datetime.datetime.now()
		exp_from = "%04d-%02d-%02d" % (now.year-1, now.month, now.day)
		exp_to = "%04d-%02d-%02d" % (now.year+15, now.month, now.day)
		domain_list = []
		for extension in ['.com', '.au']:
                    result = klass.query('get_domains_by_expiredate', 'domain', { 'exp_from' : exp_from, 'exp_to' : exp_to, 'limit' : 100000, 'page' : 1, 'domain': extension})
		    [ domain_list.append(x['name']) for x in result['attributes']['exp_domains'] ]
		return domain_list

	def get_info(self, domain):
		"""	From http://opensrs.com/docs/apidomains/get_domain_type_all_info_xml.htm """
		info = self.query('get', 'domain', { 'domain': domain, 'type': 'all_info',})
		return info['attributes']

	def blobify(self):
		url = self.url
		name = url.split('/')[-1]
		domain = self.get_info(name)

		# FIXME
		# Put together our response. We have:
		# - customer_id           <int>
		# - customer_name         <unicode>
		# - customer_url          <unicode>
		# - primary_contacts      <list> of <contact-dict>
		# - billing_contacts      <list> of <contact-dict>
		# - alternative_contacts  <list> of <contact-dict>

		customer_id = domain['affiliate_id']
		created     = domain['registry_createdate']
		updated     = domain['registry_updatedate']
		expiry      = domain['registry_expiredate']
		tld_data    = domain['tld_data']
		owner_contact = domain['contact_set']['owner']
		tech_contact = domain['contact_set']['tech']
		if name.split('.')[-1] != "au":
			admin_contact = domain['contact_set']['admin']
			billing_contact = domain['contact_set']['billing']
		nameservers = [ x['name'] for x in domain['nameserver_list'] ]

		# FIXME: Would be nice to get the customer name here
		blob = " ".join([ name, 
			str(customer_id),
			"Expires:", expiry.encode('utf8'),
			"Owner: {} {} ({}) {}".format(owner_contact['first_name'].encode('utf8'), owner_contact['last_name'].encode('utf8'), owner_contact['org_name'].encode('utf8'), owner_contact['email'].encode('utf8')),
			"Nameservers:", ", ".join(nameservers)
			])

		# XXX: This should possibly be improved by collapsing all contacts into a
		# single list, with roles tagged on.
		domainblob = {
			'name':             name,
			'blob':             blob,
			'url':              url,
			'local_id':         customer_id,
			'customer_id':      customer_id,
			'created':          created,
			'updated':          updated,
			'expiry':           expiry,
			'owner_contact':    owner_contact,
			'tech_contact':     tech_contact,
			'nameservers':      nameservers,
			}

		if tld_data != 'None':
			domainblob['tld_data'] = tld_data

		if name.split('.')[-1] != "au":
			domainblob['billing_contact'] = billing_contact
			domainblob['admin_contact']   = admin_contact

		yield domainblob
