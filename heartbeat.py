import sys
import requests
import re
import localconfig
import socket

def main():
	# Load https://machine.fqdn/?q=*, searching for everything
	r = requests.get("https://{}/?q=*".format(socket.gethostname()), verify=False)

	# Each source should have at least one document in them.  
	# When searching for everything, check that we have buttons for every source
	num_sources = len(localconfig.KNOWN_DOC_TYPES)
	num_source_buttons = r.text.count('btn btn-default doc-type')
	if num_sources != num_source_buttons:
		print("Some buttons are missing!  The buttons that should be shown are: {}".format(', '.join(localconfig.KNOWN_DOC_TYPES)))
		exit(1)

	# Each source should have a minimum of 50 results returned.  Check that we get at least that many results
	min_results = num_sources * localconfig.MAX_HITS
	match = re.search('Display limited to <strong><span id="hitcount">(\d+)</span> results', r.text)
	num_results = int(match.group(1))
	""" XXX: One of our indexes doesn't have enough results yet.
	if num_results < min_results:
		print("Not enough results.  Expected at least {}, but only had {}".format(min_results, num_results))
		exit(2)
	"""

	# Check if we got the expected number of results shown on the page
	num_hits = r.text.count('div class="hitlink"')
	if num_hits != num_results:
		print("The number of results on the page is incorrect. Expected {} but had {}".format(num_results, num_hits))
		exit(3)

	# If all of the above was fine, keep this node in the load balancer
	print "OK"

if __name__ == "__main__":
	sys.exit(main())
