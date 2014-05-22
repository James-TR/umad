Smykowski
=========

This utility grabs log events from one Redis database+key, processes them, then
dumps them into UMAD's queue for indexing/deletion.

The input format is Awesant's, usually intended for use with Logstash.

Log messages are blindly assumed to have the following format:

    MESSAGE = METHOD, white space, URL ;

    METHOD = "POST" | "GET" | "DELETE" ;

    URL is defined as per usual internet RFCs, etc.

By default, Smykowski assumes that log events arrive in database 8, and should
be deposited in database 0.
