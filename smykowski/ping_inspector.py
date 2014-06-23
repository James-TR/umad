import sys
import os
import time
import datetime

import redis
import json


def fetch_pings():
	"Grab the last half hour of pings for inspection."

	redis_server_host    = os.environ.get('UMAD_REDIS_HOST', 'localhost')
	redis_server_port    = os.environ.get('UMAD_REDIS_PORT', 6379)
	redis_server_db_dst  = os.environ.get('UMAD_REDIS_DB_DST', 0)
	dst_redis = redis.StrictRedis(host=redis_server_host, port=int(redis_server_port), db=redis_server_db_dst)

	current_time       = datetime.datetime.utcnow()
	thirty_minutes     = datetime.timedelta(minutes=30)
	thirty_minutes_ago = current_time - thirty_minutes

	current_timestamp            = int(time.mktime(current_time.timetuple()))
	thirty_minutes_ago_timestamp = int(time.mktime(thirty_minutes_ago.timetuple()))

	# pings is a list of 2-tuples, ('<URL> <TIMESTAMP>', <TIMESTAMP>)
	pings = dst_redis.zrangebyscore('umad_backend_heartbeats', thirty_minutes_ago_timestamp, '+inf', withscores=True)
	return sorted(pings)


def human_readable(pings):
	# Convert the second element to a human-readable timestamp
	return [ (x[0].partition(' ')[0], datetime.datetime.fromtimestamp(x[1]).strftime('%Y-%m-%d %H:%M:%S%z') ) for x in pings ]

def clean_first_element(pings):
	# Strip the first element back to just the URL
	return [ (x[0].partition(' ')[0], x[1] ) for x in pings ]


def filter_for_backend(pings, filter_string=''):
	return [ x for x in pings if filter_string in x[0] ]
	

def main(argv=None):
	from pprint import pprint

	pings = fetch_pings()

	# Test...
	pprint(pings)
	pprint(human_readable(pings))

	# Test test, 1-2-test... testing...
	pprint(filter_for_backend(pings, 'docs.anchor'))
	pprint(filter_for_backend(pings, 'map.eng'))

	return 0

if __name__ == "__main__":
	sys.exit(main())
