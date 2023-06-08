<!-- markdownlint-disable first-line-h1 no-space-in-emphasis -->
<dt class="sig sig-object py" id="dipdup.context.DipDupContext">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.context.</span></span><span class="sig-name descname"><span class="pre">DipDupContext</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">config</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">package</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasources</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">transactions</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext" title="Permalink to this definition">¶</a></dt>
<dd><p>Common execution context for handler and hook callbacks.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>config</strong> (<a class="reference internal" href="config-reference.html#dipdup.config.DipDupConfig" title="dipdup.config.DipDupConfig"><em>DipDupConfig</em></a>) – DipDup configuration</p></li>
<li><p><strong>package</strong> (<em>DipDupPackage</em>) – DipDup package</p></li>
<li><p><strong>datasources</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><em>dipdup.datasources.Datasource</em><em>[</em><em>dipdup.fields.Any</em><em>]</em><em>]</em>) – Mapping of available datasources</p></li>
<li><p><strong>logger</strong> – Context-aware logger instance</p></li>
<li><p><strong>transactions</strong> (<em>TransactionManager</em>) – </p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.context.HandlerContext">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.context.</span></span><span class="sig-name descname"><span class="pre">HandlerContext</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">config</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">package</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasources</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">transactions</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">logger</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">handler_config</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasource</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.HandlerContext" title="Permalink to this definition">¶</a></dt>
<dd><p>Execution context of handler callbacks.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>handler_config</strong> (<em>HandlerConfig</em>) – Configuration of the current handler</p></li>
<li><p><strong>datasource</strong> (<em>IndexDatasource</em><em>[</em><em>Any</em><em>]</em>) – Index datasource instance</p></li>
<li><p><strong>config</strong> (<a class="reference internal" href="config-reference.html#dipdup.config.DipDupConfig" title="dipdup.config.DipDupConfig"><em>DipDupConfig</em></a>) – </p></li>
<li><p><strong>package</strong> (<em>DipDupPackage</em>) – </p></li>
<li><p><strong>datasources</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><em>dipdup.datasources.Datasource</em><em>[</em><em>dipdup.fields.Any</em><em>]</em><em>]</em>) – </p></li>
<li><p><strong>transactions</strong> (<em>TransactionManager</em>) – </p></li>
<li><p><strong>logger</strong> (<em>FormattedLogger</em>) – </p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.context.HookContext">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.context.</span></span><span class="sig-name descname"><span class="pre">HookContext</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">config</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">package</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasources</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">transactions</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">logger</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">hook_config</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.HookContext" title="Permalink to this definition">¶</a></dt>
<dd><p>Execution context of hook callbacks.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>hook_config</strong> (<a class="reference internal" href="config-reference.html#dipdup.config.HookConfig" title="dipdup.config.HookConfig"><em>HookConfig</em></a>) – Configuration of the current hook</p></li>
<li><p><strong>config</strong> (<a class="reference internal" href="config-reference.html#dipdup.config.DipDupConfig" title="dipdup.config.DipDupConfig"><em>DipDupConfig</em></a>) – </p></li>
<li><p><strong>package</strong> (<em>DipDupPackage</em>) – </p></li>
<li><p><strong>datasources</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><em>dipdup.datasources.Datasource</em><em>[</em><em>dipdup.fields.Any</em><em>]</em><em>]</em>) – </p></li>
<li><p><strong>transactions</strong> (<em>TransactionManager</em>) – </p></li>
<li><p><strong>logger</strong> (<em>FormattedLogger</em>) – </p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.add_contract">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">add_contract</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">name</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">address</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">typename</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">code_hash</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.add_contract" title="Permalink to this definition">¶</a></dt>
<dd><p>Adds contract to the inventory.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>name</strong> (<em>str</em>) – Contract name</p></li>
<li><p><strong>address</strong> (<em>str</em><em> | </em><em>None</em>) – Contract address</p></li>
<li><p><strong>typename</strong> (<em>str</em><em> | </em><em>None</em>) – Alias for the contract script</p></li>
<li><p><strong>code_hash</strong> (<em>str</em><em> | </em><em>int</em><em> | </em><em>None</em>) – Contract code hash</p></li>
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'tezos'</em><em>] </em><em>| </em><em>~typing.Literal</em><em>[</em><em>'evm'</em><em>]</em>) – Either ‘tezos’ or ‘evm’ allowed</p></li>
</ul>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p>None</p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.add_index">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">add_index</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">template</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">values</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">first_level</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">0</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">last_level</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">0</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">state</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.add_index" title="Permalink to this definition">¶</a></dt>
<dd><p>Adds a new contract to the inventory.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>name</strong> (<em>str</em>) – Index name</p></li>
<li><p><strong>template</strong> (<em>str</em>) – Index template to use</p></li>
<li><p><strong>values</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><em>dipdup.fields.Any</em><em>]</em>) – Mapping of values to fill template with</p></li>
<li><p><strong>first_level</strong> (<em>int</em>) – </p></li>
<li><p><strong>last_level</strong> (<em>int</em>) – </p></li>
<li><p><strong>state</strong> (<em>Index</em><em> | </em><em>None</em>) – </p></li>
</ul>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p>None</p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.execute_sql">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">execute_sql</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">*</span></span><span class="n"><span class="pre">args</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">**</span></span><span class="n"><span class="pre">kwargs</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.execute_sql" title="Permalink to this definition">¶</a></dt>
<dd><p>Executes SQL script(s) with given name.</p>
<p>If the <cite>name</cite> path is a directory, all <cite>.sql</cite> scripts within it will be executed in alphabetical order.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>name</strong> (<em>str</em>) – File or directory within project’s <cite>sql</cite> directory</p></li>
<li><p><strong>args</strong> (<em>Any</em>) – Positional arguments to pass to the script</p></li>
<li><p><strong>kwargs</strong> (<em>Any</em>) – Keyword arguments to pass to the script</p></li>
</ul>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p>None</p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.execute_sql_query">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">execute_sql_query</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">*</span></span><span class="n"><span class="pre">values</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.execute_sql_query" title="Permalink to this definition">¶</a></dt>
<dd><p>Executes SQL query with given name included with the project</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>name</strong> (<em>str</em>) – SQL query name within <cite>&lt;project&gt;/sql</cite> directory</p></li>
<li><p><strong>values</strong> (<em>Any</em>) – </p></li>
</ul>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p><em>Any</em></p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.fire_hook">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">fire_hook</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">fmt</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">wait</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">True</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">*</span></span><span class="n"><span class="pre">args</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">**</span></span><span class="n"><span class="pre">kwargs</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.fire_hook" title="Permalink to this definition">¶</a></dt>
<dd><p>Fire hook with given name and arguments.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>name</strong> (<em>str</em>) – Hook name</p></li>
<li><p><strong>fmt</strong> (<em>str</em><em> | </em><em>None</em>) – Format string for <cite>ctx.logger</cite> messages</p></li>
<li><p><strong>wait</strong> (<em>bool</em>) – Wait for hook to finish or fire and forget</p></li>
<li><p><strong>args</strong> (<em>Any</em>) – Positional arguments to pass to the hook</p></li>
<li><p><strong>kwargs</strong> (<em>Any</em>) – Keyword arguments to pass to the hook</p></li>
</ul>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p>None</p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.get_coinbase_datasource">
<span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">get_coinbase_datasource</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.get_coinbase_datasource" title="Permalink to this definition">¶</a></dt>
<dd><p>Get <cite>coinbase</cite> datasource by name</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><p><strong>name</strong> (<em>str</em>) – </p>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p><em>CoinbaseDatasource</em></p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.get_http_datasource">
<span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">get_http_datasource</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.get_http_datasource" title="Permalink to this definition">¶</a></dt>
<dd><p>Get <cite>http</cite> datasource by name</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><p><strong>name</strong> (<em>str</em>) – </p>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p><em>HttpDatasource</em></p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.get_ipfs_datasource">
<span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">get_ipfs_datasource</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.get_ipfs_datasource" title="Permalink to this definition">¶</a></dt>
<dd><p>Get <cite>ipfs</cite> datasource by name</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><p><strong>name</strong> (<em>str</em>) – </p>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p><em>IpfsDatasource</em></p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.get_metadata_datasource">
<span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">get_metadata_datasource</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.get_metadata_datasource" title="Permalink to this definition">¶</a></dt>
<dd><p>Get <cite>metadata</cite> datasource by name</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><p><strong>name</strong> (<em>str</em>) – </p>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p><em>TzipMetadataDatasource</em></p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.get_tzkt_datasource">
<span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">get_tzkt_datasource</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.get_tzkt_datasource" title="Permalink to this definition">¶</a></dt>
<dd><p>Get <cite>tezos.tzkt</cite> datasource by name</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><p><strong>name</strong> (<em>str</em>) – </p>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p><em>TzktDatasource</em></p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.reindex">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">reindex</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">reason</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">**</span></span><span class="n"><span class="pre">context</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.reindex" title="Permalink to this definition">¶</a></dt>
<dd><p>Drops the entire database and starts the indexing process from scratch.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>reason</strong> (<em>str</em><em> | </em><a class="reference internal" href="config-reference.html#dipdup.models.ReindexingReason" title="dipdup.models.ReindexingReason"><em>ReindexingReason</em></a><em> | </em><em>None</em>) – Reason for reindexing in free-form string</p></li>
<li><p><strong>context</strong> (<em>Any</em>) – Additional information to include in exception message</p></li>
</ul>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p>None</p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.restart">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">restart</span></span><span class="sig-paren">(</span><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.restart" title="Permalink to this definition">¶</a></dt>
<dd><p>Restart process and continue indexing.</p>
<dl class="field-list simple">
<dt class="field-odd">Return type<span class="colon">:</span></dt>
<dd class="field-odd"><p>None</p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.update_contract_metadata">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">update_contract_metadata</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">network</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">address</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">metadata</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.update_contract_metadata" title="Permalink to this definition">¶</a></dt>
<dd><p>Inserts or updates corresponding rows in the internal <cite>dipdup_contract_metadata</cite> table
to provide a generic metadata interface (see docs).</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>network</strong> (<em>str</em>) – Network name (e.g. <cite>mainnet</cite>)</p></li>
<li><p><strong>address</strong> (<em>str</em>) – Contract address</p></li>
<li><p><strong>metadata</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><em>dipdup.fields.Any</em><em>] </em><em>| </em><em>None</em>) – Contract metadata to insert/update</p></li>
</ul>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p>None</p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.update_token_metadata">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">DipDupContext.</span></span><span class="sig-name descname"><span class="pre">update_token_metadata</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">network</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">address</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">token_id</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">metadata</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext.update_token_metadata" title="Permalink to this definition">¶</a></dt>
<dd><p>Inserts or updates corresponding rows in the internal <cite>dipdup_token_metadata</cite> table
to provide a generic metadata interface (see docs).</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>network</strong> (<em>str</em>) – Network name (e.g. <cite>mainnet</cite>)</p></li>
<li><p><strong>address</strong> (<em>str</em>) – Contract address</p></li>
<li><p><strong>token_id</strong> (<em>str</em>) – Token ID</p></li>
<li><p><strong>metadata</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><em>dipdup.fields.Any</em><em>] </em><em>| </em><em>None</em>) – Token metadata to insert/update</p></li>
</ul>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p>None</p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.HookContext.rollback">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">HookContext.</span></span><span class="sig-name descname"><span class="pre">rollback</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">index</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">from_level</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">to_level</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.HookContext.rollback" title="Permalink to this definition">¶</a></dt>
<dd><p>Rollback index to a given level reverting all changes made since that level.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>index</strong> (<em>str</em>) – Index name</p></li>
<li><p><strong>from_level</strong> (<em>int</em>) – Level to rollback from</p></li>
<li><p><strong>to_level</strong> (<em>int</em>) – Level to rollback to</p></li>
</ul>
</dd>
<dt class="field-even">Return type<span class="colon">:</span></dt>
<dd class="field-even"><p>None</p>
</dd>
</dl>
</dd></dl>
