
  <section id="dipdup">
<h1>dipdup<a class="headerlink" href="#dipdup" title="Permalink to this heading">¶</a></h1>
<p>Manage and run DipDup indexers.</p>
<p>Documentation: <a class="reference external" href="https://docs.dipdup.io">https://docs.dipdup.io</a></p>
<p>Issues: <a class="reference external" href="https://github.com/dipdup-net/dipdup/issues">https://github.com/dipdup-net/dipdup/issues</a></p>
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
<span id="cmdoption-dipdup-config"></span><span class="sig-name descname"><span class="pre">-c</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--config</span></span><span class="sig-prename descclassname"> <span class="pre">&lt;PATH&gt;</span></span><a class="headerlink" href="#cmdoption-dipdup-c" title="Permalink to this definition">¶</a></dt>
<dd><p>A path to DipDup project config (default: dipdup.yml).</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-e">
<span id="cmdoption-dipdup-env-file"></span><span class="sig-name descname"><span class="pre">-e</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--env-file</span></span><span class="sig-prename descclassname"> <span class="pre">&lt;PATH&gt;</span></span><a class="headerlink" href="#cmdoption-dipdup-e" title="Permalink to this definition">¶</a></dt>
<dd><p>A path to .env file containing <cite>KEY=value</cite> strings.</p>
</dd></dl>

<section id="dipdup-config">
<h2>config<a class="headerlink" href="#dipdup-config" title="Permalink to this heading">¶</a></h2>
<p>Commands to manage DipDup configuration.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup config <span class="o">[</span>OPTIONS<span class="o">]</span> COMMAND <span class="o">[</span>ARGS<span class="o">]</span>...
</pre></div>
</div>
<section id="dipdup-config-env">
<h3>env<a class="headerlink" href="#dipdup-config-env" title="Permalink to this heading">¶</a></h3>
<p>Dump environment variables used in DipDup config.</p>
<p>If variable is not set, default value will be used.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup config env <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-config-env-f">
<span id="cmdoption-dipdup-config-env-file"></span><span class="sig-name descname"><span class="pre">-f</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--file</span></span><span class="sig-prename descclassname"> <span class="pre">&lt;file&gt;</span></span><a class="headerlink" href="#cmdoption-dipdup-config-env-f" title="Permalink to this definition">¶</a></dt>
<dd><p>Output to file instead of stdout.</p>
</dd></dl>

</section>
<section id="dipdup-config-export">
<h3>export<a class="headerlink" href="#dipdup-config-export" title="Permalink to this heading">¶</a></h3>
<p>Print config after resolving all links and, optionally, templates.</p>
<p>WARNING: Avoid sharing output with 3rd-parties when <cite>–unsafe</cite> flag set - it may contain secrets!</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup config <span class="nb">export</span> <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-config-export-unsafe">
<span class="sig-name descname"><span class="pre">--unsafe</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-config-export-unsafe" title="Permalink to this definition">¶</a></dt>
<dd><p>Resolve environment variables or use default values from config.</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-config-export-full">
<span class="sig-name descname"><span class="pre">--full</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-config-export-full" title="Permalink to this definition">¶</a></dt>
<dd><p>Resolve index templates.</p>
</dd></dl>

</section>
</section>
<section id="dipdup-hasura">
<h2>hasura<a class="headerlink" href="#dipdup-hasura" title="Permalink to this heading">¶</a></h2>
<p>Commands related to Hasura integration.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup hasura <span class="o">[</span>OPTIONS<span class="o">]</span> COMMAND <span class="o">[</span>ARGS<span class="o">]</span>...
</pre></div>
</div>
<section id="dipdup-hasura-configure">
<h3>configure<a class="headerlink" href="#dipdup-hasura-configure" title="Permalink to this heading">¶</a></h3>
<p>Configure Hasura GraphQL Engine to use with DipDup.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup hasura configure <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-hasura-configure-force">
<span class="sig-name descname"><span class="pre">--force</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-hasura-configure-force" title="Permalink to this definition">¶</a></dt>
<dd><p>Proceed even if Hasura is already configured.</p>
</dd></dl>

