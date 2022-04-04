
  <section id="dipdup">
<h1>dipdup<a class="headerlink" href="#dipdup" title="Permalink to this headline">¶</a></h1>
<p>Docs: <a class="reference external" href="https://docs.dipdup.net">https://docs.dipdup.net</a></p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup <span class="o">[</span>OPTIONS<span class="o">]</span> COMMAND <span class="o">[</span>ARGS<span class="o">]</span>...
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-version">
<span class="sig-name descname"><span class="pre">--version</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-version" title="Permalink to this definition">¶</a></dt>
<dd><p>Show the version and exit.</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-c">
<span id="cmdoption-dipdup-config"></span><span class="sig-name descname"><span class="pre">-c</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--config</span></span><span class="sig-prename descclassname"> <span class="pre">&lt;config&gt;</span></span><a class="headerlink" href="#cmdoption-dipdup-c" title="Permalink to this definition">¶</a></dt>
<dd><p>Path to dipdup YAML config</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-e">
<span id="cmdoption-dipdup-env-file"></span><span class="sig-name descname"><span class="pre">-e</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--env-file</span></span><span class="sig-prename descclassname"> <span class="pre">&lt;env_file&gt;</span></span><a class="headerlink" href="#cmdoption-dipdup-e" title="Permalink to this definition">¶</a></dt>
<dd><p>Path to .env file with KEY=value strings</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-l">
<span id="cmdoption-dipdup-logging-config"></span><span class="sig-name descname"><span class="pre">-l</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--logging-config</span></span><span class="sig-prename descclassname"> <span class="pre">&lt;logging_config&gt;</span></span><a class="headerlink" href="#cmdoption-dipdup-l" title="Permalink to this definition">¶</a></dt>
<dd><p>Path to Python logging YAML config</p>
</dd></dl>

<section id="dipdup-cache">
<h2>cache<a class="headerlink" href="#dipdup-cache" title="Permalink to this headline">¶</a></h2>
<p>Manage internal cache</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup cache <span class="o">[</span>OPTIONS<span class="o">]</span> COMMAND <span class="o">[</span>ARGS<span class="o">]</span>...
</pre></div>
</div>
<section id="dipdup-cache-clear">
<h3>clear<a class="headerlink" href="#dipdup-cache-clear" title="Permalink to this headline">¶</a></h3>
<p>Clear cache</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup cache clear <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
</section>
<section id="dipdup-cache-show">
<h3>show<a class="headerlink" href="#dipdup-cache-show" title="Permalink to this headline">¶</a></h3>
<p>Show cache size information</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup cache show <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
</section>
</section>
<section id="dipdup-config">
<h2>config<a class="headerlink" href="#dipdup-config" title="Permalink to this headline">¶</a></h2>
<p>Commands to manage DipDup configuration</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup config <span class="o">[</span>OPTIONS<span class="o">]</span> COMMAND <span class="o">[</span>ARGS<span class="o">]</span>...
</pre></div>
</div>
<section id="dipdup-config-export">
<h3>export<a class="headerlink" href="#dipdup-config-export" title="Permalink to this headline">¶</a></h3>
<p>Dump DipDup configuration after resolving templates</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup config <span class="nb">export</span> <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-config-export-unsafe">
<span class="sig-name descname"><span class="pre">--unsafe</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-config-export-unsafe" title="Permalink to this definition">¶</a></dt>
<dd></dd></dl>

</section>
</section>
<section id="dipdup-hasura">
<h2>hasura<a class="headerlink" href="#dipdup-hasura" title="Permalink to this headline">¶</a></h2>
<p>Hasura integration related commands</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup hasura <span class="o">[</span>OPTIONS<span class="o">]</span> COMMAND <span class="o">[</span>ARGS<span class="o">]</span>...
</pre></div>
</div>
<section id="dipdup-hasura-configure">
<h3>configure<a class="headerlink" href="#dipdup-hasura-configure" title="Permalink to this headline">¶</a></h3>
<p>Configure Hasura GraphQL Engine</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup hasura configure <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-hasura-configure-force">
<span class="sig-name descname"><span class="pre">--force</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-hasura-configure-force" title="Permalink to this definition">¶</a></dt>
<dd><p>Proceed even if Hasura is already configured</p>
</dd></dl>

