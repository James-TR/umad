		<div id="output">
		<%
		if search_term:
			if hits:
				# XXX: Push sanity futher up the stack
				for i,hit in enumerate(hits):
					hit['result_number'] = i+1
					hit['other_metadata'] = dict(hit['other_metadata'])
				end

				# See if we might have been truncated anywhere, hit_limit applies on a per doc_type basis.
				# XXX: This is a hack, we should be checking other_metadata->doc_type (where present) instead of highlight.
				truncated = False
				for doc_type in doc_types_present:
					num_hits_of_this_type = len([ x for x in hits if x['highlight_class']==doc_type[1] ])
					if num_hits_of_this_type >= hit_limit:
						truncated = True
						break
					end
				end
				%>

				<div class="alert alert-info">
					% if not truncated:
						Showing {{ "all " if len(hits) > 1 else "" }}<strong><span id="hitcount">{{ len(hits) }}</span> {{ "result" if len(hits) == 1 else "results" }}</strong>
					% else:
						Display limited to <strong><span id="hitcount">{{ len(hits) }}</span> {{ "result" if len(hits) == 1 else "results" }}. </strong>Results may be truncated, no more than {{ hit_limit }} of each document type are displayed
					% end
				</div>
				<ul id="hits">
				% for hit in hits:
					% include('result_hit.tpl', highlight_class=hit['highlight_class'], id=hit['id'], extract=hit['extract'], other_metadata=hit['other_metadata'], score=hit['score'], umad_indexer_url=umad_indexer_url)
				% end
				</ul>
			% else:
					No results found for <span class="inline-query-display">{{ search_term }}</span>
			% end
		% else:
			<!-- No results here ^_^ -->
		% end
		</div> <!-- END output -->
