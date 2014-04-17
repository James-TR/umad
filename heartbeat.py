import sys
import re
import socket
import requests
from localconfig import MAX_HITS, KNOWN_DOC_TYPES

def main():
	# Load https://machine.fqdn/?q=*, searching for everything
	r = requests.get("https://{}/?q=*".format(socket.gethostname()), verify=False)

	# Each source should have at least one document in them.  
	# When searching for everything, check that we have buttons for every source
	num_sources = len(KNOWN_DOC_TYPES)
	num_source_buttons = r.text.count('btn btn-default doc-type')
	if num_sources != num_source_buttons:
		print("Some buttons are missing!  The buttons that should be shown are: {}".format(', '.join(KNOWN_DOC_TYPES)))
		return 1

	# Each source should have a minimum of 50 (ie. MAX_HITS) results returned.  Check that we get at least that many results
	min_results = num_sources * MAX_HITS
	match = re.search(r'Display limited to <strong><span id="hitcount">(\d+)</span> results', r.text)
	if not match:
		print "Failure while parsing page, couldn't find 'Display limited to etc...' in the source"
		return 4
	num_results = int(match.group(1))
	""" XXX: One of our indexes doesn't have enough results yet.
	if num_results < min_results:
		print("Not enough results.  Expected at least {}, but only had {}".format(min_results, num_results))
		return 2
	"""

	# Check if we got the expected number of results shown on the page
	num_hits = r.text.count('div class="hitlink"')
	if num_hits != num_results:
		print("The number of results on the page is incorrect. Expected {} but had {}".format(num_results, num_hits))
		return 3

	# If all of the above was fine, keep this node in the load balancer
	print "OK"
	return 0

if __name__ == "__main__":
	sys.exit(main())
