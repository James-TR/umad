from distil.domain import DomainDistiller
import sys
import requests

def main():
	distiller = DomainDistiller(None)
	domain_list = distiller.get_domain_list()
	for domain in domain_list:
		r = requests.get("https://umad-indexer-stg.anchor.net.au", params={'url':'https://domains.anchor.com.au/{0}'.format(domain)}, verify=False)
		print r.text

if __name__ == "__main__":
	sys.exit(main())
