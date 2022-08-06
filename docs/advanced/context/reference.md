
  <span class="target" id="module-dipdup.context"></span><dl class="py class">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.context.</span></span><span class="sig-name descname"><span class="pre">DipDupContext</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">datasources</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Dict</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">Datasource</span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">config</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><a class="reference internal" href="config-reference.html#dipdup.config.DipDupConfig" title="dipdup.config.DipDupConfig"><span class="pre">DipDupConfig</span></a></span></em>, <em class="sig-param"><span class="n"><span class="pre">callbacks</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">CallbackManager</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">transactions</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">TransactionManager</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext" title="Permalink to this definition">¶</a></dt>
<dd><p>Common execution context for handler and hook callbacks.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>datasources</strong> – Mapping of available datasources</p></li>
<li><p><strong>config</strong> – DipDup configuration</p></li>
<li><p><strong>logger</strong> – Context-aware logger instance</p></li>
</ul>
</dd>
</dl>
<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.add_contract">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">add_contract</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">address</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">typename</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.add_contract" title="Permalink to this definition">¶</a></dt>
<dd><p>Adds contract to the inventory.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>name</strong> – Contract name</p></li>
<li><p><strong>address</strong> – Contract address</p></li>
<li><p><strong>typename</strong> – Alias for the contract script</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.add_index">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">add_index</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">template</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">values</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Dict</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">Any</span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">state</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">Index</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.add_index" title="Permalink to this definition">¶</a></dt>
<dd><p>Adds a new contract to the inventory.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>name</strong> – Index name</p></li>
<li><p><strong>template</strong> – Index template to use</p></li>
<li><p><strong>values</strong> – Mapping of values to fill template with</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.execute_sql">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">execute_sql</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.execute_sql" title="Permalink to this definition">¶</a></dt>
<dd><p>Executes SQL script(s) with given name.</p>
<p>If the <cite>name</cite> path is a directory, all <cite>.sql</cite> scripts within it will be executed in alphabetical order.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><p><strong>name</strong> – File or directory within project’s <cite>sql</cite> directory</p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.fire_hook">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">fire_hook</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">fmt</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">wait</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">bool</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">True</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">*</span></span><span class="n"><span class="pre">args</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">**</span></span><span class="n"><span class="pre">kwargs</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Any</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.fire_hook" title="Permalink to this definition">¶</a></dt>
<dd><p>Fire hook with given name and arguments.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>name</strong> – Hook name</p></li>
<li><p><strong>fmt</strong> – Format string for <cite>ctx.logger</cite> messages</p></li>
<li><p><strong>wait</strong> – Wait for hook to finish or fire and forget</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.get_coinbase_datasource">
<span class="sig-name descname"><span class="pre">get_coinbase_datasource</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">CoinbaseDatasource</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.get_coinbase_datasource" title="Permalink to this definition">¶</a></dt>
<dd><p>Get <cite>coinbase</cite> datasource by name</p>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.get_http_datasource">
<span class="sig-name descname"><span class="pre">get_http_datasource</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">HttpDatasource</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.get_http_datasource" title="Permalink to this definition">¶</a></dt>
<dd><p>Get <cite>http</cite> datasource by name</p>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.get_ipfs_datasource">
<span class="sig-name descname"><span class="pre">get_ipfs_datasource</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">IpfsDatasource</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.get_ipfs_datasource" title="Permalink to this definition">¶</a></dt>
<dd><p>Get <cite>ipfs</cite> datasource by name</p>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.get_metadata_datasource">
<span class="sig-name descname"><span class="pre">get_metadata_datasource</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">MetadataDatasource</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.get_metadata_datasource" title="Permalink to this definition">¶</a></dt>
<dd><p>Get <cite>metadata</cite> datasource by name</p>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.get_tzkt_datasource">
<span class="sig-name descname"><span class="pre">get_tzkt_datasource</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">TzktDatasource</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.get_tzkt_datasource" title="Permalink to this definition">¶</a></dt>
<dd><p>Get <cite>tzkt</cite> datasource by name</p>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.reindex">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">reindex</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">reason</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">Union</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">ReindexingReason</span><span class="p"><span class="pre">]</span></span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">**</span></span><span class="n"><span class="pre">context</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.reindex" title="Permalink to this definition">¶</a></dt>
<dd><p>Drops the entire database and starts the indexing process from scratch.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>reason</strong> – Reason for reindexing in free-form string</p></li>
<li><p><strong>context</strong> – Additional information to include in exception message</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.restart">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">restart</span></span><span class="sig-paren">(</span><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.restart" title="Permalink to this definition">¶</a></dt>
<dd><p>Restart process and continue indexing.</p>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.update_contract_metadata">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">update_contract_metadata</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">network</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">address</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">metadata</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Dict</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">Any</span><span class="p"><span class="pre">]</span></span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.update_contract_metadata" title="Permalink to this definition">¶</a></dt>
<dd><p>Inserts or updates corresponding rows in the internal <cite>dipdup_contract_metadata</cite> table
to provide a generic metadata interface (see docs).</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>network</strong> – Network name (e.g. <cite>mainnet</cite>)</p></li>
<li><p><strong>address</strong> – Contract address</p></li>
<li><p><strong>metadata</strong> – Contract metadata to insert/update</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.update_token_metadata">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">update_token_metadata</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">network</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">address</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">token_id</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">metadata</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Dict</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">Any</span><span class="p"><span class="pre">]</span></span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.update_token_metadata" title="Permalink to this definition">¶</a></dt>
<dd><p>Inserts or updates corresponding rows in the internal <cite>dipdup_token_metadata</cite> table
to provide a generic metadata interface (see docs).</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>network</strong> – Network name (e.g. <cite>mainnet</cite>)</p></li>
<li><p><strong>address</strong> – Contract address</p></li>
<li><p><strong>token_id</strong> – Token ID</p></li>
<li><p><strong>metadata</strong> – Token metadata to insert/update</p></li>
</ul>
</dd>
</dl>
</dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.context.HandlerContext">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.context.</span></span><span class="sig-name descname"><span class="pre">HandlerContext</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">datasources</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Dict</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">Datasource</span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">config</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><a class="reference internal" href="config-reference.html#dipdup.config.DipDupConfig" title="dipdup.config.DipDupConfig"><span class="pre">DipDupConfig</span></a></span></em>, <em class="sig-param"><span class="n"><span class="pre">callbacks</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">CallbackManager</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">transactions</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">TransactionManager</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">logger</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">FormattedLogger</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">handler_config</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><a class="reference internal" href="config-reference.html#dipdup.config.HandlerConfig" title="dipdup.config.HandlerConfig"><span class="pre">HandlerConfig</span></a></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasource</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">TzktDatasource</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.HandlerContext" title="Permalink to this definition">¶</a></dt>
<dd><p>Execution context of handler callbacks.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>handler_config</strong> – Configuration of current handler</p></li>
<li><p><strong>datasource</strong> – Index datasource instance</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.context.HookContext">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.context.</span></span><span class="sig-name descname"><span class="pre">HookContext</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">datasources</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Dict</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">Datasource</span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">config</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><a class="reference internal" href="config-reference.html#dipdup.config.DipDupConfig" title="dipdup.config.DipDupConfig"><span class="pre">DipDupConfig</span></a></span></em>, <em class="sig-param"><span class="n"><span class="pre">callbacks</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">CallbackManager</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">transactions</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">TransactionManager</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">logger</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">FormattedLogger</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">hook_config</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><a class="reference internal" href="config-reference.html#dipdup.config.HookConfig" title="dipdup.config.HookConfig"><span class="pre">HookConfig</span></a></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.HookContext" title="Permalink to this definition">¶</a></dt>
<dd><p>Execution context of hook callbacks.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><p><strong>hook_config</strong> – Configuration of current hook</p>
</dd>
</dl>
<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.HookContext.rollback">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">rollback</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">index</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">from_level</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">int</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">to_level</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">int</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.HookContext.rollback" title="Permalink to this definition">¶</a></dt>
<dd><p>Rollback index to a given level reverting all changes made since that level.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>index</strong> – Index name</p></li>
<li><p><strong>from_level</strong> – Level to rollback from</p></li>
<li><p><strong>to_level</strong> – Level to rollback to</p></li>
</ul>
</dd>
</dl>
</dd></dl>

</dd></dl>
