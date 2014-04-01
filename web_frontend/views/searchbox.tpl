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
				<div class="btn-toolbar">
				% doc_types_present = sorted(list(doc_types_present))
				% for doc_type in doc_types_present:
					<div class="btn-group">
						<button type="button" class="btn btn-default doc-type {{ doc_type[1] }}" title="Dismiss all {{ doc_type[0] }}" onClick="javascript:killResultsMatchingClass('{{ doc_type[1] }}');">{{ doc_type[0] }} ✘</button>
					</div>
				% end
				</div>
			</div>
		</div> <!-- END searchbox -->
