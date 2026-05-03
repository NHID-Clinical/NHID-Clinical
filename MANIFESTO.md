# Why Payers Hang Up on AI Agents (And How to Fix It)

*By Brianna Baynard*

I used to work at a dental health insurer's customer service operation. Here's what I saw almost every day:

A provider's office would call in with a routine eligibility question. An AI agent would answer on their end—handling the initial intake, gathering basic info. Then it would try to transfer the call to us.

**We'd hang up.**

Not out of rudeness. Out of legal fear. Our policy was simple: **We don't speak to AI agents.** If it's not a human provider on the line, we disconnect and ask them to call back with a human representative.

This created a problem nobody talks about: **Impersonation Latency.** Time wasted because nobody can figure out who—or what—is on the other end of the call.

## The Real Problem

Here's what's actually happening in healthcare customer service right now:

1.  **Payers reject AI calls** because they don't have a framework for accepting them safely.
2.  **Providers deploy AI agents anyway** to reduce their own call handling costs.
3.  **Calls get dropped.** Providers get frustrated. Payers waste time on rejection protocols that don't exist in writing.

Nobody wins.

The legal concern is real: *"If an AI agent calls us and we talk to it, are we violating HIPAA by disclosing PHI to an unauthorized entity?"*

The answer: *Probably not, if the AI properly identifies itself and the payer has authorized it.*

But nobody has written down **how** an AI should identify itself, **when** it should do it, or **what** a payer should accept or reject. So payers default to: "No AI. Period."

## The Solution: NHID-Clinical v1.1

I built a standard called **NHID-Clinical (Non-Human Identity Disclosure)** that gives payers a framework to say "yes" to AI calls—safely.

Here's what it does:

### 1. Proactive Disclosure (Before You Ask for Anything)
The AI must identify itself **before** asking for sensitive data (NPI, Member ID, Claim Number).

* **Good:** "Hello, I'm an automated assistant for [Payer]. I can help with eligibility or claims status. To get started, what can I help you with?"
* **Bad:** "Hello. What's your NPI?" ... [Provider gives NPI] ... "Oh, by the way, I'm a robot."

### 2. No Deceptive Tricks
The AI can't use fake sounds (keyboard typing, breathing, "thinking" delays) to seem human. But it **can** use natural speech patterns and conversational pacing.

* **Allowed:** "One moment while I search your claim..."
* **Not allowed:** (Sound of typing) "Hmm, let me see..."

### 3. Safe Escalation
If the provider asks to speak to a human, the AI must:
* Acknowledge the request immediately.
* Generate a reference number so they don't have to repeat everything.
* Either transfer them or clearly state hours of operation + offer callback.

### 4. Audit Trail
Keep logs proving disclosure happened and when. That's it.

## Why This Matters

* **For Payers:** You get a governance baseline. You can tell your legal team "yes" to AI calls, because you have a standard that covers disclosure, escalation, and audit trails. You reduce provider friction. You eventually reduce call costs.
* **For Providers:** You can deploy AI agents to your own intake process without worrying they'll cause problems downstream.
* **For Compliance:** You have something to point to if a regulator asks "how do you handle AI calls?"

## What Happens Next

Right now, most payers don't accept AI calls. That's defensible today.

But in 12-18 months, as more providers deploy AI intake agents and call volume keeps climbing, payers will have to make a choice: Keep rejecting AI calls (and lose operational efficiency), or accept them—but only if they meet a clear baseline.

**NHID-Clinical v1.1 is that baseline.**

I'm releasing it early—before the market demands it—because the best time to set the standard is before everyone's arguing about it.
