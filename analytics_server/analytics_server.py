# The analytics server is embarrassingly simple, it receives events on
# WebSocket and writes them to stdout. This imposes a minimum of decisions upon
# you - it's up to you to choose and implement your logging to a file.
#
# Here at Anchor we prefer and recommend the use of Daemontools to manage
# everything. This practically gives you logging and rotation for free.
# Similarly, you could use systemd to manage the daemon as it gives you the
# same nice things. If you're in a particularly ghetto mood you can redirect
# stdout to a file yourself.

from SimpleWebSocketServer.SimpleWebSocketServer import *
import time
import sys
import os

# Force line buffering for running under daemontools
#
linebuffered_stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
def log(message):
	linebuffered_stdout.write(message)
	linebuffered_stdout.write("\n")
	linebuffered_stdout.flush()

class SimpleMoo(WebSocket):
	def handleMessage(self):
		log(self.data)
	def handleConnected(self):
		log('{"event":"SERVER_clientConnect","timestamp":%.3f}' % time.time() )

if __name__ == '__main__':
	certfile = os.environ.get('UMAD_ANALYTICS_CERT', 'localhost.localdomain.pem')
	keyfile  = os.environ.get('UMAD_ANALYTICS_KEY',  'localhost.localdomain.pem')
	print "Using {0} for certificate".format(certfile)
	print "Using {0} for key".format(keyfile)

	SimpleSSLWebSocketServer('',9876, SimpleMoo,
		certfile=certfile,
		keyfile=keyfile).serveforever()
