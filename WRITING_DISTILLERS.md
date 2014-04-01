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
tickets have a `doc_type` of "rt", which will allow you to intuitively search
for RT support tickets like so:

    rt:emergency

This essentially makes the short `doc_type` a surrogate for specifying
`_type:rt` in your search. This field is mapped to the document's blob, so
everything should Just Work as expected.


Determining doc_type
--------------------

Your localconfig.py must provide...

* A list, `distillers`, of Distiller subclasses.
* A list, `ELASTICSEARCH_NODES`, of ES nodes to connect to, eg.: `[ "10.0.0.1:9200" ]`

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


An example distiller
====================

An example Distiller class is provided, under `distil/newtype.py`. If you want
to implement a your own new document type, it should be enough to get you going
by filling in the blanks.

1. Choose a name for your new document type, restricting it to a short,
   descriptive, unambiguous string of lowercase ascii characters is best. This
   will be your **doctype**. Use underscores if you really must. Eg. `[a-z_]+`

2. Copy `newtype.py` to a new file, naming it `<doctype>.py` is best.

3. Implement the functionality as directed in the example. Note that you'll
   have also named your new Distiller class, eg. `NewtypeDistiller`

4. Import your new Distiller class in `distil/__init__.py`, eg.:

      from newtype import NewtypeDistiller

5. Add your new Distiller class to `localconfig.py`, eg.:

      # ... in distillers = []
      NewtypeDistiller ,

6. Optionally style the class up for display, this is highily recommended.
   Select a colour and add the necessary code.

      # web_frontend/static/style/umad.css
      .highlight-newtype {
        border-left: 3px solid #abcdef;
      }

      # web_frontend/umad.py
      if url.startswith('http://new.type.ms/'):
          return ('Newtype', 'highlight-newtype')

      # web_frontend/views/result_hit.tpl
      highlight_classes_to_doctypes['highlight-newtype'] = "newtypes"