</section>
</section>
<section id="dipdup-init">
<h2>init<a class="headerlink" href="#dipdup-init" title="Permalink to this heading">¶</a></h2>
<p>Generate project tree, callbacks and types.</p>
<p>This command is idempotent, meaning it won’t overwrite previously generated files unless asked explicitly.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup init <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-init-overwrite-types">
<span class="sig-name descname"><span class="pre">--overwrite-types</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-init-overwrite-types" title="Permalink to this definition">¶</a></dt>
<dd><p>Regenerate existing types.</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-init-keep-schemas">
<span class="sig-name descname"><span class="pre">--keep-schemas</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-init-keep-schemas" title="Permalink to this definition">¶</a></dt>
<dd><p>Do not remove JSONSchemas after generating types.</p>
</dd></dl>

</section>
<section id="dipdup-install">
<h2>install<a class="headerlink" href="#dipdup-install" title="Permalink to this heading">¶</a></h2>
<p>Install DipDup for the current user.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup install <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-install-q">
<span id="cmdoption-dipdup-install-quiet"></span><span class="sig-name descname"><span class="pre">-q</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--quiet</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-install-q" title="Permalink to this definition">¶</a></dt>
<dd><p>Use default values for all prompts.</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-install-f">
<span id="cmdoption-dipdup-install-force"></span><span class="sig-name descname"><span class="pre">-f</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--force</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-install-f" title="Permalink to this definition">¶</a></dt>
<dd><p>Force reinstall.</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-install-r">
<span id="cmdoption-dipdup-install-ref"></span><span class="sig-name descname"><span class="pre">-r</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--ref</span></span><span class="sig-prename descclassname"> <span class="pre">&lt;ref&gt;</span></span><a class="headerlink" href="#cmdoption-dipdup-install-r" title="Permalink to this definition">¶</a></dt>
<dd><p>Install DipDup from a specific git ref.</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-install-p">
<span id="cmdoption-dipdup-install-path"></span><span class="sig-name descname"><span class="pre">-p</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--path</span></span><span class="sig-prename descclassname"> <span class="pre">&lt;path&gt;</span></span><a class="headerlink" href="#cmdoption-dipdup-install-p" title="Permalink to this definition">¶</a></dt>
<dd><p>Install DipDup from a local path.</p>
</dd></dl>

</section>
<section id="dipdup-migrate">
<h2>migrate<a class="headerlink" href="#dipdup-migrate" title="Permalink to this heading">¶</a></h2>
<p>Migrate project to the new spec version.</p>
<p>If you’re getting <cite>MigrationRequiredError</cite> after updating DipDup, this command will fix imports and type annotations to match the current <cite>spec_version</cite>. Review and commit changes after running it.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup migrate <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
</section>
<section id="dipdup-new">
<h2>new<a class="headerlink" href="#dipdup-new" title="Permalink to this heading">¶</a></h2>
<p>Create a new project interactively.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup new <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-new-q">
<span id="cmdoption-dipdup-new-quiet"></span><span class="sig-name descname"><span class="pre">-q</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--quiet</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-new-q" title="Permalink to this definition">¶</a></dt>
<dd><p>Use default values for all prompts.</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-new-f">
<span id="cmdoption-dipdup-new-force"></span><span class="sig-name descname"><span class="pre">-f</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--force</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-new-f" title="Permalink to this definition">¶</a></dt>
<dd><p>Overwrite existing files.</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-new-r">
<span id="cmdoption-dipdup-new-replay"></span><span class="sig-name descname"><span class="pre">-r</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--replay</span></span><span class="sig-prename descclassname"> <span class="pre">&lt;replay&gt;</span></span><a class="headerlink" href="#cmdoption-dipdup-new-r" title="Permalink to this definition">¶</a></dt>
<dd><p>Replay a previously saved state.</p>
</dd></dl>

