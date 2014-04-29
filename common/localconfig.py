from distil import *

distillers = [
	MoinMapDistiller ,
	RtTicketDistiller ,
	GollumDistiller ,
	ProvsysResourceDistiller ,
	ProvsysServersDistiller ,
	ProvsysVlansDistiller ,
	CustomerDistiller ,
	DomainDistiller ,
	# This is a demo Distiller
	#NewtypeDistiller ,
	]

# How many hits do you want to display of each doctype? ES doesn't easily offer
# pagination, and besides, results past the first page probably suck anyway.
MAX_HITS = 50
