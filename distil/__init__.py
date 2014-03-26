from moin_map        import MoinMapDistiller
from rt_ticket       import RtTicketDistiller
from gollum_docs     import GollumDistiller
from provsysresource import ProvsysResourceDistiller
from provsysservers  import ProvsysServersDistiller
from provsysvlans    import ProvsysVlansDistiller
from generic_http    import GenericHttpDistiller


def get_distiller(url):
	'''Return a distiller that's suitable for the URL provided'''

	# Dodgy hackery to patch up URLs that aren't in the format we expect
	if url.startswith('rt://'):
		url = url.replace('rt://', 'https://rt.engineroom.anchor.net.au/Ticket/Display.html?id=')


	if url.startswith('https://map.engineroom.anchor.net.au/'):
		return MoinMapDistiller(url)

	if url.startswith('https://rt.engineroom.anchor.net.au/'):
		return RtTicketDistiller(url)

	if url.startswith('https://docs.anchor.net.au/'):
		return GollumDistiller(url)

	if url.startswith('https://resources.engineroom.anchor.net.au/resources/'):
		return ProvsysResourceDistiller(url)

	if url.startswith('provsysservers://'):
		return ProvsysServersDistiller(url)

	if url.startswith('provsysvlans://'):
		return ProvsysVlansDistiller(url)

	if url.startswith( ('http://', 'https://') ):
		return GenericHttpDistiller(url)

	raise LookupError("We don't have a module that can handle that URL: {0}".format(url))
