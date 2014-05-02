import sys
import os
import requests
from distil.domain import DomainDistiller

UMAD_INDEXER_URL = os.environ.get('UMAD_INDEXER_URL', 'https://umad-indexer.anchor.net.au/')

def main():
	distiller = DomainDistiller(None)
	domain_list = distiller.get_domain_list()
	for domain in domain_list:
		r = requests.get(UMAD_INDEXER_URL, params={'url':'https://domains.anchor.com.au/{0}'.format(domain)}, verify=False)
		print r.text

if __name__ == "__main__":
	sys.exit(main())
