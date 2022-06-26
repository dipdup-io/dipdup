
  <span class="target" id="module-dipdup.context"></span><dl class="py class">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.context.</span></span><span class="sig-name descname"><span class="pre">DipDupContext</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">datasources</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Dict</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">dipdup.datasources.datasource.Datasource</span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">config</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><a class="reference internal" href="config-reference.html#dipdup.config.DipDupConfig" title="dipdup.config.DipDupConfig"><span class="pre">dipdup.config.DipDupConfig</span></a></span></em>, <em class="sig-param"><span class="n"><span class="pre">callbacks</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">dipdup.context.CallbackManager</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.DipDupContext" title="Permalink to this definition">¶</a></dt>
<dd><p>Class to store application context</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters</dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>datasources</strong> – Mapping of available datasources</p></li>
<li><p><strong>config</strong> – DipDup configuration</p></li>
<li><p><strong>callbacks</strong> – Low-level callback interface (intented for internal use)</p></li>
<li><p><strong>logger</strong> – Context-aware logger instance</p></li>
</ul>
</dd>
</dl>
<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.execute_sql">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">execute_sql</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">*</span></span><span class="n"><span class="pre">args</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Any</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">**</span></span><span class="n"><span class="pre">kwargs</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.execute_sql" title="Permalink to this definition">¶</a></dt>
<dd><p>Execute SQL script with given name</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters</dt>
<dd class="field-odd"><p><strong>name</strong> – SQL script or directory name within <cite>&lt;project&gt;/sql</cite> directory</p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.execute_sql_query">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">execute_sql_query</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">*</span></span><span class="n"><span class="pre">args</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Any</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">Any</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.execute_sql_query" title="Permalink to this definition">¶</a></dt>
<dd><p>Execute SQL query with given name</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters</dt>
<dd class="field-odd"><p><strong>name</strong> – SQL query name within <cite>&lt;project&gt;/sql</cite> directory</p>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.fire_handler">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">fire_handler</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">index</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasource</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">dipdup.datasources.tzkt.datasource.TzktDatasource</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">fmt</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">*</span></span><span class="n"><span class="pre">args</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">**</span></span><span class="n"><span class="pre">kwargs</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Any</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.fire_handler" title="Permalink to this definition">¶</a></dt>
<dd><p>Fire handler with given name and arguments.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters</dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>name</strong> – Handler name</p></li>
<li><p><strong>index</strong> – Index name</p></li>
<li><p><strong>datasource</strong> – An instance of datasource that triggered the handler</p></li>
<li><p><strong>fmt</strong> – Format string for <cite>ctx.logger</cite> messages</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.fire_hook">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">fire_hook</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">fmt</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">wait</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">bool</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">True</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">*</span></span><span class="n"><span class="pre">args</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">**</span></span><span class="n"><span class="pre">kwargs</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Any</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.fire_hook" title="Permalink to this definition">¶</a></dt>
<dd><p>Fire hook with given name and arguments.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters</dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>name</strong> – Hook name</p></li>
<li><p><strong>fmt</strong> – Format string for <cite>ctx.logger</cite> messages</p></li>
<li><p><strong>wait</strong> – Wait for hook to finish or fire and forget</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.reindex">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">reindex</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">reason</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">Union</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">dipdup.enums.ReindexingReason</span><span class="p"><span class="pre">]</span></span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">**</span></span><span class="n"><span class="pre">context</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.reindex" title="Permalink to this definition">¶</a></dt>
<dd><p>Drop the whole database and restart with the same CLI arguments</p>
</dd></dl>

<dl class="py method">
<dt class="sig sig-object py" id="dipdup.context.DipDupContext.restart">
<em class="property"><span class="pre">async</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">restart</span></span><span class="sig-paren">(</span><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.context.DipDupContext.restart" title="Permalink to this definition">¶</a></dt>
<dd><p>Restart indexer preserving CLI arguments</p>
</dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.context.HandlerContext">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.context.</span></span><span class="sig-name descname"><span class="pre">HandlerContext</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">datasources</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Dict</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">dipdup.datasources.datasource.Datasource</span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">config</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><a class="reference internal" href="config-reference.html#dipdup.config.DipDupConfig" title="dipdup.config.DipDupConfig"><span class="pre">dipdup.config.DipDupConfig</span></a></span></em>, <em class="sig-param"><span class="n"><span class="pre">callbacks</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">dipdup.context.CallbackManager</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">logger</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">dipdup.utils.FormattedLogger</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">handler_config</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><a class="reference internal" href="config-reference.html#dipdup.config.HandlerConfig" title="dipdup.config.HandlerConfig"><span class="pre">dipdup.config.HandlerConfig</span></a></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasource</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">dipdup.datasources.tzkt.datasource.TzktDatasource</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.HandlerContext" title="Permalink to this definition">¶</a></dt>
<dd><p>Common handler context.</p>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.context.HookContext">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.context.</span></span><span class="sig-name descname"><span class="pre">HookContext</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">datasources</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Dict</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">dipdup.datasources.datasource.Datasource</span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">config</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><a class="reference internal" href="config-reference.html#dipdup.config.DipDupConfig" title="dipdup.config.DipDupConfig"><span class="pre">dipdup.config.DipDupConfig</span></a></span></em>, <em class="sig-param"><span class="n"><span class="pre">callbacks</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">dipdup.context.CallbackManager</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">logger</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">dipdup.utils.FormattedLogger</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">hook_config</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><a class="reference internal" href="config-reference.html#dipdup.config.HookConfig" title="dipdup.config.HookConfig"><span class="pre">dipdup.config.HookConfig</span></a></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.HookContext" title="Permalink to this definition">¶</a></dt>
<dd><p>Hook callback context.</p>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.context.TemplateValuesDict">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.context.</span></span><span class="sig-name descname"><span class="pre">TemplateValuesDict</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">ctx</span></span></em>, <em class="sig-param"><span class="o"><span class="pre">**</span></span><span class="n"><span class="pre">kwargs</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.context.TemplateValuesDict" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>
