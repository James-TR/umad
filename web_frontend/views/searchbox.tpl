		<div class="jumbotron">
			<form name="q" method="get" action="/" 
% if searchterm:
				onSubmit="evilSearchedAgain()"
% end
			>

			<div class="input-group input-group">
				<span class="input-group-addon" id="umadbox">
					<a href="/?q=cats"><img src="/static/img/umad.png" class="umadlogo" style="border:0;" alt="UMAD logo"></a></span>
			 	<input type="search" class="form-control" id="searchinput" name="q" placeholder="UMAD?" value="{{ searchterm }}" autofocus="autofocus">
			</div>

			<div id="search-toggles">
			% doc_types_present = sorted(list(doc_types_present))
			% for doc_type in doc_types_present:
				<button id="results-toggle-{{ doc_type[1] }}" type="button" data-toggle="button" class="btn btn-default doc-type {{ doc_type[1] }}" title="Show/hide {{ doc_type[0] }}">{{ doc_type[0] }} ✘</button>
				<script>$('#results-toggle-{{ doc_type[1] }}').click(function () { $('.result-card.{{ doc_type[1] }}').slideToggle(500, refreshHitcount); });</script>
			% end
			</div>
		</div> <!-- END searchbox -->
