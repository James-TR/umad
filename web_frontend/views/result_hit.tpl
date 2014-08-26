				<%
				# Use json for encoding strings
				import json
				# For creating links to the umad-indexer
				from urllib import urlencode
				%>

				<li class="result-card {{ highlight_class.encode('utf8') }}">
				<div class="hitlink">
					<%
						doc_type = other_metadata.get('doc_type')
						# Kill a field whose name=doc_type if
						# it exists; no need to print it later.
						other_metadata.pop(doc_type, None)

						linktext = other_metadata.get('name', id)
						linktext = other_metadata.get('title', linktext)
						if linktext:
							if doc_type not in ['domain']:
								# Domain names look stupid when capitalised.
								linktext = linktext[0].upper() + linktext[1:]
							end
						end

						customer_name = other_metadata.get('customer_name', u'')
						if customer_name:
							customer_search_query_string = urlencode({'q':'customer: "{0}"'.format(customer_name.encode('utf8'))})
							customer_name = u"""↜ <a href="/?{1}">{0}</a>""".format(customer_name, customer_search_query_string)
						end

						href = other_metadata.get('functional_url', id)
					%>
					<a href="{{ href.encode('utf8') }}" onClick="evilUserClick({{ json.dumps(hit) }})">{{ linktext.encode('utf8') }}</a> <span class="customer-name">{{! customer_name.encode('utf8') }}</span> <span class="document-score">scored {{ score }}</span>
					<!-- OPTIONAL FOR NOW
					<a href="https://twitter.com/share" class="twitter-share-button" data-url="{{ id.encode('utf8') }}" data-text="{{ linktext.encode('utf8') }}" data-dnt="true">
					<span class="glyphicon glyphicon-thumbs-up" title="SHARE with #robots" onClick="javascript:shareWithSysadmins('{{ id.encode('utf8').encode('base64').replace('\n','').strip() }}', '{{ linktext.encode('utf8').encode('base64').replace('\n','').strip() }}');">sns</span>
					Tweet that shiz</a>
					-->
				</div>

				% # Some doc types don't actually have URLs, so we don't display them
				% if doc_type not in ['domain']:
					% if "name" in other_metadata or "title" in other_metadata:
					<div class="hiturl">{{ id.encode('utf8') }}</div>
					% end
				% end

				% if doc_type == 'customer':
					<span class="excerpt"> Customer id: {{ other_metadata['customer_id'] }}\\
						<% output = ''
						if 'primary_contacts' in other_metadata:
							output += '\n' + other_metadata['primary_contacts']
						end
						if 'billing_contacts' in other_metadata:
							output += '\n' + other_metadata['billing_contacts']
						end
						if 'technical_contacts' in other_metadata:
							output += '\n' + other_metadata['technical_contacts']
						end
						new_ticket_link = 'https://rt.engineroom.anchor.net.au/Ticket/Create.html?Queue=13&Object-RT::Ticket--CustomField-92-Value={customer_id}'.format(**other_metadata)
						customer_tickets_link = 'https://rt.engineroom.anchor.net.au/Search/Results.html?Order=DESC&OrderBy=LastUpdated&Query=%27CF.{{Related%20Customer}}%27%3D{customer_id}'.format(**other_metadata)
						%>
						{{ output.encode('utf8') }}
						<a href="{{ new_ticket_link }}" target="_blank" ><span class="glyphicon glyphicon-plus"></span> Create a ticket</a>
						<a href="{{ customer_tickets_link }}"><span class="glyphicon glyphicon-list"></span> Show customer's tickets</a>
					</span>
				% elif doc_type == 'domain':
					<span class="excerpt"> Expiry: {{ other_metadata['expiry'].split('T')[0] }}\\
						<% output = ''
						if 'customer_name' in other_metadata:
							output += '\n' + "Customer: {customer_name} ({customer_id})".format(**other_metadata)
						end
						if 'au_registrant' in other_metadata:
							output += '\n' + "Registrant: {}".format(other_metadata['au_registrant'])
							output += '\n' + "{first_name} {last_name} {email}".format(**other_metadata['owner_contact'])
						else:
							if other_metadata['owner_contact']['org_name'] == u"{first_name} {last_name}".format(**other_metadata['owner_contact']):
								output += '\n' + "{first_name} {last_name} {email}".format(**other_metadata['owner_contact'])
							else:
								output += '\n' + "{first_name} {last_name} ({org_name}) {email}".format(**other_metadata['owner_contact'])
							end
						end
						if 'nameservers' in other_metadata:
							output += '\n' + "Nameservers: {} ".format(" ".join(sorted(other_metadata['nameservers'])))
						end
						%>
						{{ output.encode('utf8') }}
					</span>
				% elif doc_type == 'rt':
					<span class="excerpt"> <span class="rt_status">Status: {{ other_metadata['status'] }} </span><span class="rt_last_updated">Last updated: {{ other_metadata['last_updated_sydney'] }}</span>
					{{! other_metadata['excerpt'].encode('utf8') }}</span>
				% else:
					<span class="excerpt">{{! extract.encode('utf8') }}</span>
				% end

				<div class="reindex-button">
					% umad_indexer_query_string = urlencode({'url':id.encode('utf8')})
					<a href="{{ umad_indexer_url }}?{{! umad_indexer_query_string }}" target="_blank" onClick="evilUserReindex({{ json.dumps(hit) }})"><span class="glyphicon glyphicon-refresh" title="Reindex this result"></span></a>
				</div>

				<div class="metadata-button">
					<span class="glyphicon glyphicon-tags"></span>

					% # Only if the list is non-empty
					% if other_metadata:
						<%
						# Don't need to print these keys, they're already part of the main display
						if doc_type == 'domain':
							other_metadata.pop('owner_contact', None)
						end
						other_metadata.pop('excerpt', None)
						other_metadata.pop('title', None)
						other_metadata.pop('doc_type', None)
						other_metadata.pop('public_blob', None)
						%>
					<div class="other-metadata alert alert-success">
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

