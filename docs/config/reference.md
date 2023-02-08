<!-- markdownlint-disable first-line-h1 no-space-in-emphasis -->

  <dl class="py class">
<dt class="sig sig-object py" id="DipDupConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">DipDupConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">spec_version</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">package</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasources=&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">database=SqliteDatabaseConfig(kind='sqlite'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">path=':memory:')</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">contracts=&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">indexes=&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">templates=&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">jobs=&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">hooks=&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">hasura=None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">sentry=SentryConfig(dsn=''</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">environment=None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">server_name=None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">release=None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">user_id=None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">debug=False)</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">prometheus=None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">advanced=AdvancedConfig(reindex={}</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">scheduler=None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">postpone_jobs=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">early_realtime=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">merge_subscriptions=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">metadata_interface=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">skip_version_check=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">rollback_depth=2</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">crash_reporting=False)</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">custom=&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">logging=LoggingValues.default</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#DipDupConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Main indexer config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>spec_version</strong> (<em>str</em>) – Version of config specification, currently always <cite>1.2</cite></p></li>
<li><p><strong>package</strong> (<em>str</em>) – Name of indexer’s Python package, existing or not</p></li>
<li><p><strong>datasources</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><a class="reference internal" href="#tezos_tzkt.TzktDatasourceConfig" title="tezos_tzkt.TzktDatasourceConfig"><em>tezos_tzkt.TzktDatasourceConfig</em></a><em> | </em><a class="reference internal" href="#CoinbaseDatasourceConfig" title="coinbase.CoinbaseDatasourceConfig"><em>coinbase.CoinbaseDatasourceConfig</em></a><em> | </em><a class="reference internal" href="#tezos_metadata.TezosMetadataDatasourceConfig" title="tezos_metadata.TezosMetadataDatasourceConfig"><em>tezos_metadata.TezosMetadataDatasourceConfig</em></a><em> | </em><a class="reference internal" href="#ipfs.IpfsDatasourceConfig" title="ipfs.IpfsDatasourceConfig"><em>ipfs.IpfsDatasourceConfig</em></a><em> | </em><a class="reference internal" href="#HttpDatasourceConfig" title="http.HttpDatasourceConfig"><em>http.HttpDatasourceConfig</em></a><em> | </em><em>evm_subsquid.EvmSubsquidDatasourceConfig</em><em>]</em>) – Mapping of datasource aliases and datasource configs</p></li>
<li><p><strong>database</strong> (<a class="reference internal" href="#SqliteDatabaseConfig" title="SqliteDatabaseConfig"><em>SqliteDatabaseConfig</em></a><em> | </em><a class="reference internal" href="#PostgresDatabaseConfig" title="PostgresDatabaseConfig"><em>PostgresDatabaseConfig</em></a>) – Database config</p></li>
<li><p><strong>contracts</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><a class="reference internal" href="#ContractConfig" title="ContractConfig"><em>ContractConfig</em></a><em>]</em>) – Mapping of contract aliases and contract configs</p></li>
<li><p><strong>indexes</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><em>evm_subsquid_events.EvmSubsquidEventsIndexConfig</em><em> | </em><em>evm_subsquid_operations.EvmSubsquidOperationsIndexConfig</em><em> | </em><a class="reference internal" href="#tezos_tzkt_operations.TzktOperationsIndexConfig" title="tezos_tzkt_operations.TzktOperationsIndexConfig"><em>tezos_tzkt_operations.TzktOperationsIndexConfig</em></a><em> | </em><a class="reference internal" href="#tezos_tzkt_big_maps.TzktBigMapsIndexConfig" title="tezos_tzkt_big_maps.TzktBigMapsIndexConfig"><em>tezos_tzkt_big_maps.TzktBigMapsIndexConfig</em></a><em> | </em><a class="reference internal" href="#tezos_tzkt_head.TzktHeadIndexConfig" title="tezos_tzkt_head.TzktHeadIndexConfig"><em>tezos_tzkt_head.TzktHeadIndexConfig</em></a><em> | </em><a class="reference internal" href="#tezos_tzkt_token_transfers.TzktTokenTransfersIndexConfig" title="tezos_tzkt_token_transfers.TzktTokenTransfersIndexConfig"><em>tezos_tzkt_token_transfers.TzktTokenTransfersIndexConfig</em></a><em> | </em><a class="reference internal" href="#tezos_tzkt_events.TzktEventsIndexConfig" title="tezos_tzkt_events.TzktEventsIndexConfig"><em>tezos_tzkt_events.TzktEventsIndexConfig</em></a><em> | </em><a class="reference internal" href="#tezos_tzkt_operations.TzktOperationsUnfilteredIndexConfig" title="tezos_tzkt_operations.TzktOperationsUnfilteredIndexConfig"><em>tezos_tzkt_operations.TzktOperationsUnfilteredIndexConfig</em></a><em> | </em><a class="reference internal" href="#IndexTemplateConfig" title="IndexTemplateConfig"><em>IndexTemplateConfig</em></a><em>]</em>) – Mapping of index aliases and index configs</p></li>
<li><p><strong>templates</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><em>evm_subsquid_events.EvmSubsquidEventsIndexConfig</em><em> | </em><em>evm_subsquid_operations.EvmSubsquidOperationsIndexConfig</em><em> | </em><a class="reference internal" href="#tezos_tzkt_operations.TzktOperationsIndexConfig" title="tezos_tzkt_operations.TzktOperationsIndexConfig"><em>tezos_tzkt_operations.TzktOperationsIndexConfig</em></a><em> | </em><a class="reference internal" href="#tezos_tzkt_big_maps.TzktBigMapsIndexConfig" title="tezos_tzkt_big_maps.TzktBigMapsIndexConfig"><em>tezos_tzkt_big_maps.TzktBigMapsIndexConfig</em></a><em> | </em><a class="reference internal" href="#tezos_tzkt_head.TzktHeadIndexConfig" title="tezos_tzkt_head.TzktHeadIndexConfig"><em>tezos_tzkt_head.TzktHeadIndexConfig</em></a><em> | </em><a class="reference internal" href="#tezos_tzkt_token_transfers.TzktTokenTransfersIndexConfig" title="tezos_tzkt_token_transfers.TzktTokenTransfersIndexConfig"><em>tezos_tzkt_token_transfers.TzktTokenTransfersIndexConfig</em></a><em> | </em><a class="reference internal" href="#tezos_tzkt_events.TzktEventsIndexConfig" title="tezos_tzkt_events.TzktEventsIndexConfig"><em>tezos_tzkt_events.TzktEventsIndexConfig</em></a><em> | </em><a class="reference internal" href="#tezos_tzkt_operations.TzktOperationsUnfilteredIndexConfig" title="tezos_tzkt_operations.TzktOperationsUnfilteredIndexConfig"><em>tezos_tzkt_operations.TzktOperationsUnfilteredIndexConfig</em></a><em>]</em>) – Mapping of template aliases and index templates</p></li>
<li><p><strong>jobs</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><a class="reference internal" href="#JobConfig" title="JobConfig"><em>JobConfig</em></a><em>]</em>) – Mapping of job aliases and job configs</p></li>
<li><p><strong>hooks</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><a class="reference internal" href="#HookConfig" title="HookConfig"><em>HookConfig</em></a><em>]</em>) – Mapping of hook aliases and hook configs</p></li>
<li><p><strong>hasura</strong> (<a class="reference internal" href="#HasuraConfig" title="HasuraConfig"><em>HasuraConfig</em></a><em> | </em><em>None</em>) – Hasura integration config</p></li>
<li><p><strong>sentry</strong> (<a class="reference internal" href="#SentryConfig" title="SentryConfig"><em>SentryConfig</em></a>) – Sentry integration config</p></li>
<li><p><strong>prometheus</strong> (<a class="reference internal" href="#PrometheusConfig" title="PrometheusConfig"><em>PrometheusConfig</em></a><em> | </em><em>None</em>) – Prometheus integration config</p></li>
<li><p><strong>advanced</strong> (<a class="reference internal" href="#AdvancedConfig" title="AdvancedConfig"><em>AdvancedConfig</em></a>) – Advanced config</p></li>
<li><p><strong>custom</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><em>Any</em><em>]</em>) – User-defined configuration to use in callbacks</p></li>
<li><p><strong>logging</strong> (<a class="reference internal" href="#dipdup.models.LoggingValues" title="dipdup.models.LoggingValues"><em>LoggingValues</em></a>) – Modify logging verbosity</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="AdvancedConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">AdvancedConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">reindex=&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">scheduler=None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">postpone_jobs=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">early_realtime=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">merge_subscriptions=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">metadata_interface=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">skip_version_check=False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">rollback_depth=2</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">crash_reporting=False</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#AdvancedConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Feature flags and other advanced config.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>reindex</strong> (<em>dict</em><em>[</em><a class="reference internal" href="#dipdup.models.ReindexingReason" title="dipdup.models.ReindexingReason"><em>dipdup.models.ReindexingReason</em></a><em>, </em><a class="reference internal" href="#dipdup.models.ReindexingAction" title="dipdup.models.ReindexingAction"><em>dipdup.models.ReindexingAction</em></a><em>]</em>) – Mapping of reindexing reasons and actions DipDup performs</p></li>
<li><p><strong>scheduler</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><em>Any</em><em>] </em><em>| </em><em>None</em>) – <cite>apscheduler</cite> scheduler config</p></li>
<li><p><strong>postpone_jobs</strong> (<em>bool</em>) – Do not start job scheduler until all indexes are in realtime state</p></li>
<li><p><strong>early_realtime</strong> (<em>bool</em>) – Establish realtime connection immediately after startup</p></li>
<li><p><strong>merge_subscriptions</strong> (<em>bool</em>) – Subscribe to all operations instead of exact channels</p></li>
<li><p><strong>metadata_interface</strong> (<em>bool</em>) – Expose metadata interface for TzKT</p></li>
<li><p><strong>skip_version_check</strong> (<em>bool</em>) – Do not check for new DipDup versions on startup</p></li>
<li><p><strong>rollback_depth</strong> (<em>int</em>) – A number of levels to keep for rollback</p></li>
<li><p><strong>crash_reporting</strong> (<em>bool</em>) – Enable crash reporting</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_big_maps.TzktBigMapsHandlerConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_big_maps.</span></span><span class="sig-name descname"><span class="pre">TzktBigMapsHandlerConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">contract</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">path</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_big_maps.TzktBigMapsHandlerConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Big map handler config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>callback</strong> (<em>str</em>) – Callback name</p></li>
<li><p><strong>contract</strong> (<em>str</em><em> | </em><a class="reference internal" href="#ContractConfig" title="ContractConfig"><em>ContractConfig</em></a>) – Contract to fetch big map from</p></li>
<li><p><strong>path</strong> (<em>str</em>) – Path to big map (alphanumeric string with dots)</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_big_maps.TzktBigMapsIndexConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_big_maps.</span></span><span class="sig-name descname"><span class="pre">TzktBigMapsIndexConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasource</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">handlers</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">skip_history</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">SkipHistory.never</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">first_level</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">0</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">last_level</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">0</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_big_maps.TzktBigMapsIndexConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Big map index config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'tezos.tzkt.big_maps'</em><em>]</em>) – always <cite>big_map</cite></p></li>
<li><p><strong>datasource</strong> (<em>str</em><em> | </em><a class="reference internal" href="#tezos_tzkt.TzktDatasourceConfig" title="tezos_tzkt.TzktDatasourceConfig"><em>TzktDatasourceConfig</em></a>) – Index datasource to fetch big maps with</p></li>
<li><p><strong>handlers</strong> (<em>tuple</em><em>[</em><a class="reference internal" href="#tezos_tzkt_big_maps.TzktBigMapsHandlerConfig" title="tezos_tzkt_big_maps.TzktBigMapsHandlerConfig"><em>tezos_tzkt_big_maps.TzktBigMapsHandlerConfig</em></a><em>, </em><em>...</em><em>]</em>) – Mapping of big map diff handlers</p></li>
<li><p><strong>skip_history</strong> (<a class="reference internal" href="#dipdup.models.SkipHistory" title="dipdup.models.SkipHistory"><em>SkipHistory</em></a>) – Fetch only current big map keys ignoring historical changes</p></li>
<li><p><strong>first_level</strong> (<em>int</em>) – Level to start indexing from</p></li>
<li><p><strong>last_level</strong> (<em>int</em>) – Level to stop indexing at</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="CoinbaseDatasourceConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">CoinbaseDatasourceConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">api_key</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">secret_key</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">passphrase</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">http</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#CoinbaseDatasourceConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Coinbase datasource config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'coinbase'</em><em>]</em>) – always ‘coinbase’</p></li>
<li><p><strong>api_key</strong> (<em>str</em><em> | </em><em>None</em>) – API key</p></li>
<li><p><strong>secret_key</strong> (<em>str</em><em> | </em><em>None</em>) – API secret key</p></li>
<li><p><strong>passphrase</strong> (<em>str</em><em> | </em><em>None</em>) – API passphrase</p></li>
<li><p><strong>http</strong> (<a class="reference internal" href="#HttpConfig" title="HttpConfig"><em>HttpConfig</em></a><em> | </em><em>None</em>) – HTTP client configuration</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="ContractConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">ContractConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">address</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">code_hash</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">typename</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#ContractConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Contract config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>address</strong> (<em>str</em><em> | </em><em>None</em>) – Contract address</p></li>
<li><p><strong>code_hash</strong> (<em>int</em><em> | </em><em>str</em><em> | </em><em>None</em>) – Contract code hash or address to fetch it from</p></li>
<li><p><strong>typename</strong> (<em>str</em><em> | </em><em>None</em>) – User-defined alias for the contract script</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_events.TzktEventsHandlerConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_events.</span></span><span class="sig-name descname"><span class="pre">TzktEventsHandlerConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">contract</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">tag</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_events.TzktEventsHandlerConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Event handler config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>callback</strong> (<em>str</em>) – Callback name</p></li>
<li><p><strong>contract</strong> (<em>str</em><em> | </em><a class="reference internal" href="#ContractConfig" title="ContractConfig"><em>ContractConfig</em></a>) – Contract which emits event</p></li>
<li><p><strong>tag</strong> (<em>str</em>) – Event tag</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_events.TzktEventsIndexConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_events.</span></span><span class="sig-name descname"><span class="pre">TzktEventsIndexConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasource</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">handlers=&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">first_level=0</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">last_level=0</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_events.TzktEventsIndexConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Event index config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'tezos.tzkt.events'</em><em>]</em>) – Index kind</p></li>
<li><p><strong>datasource</strong> (<em>str</em><em> | </em><a class="reference internal" href="#tezos_tzkt.TzktDatasourceConfig" title="tezos_tzkt.TzktDatasourceConfig"><em>TzktDatasourceConfig</em></a>) – Datasource config</p></li>
<li><p><strong>handlers</strong> (<em>tuple</em><em>[</em><a class="reference internal" href="#tezos_tzkt_events.TzktEventsHandlerConfig" title="tezos_tzkt_events.TzktEventsHandlerConfig"><em>tezos_tzkt_events.TzktEventsHandlerConfig</em></a><em> | </em><a class="reference internal" href="#tezos_tzkt_events.TzktEventsUnknownEventHandlerConfig" title="tezos_tzkt_events.TzktEventsUnknownEventHandlerConfig"><em>tezos_tzkt_events.TzktEventsUnknownEventHandlerConfig</em></a><em>, </em><em>...</em><em>]</em>) – Event handlers</p></li>
<li><p><strong>first_level</strong> (<em>int</em>) – First block level to index</p></li>
<li><p><strong>last_level</strong> (<em>int</em>) – Last block level to index</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="HasuraConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">HasuraConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">url</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">admin_secret</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">create_source</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">source</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">'default'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">select_limit</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">100</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">allow_aggregations</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">True</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">allow_inconsistent_metadata</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">camel_case</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">rest</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">True</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">http</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#HasuraConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Config for the Hasura integration.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>url</strong> (<em>str</em>) – URL of the Hasura instance.</p></li>
<li><p><strong>admin_secret</strong> (<em>str</em><em> | </em><em>None</em>) – Admin secret of the Hasura instance.</p></li>
<li><p><strong>create_source</strong> (<em>bool</em>) – Whether source should be added to Hasura if missing.</p></li>
<li><p><strong>source</strong> (<em>str</em>) – Hasura source for DipDup to configure, others will be left untouched.</p></li>
<li><p><strong>select_limit</strong> (<em>int</em>) – Row limit for unauthenticated queries.</p></li>
<li><p><strong>allow_aggregations</strong> (<em>bool</em>) – Whether to allow aggregations in unauthenticated queries.</p></li>
<li><p><strong>allow_inconsistent_metadata</strong> (<em>bool</em>) – Whether to ignore errors when applying Hasura metadata.</p></li>
<li><p><strong>camel_case</strong> (<em>bool</em>) – Whether to use camelCase instead of default pascal_case for the field names (incompatible with <cite>metadata_interface</cite> flag)</p></li>
<li><p><strong>rest</strong> (<em>bool</em>) – Enable REST API both for autogenerated and custom queries.</p></li>
<li><p><strong>http</strong> (<a class="reference internal" href="#HttpConfig" title="HttpConfig"><em>HttpConfig</em></a><em> | </em><em>None</em>) – HTTP connection tunables</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_head.HeadHandlerConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_head.</span></span><span class="sig-name descname"><span class="pre">HeadHandlerConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_head.HeadHandlerConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Head block handler config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><p><strong>callback</strong> (<em>str</em>) – Callback name</p>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_head.TzktHeadIndexConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_head.</span></span><span class="sig-name descname"><span class="pre">TzktHeadIndexConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasource</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">handlers</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_head.TzktHeadIndexConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Head block index config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'tezos.tzkt.head'</em><em>]</em>) – always <cite>tezos.tzkt.head</cite></p></li>
<li><p><strong>datasource</strong> (<em>str</em><em> | </em><a class="reference internal" href="#tezos_tzkt.TzktDatasourceConfig" title="tezos_tzkt.TzktDatasourceConfig"><em>TzktDatasourceConfig</em></a>) – Index datasource to receive head blocks</p></li>
<li><p><strong>handlers</strong> (<em>tuple</em><em>[</em><a class="reference internal" href="#tezos_tzkt_head.HeadHandlerConfig" title="tezos_tzkt_head.HeadHandlerConfig"><em>tezos_tzkt_head.HeadHandlerConfig</em></a><em>, </em><em>...</em><em>]</em>) – Mapping of head block handlers</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="HookConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">HookConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">args=&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">atomic=False</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#HookConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Hook config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>args</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><em>str</em><em>]</em>) – Mapping of argument names and annotations (checked lazily when possible)</p></li>
<li><p><strong>atomic</strong> (<em>bool</em>) – Wrap hook in a single database transaction</p></li>
<li><p><strong>callback</strong> (<em>str</em>) – Callback name</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="HttpConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">HttpConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">retry_count</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">retry_sleep</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">retry_multiplier</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">ratelimit_rate</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">ratelimit_period</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">ratelimit_sleep</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">connection_limit</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">connection_timeout</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">batch_size</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">replay_path</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#HttpConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Advanced configuration of HTTP client</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>retry_count</strong> (<em>int</em><em> | </em><em>None</em>) – Number of retries after request failed before giving up</p></li>
<li><p><strong>retry_sleep</strong> (<em>float</em><em> | </em><em>None</em>) – Sleep time between retries</p></li>
<li><p><strong>retry_multiplier</strong> (<em>float</em><em> | </em><em>None</em>) – Multiplier for sleep time between retries</p></li>
<li><p><strong>ratelimit_rate</strong> (<em>int</em><em> | </em><em>None</em>) – Number of requests per period (“drops” in leaky bucket)</p></li>
<li><p><strong>ratelimit_period</strong> (<em>int</em><em> | </em><em>None</em>) – Time period for rate limiting in seconds</p></li>
<li><p><strong>ratelimit_sleep</strong> (<em>float</em><em> | </em><em>None</em>) – Sleep time between requests when rate limit is reached</p></li>
<li><p><strong>connection_limit</strong> (<em>int</em><em> | </em><em>None</em>) – Number of simultaneous connections</p></li>
<li><p><strong>connection_timeout</strong> (<em>int</em><em> | </em><em>None</em>) – Connection timeout in seconds</p></li>
<li><p><strong>batch_size</strong> (<em>int</em><em> | </em><em>None</em>) – Number of items fetched in a single paginated request (for some APIs)</p></li>
<li><p><strong>replay_path</strong> (<em>str</em><em> | </em><em>None</em>) – Development-only option to use cached HTTP responses instead of making real requests</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="HttpDatasourceConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">HttpDatasourceConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">url</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">http</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#HttpDatasourceConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Generic HTTP datasource config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'http'</em><em>]</em>) – always ‘http’</p></li>
<li><p><strong>url</strong> (<em>str</em>) – URL to fetch data from</p></li>
<li><p><strong>http</strong> (<a class="reference internal" href="#HttpConfig" title="HttpConfig"><em>HttpConfig</em></a><em> | </em><em>None</em>) – HTTP client configuration</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="IndexTemplateConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">IndexTemplateConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">template</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">values</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">first_level</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">0</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">last_level</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">0</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#IndexTemplateConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Index template config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> – always <cite>template</cite></p></li>
<li><p><strong>values</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><em>str</em><em>]</em>) – Values to be substituted in template (<cite>&lt;key&gt;</cite> -&gt; <cite>value</cite>)</p></li>
<li><p><strong>first_level</strong> (<em>int</em>) – Level to start indexing from</p></li>
<li><p><strong>last_level</strong> (<em>int</em>) – Level to stop indexing at</p></li>
<li><p><strong>template</strong> (<em>str</em>) – Template alias in <cite>templates</cite> section</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="ipfs.IpfsDatasourceConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">ipfs.</span></span><span class="sig-name descname"><span class="pre">IpfsDatasourceConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">url</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">'https://ipfs.io/ipfs'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">http</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#ipfs.IpfsDatasourceConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>IPFS datasource config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'ipfs'</em><em>]</em>) – always ‘ipfs’</p></li>
<li><p><strong>url</strong> (<em>str</em>) – IPFS node URL, e.g. <a class="reference external" href="https://ipfs.io/ipfs/">https://ipfs.io/ipfs/</a></p></li>
<li><p><strong>http</strong> (<a class="reference internal" href="#HttpConfig" title="HttpConfig"><em>HttpConfig</em></a><em> | </em><em>None</em>) – HTTP client configuration</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="JobConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">JobConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">hook</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">args=&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">crontab=None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">interval=None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">daemon=False</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#JobConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Job schedule config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>hook</strong> (<em>str</em><em> | </em><a class="reference internal" href="#HookConfig" title="HookConfig"><em>HookConfig</em></a>) – Name of hook to run</p></li>
<li><p><strong>crontab</strong> (<em>str</em><em> | </em><em>None</em>) – Schedule with crontab syntax (<cite>* * * * *</cite>)</p></li>
<li><p><strong>interval</strong> (<em>int</em><em> | </em><em>None</em>) – Schedule with interval in seconds</p></li>
<li><p><strong>daemon</strong> (<em>bool</em>) – Run hook as a daemon (never stops)</p></li>
<li><p><strong>args</strong> (<em>dict</em><em>[</em><em>str</em><em>, </em><em>Any</em><em>]</em>) – Arguments to pass to the hook</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.models.LoggingValues">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.models.</span></span><span class="sig-name descname"><span class="pre">LoggingValues</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">value</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.models.LoggingValues" title="Permalink to this definition">¶</a></dt>
<dd><p>Enum for <cite>logging</cite> field values.</p>
<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.LoggingValues.default">
<span class="sig-name descname"><span class="pre">default</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'default'</span></em><a class="headerlink" href="#dipdup.models.LoggingValues.default" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.LoggingValues.quiet">
<span class="sig-name descname"><span class="pre">quiet</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'quiet'</span></em><a class="headerlink" href="#dipdup.models.LoggingValues.quiet" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.LoggingValues.verbose">
<span class="sig-name descname"><span class="pre">verbose</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'verbose'</span></em><a class="headerlink" href="#dipdup.models.LoggingValues.verbose" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_metadata.TezosMetadataDatasourceConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_metadata.</span></span><span class="sig-name descname"><span class="pre">TezosMetadataDatasourceConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">network</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">url</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">'https://metadata.dipdup.net'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">http</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_metadata.TezosMetadataDatasourceConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>DipDup Metadata datasource config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'tezos.metadata'</em><em>]</em>) – always ‘metadata’</p></li>
<li><p><strong>network</strong> (<em>MetadataNetwork</em>) – Network name, e.g. mainnet, ghostnet, etc.</p></li>
<li><p><strong>url</strong> (<em>str</em>) – GraphQL API URL, e.g. <a class="reference external" href="https://metadata.dipdup.net">https://metadata.dipdup.net</a></p></li>
<li><p><strong>http</strong> (<a class="reference internal" href="#HttpConfig" title="HttpConfig"><em>HttpConfig</em></a><em> | </em><em>None</em>) – HTTP client configuration</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_operations.TzktOperationsHandlerConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_operations.</span></span><span class="sig-name descname"><span class="pre">TzktOperationsHandlerConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">pattern</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_operations.TzktOperationsHandlerConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Operation handler config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>callback</strong> (<em>str</em>) – Callback name</p></li>
<li><p><strong>pattern</strong> (<em>tuple</em><em>[</em><a class="reference internal" href="#tezos_tzkt_operations.OperationsHandlerTransactionPatternConfig" title="tezos_tzkt_operations.OperationsHandlerTransactionPatternConfig"><em>tezos_tzkt_operations.OperationsHandlerTransactionPatternConfig</em></a><em> | </em><a class="reference internal" href="#tezos_tzkt_operations.OperationsHandlerOriginationPatternConfig" title="tezos_tzkt_operations.OperationsHandlerOriginationPatternConfig"><em>tezos_tzkt_operations.OperationsHandlerOriginationPatternConfig</em></a><em>, </em><em>...</em><em>]</em>) – Filters to match operation groups</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_operations.OperationsHandlerOriginationPatternConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_operations.</span></span><span class="sig-name descname"><span class="pre">OperationsHandlerOriginationPatternConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">type</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">'origination'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">source</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">similar_to</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">originated_contract</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">optional</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">strict</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">alias</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_operations.OperationsHandlerOriginationPatternConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Origination handler pattern config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>type</strong> (<em>Literal</em><em>[</em><em>'origination'</em><em>]</em>) – always ‘origination’</p></li>
<li><p><strong>source</strong> (<em>str</em><em> | </em><a class="reference internal" href="#ContractConfig" title="ContractConfig"><em>ContractConfig</em></a><em> | </em><em>None</em>) – Match operations by source contract alias</p></li>
<li><p><strong>similar_to</strong> (<em>str</em><em> | </em><a class="reference internal" href="#ContractConfig" title="ContractConfig"><em>ContractConfig</em></a><em> | </em><em>None</em>) – Match operations which have the same code/signature (depending on <cite>strict</cite> field)</p></li>
<li><p><strong>originated_contract</strong> (<em>str</em><em> | </em><a class="reference internal" href="#ContractConfig" title="ContractConfig"><em>ContractConfig</em></a><em> | </em><em>None</em>) – Match origination of exact contract</p></li>
<li><p><strong>optional</strong> (<em>bool</em>) – Whether can operation be missing in operation group</p></li>
<li><p><strong>strict</strong> (<em>bool</em>) – Match operations by storage only or by the whole code</p></li>
<li><p><strong>alias</strong> (<em>str</em><em> | </em><em>None</em>) – Alias for transaction (helps to avoid duplicates)</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_operations.OperationsHandlerTransactionPatternConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_operations.</span></span><span class="sig-name descname"><span class="pre">OperationsHandlerTransactionPatternConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">type</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">'transaction'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">source</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">destination</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">entrypoint</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">optional</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">False</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">alias</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_operations.OperationsHandlerTransactionPatternConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Operation handler pattern config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>type</strong> (<em>Literal</em><em>[</em><em>'transaction'</em><em>]</em>) – always ‘transaction’</p></li>
<li><p><strong>source</strong> (<em>str</em><em> | </em><a class="reference internal" href="#ContractConfig" title="ContractConfig"><em>ContractConfig</em></a><em> | </em><em>None</em>) – Match operations by source contract alias</p></li>
<li><p><strong>destination</strong> (<em>str</em><em> | </em><a class="reference internal" href="#ContractConfig" title="ContractConfig"><em>ContractConfig</em></a><em> | </em><em>None</em>) – Match operations by destination contract alias</p></li>
<li><p><strong>entrypoint</strong> (<em>str</em><em> | </em><em>None</em>) – Match operations by contract entrypoint</p></li>
<li><p><strong>optional</strong> (<em>bool</em>) – Whether can operation be missing in operation group</p></li>
<li><p><strong>alias</strong> (<em>str</em><em> | </em><em>None</em>) – Alias for transaction (helps to avoid duplicates)</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_operations.TzktOperationsIndexConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_operations.</span></span><span class="sig-name descname"><span class="pre">TzktOperationsIndexConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasource</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">handlers</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">contracts=&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">types=(&lt;TzktOperationType.transaction:</span> <span class="pre">'transaction'&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">)</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">first_level=0</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">last_level=0</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_operations.TzktOperationsIndexConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Operation index config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'tezos.tzkt.operations'</em><em>]</em>) – always <cite>operation</cite></p></li>
<li><p><strong>datasource</strong> (<em>str</em><em> | </em><a class="reference internal" href="#tezos_tzkt.TzktDatasourceConfig" title="tezos_tzkt.TzktDatasourceConfig"><em>TzktDatasourceConfig</em></a>) – Alias of index datasource in <cite>datasources</cite> section</p></li>
<li><p><strong>handlers</strong> (<em>tuple</em><em>[</em><a class="reference internal" href="#tezos_tzkt_operations.TzktOperationsHandlerConfig" title="tezos_tzkt_operations.TzktOperationsHandlerConfig"><em>tezos_tzkt_operations.TzktOperationsHandlerConfig</em></a><em>, </em><em>...</em><em>]</em>) – List of indexer handlers</p></li>
<li><p><strong>types</strong> (<em>tuple</em><em>[</em><a class="reference internal" href="#dipdup.models.tezos_tzkt.TzktOperationType" title="dipdup.models.tezos_tzkt.TzktOperationType"><em>dipdup.models.tezos_tzkt.TzktOperationType</em></a><em>, </em><em>...</em><em>]</em>) – Types of transaction to fetch</p></li>
<li><p><strong>contracts</strong> (<em>list</em><em>[</em><em>str</em><em> | </em><a class="reference internal" href="#ContractConfig" title="ContractConfig"><em>ContractConfig</em></a><em>]</em>) – Aliases of contracts being indexed in <cite>contracts</cite> section</p></li>
<li><p><strong>first_level</strong> (<em>int</em>) – Level to start indexing from</p></li>
<li><p><strong>last_level</strong> (<em>int</em>) – Level to stop indexing at</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.models.tezos_tzkt.TzktOperationType">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.models.tezos_tzkt.</span></span><span class="sig-name descname"><span class="pre">TzktOperationType</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">value</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.models.tezos_tzkt.TzktOperationType" title="Permalink to this definition">¶</a></dt>
<dd><p>Type of blockchain operation</p>
<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.tezos_tzkt.TzktOperationType.migration">
<span class="sig-name descname"><span class="pre">migration</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'migration'</span></em><a class="headerlink" href="#dipdup.models.tezos_tzkt.TzktOperationType.migration" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.tezos_tzkt.TzktOperationType.origination">
<span class="sig-name descname"><span class="pre">origination</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'origination'</span></em><a class="headerlink" href="#dipdup.models.tezos_tzkt.TzktOperationType.origination" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.tezos_tzkt.TzktOperationType.transaction">
<span class="sig-name descname"><span class="pre">transaction</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'transaction'</span></em><a class="headerlink" href="#dipdup.models.tezos_tzkt.TzktOperationType.transaction" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_operations.TzktOperationsUnfilteredIndexConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_operations.</span></span><span class="sig-name descname"><span class="pre">TzktOperationsUnfilteredIndexConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasource</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">callback</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">types=(&lt;TzktOperationType.transaction:</span> <span class="pre">'transaction'&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">)</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">first_level=0</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">last_level=0</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_operations.TzktOperationsUnfilteredIndexConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Operation index config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'tezos.tzkt.operations_unfiltered'</em><em>]</em>) – always <cite>operation_unfiltered</cite></p></li>
<li><p><strong>datasource</strong> (<em>str</em><em> | </em><a class="reference internal" href="#tezos_tzkt.TzktDatasourceConfig" title="tezos_tzkt.TzktDatasourceConfig"><em>TzktDatasourceConfig</em></a>) – Alias of index datasource in <cite>datasources</cite> section</p></li>
<li><p><strong>callback</strong> (<em>str</em>) – Callback name</p></li>
<li><p><strong>types</strong> (<em>tuple</em><em>[</em><a class="reference internal" href="#dipdup.models.tezos_tzkt.TzktOperationType" title="dipdup.models.tezos_tzkt.TzktOperationType"><em>dipdup.models.tezos_tzkt.TzktOperationType</em></a><em>, </em><em>...</em><em>]</em>) – Types of transaction to fetch</p></li>
<li><p><strong>first_level</strong> (<em>int</em>) – Level to start indexing from</p></li>
<li><p><strong>last_level</strong> (<em>int</em>) – Level to stop indexing at</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="PostgresDatabaseConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">PostgresDatabaseConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">host</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">user='postgres'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">database='postgres'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">port=5432</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">schema_name='public'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">password=''</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">immune_tables=&lt;factory&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">connection_timeout=60</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#PostgresDatabaseConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Postgres database connection config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'postgres'</em><em>]</em>) – always ‘postgres’</p></li>
<li><p><strong>host</strong> (<em>str</em>) – Host</p></li>
<li><p><strong>port</strong> (<em>int</em>) – Port</p></li>
<li><p><strong>user</strong> (<em>str</em>) – User</p></li>
<li><p><strong>password</strong> (<em>str</em>) – Password</p></li>
<li><p><strong>database</strong> (<em>str</em>) – Database name</p></li>
<li><p><strong>schema_name</strong> (<em>str</em>) – Schema name</p></li>
<li><p><strong>immune_tables</strong> (<em>set</em><em>[</em><em>str</em><em>]</em>) – List of tables to preserve during reindexing</p></li>
<li><p><strong>connection_timeout</strong> (<em>int</em>) – Connection timeout</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="PrometheusConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">PrometheusConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">host</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">port</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">8000</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">update_interval</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">1.0</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#PrometheusConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Config for Prometheus integration.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>host</strong> (<em>str</em>) – Host to bind to</p></li>
<li><p><strong>port</strong> (<em>int</em>) – Port to bind to</p></li>
<li><p><strong>update_interval</strong> (<em>float</em>) – Interval to update some metrics in seconds</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.models.ReindexingAction">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.models.</span></span><span class="sig-name descname"><span class="pre">ReindexingAction</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">value</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.models.ReindexingAction" title="Permalink to this definition">¶</a></dt>
<dd><p>Action that should be performed on reindexing</p>
<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.ReindexingAction.exception">
<span class="sig-name descname"><span class="pre">exception</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'exception'</span></em><a class="headerlink" href="#dipdup.models.ReindexingAction.exception" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.ReindexingAction.ignore">
<span class="sig-name descname"><span class="pre">ignore</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'ignore'</span></em><a class="headerlink" href="#dipdup.models.ReindexingAction.ignore" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.ReindexingAction.wipe">
<span class="sig-name descname"><span class="pre">wipe</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'wipe'</span></em><a class="headerlink" href="#dipdup.models.ReindexingAction.wipe" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.models.ReindexingReason">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.models.</span></span><span class="sig-name descname"><span class="pre">ReindexingReason</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">value</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.models.ReindexingReason" title="Permalink to this definition">¶</a></dt>
<dd><p>Reason that caused reindexing</p>
<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.ReindexingReason.config_modified">
<span class="sig-name descname"><span class="pre">config_modified</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'config_modified'</span></em><a class="headerlink" href="#dipdup.models.ReindexingReason.config_modified" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.ReindexingReason.manual">
<span class="sig-name descname"><span class="pre">manual</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'manual'</span></em><a class="headerlink" href="#dipdup.models.ReindexingReason.manual" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.ReindexingReason.migration">
<span class="sig-name descname"><span class="pre">migration</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'migration'</span></em><a class="headerlink" href="#dipdup.models.ReindexingReason.migration" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.ReindexingReason.rollback">
<span class="sig-name descname"><span class="pre">rollback</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'rollback'</span></em><a class="headerlink" href="#dipdup.models.ReindexingReason.rollback" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.ReindexingReason.schema_modified">
<span class="sig-name descname"><span class="pre">schema_modified</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'schema_modified'</span></em><a class="headerlink" href="#dipdup.models.ReindexingReason.schema_modified" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="SentryConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">SentryConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">dsn</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">''</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">environment</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">server_name</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">release</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">user_id</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">debug</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">False</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#SentryConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Config for Sentry integration.</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>dsn</strong> (<em>str</em>) – DSN of the Sentry instance</p></li>
<li><p><strong>environment</strong> (<em>str</em><em> | </em><em>None</em>) – Environment; if not set, guessed from docker/ci/gha/local.</p></li>
<li><p><strong>server_name</strong> (<em>str</em><em> | </em><em>None</em>) – Server name; defaults to obfuscated hostname.</p></li>
<li><p><strong>release</strong> (<em>str</em><em> | </em><em>None</em>) – Release version; defaults to DipDup package version.</p></li>
<li><p><strong>user_id</strong> (<em>str</em><em> | </em><em>None</em>) – User ID; defaults to obfuscated package/environment.</p></li>
<li><p><strong>debug</strong> (<em>bool</em>) – Catch warning messages, increase verbosity.</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="dipdup.models.SkipHistory">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">dipdup.models.</span></span><span class="sig-name descname"><span class="pre">SkipHistory</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">value</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#dipdup.models.SkipHistory" title="Permalink to this definition">¶</a></dt>
<dd><p>Whether to skip indexing operation history and use only current state</p>
<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.SkipHistory.always">
<span class="sig-name descname"><span class="pre">always</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'always'</span></em><a class="headerlink" href="#dipdup.models.SkipHistory.always" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.SkipHistory.never">
<span class="sig-name descname"><span class="pre">never</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'never'</span></em><a class="headerlink" href="#dipdup.models.SkipHistory.never" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

<dl class="py attribute">
<dt class="sig sig-object py" id="dipdup.models.SkipHistory.once">
<span class="sig-name descname"><span class="pre">once</span></span><em class="property"><span class="w"> </span><span class="p"><span class="pre">=</span></span><span class="w"> </span><span class="pre">'once'</span></em><a class="headerlink" href="#dipdup.models.SkipHistory.once" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="SqliteDatabaseConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre"></span></span><span class="sig-name descname"><span class="pre">SqliteDatabaseConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">path</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">':memory:'</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#SqliteDatabaseConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>SQLite connection config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'sqlite'</em><em>]</em>) – always ‘sqlite’</p></li>
<li><p><strong>path</strong> (<em>str</em>) – Path to .sqlite3 file, leave default for in-memory database (<cite>:memory:</cite>)</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_token_transfers.TzktTokenTransfersHandlerConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_token_transfers.</span></span><span class="sig-name descname"><span class="pre">TzktTokenTransfersHandlerConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">contract</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">token_id</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">from_</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">FieldInfo(alias='from',</span> <span class="pre">alias_priority=2,</span> <span class="pre">extra={})</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">to</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_token_transfers.TzktTokenTransfersHandlerConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Token transfer handler config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>callback</strong> (<em>str</em>) – Callback name</p></li>
<li><p><strong>contract</strong> (<em>str</em><em> | </em><a class="reference internal" href="#ContractConfig" title="ContractConfig"><em>ContractConfig</em></a><em> | </em><em>None</em>) – Filter by contract</p></li>
<li><p><strong>token_id</strong> (<em>int</em><em> | </em><em>None</em>) – Filter by token ID</p></li>
<li><p><strong>from</strong> – Filter by sender</p></li>
<li><p><strong>to</strong> (<em>str</em><em> | </em><a class="reference internal" href="#ContractConfig" title="ContractConfig"><em>ContractConfig</em></a><em> | </em><em>None</em>) – Filter by recipient</p></li>
<li><p><strong>from_</strong> (<em>str</em><em> | </em><a class="reference internal" href="#ContractConfig" title="ContractConfig"><em>ContractConfig</em></a><em> | </em><em>None</em>) – </p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_token_transfers.TzktTokenTransfersIndexConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_token_transfers.</span></span><span class="sig-name descname"><span class="pre">TzktTokenTransfersIndexConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">datasource</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">handlers=FieldInfo(default=PydanticUndefined</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">default_factory=&lt;class</span> <span class="pre">'tuple'&gt;</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">extra={})</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">first_level=0</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">last_level=0</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_token_transfers.TzktTokenTransfersIndexConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Token transfer index config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'tezos.tzkt.token_transfers'</em><em>]</em>) – always <cite>token_transfer</cite></p></li>
<li><p><strong>datasource</strong> (<em>str</em><em> | </em><a class="reference internal" href="#tezos_tzkt.TzktDatasourceConfig" title="tezos_tzkt.TzktDatasourceConfig"><em>TzktDatasourceConfig</em></a>) – Index datasource to use</p></li>
<li><p><strong>handlers</strong> (<em>tuple</em><em>[</em><a class="reference internal" href="#tezos_tzkt_token_transfers.TzktTokenTransfersHandlerConfig" title="tezos_tzkt_token_transfers.TzktTokenTransfersHandlerConfig"><em>tezos_tzkt_token_transfers.TzktTokenTransfersHandlerConfig</em></a><em>, </em><em>...</em><em>]</em>) – Mapping of token transfer handlers</p></li>
<li><p><strong>first_level</strong> (<em>int</em>) – Level to start indexing from</p></li>
<li><p><strong>last_level</strong> (<em>int</em>) – Level to stop indexing at</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt.TzktDatasourceConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt.</span></span><span class="sig-name descname"><span class="pre">TzktDatasourceConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">kind</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">url</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">'https://api.tzkt.io'</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">http</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">None</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">buffer_size</span></span><span class="o"><span class="pre">=</span></span><span class="default_value"><span class="pre">0</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt.TzktDatasourceConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>TzKT datasource config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>kind</strong> (<em>Literal</em><em>[</em><em>'tezos.tzkt'</em><em>]</em>) – always ‘tezos.tzkt’</p></li>
<li><p><strong>url</strong> (<em>str</em>) – Base API URL, e.g. <a class="reference external" href="https://api.tzkt.io/">https://api.tzkt.io/</a></p></li>
<li><p><strong>http</strong> (<a class="reference internal" href="#HttpConfig" title="HttpConfig"><em>HttpConfig</em></a><em> | </em><em>None</em>) – HTTP client configuration</p></li>
<li><p><strong>buffer_size</strong> (<em>int</em>) – Number of levels to keep in FIFO buffer before processing</p></li>
</ul>
</dd>
</dl>
</dd></dl>

