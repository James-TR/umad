from provisioningclient import *

from provsysresource import ProvsysResourceDistiller

from distiller import Distiller

class ProvsysVlansDistiller(Distiller):
	doc_type = 'provsys'

	@classmethod
	def will_handle(klass, url):
		return url.startswith('provsysvlans://')

	def blobify(self):
		server.requester    = 'umad_tma'
		server.uri          = 'https://resources.engineroom.anchor.net.au/'
		server.user         = "script"
		server.password     = "script"
		server.apikey       = "Sysadmin convenience script"
		server.ca_cert_file = None

		results = Resource.search(supertype="VLAN Definition", status="Any")
		if not results:
			return

		for vlan in results:
			self.debug("Document'ing VLAN {0}".format(vlan.name))
			yield ProvsysResourceDistiller.vlan_to_document(vlan)
