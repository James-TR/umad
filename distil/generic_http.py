import requests
from lxml import html

# Plaintext-ify all the junk we get
import html2text

from distiller import Distiller

class GenericHttpDistiller(Distiller):

	def blobify(self):
		response = requests.get(self.url, verify=True)

		content = html2text.html2text(response.text)
		doc_tree = html.fromstring(response.text)

		title_list = doc_tree.xpath('//title/text()')
		if title_list:
			title = title_list[0]
		else:
			title = self.url

		yield { 'url':self.url, 'blob':content, 'title':title }
