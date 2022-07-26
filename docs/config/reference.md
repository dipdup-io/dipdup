
  <span class="target" id="module-dipdup.config"></span><dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.AdvancedConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">AdvancedConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">reindex:</span> <span class="pre">~typing.Dict[~dipdup.enums.ReindexingReason</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.enums.ReindexingAction]</span> <span class="pre">=</span> <span class="pre">&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">scheduler:</span> <span class="pre">~typing.Optional[~typing.Dict[str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~typing.Any]]</span> <span class="pre">=</span> <span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">postpone_jobs:</span> <span class="pre">bool</span> <span class="pre">=</span> <span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">early_realtime:</span> <span class="pre">bool</span> <span class="pre">=</span> <span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">merge_subscriptions:</span> <span class="pre">bool</span> <span class="pre">=</span> <span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">metadata_interface:</span> <span class="pre">bool</span> <span class="pre">=</span> <span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">skip_version_check:</span> <span class="pre">bool</span> <span class="pre">=</span> <span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">rollback_depth:</span> <span class="pre">int</span> <span class="pre">=</span> <span class="pre">2</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">crash_reporting:</span> <span class="pre">bool</span> <span class="pre">=</span> <span class="pre">False</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.AdvancedConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Feature flags and other advanced config.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>reindex</strong> – Mapping of reindexing reasons and actions DipDup performs</p></li>
