from provisioningclient import *

from provsysresource import ProvsysResourceDistiller

from distiller import Distiller

class ProvsysServersDistiller(Distiller):
	def blobify(self):
		server.requester    = 'umad_tma'
		server.uri          = 'https://resources.engineroom.anchor.net.au/'
		server.user         = "script"
		server.password     = "script"
		server.apikey       = "Sysadmin convenience script"
		server.ca_cert_file = None

		results = Resource.search(supertype="Generic OS install")
		if not results:
			return

		for os in results:
			self.debug("Document'ing OS {0}".format(os.name))
			yield ProvsysResourceDistiller.os_to_document(os)
