				<%
				# Convert CSS highlighting classes to a semantic description of the document type (always plural)
				highlight_classes_to_doctypes = {}
				highlight_classes_to_doctypes['highlight-portal-orange'] = "provsys servers"
				highlight_classes_to_doctypes['highlight-portal-blue'] = "gollum docs"
				highlight_classes_to_doctypes['highlight-luka'] = "RT tickets"
				highlight_classes_to_doctypes['highlight-miku'] = "Map wiki pages"
				highlight_classes_to_doctypes[''] = "documents of unknown origin"

				# Use json for encoding strings
				import json
				# For creating links to the umad-indexer
				from urllib import urlencode
				%>

				<li class="result-card {{ highlight_class.encode('utf8') }}">
				<div class="hitlink">
					<%
					linktext = other_metadata.get('name', id)
					linktext = other_metadata.get('title', linktext)
					customer_name = other_metadata.get('customer_name', u'')
					if customer_name:
						customer_name = u'↜ {0}'.format(customer_name)
					end
					doc_type = other_metadata.get('doc_type')
					if doc_type:
						del(other_metadata[doc_type])
					end
					href = other_metadata.get('functional_url', id)
					%>
					<a href="{{ href.encode('utf8') }}" onClick="evilUserClick({{ json.dumps(hit) }})">{{ linktext.encode('utf8') }}</a> <span class="customer-name">{{ customer_name.encode('utf8') }}</span> <span class="document-score">scored {{ score }}</span>
					<!-- OPTIONAL FOR NOW
					<span class="lsf social-button-jabber" title="SHARE with #robots" onClick="javascript:shareWithSysadmins('{{ id.encode('utf8').encode('base64').replace('\n','').strip() }}', '{{ linktext.encode('utf8').encode('base64').replace('\n','').strip() }}');">sns</span>
					<a href="https://twitter.com/share" class="twitter-share-button" data-url="{{ id.encode('utf8') }}" data-text="{{ linktext.encode('utf8') }}" data-dnt="true">Tweet that shiz</a>
					-->
				</div>

				% if "name" in other_metadata or "title" in other_metadata:
				<div class="hiturl">{{ id.encode('utf8') }}</div>
				% end

				% if doc_type == 'customer':
				<!-- XXX: This fails when there's no customer_id.  Why is there no customer ID? -->
				<span class="excerpt"> Customer id: {{ other_metadata['customer_id'] }}\\
					<% output = ''
					if other_metadata.has_key('primary_contacts'):
						output += '\n' + other_metadata['primary_contacts']
					end
					if other_metadata.has_key('billing_contacts'):
						output += '\n' + other_metadata['billing_contacts']
					end
					if other_metadata.has_key('technical_contacts'):
						output += '\n' + other_metadata['technical_contacts']
					end
					new_ticket_link = 'https://rt.engineroom.anchor.net.au/Ticket/Create.html?Queue=13&Object-RT::Ticket--CustomField-92-Value=' + str(other_metadata['customer_id'])
					%>
					{{ output.encode('utf8') }}
					<a href={{ new_ticket_link }} target="_blank" >Create a ticket</a>
				</span><br />
				% else:
					<span class="excerpt">{{! extract.encode('utf8') }}</span><br />
				% end

				<div class="reindex-button">
					% umad_indexer_query_string = urlencode({'url':id.encode('utf8')})
					<span class="lsf" title="Reindex this result"><a href="https://umad-indexer.anchor.net.au/?{{! umad_indexer_query_string }}" target="_blank" onClick="evilUserReindex({{ json.dumps(hit) }})">sync</a></span>
				</div>

				<div class="metadata-button">
					<span class="lsf">tag</span>

					% # Only if the list is non-empty
					% if other_metadata:
						<%
						# Don't need to print these keys, they're already part of the main display
						if 'excerpt' in other_metadata:
							del(other_metadata['excerpt'])
						end
						if 'title' in other_metadata:
							del(other_metadata['title'])
						end
						if 'doc_type' in other_metadata:
							del(other_metadata['doc_type'])
						end
						if 'public_blob' in other_metadata:
							del(other_metadata['public_blob'])
						end
						%>
					<div class="other-metadata">
						Other metadata
						<ul>
						% for key in sorted(other_metadata):
							% metadata_value = other_metadata[key]
							% # Not quite ideal, we should really be catching any "real" iterable (list/dict/tuple), and falling back to default for anything else
							% if isinstance(metadata_value, (str, unicode)):
								<li class="metadata"><strong>{{ key.encode('utf8') }}:</strong> {{ metadata_value.encode('utf8') }}</li>
							% elif isinstance(metadata_value, (bool, int)):
								<li class="metadata"><strong>{{ key.encode('utf8') }}:</strong> {{ "{0}".format(metadata_value) }}</li>
							% else:
								<li class="metadata"><strong>{{ key.encode('utf8') }}:</strong> {{ ', '.join(sorted(metadata_value)).encode('utf8') }}</li>
							% end
						% end
						</ul>
					</div>
					% end
				</div>
				</li>