<li><p><strong>scheduler</strong> – <cite>apscheduler</cite> scheduler config</p></li>
<li><p><strong>postpone_jobs</strong> – Do not start job scheduler until all indexes are in realtime state</p></li>
<li><p><strong>early_realtime</strong> – Establish realtime connection immediately after startup</p></li>
<li><p><strong>merge_subscriptions</strong> – Subscribe to all operations instead of exact channels</p></li>
<li><p><strong>metadata_interface</strong> – Expose metadata interface for TzKT</p></li>
<li><p><strong>skip_version_check</strong> – Do not check for new DipDup versions on startup</p></li>
<li><p><strong>rollback_depth</strong> – A number of levels to keep for rollback</p></li>
<li><p><strong>crash_reporting</strong> – Enable crash reporting</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.BigMapHandlerConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">BigMapHandlerConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">contract</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Union</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><a class="reference internal" href="#dipdup.config.ContractConfig" title="dipdup.config.ContractConfig"><span class="pre">ContractConfig</span></a><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">path</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.BigMapHandlerConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Big map handler config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>contract</strong> – Contract to fetch big map from</p></li>
<li><p><strong>path</strong> – Path to big map (alphanumeric string with dots)</p></li>
</ul>
</dd>
</dl>
<dl class="py method">
<dt class="sig sig-object py" id="dipdup.config.BigMapHandlerConfig.initialize_big_map_type">
<span class="sig-name descname"><span class="pre">initialize_big_map_type</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">package</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">None</span></span></span><a class="headerlink" href="#dipdup.config.BigMapHandlerConfig.initialize_big_map_type" title="Permalink to this definition">¶</a></dt>
<dd><p>Resolve imports and initialize key and value type classes</p>
</dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.BigMapIndexConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">BigMapIndexConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Literal</span><span class="p"><span class="pre">[</span></span><span class="s"><span class="pre">'big_map'</span></span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasource</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Union</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><a class="reference internal" href="#dipdup.config.TzktDatasourceConfig" title="dipdup.config.TzktDatasourceConfig"><span class="pre">TzktDatasourceConfig</span></a><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">handlers</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Tuple</span><span class="p"><span class="pre">[</span></span><a class="reference internal" href="#dipdup.config.BigMapHandlerConfig" title="dipdup.config.BigMapHandlerConfig"><span class="pre">BigMapHandlerConfig</span></a><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="p"><span class="pre">...</span></span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">skip_history</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">SkipHistory</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">SkipHistory.never</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">first_level</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">int</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">0</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">last_level</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">int</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">0</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.BigMapIndexConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Big map index config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> – always <cite>big_map</cite></p></li>
<li><p><strong>datasource</strong> – Index datasource to fetch big maps with</p></li>
<li><p><strong>handlers</strong> – Description of big map diff handlers</p></li>
<li><p><strong>skip_history</strong> – Fetch only current big map keys ignoring historical changes</p></li>
<li><p><strong>first_level</strong> – Level to start indexing from</p></li>
<li><p><strong>last_level</strong> – Level to stop indexing at (Dipdup will terminate at this level)</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.CallbackMixin">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">CallbackMixin</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.CallbackMixin" title="Permalink to this definition">¶</a></dt>
<dd><p>Mixin for callback configs</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><p><strong>callback</strong> – Callback name</p>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.CodegenMixin">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">CodegenMixin</span></span><a class="headerlink" href="#dipdup.config.CodegenMixin" title="Permalink to this definition">¶</a></dt>
<dd><p>Base for pattern config classes containing methods required for codegen</p>
<dl class="py method">
<dt class="sig sig-object py" id="dipdup.config.CodegenMixin.locate_arguments">
<span class="sig-name descname"><span class="pre">locate_arguments</span></span><span class="sig-paren">(</span><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">Dict</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">Type</span><span class="p"><span class="pre">]</span></span><span class="p"><span class="pre">]</span></span></span></span><a class="headerlink" href="#dipdup.config.CodegenMixin.locate_arguments" title="Permalink to this definition">¶</a></dt>
<dd><p>Try to resolve scope annotations for arguments</p>
</dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.CoinbaseDatasourceConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">CoinbaseDatasourceConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Literal</span><span class="p"><span class="pre">[</span></span><span class="s"><span class="pre">'coinbase'</span></span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">api_key</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">secret_key</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">passphrase</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">http</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><a class="reference internal" href="#dipdup.config.HTTPConfig" title="dipdup.config.HTTPConfig"><span class="pre">HTTPConfig</span></a><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.CoinbaseDatasourceConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Coinbase datasource config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> – always ‘coinbase’</p></li>
<li><p><strong>api_key</strong> – API key</p></li>
<li><p><strong>secret_key</strong> – API secret key</p></li>
<li><p><strong>passphrase</strong> – API passphrase</p></li>
<li><p><strong>http</strong> – HTTP client configuration</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.ContractConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">ContractConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">address</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">typename</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.ContractConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Contract config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>address</strong> – Contract address</p></li>
<li><p><strong>typename</strong> – User-defined alias for the contract script</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.DipDupConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">DipDupConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">spec_version:</span> <span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">package:</span> <span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasources:</span> <span class="pre">~typing.Dict[str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~typing.Union[~dipdup.config.TzktDatasourceConfig</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.CoinbaseDatasourceConfig</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.MetadataDatasourceConfig</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.IpfsDatasourceConfig</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.HttpDatasourceConfig]]</span> <span class="pre">=</span> <span class="pre">&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">database:</span> <span class="pre">~typing.Union[~dipdup.config.SqliteDatabaseConfig</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.PostgresDatabaseConfig]</span> <span class="pre">=</span> <span class="pre">SqliteDatabaseConfig(kind='sqlite'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">path=':memory:')</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">contracts:</span> <span class="pre">~typing.Dict[str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.ContractConfig]</span> <span class="pre">=</span> <span class="pre">&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">indexes:</span> <span class="pre">~typing.Dict[str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~typing.Union[~dipdup.config.OperationIndexConfig</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.BigMapIndexConfig</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.HeadIndexConfig</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.TokenTransferIndexConfig</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.IndexTemplateConfig]]</span> <span class="pre">=</span> <span class="pre">&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">templates:</span> <span class="pre">~typing.Dict[str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~typing.Union[~dipdup.config.OperationIndexConfig</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.BigMapIndexConfig</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.HeadIndexConfig</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.TokenTransferIndexConfig]]</span> <span class="pre">=</span> <span class="pre">&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">jobs:</span> <span class="pre">~typing.Dict[str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.JobConfig]</span> <span class="pre">=</span> <span class="pre">&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">hooks:</span> <span class="pre">~typing.Dict[str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~dipdup.config.HookConfig]</span> <span class="pre">=</span> <span class="pre">&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">hasura:</span> <span class="pre">~typing.Optional[~dipdup.config.HasuraConfig]</span> <span class="pre">=</span> <span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">sentry:</span> <span class="pre">~typing.Optional[~dipdup.config.SentryConfig]</span> <span class="pre">=</span> <span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">prometheus:</span> <span class="pre">~typing.Optional[~dipdup.config.PrometheusConfig]</span> <span class="pre">=</span> <span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">advanced:</span> <span class="pre">~dipdup.config.AdvancedConfig</span> <span class="pre">=</span> <span class="pre">AdvancedConfig(reindex={}</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">scheduler=None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">postpone_jobs=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">early_realtime=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">merge_subscriptions=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">metadata_interface=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">skip_version_check=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">rollback_depth=2</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">crash_reporting=False)</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">custom:</span> <span class="pre">~typing.Dict[str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">~typing.Any]</span> <span class="pre">=</span> <span class="pre">&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">logging:</span> <span class="pre">~dipdup.enums.LoggingValues</span> <span class="pre">=</span> <span class="pre">LoggingValues.default</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.DipDupConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Main indexer config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>spec_version</strong> – Version of specification</p></li>
<li><p><strong>package</strong> – Name of indexer’s Python package, existing or not</p></li>
<li><p><strong>datasources</strong> – Mapping of datasource aliases and datasource configs</p></li>
<li><p><strong>database</strong> – Database config</p></li>
<li><p><strong>contracts</strong> – Mapping of contract aliases and contract configs</p></li>
<li><p><strong>indexes</strong> – Mapping of index aliases and index configs</p></li>
<li><p><strong>templates</strong> – Mapping of template aliases and index templates</p></li>
<li><p><strong>jobs</strong> – Mapping of job aliases and job configs</p></li>
<li><p><strong>hooks</strong> – Mapping of hook aliases and hook configs</p></li>
<li><p><strong>hasura</strong> – Hasura integration config</p></li>
<li><p><strong>sentry</strong> – Sentry integration config</p></li>
<li><p><strong>prometheus</strong> – Prometheus integration config</p></li>
<li><p><strong>advanced</strong> – Advanced config</p></li>
<li><p><strong>custom</strong> – User-defined Custom config</p></li>
</ul>
</dd>
</dl>
<dl class="py property">
<dt class="sig sig-object py" id="dipdup.config.DipDupConfig.oneshot">
<em class="property"><span class="pre">property</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">oneshot</span></span><em class="property"><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="pre">bool</span></em><a class="headerlink" href="#dipdup.config.DipDupConfig.oneshot" title="Permalink to this definition">¶</a></dt>
<dd><p>Whether all indexes have <cite>last_level</cite> field set</p>
</dd></dl>

