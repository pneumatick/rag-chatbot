<script>
  import { onMount, tick } from "svelte";

  let queryText = "";
  let entries = []; // { id, query, answer, sources, error, streaming: boolean }
  let loading = false;
  let controllerRef = null;
  let health = "checking"; // checking | online | offline
  let scrollEl;

  let showIndexPanel = false;
  let dirname = "user-docs";
  let indexLoading = false;
  let indexMessage = "";
  let indexIsError = false;

  onMount(async () => {
    try {
      const res = await fetch("/api/health");
      health = res.ok ? "online" : "offline";
    } catch {
      health = "offline";
    }
  });

  async function scrollToBottom() {
    await tick();
    if (scrollEl) scrollEl.scrollTo({ top: scrollEl.scrollHeight, behavior: "smooth" });
  }

  async function submitQuery() {
    const q = queryText.trim();
    if (!q || loading) return;

    const id = crypto.randomUUID();
    entries = [...entries, { id, query: q, reasoning: "", answer: "", sources: [], error: null, streaming: true }];
    queryText = "";
    loading = true;
    await scrollToBottom();

    controllerRef = new AbortController();

    try {
      console.log("Sending POST...")
      const res = await fetch("/api/query/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
        signal: controllerRef.signal,
        duplex: "half"
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `HTTP ${res.status}: ${res.statusText}`);
      }
      console.log("Response received: ", res)

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        while (true) {
          const newlineIndex = buffer.indexOf("\n\n");
          if (newlineIndex === -1) break;

          const line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 2);

          console.log(line.trim())
          if (line.trim().startsWith("data:")) {
            try {
              const event = JSON.parse(line.slice(5).trim());

              console.log(event)
              switch (event.event) {
                case "started":
                  entries[entries.length -1].sources = event.sources || []
                  await scrollToBottom();
                  break;
                case "reasoning":
                  entries[entries.length - 1].reasoning += event.message;
                  await scrollToBottom();
                  break;
                case "chunk":
                  entries[entries.length - 1].answer += event.message;
                  await scrollToBottom();
                  break;
                case "completed":
                  loading = false;
                  controllerRef = null;
                  await scrollToBottom();
                  break;
              }
            } catch {
              // Capture Parse errors for malformed SSE lines
              console.error("Could not parse the following: ", line.slice(5).trim());
            }
          }
        }
      }

    } catch (err) {
      if (err.name !== "AbortError") {
        const errorMessage = err.message || "Something went wrong.";
        entries = entries.map((e) =>
          e.id === id ? { ...e, error: errorMessage } : e
        );
      }
    } finally {
      await scrollToBottom();
    }
  }

  function handleKeydown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitQuery();
    }
  }

  async function addDocs() {
    if (indexLoading) return;
    indexLoading = true;
    indexMessage = "";
    indexIsError = false;

    try {
      const res = await fetch("/api/add_docs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dirname })
      });
      const data = await res.json();

      if (res.ok) {
        indexMessage = `Indexed ${data.chunks_added} passage${data.chunks_added === 1 ? "" : "s"} from "${dirname}".`;
      } else {
        indexIsError = true;
        indexMessage = data.error || "Indexing failed.";
      }
    } catch {
      indexIsError = true;
      indexMessage = "Couldn't reach the backend. Is it running?";
    } finally {
      indexLoading = false;
    }
  }
</script>

