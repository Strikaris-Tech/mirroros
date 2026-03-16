# Before the Agent Acts: How MirrorOS Brings Formal Governance to Enterprise AI

*By Kevin Ryan Khan & Brandon Lee Zeek — Co-founders, [Strikaris LLC](https://strikaris.com)*

*Kevin brings 10+ years of enterprise NetSuite architecture experience, specializing in SuiteScript, SDF/SuiteCloud, and large-scale ERP integrations. Brandon is a full-stack engineer with 15+ years of experience across Laravel, Python, React, and Golang, with direct NetSuite SuiteScript and backend integration experience. Together they founded Strikaris to deliver governance-first AI automation for enterprise environments.*

---

## The Problem Nobody Is Talking About Yet

Picture this: you've just deployed an AI agent to help manage your company's accounts payable queue. It's fast, it's accurate, and it's saving your team hours every week. Then one day it approves a $15,000 payment to a vendor your compliance team never cleared. Nobody told the agent it wasn't allowed to do that. Nobody built in a rule. The agent didn't hallucinate — it just acted, because nothing stopped it.

This isn't a hypothetical. It's the direction enterprise AI is heading right now, and the governance infrastructure to handle it doesn't exist yet.

That's the problem Strikaris set out to solve when we built **MirrorOS Core**.

---

## See It in Action First

Before we explain how it works, here's what it looks like.

LedgerLark is an accounts payable orchestration agent governed by MirrorOS. It processes an expense queue, routing each expense through two governance gates before any action is taken: a routing gate (which agent handles this?) and an approval gate (is that agent authorized for this amount?).

| Expense | Vendor | Result | Route |
|---|---|---|---|
| $450 | Office Supplies Co | PERMITTED | → clerk |
| $8,500 | Cloud Infra Ltd | PERMITTED | → auditor |
| $300 | Unknown Vendor Co | REJECTED | blocked at routing gate |
| $15,000 | Strikaris Dev Services | PERMITTED | → auditor |

The unknown vendor never reaches the AP system. The $15,000 expense goes to an auditor, not a clerk. Every decision is sealed in a tamper-proof ledger backed by a Merkle tree. The agent acts only on what it has been formally permitted to do.

No human reviewed these in real time. No LLM decided who was authorized. The verdicts came from formal logic — and they are deterministic. Run the same queue a thousand times and you get the same result every time.

---

## How It Works

MirrorOS is an open-source governance substrate for agentic AI systems. It sits between an agent and the systems it wants to touch. Before the agent does anything — approves a payment, updates a record, triggers a workflow — MirrorOS runs two checks:

**Gate 1 — Prolog behavioral verification.** Does this action violate any rule in the **Codex**? The Codex is a set of formal laws written in **SWI-Prolog**. Rules like "no agent can approve its own expense" or "invoices over $10,000 require an auditor." These aren't prompts. They're logic.

**Gate 2 — Z3 structural verification.** Is this action mathematically consistent with the system's axioms? **Z3** is a formal theorem prover from Microsoft Research. It doesn't guess — it proves.

If both gates pass, the agent executes. If either gate fails, the agent is blocked. The decision is sealed in a tamper-proof ledger powered by **immudb**. That record cannot be altered after the fact.

The gate verdicts are deterministic. The audit ledger is tamper-proof.

MirrorOS is agent-agnostic. It doesn't care what kind of agent is asking — a browser automation tool, a LangChain agent, a custom ERP integration, a scheduled script, or any code-driven system that can call the MRS bridge. If it declares intent, MirrorOS governs it.

---

## Why Nova Act Specifically

This is the key architectural distinction from standard Nova Act integrations.

**Standard pattern:**
```python
nova.act(
    "Go to invoices, find #1042 for $25,000, check if it's within "
    "approval limits and the vendor is verified, then approve if compliant"
)
```
The LLM decides whether to approve. The governance is inside the prompt. It's probabilistic and cannot be audited.

**MirrorOS pattern:**
```python
# Prolog already ruled — verdict is PERMITTED
# Nova Act is a cursor, not a decision-maker
nova.act(f"Approve invoice {invoice_id}")
```

By the time Nova Act receives an instruction, MirrorOS has already evaluated the action against the Codex, verified structural consistency with Z3, and sealed the verdict in immudb. Nova Act is never asked whether the action is allowed. It is only told what to click.

You cannot prompt-inject Nova Act into approving a prohibited payment. It was never asked. The gate is upstream of the model.

---

## Why This Matters — For Two Different Audiences

### For Compliance and Audit Teams

The hardest part of deploying AI in enterprise isn't the model — it's the compliance question. *How do we prove to our auditors that the AI only did what it was supposed to do?*

Today, most teams answer that with logs. But logs are descriptive — they tell you what happened after the fact. MirrorOS is prescriptive — it prevents violations before they happen and proves compliance mathematically at the moment of action.

Instead of reviewing thousands of log entries after a quarter closes, you get a sealed, verifiable decision trail where every action carries a formal proof of authorization.

### For Enterprise AI Builders

MirrorOS gives you something prompt engineering never can — a guarantee. Not because you trust the model, but because the model's actions are constrained by law, not by hope.

The authority hierarchy is explicit and never inverted:

```
Prolog (Law) → Z3 (Verification) → Python (Bridge) → Agents (Action)
```

No temperature. No hallucination. No prompt injection.

---

## Why NetSuite Specifically

At Strikaris, our consulting work lives inside NetSuite environments. We've seen firsthand what happens when automation runs without guardrails: scripts that quietly drift out of compliance, scheduled jobs with unrestricted record access, integrations that bypass approval workflows.

When an AI agent makes thousands of micro-decisions a day across your ERP environment, you need governance that operates at the same speed. MirrorOS is that layer — formal Codex rules that reflect real business policies, enforced before every action, not after.

---

## What Comes Next

Our prototype phase gave us a working foundation. What we're building toward:

- **Governed MCP usage**: MirrorOS sitting between an LLM and MCP servers means every tool call — NetSuite, Shopify, any connected system — routes through the dual gate before it executes. Formal constraints on MCP tool use, with a tamper-proof audit trail. This is the natural next layer for any team already adopting the Model Context Protocol.

- **SDF analyzer → MirrorOS pipeline**: Strikaris is building a SuiteCloud SDF project analyzer that produces deterministic snapshots of a NetSuite environment — what scripts exist, what they access, how they connect — giving governance architects the full picture before they write a single Codex rule.

- **LLM-powered risk assessment**: integrating a domain-specialized language model to provide plain-English risk assessments alongside MirrorOS's formal verdicts.

- **Expanded Codex rule sets**: covering procurement, HR, CI/CD, and financial workflows.

The core insight we want to leave builders with:

> **Trust in AI agents isn't built by making better models — it's built by making better systems around them.**

MirrorOS is that system.

---

*MirrorOS Core is open-source at [github.com/Strikaris-Tech/mirroros-core](https://github.com/Strikaris-Tech/mirroros-core). Strikaris LLC offers NetSuite governance consulting and AI automation services at [strikaris.com](https://strikaris.com). If you're building agentic systems in enterprise environments and want to talk governance, reach out.*
