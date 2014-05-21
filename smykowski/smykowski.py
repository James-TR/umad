import sys
import os
import time

import redis
import json


# Smykowski takes the specifications from the customers and brings them down to
# the software engineers.


# XXX: maybe these should be to stdout instead of stderr, I dunno
def debug(msg, force_debug=False):
	if DEBUG or force_debug:
		sys.stderr.write(PID_PREFIX + str(msg) + '\n')
		sys.stderr.flush()

def mention(msg):
	sys.stderr.write(PID_PREFIX + str(msg) + '\n')
	sys.stderr.flush()


DEBUG = os.environ.get('UMAD_SMYKOWSKI_DEBUG')
PID_PREFIX = '[pid {0}] '.format(os.getpid())


def enqueue(dst_redis, queue_name, url):
	try:
		debug(u"About to insert {0} into {1}".format(url, queue_name))
		pipeline = dst_redis.pipeline()
		pipeline.zadd(queue_name, time.time(), url)
		pipeline.lpush('barber', 'dummy_value')
		pipeline.execute() # will return something like:   [ {0|1}, num_dummies ]
		debug(u"Successful insertion of {0} into {1}".format(url, queue_name))
		mention(u"Successful insertion of {0} into {1}".format(url, queue_name))
	except Exception as e:
		mention("Something went boom while inserting {0}: {1}".format(url, e))
		raise


def main(argv=None):
	debug("Debug logging is enabled")

	redis_server_host    = os.environ.get('UMAD_REDIS_HOST', 'localhost')
	redis_server_port    = os.environ.get('UMAD_REDIS_PORT', 6379)
	redis_server_db_src  = os.environ.get('UMAD_REDIS_DB', 8)
	redis_server_db_dst  = os.environ.get('UMAD_REDIS_DB', 0)
	redis_server_src_key = os.environ.get('UMAD_REDIS_AWESANT_KEY', 'umad_event:queue')
	src_redis = redis.StrictRedis(host=redis_server_host, port=redis_server_port, db=redis_server_db_src)
	dst_redis = redis.StrictRedis(host=redis_server_host, port=redis_server_port, db=redis_server_db_dst)

	# Get URLs out of Redis, look for interesting ones, put them into the
	# indexing listener's queue. Make this very stupid, daemontools will
	# restart us if the world explodes.
	while True:
		log_entry_json = src_redis.blpop(redis_server_src_key)[1] # Disregard the popped keyname
		log_entry_dict = json.loads(log_entry_json)
		log_message    = log_entry_dict[u'@message']

		(request_method, request_url) = log_message.split()

		#debug("Got a request with method {0} and URL of {1}".format(request_method, request_url))

		# Skip junk
		if any([
				'/moin_static' in request_url, # there may be a numeric suffix on this before the next slash
				'/gollum_static/' in request_url,
				request_url.endswith('.js'),
				request_url.endswith('.css'),
				request_url.endswith( ('.jpg','.png','.gif') ),
				request_url.endswith( ('.woff','.ttf','.otf') ),
			]):
			continue

		# Throw it in the queue
		if request_method in ('POST', 'GET'):
			enqueue(dst_redis, 'umad_indexing_queue', request_url)

		if request_method in ('DELETE',):
			enqueue(dst_redis, 'umad_deletion_queue', request_url)

	return 0


if __name__ == "__main__":
	sys.exit(main())