<dl class="py property">
<dt class="sig sig-object py" id="dipdup.config.DipDupConfig.package_path">
<em class="property"><span class="pre">property</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">package_path</span></span><em class="property"><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="pre">str</span></em><a class="headerlink" href="#dipdup.config.DipDupConfig.package_path" title="Permalink to this definition">¶</a></dt>
<dd><p>Absolute path to the indexer package, existing or default</p>
</dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.HTTPConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">HTTPConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">cache</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">bool</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">retry_count</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">int</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">retry_sleep</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">float</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">retry_multiplier</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">float</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">ratelimit_rate</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">int</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">ratelimit_period</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">int</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">connection_limit</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">int</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">connection_timeout</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">int</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">batch_size</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">int</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.HTTPConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Advanced configuration of HTTP client</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>cache</strong> – Whether to cache responses</p></li>
<li><p><strong>retry_count</strong> – Number of retries after request failed before giving up</p></li>
<li><p><strong>retry_sleep</strong> – Sleep time between retries</p></li>
<li><p><strong>retry_multiplier</strong> – Multiplier for sleep time between retries</p></li>
<li><p><strong>ratelimit_rate</strong> – Number of requests per period (“drops” in leaky bucket)</p></li>
<li><p><strong>ratelimit_period</strong> – Time period for rate limiting in seconds</p></li>
<li><p><strong>connection_limit</strong> – Number of simultaneous connections</p></li>
<li><p><strong>connection_timeout</strong> – Connection timeout in seconds</p></li>
<li><p><strong>batch_size</strong> – Number of items fetched in a single paginated request (for some APIs)</p></li>
</ul>
</dd>
</dl>
<dl class="py method">
<dt class="sig sig-object py" id="dipdup.config.HTTPConfig.merge">
<span class="sig-name descname"><span class="pre">merge</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">other</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><a class="reference internal" href="#dipdup.config.HTTPConfig" title="dipdup.config.HTTPConfig"><span class="pre">HTTPConfig</span></a><span class="p"><span class="pre">]</span></span></span></em><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><a class="reference internal" href="#dipdup.config.HTTPConfig" title="dipdup.config.HTTPConfig"><span class="pre">HTTPConfig</span></a></span></span><a class="headerlink" href="#dipdup.config.HTTPConfig.merge" title="Permalink to this definition">¶</a></dt>
<dd><p>Set missing values from other config</p>
</dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.HandlerConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">HandlerConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.HandlerConfig" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.HasuraConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">HasuraConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">url</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">admin_secret</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">create_source</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">bool</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">source</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">'default'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">select_limit</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">int</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">100</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">allow_aggregations</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">bool</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">True</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">camel_case</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">bool</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">rest</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">bool</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">True</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">http</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><a class="reference internal" href="#dipdup.config.HTTPConfig" title="dipdup.config.HTTPConfig"><span class="pre">HTTPConfig</span></a><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.HasuraConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Config for the Hasura integration.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>url</strong> – URL of the Hasura instance.</p></li>
<li><p><strong>admin_secret</strong> – Admin secret of the Hasura instance.</p></li>
<li><p><strong>create_source</strong> – Whether source should be added to Hasura if missing.</p></li>
<li><p><strong>source</strong> – Hasura source for DipDup to configure, others will be left untouched.</p></li>
<li><p><strong>select_limit</strong> – Row limit for unauthenticated queries.</p></li>
<li><p><strong>allow_aggregations</strong> – Whether to allow aggregations in unauthenticated queries.</p></li>
<li><p><strong>camel_case</strong> – Whether to use camelCase instead of default pascal_case for the field names (incompatible with <cite>metadata_interface</cite> flag)</p></li>
<li><p><strong>rest</strong> – Enable REST API both for autogenerated and custom queries.</p></li>
<li><p><strong>http</strong> – HTTP connection tunables</p></li>
</ul>
</dd>
</dl>
<dl class="py property">
<dt class="sig sig-object py" id="dipdup.config.HasuraConfig.headers">
<em class="property"><span class="pre">property</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">headers</span></span><em class="property"><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="pre">Dict</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></em><a class="headerlink" href="#dipdup.config.HasuraConfig.headers" title="Permalink to this definition">¶</a></dt>
<dd><p>Headers to include with every request</p>
</dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.HeadHandlerConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">HeadHandlerConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.HeadHandlerConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Head block handler config</p>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.HeadIndexConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">HeadIndexConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Literal</span><span class="p"><span class="pre">[</span></span><span class="s"><span class="pre">'head'</span></span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasource</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Union</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><a class="reference internal" href="#dipdup.config.TzktDatasourceConfig" title="dipdup.config.TzktDatasourceConfig"><span class="pre">TzktDatasourceConfig</span></a><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">handlers</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Tuple</span><span class="p"><span class="pre">[</span></span><a class="reference internal" href="#dipdup.config.HeadHandlerConfig" title="dipdup.config.HeadHandlerConfig"><span class="pre">HeadHandlerConfig</span></a><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="p"><span class="pre">...</span></span><span class="p"><span class="pre">]</span></span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.HeadIndexConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Head block index config</p>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.HookConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">HookConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback:</span> <span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">args:</span> <span class="pre">~typing.Dict[str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">str]</span> <span class="pre">=</span> <span class="pre">&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">atomic:</span> <span class="pre">bool</span> <span class="pre">=</span> <span class="pre">False</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.HookConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Hook config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>args</strong> – Mapping of argument names and annotations (checked lazily when possible)</p></li>
<li><p><strong>atomic</strong> – Wrap hook in a single database transaction</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.HttpDatasourceConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">HttpDatasourceConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Literal</span><span class="p"><span class="pre">[</span></span><span class="s"><span class="pre">'http'</span></span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">url</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">http</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><a class="reference internal" href="#dipdup.config.HTTPConfig" title="dipdup.config.HTTPConfig"><span class="pre">HTTPConfig</span></a><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.HttpDatasourceConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Generic HTTP datasource config</p>
<p>kind: always ‘http’
url: URL to fetch data from
http: HTTP client configuration</p>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.IndexConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">IndexConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasource</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Union</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><a class="reference internal" href="#dipdup.config.TzktDatasourceConfig" title="dipdup.config.TzktDatasourceConfig"><span class="pre">TzktDatasourceConfig</span></a><span class="p"><span class="pre">]</span></span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.IndexConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Index config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><p><strong>datasource</strong> – Alias of index datasource in <cite>datasources</cite> section</p>
</dd>
</dl>
<dl class="py method">
<dt class="sig sig-object py" id="dipdup.config.IndexConfig.hash">
<span class="sig-name descname"><span class="pre">hash</span></span><span class="sig-paren">(</span><span class="sig-paren">)</span> <span class="sig-return"><span class="sig-return-icon">&#x2192;</span> <span class="sig-return-typehint"><span class="pre">str</span></span></span><a class="headerlink" href="#dipdup.config.IndexConfig.hash" title="Permalink to this definition">¶</a></dt>
<dd><p>Calculate hash to ensure config has not changed since last run.</p>
</dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.IndexTemplateConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">IndexTemplateConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">template</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">values</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Dict</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">first_level</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">int</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">0</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">last_level</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">int</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">0</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.IndexTemplateConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Index template config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> – always <cite>template</cite></p></li>
<li><p><strong>name</strong> – Name of index template</p></li>
<li><p><strong>template_values</strong> – Values to be substituted in template (<cite>&lt;key&gt;</cite> -&gt; <cite>value</cite>)</p></li>
<li><p><strong>first_level</strong> – Level to start indexing from</p></li>
<li><p><strong>last_level</strong> – Level to stop indexing at (DipDup will terminate at this level)</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.IpfsDatasourceConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">IpfsDatasourceConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Literal</span><span class="p"><span class="pre">[</span></span><span class="s"><span class="pre">'ipfs'</span></span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">url</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">'https://ipfs.io/ipfs'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">http</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><a class="reference internal" href="#dipdup.config.HTTPConfig" title="dipdup.config.HTTPConfig"><span class="pre">HTTPConfig</span></a><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.IpfsDatasourceConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>IPFS datasource config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> – always ‘ipfs’</p></li>
<li><p><strong>url</strong> – IPFS node URL, e.g. <a class="reference external" href="https://ipfs.io/ipfs/">https://ipfs.io/ipfs/</a></p></li>
<li><p><strong>http</strong> – HTTP client configuration</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.JobConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">JobConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="pre">hook:</span> <span class="pre">~typing.Union[str,</span> <span class="pre">~dipdup.config.HookConfig],</span> <span class="pre">crontab:</span> <span class="pre">~typing.Optional[str]</span> <span class="pre">=</span> <span class="pre">None,</span> <span class="pre">interval:</span> <span class="pre">~typing.Optional[int]</span> <span class="pre">=</span> <span class="pre">None,</span> <span class="pre">daemon:</span> <span class="pre">bool</span> <span class="pre">=</span> <span class="pre">False,</span> <span class="pre">args:</span> <span class="pre">~typing.Dict[str,</span> <span class="pre">~typing.Any]</span> <span class="pre">=</span> <span class="pre">&lt;factory&gt;</span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.JobConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Job schedule config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>hook</strong> – Name of hook to run</p></li>
<li><p><strong>crontab</strong> – Schedule with crontab syntax (<cite>** ** *</cite>)</p></li>
<li><p><strong>interval</strong> – Schedule with interval in seconds</p></li>
<li><p><strong>daemon</strong> – Run hook as a daemon (never stops)</p></li>
<li><p><strong>args</strong> – Arguments to pass to the hook</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.LoggingConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">LoggingConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">config</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Dict</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="pre">Any</span><span class="p"><span class="pre">]</span></span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.LoggingConfig" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.MetadataDatasourceConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">MetadataDatasourceConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Literal</span><span class="p"><span class="pre">[</span></span><span class="s"><span class="pre">'metadata'</span></span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">network</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">MetadataNetwork</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">url</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">'https://metadata.dipdup.net'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">http</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><a class="reference internal" href="#dipdup.config.HTTPConfig" title="dipdup.config.HTTPConfig"><span class="pre">HTTPConfig</span></a><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.MetadataDatasourceConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>DipDup Metadata datasource config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> – always ‘metadata’</p></li>
<li><p><strong>network</strong> – Network name, e.g. mainnet, hangzhounet, etc.</p></li>
<li><p><strong>url</strong> – GraphQL API URL, e.g. <a class="reference external" href="https://metadata.dipdup.net">https://metadata.dipdup.net</a></p></li>
<li><p><strong>http</strong> – HTTP client configuration</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.NameMixin">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">NameMixin</span></span><a class="headerlink" href="#dipdup.config.NameMixin" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.OperationHandlerConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">OperationHandlerConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">pattern</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Tuple</span><span class="p"><span class="pre">[</span></span><span class="pre">Union</span><span class="p"><span class="pre">[</span></span><a class="reference internal" href="#dipdup.config.OperationHandlerOriginationPatternConfig" title="dipdup.config.OperationHandlerOriginationPatternConfig"><span class="pre">OperationHandlerOriginationPatternConfig</span></a><span class="p"><span class="pre">,</span></span><span class="w"> </span><a class="reference internal" href="#dipdup.config.OperationHandlerTransactionPatternConfig" title="dipdup.config.OperationHandlerTransactionPatternConfig"><span class="pre">OperationHandlerTransactionPatternConfig</span></a><span class="p"><span class="pre">]</span></span><span class="p"><span class="pre">,</span></span><span class="w"> </span><span class="p"><span class="pre">...</span></span><span class="p"><span class="pre">]</span></span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.OperationHandlerConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Operation handler config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>callback</strong> – Name of method in <cite>handlers</cite> package</p></li>
<li><p><strong>pattern</strong> – Filters to match operation groups</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.OperationHandlerOriginationPatternConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">OperationHandlerOriginationPatternConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">type</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Literal</span><span class="p"><span class="pre">[</span></span><span class="s"><span class="pre">'origination'</span></span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">'origination'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">source</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">Union</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><a class="reference internal" href="#dipdup.config.ContractConfig" title="dipdup.config.ContractConfig"><span class="pre">ContractConfig</span></a><span class="p"><span class="pre">]</span></span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">similar_to</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">Union</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><a class="reference internal" href="#dipdup.config.ContractConfig" title="dipdup.config.ContractConfig"><span class="pre">ContractConfig</span></a><span class="p"><span class="pre">]</span></span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">originated_contract</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">Union</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><a class="reference internal" href="#dipdup.config.ContractConfig" title="dipdup.config.ContractConfig"><span class="pre">ContractConfig</span></a><span class="p"><span class="pre">]</span></span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">optional</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">bool</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">strict</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">bool</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">False</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.OperationHandlerOriginationPatternConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Origination handler pattern config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>type</strong> – always ‘origination’</p></li>
<li><p><strong>source</strong> – Match operations by source contract alias</p></li>
<li><p><strong>similar_to</strong> – Match operations which have the same code/signature (depending on <cite>strict</cite> field)</p></li>
<li><p><strong>originated_contract</strong> – Match origination of exact contract</p></li>
<li><p><strong>optional</strong> – Whether can operation be missing in operation group</p></li>
<li><p><strong>strict</strong> – Match operations by storage only or by the whole code</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.OperationHandlerTransactionPatternConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">OperationHandlerTransactionPatternConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">type</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Literal</span><span class="p"><span class="pre">[</span></span><span class="s"><span class="pre">'transaction'</span></span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">'transaction'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">source</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">Union</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><a class="reference internal" href="#dipdup.config.ContractConfig" title="dipdup.config.ContractConfig"><span class="pre">ContractConfig</span></a><span class="p"><span class="pre">]</span></span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">destination</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">Union</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">,</span></span><span class="w"> </span><a class="reference internal" href="#dipdup.config.ContractConfig" title="dipdup.config.ContractConfig"><span class="pre">ContractConfig</span></a><span class="p"><span class="pre">]</span></span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">entrypoint</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">optional</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">bool</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">False</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.OperationHandlerTransactionPatternConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Operation handler pattern config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>type</strong> – always ‘transaction’</p></li>
<li><p><strong>source</strong> – Match operations by source contract alias</p></li>
<li><p><strong>destination</strong> – Match operations by destination contract alias</p></li>
<li><p><strong>entrypoint</strong> – Match operations by contract entrypoint</p></li>
<li><p><strong>optional</strong> – Whether can operation be missing in operation group</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.OperationIndexConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">OperationIndexConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="pre">kind:</span> <span class="pre">~typing.Literal['operation'],</span> <span class="pre">datasource:</span> <span class="pre">~typing.Union[str,</span> <span class="pre">~dipdup.config.TzktDatasourceConfig],</span> <span class="pre">handlers:</span> <span class="pre">~typing.Tuple[~dipdup.config.OperationHandlerConfig,</span> <span class="pre">...],</span> <span class="pre">types:</span> <span class="pre">~typing.Tuple[~dipdup.enums.OperationType,</span> <span class="pre">...]</span> <span class="pre">=</span> <span class="pre">(&lt;OperationType.transaction:</span> <span class="pre">'transaction'&gt;,),</span> <span class="pre">contracts:</span> <span class="pre">~typing.List[~typing.Union[str,</span> <span class="pre">~dipdup.config.ContractConfig]]</span> <span class="pre">=</span> <span class="pre">&lt;factory&gt;,</span> <span class="pre">first_level:</span> <span class="pre">int</span> <span class="pre">=</span> <span class="pre">0,</span> <span class="pre">last_level:</span> <span class="pre">int</span> <span class="pre">=</span> <span class="pre">0</span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.OperationIndexConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Operation index config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> – always <cite>operation</cite></p></li>
<li><p><strong>handlers</strong> – List of indexer handlers</p></li>
<li><p><strong>types</strong> – Types of transaction to fetch</p></li>
<li><p><strong>contracts</strong> – Aliases of contracts being indexed in <cite>contracts</cite> section</p></li>
<li><p><strong>first_level</strong> – Level to start indexing from</p></li>
<li><p><strong>last_level</strong> – Level to stop indexing at (DipDup will terminate at this level)</p></li>
</ul>
</dd>
</dl>
<dl class="py property">
<dt class="sig sig-object py" id="dipdup.config.OperationIndexConfig.address_filter">
<em class="property"><span class="pre">property</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">address_filter</span></span><em class="property"><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="pre">Set</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></em><a class="headerlink" href="#dipdup.config.OperationIndexConfig.address_filter" title="Permalink to this definition">¶</a></dt>
<dd><p>Set of addresses (any field) to filter operations with before an actual matching</p>
</dd></dl>

<dl class="py property">
<dt class="sig sig-object py" id="dipdup.config.OperationIndexConfig.entrypoint_filter">
<em class="property"><span class="pre">property</span><span class="w"> </span></em><span class="sig-name descname"><span class="pre">entrypoint_filter</span></span><em class="property"><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="pre">Set</span><span class="p"><span class="pre">[</span></span><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span><span class="p"><span class="pre">]</span></span></em><a class="headerlink" href="#dipdup.config.OperationIndexConfig.entrypoint_filter" title="Permalink to this definition">¶</a></dt>
<dd><p>Set of entrypoints to filter operations with before an actual matching</p>
</dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.ParameterTypeMixin">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">ParameterTypeMixin</span></span><a class="headerlink" href="#dipdup.config.ParameterTypeMixin" title="Permalink to this definition">¶</a></dt>
<dd><p><cite>parameter_type_cls</cite> field</p>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.ParentMixin">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">ParentMixin</span></span><a class="headerlink" href="#dipdup.config.ParentMixin" title="Permalink to this definition">¶</a></dt>
<dd><p><cite>parent</cite> field for index and template configs</p>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.PatternConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">PatternConfig</span></span><a class="headerlink" href="#dipdup.config.PatternConfig" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.PostgresDatabaseConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">PostgresDatabaseConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="pre">kind:</span> <span class="pre">~typing.Literal['postgres'],</span> <span class="pre">host:</span> <span class="pre">str,</span> <span class="pre">user:</span> <span class="pre">str</span> <span class="pre">=</span> <span class="pre">'postgres',</span> <span class="pre">database:</span> <span class="pre">str</span> <span class="pre">=</span> <span class="pre">'postgres',</span> <span class="pre">port:</span> <span class="pre">int</span> <span class="pre">=</span> <span class="pre">5432,</span> <span class="pre">schema_name:</span> <span class="pre">str</span> <span class="pre">=</span> <span class="pre">'public',</span> <span class="pre">password:</span> <span class="pre">str</span> <span class="pre">=</span> <span class="pre">'',</span> <span class="pre">immune_tables:</span> <span class="pre">~typing.Set[str]</span> <span class="pre">=</span> <span class="pre">&lt;factory&gt;,</span> <span class="pre">connection_timeout:</span> <span class="pre">int</span> <span class="pre">=</span> <span class="pre">60</span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.PostgresDatabaseConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Postgres database connection config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> – always ‘postgres’</p></li>
<li><p><strong>host</strong> – Host</p></li>
<li><p><strong>port</strong> – Port</p></li>
<li><p><strong>user</strong> – User</p></li>
<li><p><strong>password</strong> – Password</p></li>
<li><p><strong>database</strong> – Database name</p></li>
<li><p><strong>schema_name</strong> – Schema name</p></li>
<li><p><strong>immune_tables</strong> – List of tables to preserve during reindexing</p></li>
<li><p><strong>connection_timeout</strong> – Connection timeout</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.PrometheusConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">PrometheusConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">host</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">port</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">int</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">8000</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">update_interval</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">float</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">1.0</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.PrometheusConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Config for Prometheus integration.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>host</strong> – Host to bind to</p></li>
<li><p><strong>port</strong> – Port to bind to</p></li>
<li><p><strong>update_interval</strong> – Interval to update some metrics in seconds</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.SentryConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">SentryConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">dsn</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">environment</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">server_name</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">release</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><span class="pre">str</span><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">debug</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">bool</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">False</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.SentryConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Config for Sentry integration.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>dsn</strong> – DSN of the Sentry instance</p></li>
<li><p><strong>environment</strong> – Environment (defaults to <cite>production</cite>)</p></li>
<li><p><strong>server_name</strong> – Server name (defaults to hostname)</p></li>
<li><p><strong>release</strong> – Release version (defaults to DipDup version)</p></li>
<li><p><strong>debug</strong> – Catch warning messages and more context</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.SqliteDatabaseConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">SqliteDatabaseConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Literal</span><span class="p"><span class="pre">[</span></span><span class="s"><span class="pre">'sqlite'</span></span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">path</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">':memory:'</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.SqliteDatabaseConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>SQLite connection config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> – always ‘sqlite’</p></li>
<li><p><strong>path</strong> – Path to .sqlite3 file, leave default for in-memory database (<cite>:memory:</cite>)</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.StorageTypeMixin">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">StorageTypeMixin</span></span><a class="headerlink" href="#dipdup.config.StorageTypeMixin" title="Permalink to this definition">¶</a></dt>
<dd><p><cite>storage_type_cls</cite> field</p>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.SubscriptionsMixin">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">SubscriptionsMixin</span></span><a class="headerlink" href="#dipdup.config.SubscriptionsMixin" title="Permalink to this definition">¶</a></dt>
<dd><p><cite>subscriptions</cite> field</p>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.TemplateValuesMixin">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">TemplateValuesMixin</span></span><a class="headerlink" href="#dipdup.config.TemplateValuesMixin" title="Permalink to this definition">¶</a></dt>
<dd><p><cite>template_values</cite> field</p>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.TokenTransferHandlerConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">TokenTransferHandlerConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.TokenTransferHandlerConfig" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.TokenTransferIndexConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">TokenTransferIndexConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="pre">kind:</span> <span class="pre">~typing.Literal['token_transfer'],</span> <span class="pre">datasource:</span> <span class="pre">~typing.Union[str,</span> <span class="pre">~dipdup.config.TzktDatasourceConfig],</span> <span class="pre">handlers:</span> <span class="pre">~typing.Tuple[~dipdup.config.TokenTransferHandlerConfig,</span> <span class="pre">...]</span> <span class="pre">=</span> <span class="pre">&lt;factory&gt;,</span> <span class="pre">first_level:</span> <span class="pre">int</span> <span class="pre">=</span> <span class="pre">0,</span> <span class="pre">last_level:</span> <span class="pre">int</span> <span class="pre">=</span> <span class="pre">0</span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.TokenTransferIndexConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Token index config</p>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.TransactionIdxMixin">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">TransactionIdxMixin</span></span><a class="headerlink" href="#dipdup.config.TransactionIdxMixin" title="Permalink to this definition">¶</a></dt>
<dd><p><cite>transaction_idx</cite> field to track index of operation in group</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><p><strong>transaction_idx</strong> – </p>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.config.TzktDatasourceConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.config.</span></span><span class="sig-name descname"><span class="pre">TzktDatasourceConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Literal</span><span class="p"><span class="pre">[</span></span><span class="s"><span class="pre">'tzkt'</span></span><span class="p"><span class="pre">]</span></span></span></em>, <em class="sig-param"><span class="n"><span class="pre">url</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">str</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">http</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">Optional</span><span class="p"><span class="pre">[</span></span><a class="reference internal" href="#dipdup.config.HTTPConfig" title="dipdup.config.HTTPConfig"><span class="pre">HTTPConfig</span></a><span class="p"><span class="pre">]</span></span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">buffer_size</span></span><span class="p"><span class="pre">:</span></span><span class="w"> </span><span class="n"><span class="pre">int</span></span><span class="w"> </span><span class="o"><span class="pre">=</span></span><span class="w"> </span><span class="default_value"><span class="pre">0</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.config.TzktDatasourceConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>TzKT datasource config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> – always ‘tzkt’</p></li>
<li><p><strong>url</strong> – Base API URL, e.g. <a class="reference external" href="https://api.tzkt.io/">https://api.tzkt.io/</a></p></li>
<li><p><strong>http</strong> – HTTP client configuration</p></li>
<li><p><strong>buffer_size</strong> – Number of levels to keep in FIFO buffer before processing</p></li>
</ul>
</dd>
</dl>
</dd></dl>
