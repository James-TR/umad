		<div id="searchbox">
			<a href="/?q=mad"><img src="/static/umad.png" style="border:0;" alt="UMAD logo"></a><br />

			<form name="q" method="get" action="/" 
% if searchterm:
				onSubmit="evilSearchedAgain()"
% end
			>
				<p id="searchform">
					<input type="search" id="searchinput" name="q" placeholder="What be ye lookin' for?" value="{{ searchterm }}" autofocus="autofocus">
					<input type="submit" value="Unearth Me A Document!">
				</p>
			</form>

			<div id="search-toggles">
				% for doc_type in doc_types_present:
				<div class="doc-type {{ doc_type[1] }}" title="Dismiss all {{ doc_type[0] }}" onClick="javascript:killResultsMatchingClass('{{ doc_type[1] }}');"> {{ doc_type[0] }} <span class="right">✘</span> </div>
				% end
			</div>
		</div> <!-- END searchbox -->
