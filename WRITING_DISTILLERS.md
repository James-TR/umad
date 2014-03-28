UMAD's data vampirism is modular, you write distillation modules that take a
URL and return a blob to be indexed.

Document Types
==============

`doc_type` is a core ElasticSearch concept to help you organise your documents.
UMAD inspects the URL of the document (according to rules that you specify) to
derive the `doc_type`, which is a short string identifying the human source of
the document.

As part of a current hack to make searching faster/easier, documents will be
indexed with a field whose name matches the `doc_type`. For example, RT support
tickets have a `doc_type` of "rt", which will allow you to search for a
domain-specific unique identifier, like so:

    rt:123456

This essentially makes the short `doc_type` a surrogate for specifying
`doc_type:rt` in your search. The unique identifier is provided during
indexing, in a field named `local_id`.


Determining doc_type
--------------------

Your localconfig.py must provide...

TBC


Interface
=========

The interface is super simple:

* You subclass the Distiller class.
* Your class implements two methods, `will_handle` and `blobify`, and provides
  a class attribute, `doc_type`.
* `will_handle` returns True or False indicating whether it can handle a given
  URL. This is generally a simple string.startswith() check.
* When called, `blobify` (usually) inspects `self.url` then gets to work.
    * The URL is opaque and may have a bogus schema and everything, what you do
      with it is up to you.
* You return an iterable of documents to be indexed.
    * Better yet, `yield`ing an iterator is particularly elegant.
* Documents are a dictionary with two mandatory keys, `url` and `blob`, plus
  any additional keys that you wish to include.
    * A distiller may return multiple documents for a single `self.url`, which
      is why each document includes its own `url`. It should also tidy the URL
      into a canonical form if necessary, resolving any redirects.


Optional keys
-------------

You may return additional keys in your blob, indeed this is encouraged. Additional keys allow for more nuanced information to be presented to the user, and they are also directly searchable.

* If `title` is present, it will be used when the document is displayed,
  instead of the raw `url`
* `local_id` can be provided as a domain-specific identifier for a document.
  This should be a high-value hit if the user searches for it.
    * For example, support ticket numbers are a unique identifier for support
     tickets, and something a user is likely to mash into the search box.
    * `local_id` is not treated specially, it's just a hack to having a field
      that's easy to match exactly
* `last_updated` is used to better rank documents if it's provided, newer
  documents get boosted higher (not yet implemented)


Hello World distiller
=====================

1. Create your module in the `distil/` directory, we're calling it
   `helloworld.py`

      import sys
      import foo
      import bambleweenie

      def blobify(url):
          result = {}
          result['url'] = "hello://adam.jensen/greeting"
          result['blob'] = "I didn't ask for this"
          return [result]

2. You need to hook your module into the framework, add yourself to
   `__init__.py`

      # At the top
      import helloworld

      # And in the URL-matching messiness
      ...
      elif url.startswith('hello://'):
          self.fetcher = helloworld