</section>
<section id="dipdup-run">
<h2>run<a class="headerlink" href="#dipdup-run" title="Permalink to this heading">¶</a></h2>
<p>Run indexer.</p>
<p>Execution can be gracefully interrupted with <cite>Ctrl+C</cite> or <cite>SIGTERM</cite> signal.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup run <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
</section>
<section id="dipdup-schema">
<h2>schema<a class="headerlink" href="#dipdup-schema" title="Permalink to this heading">¶</a></h2>
<p>Commands to manage database schema.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup schema <span class="o">[</span>OPTIONS<span class="o">]</span> COMMAND <span class="o">[</span>ARGS<span class="o">]</span>...
</pre></div>
</div>
<section id="dipdup-schema-approve">
<h3>approve<a class="headerlink" href="#dipdup-schema-approve" title="Permalink to this heading">¶</a></h3>
<p>Continue to use existing schema after reindexing was triggered.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup schema approve <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
</section>
<section id="dipdup-schema-export">
<h3>export<a class="headerlink" href="#dipdup-schema-export" title="Permalink to this heading">¶</a></h3>
<p>Print SQL schema including scripts from <cite>sql/on_reindex</cite>.</p>
<p>This command may help you debug inconsistency between project models and expected SQL schema.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup schema <span class="nb">export</span> <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
</section>
<section id="dipdup-schema-init">
<h3>init<a class="headerlink" href="#dipdup-schema-init" title="Permalink to this heading">¶</a></h3>
<p>Prepare a database for running DipDip.</p>
<p>This command creates tables based on your models, then executes <cite>sql/on_reindex</cite> to finish preparation - the same things DipDup does when run on a clean database.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup schema init <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
</section>
<section id="dipdup-schema-wipe">
<h3>wipe<a class="headerlink" href="#dipdup-schema-wipe" title="Permalink to this heading">¶</a></h3>
<p>Drop all database tables, functions and views.</p>
<p>WARNING: This action is irreversible! All indexed data will be lost!</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup schema wipe <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-schema-wipe-immune">
<span class="sig-name descname"><span class="pre">--immune</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-schema-wipe-immune" title="Permalink to this definition">¶</a></dt>
<dd><p>Drop immune tables too.</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-schema-wipe-force">
<span class="sig-name descname"><span class="pre">--force</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-schema-wipe-force" title="Permalink to this definition">¶</a></dt>
<dd><p>Skip confirmation prompt.</p>
</dd></dl>

</section>
</section>
<section id="dipdup-status">
<h2>status<a class="headerlink" href="#dipdup-status" title="Permalink to this heading">¶</a></h2>
<p>Show the current status of indexes in the database.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup status <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
</section>
<section id="dipdup-uninstall">
<h2>uninstall<a class="headerlink" href="#dipdup-uninstall" title="Permalink to this heading">¶</a></h2>
<p>Uninstall DipDup for the current user.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup uninstall <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-uninstall-q">
<span id="cmdoption-dipdup-uninstall-quiet"></span><span class="sig-name descname"><span class="pre">-q</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--quiet</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-uninstall-q" title="Permalink to this definition">¶</a></dt>
<dd><p>Use default values for all prompts.</p>
</dd></dl>

</section>
<section id="dipdup-update">
<h2>update<a class="headerlink" href="#dipdup-update" title="Permalink to this heading">¶</a></h2>
<p>Update DipDup for the current user.</p>
<div class="highlight-shell notranslate"><div class="highlight"><pre><span></span>dipdup update <span class="o">[</span>OPTIONS<span class="o">]</span>
</pre></div>
</div>
<p class="rubric">Options</p>
<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-update-q">
<span id="cmdoption-dipdup-update-quiet"></span><span class="sig-name descname"><span class="pre">-q</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--quiet</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-update-q" title="Permalink to this definition">¶</a></dt>
<dd><p>Use default values for all prompts.</p>
</dd></dl>

<dl class="std option">
<dt class="sig sig-object std" id="cmdoption-dipdup-update-f">
<span id="cmdoption-dipdup-update-force"></span><span class="sig-name descname"><span class="pre">-f</span></span><span class="sig-prename descclassname"></span><span class="sig-prename descclassname"><span class="pre">,</span> </span><span class="sig-name descname"><span class="pre">--force</span></span><span class="sig-prename descclassname"></span><a class="headerlink" href="#cmdoption-dipdup-update-f" title="Permalink to this definition">¶</a></dt>
<dd><p>Force reinstall.</p>
</dd></dl>

</section>
</section>
