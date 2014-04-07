# This is a quick and dirty test script for the provsys poller. It makes a
# trivial change to a fixed provsys resource, which should be picked up by the
# poller when it next runs.

import datetime

from provisioningclient import *

server.requester    = 'umad'
server.uri          = 'https://resources.engineroom.anchor.net.au/'
server.user         = "script"
server.password     = "script"
server.apikey       = "umad_distiller test script"
server.ca_cert_file = None

misaka = Resource.get('8737')
current_time = datetime.datetime.now()
misaka.details['notes'] = "Test comment {0}".format(current_time)
misaka.save()
