% include('TOP.tpl')

% include('searchbox.tpl', search_term=search_term, hits=hits, doc_types_present=doc_types_present)

% include('motd.tpl', search_term=search_term)

% if valid_search_query:
	% include('searchresults.tpl', search_term=search_term, hits=hits, hit_limit=hit_limit, doc_types_present=doc_types_present, umad_indexer_url=umad_indexer_url)
% else:
	% include('invalidquery.tpl', search_term=search_term)
% end

% include('BOTTOM.tpl', version_string=version_string)