<div class="shell">
  <header>
    <div class="title-block">
      <h1>Marginalia</h1>
      <p class="tagline">ask questions of your own writing</p>
    </div>
    <div class="header-actions">
      <button class="status" class:online={health === "online"} class:offline={health === "offline"} title="Backend status">
        <span class="dot" />
        {health === "checking" ? "connecting" : health}
      </button>
      <button class="ghost-btn" on:click={() => (showIndexPanel = !showIndexPanel)}>
        {showIndexPanel ? "close" : "index writings"}
      </button>
    </div>
  </header>

  {#if showIndexPanel}
    <div class="index-panel">
      <label>
        <span>Folder to index</span>
        <input type="text" bind:value={dirname} placeholder="user-docs" />
      </label>
      <button class="brass-btn" on:click={addDocs} disabled={indexLoading}>
        {indexLoading ? "indexing…" : "add to archive"}
      </button>
      {#if indexMessage}
        <p class="index-message" class:error={indexIsError}>{indexMessage}</p>
      {/if}
    </div>
  {/if}

  <main bind:this={scrollEl}>
    {#if entries.length === 0}
      <div class="empty">
        <p class="empty-mark">⟡</p>
        <p>Nothing asked yet. Your archive is waiting to be read.</p>
      </div>
    {/if}

    {#each entries as entry (entry.id)}
      <section class="entry">
        <p class="entry-query">{entry.query}</p>

        {#if entry.error}
          <p class="errata">Errata — {entry.error}</p>
        {:else if entry.answer != []}
          <div class="answer">{entry.answer}</div>
        {:else}
          <p class="thinking"><span>reading through the archive</span><span class="ellipsis" /></p>
          {#if entry.sources.length > 0}
            <div class="sources">
              <p class="sources-label">excerpts consulted</p>
              <div class="card-row">
                {#each entry.sources as source, i}
                  <article class="card" style="--tilt: {(i % 2 === 0 ? 1 : -1) * (1 + (i % 3))}deg">
                    <span class="card-number">{i + 1}</span>
                    <p class="card-text">{source}</p>
                  </article>
                {/each}
              </div>
            </div>
          {/if}
          <div class="answer">{entry.reasoning}</div>
        {/if}
      </section>
    {/each}
  </main>

  <footer>
    <textarea
      rows="1"
      placeholder="What patterns emerge in…"
      bind:value={queryText}
      on:keydown={handleKeydown}
      disabled={loading}
    />
      <button class="ask-btn" on:click={submitQuery} disabled={loading || (controllerRef && loading)}>
      ask
    </button>
  </footer>
</div>

<style>
  .shell {
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-width: 760px;
    margin: 0 auto;
  }

  header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    padding: 2rem 1.5rem 1.25rem;
    border-bottom: 1px solid rgba(236, 231, 216, 0.1);
  }

  .title-block h1 {
    font-family: var(--font-display);
    font-weight: 500;
    font-size: 2rem;
    letter-spacing: 0.01em;
    margin: 0;
  }

  .tagline {
    margin: 0.25rem 0 0;
    font-size: 0.85rem;
    color: var(--chalk-dim);
    font-style: italic;
    font-family: var(--font-display);
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  .status {
    background: none;
    border: 1px solid rgba(236, 231, 216, 0.15);
    color: var(--chalk-dim);
    border-radius: 999px;
    padding: 0.35rem 0.7rem;
    font-size: 0.7rem;
    font-family: var(--font-mono);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    cursor: default;
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--chalk-dim);
  }

  .status.online .dot {
    background: var(--moss);
    box-shadow: 0 0 6px var(--moss);
  }

  .status.offline .dot {
    background: var(--rust);
    box-shadow: 0 0 6px var(--rust);
  }

  .ghost-btn {
    background: none;
    border: 1px solid rgba(236, 231, 216, 0.2);
    color: var(--chalk);
    border-radius: 999px;
    padding: 0.35rem 0.85rem;
    font-size: 0.75rem;
    letter-spacing: 0.02em;
    cursor: pointer;
    transition: border-color 0.15s ease, color 0.15s ease;
  }

  .ghost-btn:hover {
    border-color: var(--brass);
    color: var(--brass);
  }

  .index-panel {
    padding: 1rem 1.5rem;
    background: var(--ink-raised);
    border-bottom: 1px solid rgba(236, 231, 216, 0.1);
    display: flex;
    align-items: flex-end;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .index-panel label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.7rem;
    color: var(--chalk-dim);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .index-panel input {
    background: var(--ink);
    border: 1px solid rgba(236, 231, 216, 0.2);
    color: var(--chalk);
    border-radius: 6px;
    padding: 0.5rem 0.65rem;
    font-family: var(--font-mono);
    font-size: 0.85rem;
    min-width: 200px;
  }

  .index-panel input:focus {
    outline: none;
    border-color: var(--brass);
  }

  .brass-btn {
    background: var(--brass);
    color: var(--ink);
    border: none;
    border-radius: 6px;
    padding: 0.55rem 1rem;
    font-weight: 600;
    font-size: 0.85rem;
    cursor: pointer;
    transition: filter 0.15s ease;
  }

  .brass-btn:hover:not(:disabled) {
    filter: brightness(1.1);
  }

  .brass-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .index-message {
    font-size: 0.8rem;
    color: var(--moss);
    margin: 0;
    flex-basis: 100%;
  }

  .index-message.error {
    color: var(--rust);
  }

  main {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem 1.5rem 2rem;
    display: flex;
    flex-direction: column;
    gap: 2.25rem;
  }

  .empty {
    margin: auto;
    text-align: center;
    color: var(--chalk-dim);
  }

  .empty-mark {
    font-size: 1.75rem;
    color: var(--brass);
    margin: 0 0 0.5rem;
  }

  .entry-query {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    color: var(--brass);
    margin: 0 0 0.75rem;
  }

  .entry-query::before {
    content: "› ";
  }

  .thinking {
    color: var(--chalk-dim);
    font-style: italic;
    font-family: var(--font-display);
  }

  .ellipsis::after {
    content: "";
    animation: dots 1.4s steps(4, end) infinite;
  }

  @keyframes dots {
    0% { content: ""; }
    25% { content: "."; }
    50% { content: ".."; }
    75% { content: "..."; }
  }

  .answer {
    font-family: var(--font-display);
    font-size: 1.08rem;
    line-height: 1.7;
    color: var(--chalk);
    white-space: pre-wrap;
  }

  .entry.streaming .thinking {
    display: none;
  }

  .entry.streaming .answer {
    animation: fadeIn 0.3s ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .sources {
    margin-top: 1.5rem;
  }

  .sources-label {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--chalk-dim);
    margin: 0 0 0.75rem;
  }

  .card-row {
    display: flex;
    gap: 1rem;
    overflow-x: auto;
    padding: 0.5rem 0.25rem 1rem;
  }

  .card {
    flex: 0 0 200px;
    background: var(--paper);
    color: #2a2417;
    border-radius: 3px;
    padding: 0.85rem 0.9rem 0.7rem;
    position: relative;
    transform: rotate(var(--tilt, 0deg));
    box-shadow: 0 6px 14px rgba(0, 0, 0, 0.35);
    transition: transform 0.2s ease;
  }

  .card:hover {
    transform: rotate(0deg) translateY(-3px);
  }

  .card-number {
    position: absolute;
    top: 0.5rem;
    right: 0.6rem;
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--rust);
  }

  .card-text {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    line-height: 1.5;
    margin: 0;
    max-height: 130px;
    overflow-y: auto;
  }

  .errata {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    color: var(--rust);
  }

  footer {
    display: flex;
    align-items: flex-end;
    gap: 0.75rem;
    padding: 1rem 1.5rem 1.5rem;
    border-top: 1px solid rgba(236, 231, 216, 0.1);
  }

  textarea {
    flex: 1;
    resize: none;
    background: transparent;
    border: none;
    border-bottom: 1px solid rgba(236, 231, 216, 0.3);
    color: var(--chalk);
    font-family: var(--font-display);
    font-size: 1.05rem;
    padding: 0.5rem 0.1rem;
    max-height: 8rem;
  }

  textarea:focus {
    outline: none;
    border-bottom-color: var(--brass);
  }

  textarea::placeholder {
    color: var(--chalk-dim);
    font-style: italic;
  }

  .ask-btn {
    background: var(--rust);
    color: var(--chalk);
    border: none;
    border-radius: 999px;
    padding: 0.65rem 1.4rem;
    font-size: 0.85rem;
    letter-spacing: 0.03em;
    cursor: pointer;
    transition: filter 0.15s ease;
  }

  .ask-btn:hover:not(:disabled) {
    filter: brightness(1.15);
  }

  .ask-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
</style>
