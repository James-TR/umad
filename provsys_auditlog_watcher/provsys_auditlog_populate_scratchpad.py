import sys
import os
from provsys_auditlog_lib import AuditlogScratchpad

def main(argv=None):
	if argv is None:
		argv = sys.argv[1:]

	# Allow lazy interactive usage
	if type(argv) != type([]):
		argv = [argv]

	redis_server_host = os.environ.get('UMAD_REDIS_HOST', 'localhost')
	redis_server_port = os.environ.get('UMAD_REDIS_PORT', 6379)

	scratchpad = AuditlogScratchpad(host=redis_server_host, port=redis_server_port)

	# SET mode
	if argv:
		new_position = scratchpad.set(*argv)
		print "All done, position has been recorded as {0}".format(new_position)

	# GET mode
	else:
		position = scratchpad.get()
		print "Recorded auditlog position is {0}".format(position)


	return 0

if __name__ == "__main__":
	sys.exit(main())