</section>
</section>
<section id="dipdup-init">
<h2>init<a class="headerlink" href="#dipdup-init" title="Permalink to this headline">¶</a></h2>
<p>Generate project tree and missing callbacks and types</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup init <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-init-overwrite-types">
<span class="sig-name descname"><span class="pre">--overwrite-types</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-init-overwrite-types" title="Permalink to this definition">¶</a></dt>
<dd><p>Regenerate existing types</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-init-keep-schemas">
<span class="sig-name descname"><span class="pre">--keep-schemas</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-init-keep-schemas" title="Permalink to this definition">¶</a></dt>
<dd><p>Do not remove JSONSchemas after generating types</p>
</dd></dl>

</section>
<section id="dipdup-migrate">
<h2>migrate<a class="headerlink" href="#dipdup-migrate" title="Permalink to this headline">¶</a></h2>
<p>Migrate project to the new spec version</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup migrate <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
</section>
<section id="dipdup-run">
<h2>run<a class="headerlink" href="#dipdup-run" title="Permalink to this headline">¶</a></h2>
<p>Run indexing</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup run <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-run-postpone-jobs">
<span class="sig-name descname"><span class="pre">--postpone-jobs</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-run-postpone-jobs" title="Permalink to this definition">¶</a></dt>
<dd><p>Do not start job scheduler until all indexes are synchronized</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-run-early-realtime">
<span class="sig-name descname"><span class="pre">--early-realtime</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-run-early-realtime" title="Permalink to this definition">¶</a></dt>
<dd><p>Establish a realtime connection before all indexes are synchronized</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-run-merge-subscriptions">
<span class="sig-name descname"><span class="pre">--merge-subscriptions</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-run-merge-subscriptions" title="Permalink to this definition">¶</a></dt>
<dd><p>Subscribe to all operations/big map diffs during realtime indexing</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-run-metadata-interface">
<span class="sig-name descname"><span class="pre">--metadata-interface</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-run-metadata-interface" title="Permalink to this definition">¶</a></dt>
<dd><p>Enable metadata interface</p>
</dd></dl>

</section>
<section id="dipdup-schema">
<h2>schema<a class="headerlink" href="#dipdup-schema" title="Permalink to this headline">¶</a></h2>
<p>Manage database schema</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup schema <span class="o">[</span>OPTIONS<span class="o">]</span> COMMAND <span class="o">[</span>ARGS<span class="o">]</span>...
</pre></div>
</div>
<section id="dipdup-schema-approve">
<h3>approve<a class="headerlink" href="#dipdup-schema-approve" title="Permalink to this headline">¶</a></h3>
<p>Continue to use existing schema after reindexing was triggered</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup schema approve <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
</section>
<section id="dipdup-schema-export">
<h3>export<a class="headerlink" href="#dipdup-schema-export" title="Permalink to this headline">¶</a></h3>
<p>Print schema SQL including <cite>on_reindex</cite> hook</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup schema <span class="nb">export</span> <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
</section>
<section id="dipdup-schema-init">
<h3>init<a class="headerlink" href="#dipdup-schema-init" title="Permalink to this headline">¶</a></h3>
<p>Initialize database schema and trigger <cite>on_reindex</cite></p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup schema init <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
</section>
<section id="dipdup-schema-wipe">
<h3>wipe<a class="headerlink" href="#dipdup-schema-wipe" title="Permalink to this headline">¶</a></h3>
<p>Drop all database tables, functions and views</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup schema wipe <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-schema-wipe-immune">
<span class="sig-name descname"><span class="pre">--immune</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-schema-wipe-immune" title="Permalink to this definition">¶</a></dt>
<dd><p>Drop immune tables too</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-schema-wipe-force">
<span class="sig-name descname"><span class="pre">--force</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-schema-wipe-force" title="Permalink to this definition">¶</a></dt>
<dd><p>Skip confirmation prompt</p>
</dd></dl>

</section>
</section>
<section id="dipdup-status">
<h2>status<a class="headerlink" href="#dipdup-status" title="Permalink to this headline">¶</a></h2>
<p>Show current status of indexes in database</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup status <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
</section>
</section>
