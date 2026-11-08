# Pattern catalog

Every tell, grouped by the layer it lives in. The ids in **Words and phrases** match the scanner's
rule ids, so `.unslop.json` and `scan.py` output point here. The other layers are for you to catch by
reading; no regex sees them.

Examples come from real kinds of work: an events and ticketing product, a Flask and Celery backend,
a SwiftUI app, a Next.js portfolio, open-source PRs.

<!-- unslop:off -->

## Words and phrases (the scanner flags these)

### High: remove on sight

**ai-attribution.** `Co-Authored-By: Claude`, `Generated with Claude Code`, session trailers.
The work ships under the author's name. Delete the line.

**chatbot-opener.** "Certainly!", "Great question.", "Of course!", "Happy to help." Start with the answer.

**sycophancy.** "You're absolutely right", "great catch", "what a fantastic idea". Respond to the
substance. If they were right, act on it.

**chatbot-closer.** "I hope this helps", "let me know if you have any questions", "feel free to reach
out", "happy coding". End on the last sentence that does work.

**ai-disclaimer.** "As an AI", "my knowledge cutoff". If a limit matters, state it as a fact: "I
can't see your production logs."

**ai-vocab.** delve, tapestry, testament to, realm, ever-evolving, embark, unleash, unlock the
potential, game-changer, myriad, beacon, "plays a crucial role", "in today's fast-paced world". These
words are rare in human technical writing and common in model output, so one is enough to taint a page.

> Before: Celery plays a crucial role in our ever-evolving notification stack.
> After: Celery sends every WhatsApp and push notification.

**em-dash.** House rule: none. A dash usually glues two sentences together, so split them. A comma or
parentheses works when the aside is short.

> Before: The refund job is idempotent — running it twice is safe.
> After: The refund job is idempotent. Running it twice is safe.

### Medium: usually filler, sometimes earned

**buzzword.** robust, seamless, leverage, utilize, comprehensive, cutting-edge, streamline, empower,
elevate, showcase, foster, pivotal, vibrant. Each one claims a quality without proving it. Use the
plain word (use, full, fast) or the fact that proves the claim.

> Before: A robust retry layer that seamlessly handles Razorpay failures.
> After: Failed Razorpay captures retry twice, 30 seconds apart, then mark the order failed.

**hype.** "excited to announce", "thrilled to share", "mind-blowing", "next-level". State what shipped.

**cute-line.** "And that's the whole point.", "Simple as that.", "Turns out,", "Here's the twist",
"Less config, more shipping." Aphorisms and drumrolls. End on the fact instead.

**corporate-idiom.** going forward, at the end of the day, move the needle, circle back, deep dive,
north star, low-hanging fruit, at its core. Say it literally: "next sprint", "the main goal".

**filler-phrase.** in order to (to), due to the fact that (because), is able to (can), in the event that
(if), when it comes to (for, or cut), a wide range of (many, or the actual list), the fact that (cut).

**importance-flag.** "It's important to note that", "keep in mind that", "Notably,". If it matters,
saying it is enough.

**signposting.** "Let's dive in", "here's what you need to know", "in this post I'll", "let me walk you
through". Delete and start.

**not-x-but-y.** "It's not just a checkout, it's an experience." "More than just a tool." The pattern
invents a weaker claim to knock down. State the real one.

> Before: Live Activities aren't just a nice touch, they're how fans track the queue.
> After: Fans track their queue position from the lock screen with a Live Activity.

**fancy-copula.** "serves as", "stands as", "boasts". Say "is" or "has".

**ing-tail.** ", ensuring...", ", highlighting...", ", paving the way for...". A dangling participle
that asserts a benefit nobody checked. End the sentence. If the effect is real, give it a sentence with
a subject and a verb.

> Before: Tickets are cached per event, ensuring a fast checkout.
> After: Tickets are cached per event. Checkout no longer queries Mongo for stock.

**vague-authority.** "Experts agree", "studies show", "many developers believe". Name the source or cut.

