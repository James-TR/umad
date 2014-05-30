import sys
import os
import time
import datetime

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
		mention(u"Successful insertion of {0} into {1}".format(url, queue_name))
	except Exception as e:
		mention("Something went boom while inserting {0}: {1}".format(url, e))
		raise


def main(argv=None):
	debug("Debug logging is enabled")

	redis_server_host    = os.environ.get('UMAD_REDIS_HOST', 'localhost')
	redis_server_port    = os.environ.get('UMAD_REDIS_PORT', 6379)
	redis_server_db_src  = os.environ.get('UMAD_REDIS_DB_SRC', 8)
	redis_server_db_dst  = os.environ.get('UMAD_REDIS_DB_DST', 0)
	redis_server_src_key = os.environ.get('UMAD_REDIS_AWESANT_KEY', 'umad_event:queue')
	src_redis = redis.StrictRedis(host=redis_server_host, port=int(redis_server_port), db=redis_server_db_src)
	dst_redis = redis.StrictRedis(host=redis_server_host, port=int(redis_server_port), db=redis_server_db_dst)

	# Get URLs out of Redis, look for interesting ones, put them into the
	# indexing listener's queue. Make this very stupid, daemontools will
	# restart us if the world explodes.
	while True:
		log_entry_json = src_redis.blpop(redis_server_src_key)[1] # Disregard the popped keyname
		log_entry_dict = json.loads(log_entry_json)
		log_message    = log_entry_dict[u'@message']

		(request_method, request_url) = log_message.split(None, 1)

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
		if request_url.startswith('https://docs.anchor.net.au/'):
			# Our gollum wikis are special (ie. annoying).  Gollum
			# POSTs to URLs that don't really exists, so we have to
			# derive the actual pagename ourself and call a fake
			# POST on that. -_- To ensure we can tell the fakes
			# from the real ones, we use INDEX as the method
			# instesd.
			if request_method in ('INDEX',):
				enqueue(dst_redis, 'umad_indexing_queue', request_url)

		else:
			if request_method in ('POST', 'PUT'):
				enqueue(dst_redis, 'umad_indexing_queue', request_url)

			if request_method in ('DELETE',):
				enqueue(dst_redis, 'umad_deletion_queue', request_url)

		# Make a note that we saw a heartbeat. We'd like to keep all
		# the hits we've seen in the last N minutes (eg. 5min), but
		# Redis doesn't export expiry of list elements, only the whole
		# key. Instead we use a sorted set to associate a timestamp
		# with each heartbeat ping, making it easy for us to grab only
		# recent pings for inspection, and delete old ones once their
		# usefulness has passed.
		if request_method == 'PING':
			# This is made somewhat harder because we want to keep
			# a numeric range of timestamps, not a quantity of
			# them. Sorted sets look like the only way to do it.

			# By way of example, assume that each backend pings
			# every 5min, and we'd like to keep the last 30min
			# worth of ping timestamps. We *could* keep a list of
			# ping timestamps and truncate to len=100 all the time,
			# but that doesn't assure a sane distribution of
			# timestamps and tell us what we *really* want to know.

			# Because sets are unique, I think I'll need to use
			# dummy key names, and keep the timestamps purely as
			# scores.

			# I'd like to do a proper conversion of URL-to-doctype,
			# but that would introduct a dependency on the
			# distillers. It'd be fine, but I think I'd rather
			# avoid it right now, so we'll leave it to be someone
			# else's problem when it's read back for monitoring.

			# Assume that the PING'd urls for each backend don't
			# change over time, we can still do pattern
			# recognition.

			current_time       = datetime.datetime.utcnow()
			thirty_minutes     = datetime.timedelta(minutes=30)
			thirty_minutes_ago = current_time - thirty_minutes

			current_timestamp            = int(time.mktime(current_time.timetuple()))
			thirty_minutes_ago_timestamp = int(time.mktime(thirty_minutes_ago.timetuple()))

			dst_redis.zremrangebyscore('umad_backend_heartbeats', '-inf', thirty_minutes_ago_timestamp)
			dst_redis.zadd('umad_backend_heartbeats', current_timestamp, "{0} {1}".format(request_url, current_timestamp) )
			mention(u"Logged heartbeat ping for {0} at {1}".format(request_url, current_timestamp))

			# On readback we simply do:
			# dst_redis.zrangebyscore('umad_backend_heartbeats', thirty_minutes_ago_timestamp, '+inf')
			# Split each result, keep the ones for which the first
			# element is the backend we care about, then analyse
			# the numbers.

	return 0


if __name__ == "__main__":
	sys.exit(main())
