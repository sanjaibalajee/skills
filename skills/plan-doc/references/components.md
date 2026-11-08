# Components

Every block the template's CSS already styles. Copy the snippet, fill it, delete what you don't
need. Don't invent new classes or inline colors. If a doc needs something new, add it to
`assets/template.html` with tokens so every future doc gets it.

Required blocks are in the template already: header, `#recommendation`, `#outcome`, `#changes`,
`#steps`, `#questions`, `#changelog`. The ones below are optional. Use one only when the plan has
that kind of content.

## Order

Put the blocks in this order. Skip any you don't need:

1. header (status, date, author, repo, title, lede)
2. recommendation
3. what happens when this ships
4. status (only for a progress or audit doc)
5. what changes
6. steps
7. decisions
8. diagram (next to the step or decision it explains, if that reads better)
9. risks
10. out of scope
11. open questions
12. changelog

## Status values

`data-s` on the header pill: `draft`, `in-review`, `approved`, `in-progress`, `done`, `dropped`.
Change it in place as the plan moves, and add a changelog line.

## Tags

`<span class="tag" data-k="...">` with one of these:

| `data-k` | color | use for |
| --- | --- | --- |
| `add`, `done`, `low`, `easy` | green | new file, finished item, low risk, easy to undo |
| `edit`, `open`, `med`, `medium` | amber | changed file, open item, medium risk |
| `delete`, `blocked`, `high`, `hard` | red | removed file, blocked item, high risk, hard to undo |
| anything else | muted | neutral labels like `env`, `migration`, `job`, `config` |

The text inside the tag is what readers see. Keep it to one lowercase word.

## Decision

Use one for each choice that someone could reasonably argue the other way, and always when it's
hard to undo (wire format, public ids, data shape, auth boundaries, a new paid dependency).

```html
<section id="decisions">
  <h2>Decisions</h2>
  <div class="decision">
    <h3>Retry in Celery, not in the webhook handler <span class="tag" data-k="easy">easy to undo</span></h3>
    <p>The handler has to answer Razorpay within 5 seconds. A Celery task can back off for minutes without holding the request.</p>
    <p class="alts">Considered: retrying inline (blocks the response), a separate queue service (new infra for one job).</p>
  </div>
</section>
```

## Risks

```html
<section id="risks">
  <h2>Risks</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>risk</th><th>level</th><th>what we do about it</th></tr></thead>
      <tbody>
        <tr><td>Duplicate tickets if a retry races the original</td><td><span class="tag" data-k="high">high</span></td><td>Idempotency key on <code>payment_id</code>; second write is a no-op.</td></tr>
      </tbody>
    </table>
  </div>
</section>
```

## Status (issue by issue)

For progress reports, audits and "is it fixed yet" docs. One row per issue, with its state.

```html
<section id="status">
  <h2>Status</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>issue</th><th>state</th><th>note</th></tr></thead>
      <tbody>
        <tr><td>Refund email sent twice</td><td><span class="tag" data-k="done">fixed</span></td><td>Dedup on <code>refund_id</code>, shipped in #412.</td></tr>
        <tr><td>Live Activity stuck after event ends</td><td><span class="tag" data-k="open">open</span></td><td>Needs an end push from the worker.</td></tr>
      </tbody>
    </table>
  </div>
</section>
```

## Out of scope

```html
<section id="out-of-scope">
  <h2>Out of scope</h2>
  <ul>
    <li>Retrying failed refunds. Same pattern, separate change.</li>
  </ul>
</section>
```

## Diagram

Draw one only when the plan is about how things connect (a request path, a queue, a state machine).
Prefer inline SVG with the template's classes so it themes itself and works offline. Keep it small:
three to seven nodes. Mark the part that changes with `node hot`.

```html
<figure class="diagram">
  <svg viewBox="0 0 640 120" role="img" aria-label="Razorpay webhook to Flask, which queues a Celery retry task">
    <defs><marker id="arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="8" markerHeight="8" orient="auto"><path class="arrow" d="M0 0 8 4 0 8z"/></marker></defs>
    <rect class="node" x="8" y="36" width="150" height="48" rx="6"/><text x="83" y="65" text-anchor="middle">Razorpay webhook</text>
    <rect class="node" x="244" y="36" width="150" height="48" rx="6"/><text x="319" y="65" text-anchor="middle">Flask handler</text>
    <rect class="node hot" x="480" y="36" width="150" height="48" rx="6"/><text x="555" y="65" text-anchor="middle">Celery retry task</text>
    <path class="edge" d="M158 60H240" marker-end="url(#arr)"/><path class="edge" d="M394 60H476" marker-end="url(#arr)"/>
  </svg>
  <figcaption>The handler only enqueues. The retry task owns backoff.</figcaption>
</figure>
```

Mermaid is fine for bigger graphs. The source stays readable if the script can't load:

```html
<pre class="mermaid">
flowchart LR
  A[Razorpay webhook] --> B[Flask handler] --> C[(Celery queue)] --> D[retry task]
</pre>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script>window.mermaid && mermaid.initialize({ startOnLoad: true, theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "neutral" });</script>
```

`plandoc.py fragment` drops both script tags, because artifact viewers render `pre.mermaid` themselves.

## Code

Only for an interface the reader must agree on (a payload, a function signature, a config shape) or
a short algorithm. Not for implementation detail.

```html
<pre><code>{
  "event": "payment.captured",
  "payment_id": "pay_29QQoUBi66xm2f",
  "attempt": 2
}</code></pre>
```

## Timeline

Only with real dates or a real deadline. Never invent week numbers to look thorough.

```html
<section id="timeline">
  <h2>Timeline</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>when</th><th>what</th></tr></thead>
      <tbody>
        <tr><td><span class="mono">2026-11-14</span></td><td>Merged and deployed behind <code>RETRY_WEBHOOKS</code></td></tr>
      </tbody>
    </table>
  </div>
</section>
```

## Note

A muted aside under any block: `<p class="note">Razorpay retries on its side too, for 24 hours.</p>`