<dl class="py class">
<dt class="sig sig-object py" id="tezos_tzkt_events.TzktEventsUnknownEventHandlerConfig">
<em class="property"><span class="pre">class</span><span class="w"> </span></em><span class="sig-prename descclassname"><span class="pre">tezos_tzkt_events.</span></span><span class="sig-name descname"><span class="pre">TzktEventsUnknownEventHandlerConfig</span></span><span class="sig-paren">(</span><em class="sig-param"><span class="n"><span class="pre">callback</span></span></em>, <em class="sig-param"><span class="n"><span class="pre">contract</span></span></em><span class="sig-paren">)</span><a class="headerlink" href="#tezos_tzkt_events.TzktEventsUnknownEventHandlerConfig" title="Permalink to this definition">¶</a></dt>
<dd><p>Unknown event handler config</p>
<dl class="field-list simple">
<dt class="field-odd">Parameters<span class="colon">:</span></dt>
<dd class="field-odd"><ul class="simple">
<li><p><strong>callback</strong> (<em>str</em>) – Callback name</p></li>
<li><p><strong>contract</strong> (<em>str</em><em> | </em><a class="reference internal" href="#ContractConfig" title="ContractConfig"><em>ContractConfig</em></a>) – Contract which emits event</p></li>
</ul>
</dd>
</dl>
</dd></dl>
