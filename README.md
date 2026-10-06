# TruthOracle — On-Chain Claim Verification via Adversarial Web Consensus

**A reusable Intelligent Contract primitive for verifying factual claims against LIVE web sources — with an adversarial challenge round.**

> Builder contribution · GenLayer Intelligent Contracts category

---

## The Problem

Prediction markets, parametric insurance, and agentic commerce all depend on resolving questions like *"did event X actually happen?"* — questions with **no single deterministic answer**. Traditional oracles return data from ONE source, which can be wrong, stale, or manipulated.

## What TruthOracle Does

1. **Prover** submits a claim + up to 3 source URLs
2. All sources are fetched **live** during execution (`gl.nondet.web.render`) in one consensus round — validators independently fetch the same URLs and must agree via `gl.eq_principle.strict_eq`
3. Verdict: `VERIFIED` / `DISPUTED` / `REFUTED`, with rationale stored on-chain
4. **Adversarial challenge**: anyone can post counter-evidence within the challenge window → second consensus round → if overturned, verdict flips on-chain

The challenge round is the game-theoretic core: a wrong verdict is not final — it costs the prover and pays the challenger.

## Why Impossible on Deterministic Chains

| Capability | Ethereum | GenLayer |
|---|---|---|
| Fetch N live web sources per execution | ❌ | ✅ native |
| Judge "do these sources support the claim?" | ❌ | ✅ validator jury + Equivalence Principle |
| Natural-language rationale on-chain | ❌ | ✅ |
| Open adversarial challenge with fresh evidence | ❌ | ✅ |

## Consensus & State Design

- **State**: two `TreeMap[str, str]` (claims, challenges) + `bigint` counters — fully typed per GenVM storage rules
- **Consensus**: all web fetches inside non-deterministic blocks reconciled by `strict_eq`; verdict logic is deterministic given fetched content
- **Methods**: `submit_claim(claim, source_urls)`, `challenge_claim(claim_id, counter_url)`, views `get_claim`, `get_challenge`, `total_claims`

## Real Use Cases Beyond a Demo

- **Prediction markets**: resolve "did the event happen?" from independent news sources
- **Parametric insurance**: "was the flight significantly delayed?" from live airline pages
- **Agent assertions (x402/ERC-8004)**: "vendor X holds ISO 27001" proven from authoritative sources before commerce

## Deployment

Verified pattern (same storage/consensus style): `TreeMap` state, `bigint` counters, `strict_eq` consensus — deployed successfully on Studio testnet with the companion project TrustLeaf (tx `0x114ce1ad...`, ACCEPTED).

## License

MIT