**generic-ending.** "In conclusion,", "Overall,", "the future looks bright", "only time will tell".
End on a specific next step, or just end.

**self-narration.** "This PR introduces", "This commit adds", "In this PR". The reader knows what they
are reading. Lead with the change.

**meta-reply.** "Here's the updated version:", "I've gone ahead and", "as requested". Give the thing.

**hedge-stack.** "could potentially", "might possibly", "arguably", "to some extent". Hedge once, where
the doubt is real.

**bold-label-bullet.** `- **Performance:** Performance is better...`. A bold label that the line then
repeats. Write the sentence, or use a table when every item has the same labels.

**emoji-marker.** Emoji at the start of headings or bullets. Remove. An emoji the author uses in a
caption or a chat message is their voice; leave it.

### Low: fine once, a tell in bulk

**intensifier.** very, really, truly, incredibly, extremely, significantly. Cut it, or use the number.

**exclamation.** One in a friendly message is fine. Three in a README is a tell.

**curly-quotes.** Straight quotes in docs and code-adjacent text. Curly quotes often mean pasted model output.

**rule-of-three.** "fast, reliable, and scalable". Triplets of adjectives are filler rhythm. Keep the
items that carry weight. Two is fine. One is often better.

**title-case-heading.** "Our Comprehensive Rollout Strategy". Use sentence case: "Rollout plan".

### Commit-only checks

**commit-subject-length** over 72 characters. **commit-subject-period** at the end of the subject.
**commit-subject-mood**: "Added" or "Adds" instead of the imperative "add".

### Dictation-only checks (`--dictation`)

**dictation-filler** (uh, um, I mean, you know, kind of), **self-correction** (", sorry,", "scratch
that", "or rather"), **repeated-word** ("the the").

## Sentences (read for these)

**Empty sentence.** It could appear unchanged in any other project's README. "Built with performance in
mind." Cut it, or replace it with the measurement.

**Feeling instead of mechanism.** "Makes deploys painless." What actually happens? "One command builds,
pushes to ECR and rolls the ECS service."

**Hollow specificity.** Numbers that look precise and come from nowhere ("10x faster", "99.9% fewer
errors"). Keep only numbers you can trace to a measurement.

**Synonym cycling.** fan, attendee, user, customer, guest, all meaning the same person in one section.
Pick one term and repeat it. Repetition is clarity in technical writing.

**Personified code.** "The worker wants a lock", "the plan holds it". Fine once. In bulk, name the
actor and the action: "the worker takes a Redis lock".

**Defensive opener.** "While some may see X as outdated..." Start with your point, not with someone
else's imagined objection.

**Mirror opener.** A reply that restates the question before answering. Answer.

**Passive pile-up.** "The order is validated, then the payment is captured and the ticket is issued."
Name who does it: "The API validates the order, captures the payment and issues the ticket."

**Over-compression.** "Webhook fails → retry x2 → mark failed, no email." Write the sentence: "If the
webhook fails, it retries twice, then marks the order failed without sending an email."

## Structure (read for these)

**Summary sandwich.** An intro that previews, the body, a conclusion that repeats. Keep the body.

**Heading per paragraph.** A 300-word doc with five headings. Headings are for navigation. Below about
a screen of text, you rarely need any.

**Bullets for prose.** Bullets work for parallel, scannable items. A chain of reasoning ("because",
"so", "which means") belongs in a paragraph.

**Everything in threes.** Three bullets, three adjectives, three examples, every time. Use the number
the content has.

**Uniform blocks.** Every section the same length, every bullet the same shape. Real content is lumpy.

**Question headers.** "Why does this matter?", "What's next?". Use a statement or drop the heading.

**Stock sections.** "Key takeaways", "Why this matters", "Conclusion", "Final thoughts". Merge what's
real into the body.

**Reused ending.** The same closing shape across posts or replies (a one-line moral, a rhetorical
question). Vary it, or stop one sentence earlier.

**Over-formatting.** Bold on every other phrase, nested bullets three deep, a table with one row. Each
device should mark something the reader would otherwise miss.

<!-- unslop:on -->
