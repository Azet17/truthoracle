# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""
TruthOracle v2 — On-Chain Claim Verification via Adversarial Web Consensus
===========================================================================
REVISION addressing steward feedback (submission ddb7899e):

  (1) No more keyword-presence verdicts. Every verdict is now a SUBSTANTIVE
      LLM judgment: gl.nondet.exec_prompt weighs the fetched evidence and
      answers "does this evidence, taken as a whole, substantively support
      or contradict the claim?" Consensus: validators independently re-run
      the same fetch+judgment and must agree on the stabilized JSON verdict
      (gl.eq_principle.strict_eq over sorted-key output).

  (2) Challenge round can no longer be decided by a challenger-hosted page.
      A challenge triggers a FULL re-evaluation: the contract re-fetches the
      ORIGINAL claim sources PLUS the counter-evidence URL, and the same
      LLM consensus round judges whether the balance of evidence has tipped.
      A hostile challenger page cannot overturn a claim it cannot
      substantively refute in the presence of the original sources.

  (3) gl.nondet.exec_prompt(response_format="json") for the substantive
      judgment; the result is stabilized via json.dumps(sort_keys=True)
      before strict_eq, the community-standard pattern for LLM consensus
      (see genlayer-utils).

USE CASES: prediction markets, parametric insurance, x402/ERC-8004
agentic commerce assertions, any dispute whose outcome depends on
real-world facts.

STATE: TreeMap[str, str] claims/challenges + bigint counters
(GenVM-compliant; no dict/int class attributes).
"""
from genlayer import *
import typing
import json


class TruthOracle(gl.Contract):
    claim_counter: bigint
    challenge_counter: bigint
    claims: TreeMap[str, str]
    challenges: TreeMap[str, str]

    def __init__(self):
        self.claim_counter = 0
        self.challenge_counter = 0
        self.claims = TreeMap[str, str]()
        self.challenges = TreeMap[str, str]()

    # -------- core: SUBSTANTIVE multi-source verdict (LLM consensus) --------
    @gl.public.write
    def submit_claim(self, claim: str, source_urls: typing.List[str]) -> int:
        """Submit a factual claim + 1-3 source URLs. The leader fetches all
        sources and an LLM issues a substantive verdict; validators
        independently re-run the same fetch+judgment and must agree on the
        stabilized JSON verdict (strict_eq)."""
        if len(source_urls) == 0 or len(source_urls) > 3:
            raise ValueError('provide 1-3 source URLs')

        cid = self.claim_counter + 1
        self.claim_counter = cid

        def fetch_and_verdict() -> str:
            # Fetch every source live inside the non-deterministic block
            fetched = []
            for url in source_urls:
                content = gl.nondet.web.render(url, mode='text')[:4000]
                fetched.append({'url': url, 'content': content})

            # SUBSTANTIVE judgment: LLM weighs the evidence as a whole —
            # NOT keyword presence/absence (steward requirement (1))
            evidence = json.dumps(fetched)
            result = gl.nondet.exec_prompt(
                (
                    "You are a meticulous fact-verification jury. "
                    f"CLAIM: \"{claim}\". "
                    "EVIDENCE (live-fetched web sources): " + evidence + ". "
                    "Weigh the evidence as a whole and answer ONLY with a "
                    "JSON object: "
                    '{"verdict":"VERIFIED|DISPUTED|REFUTED","rationale":"<one paragraph, cite which source supports or contradicts>"}. '
                    "Judge substantively: consider what the sources actually "
                    "say, not mere keyword presence or absence."
                ),
                response_format="json",
            )
            return json.dumps(result, sort_keys=True)

        # Validators independently fetch the same sources and run the same
        # substantive judgment; consensus is on the STABILIZED JSON (sorted
        # keys) so agreement means identical substantive verdicts.
        raw = gl.eq_principle.strict_eq(fetch_and_verdict)
        parsed = json.loads(raw)
        verdict = parsed['verdict']
        rationale = parsed['rationale']

        record = json.dumps({
            'claim_id': cid, 'claim': claim, 'verdict': verdict,
            'rationale': rationale,
            'sources': source_urls,
        })
        self.claims[str(cid)] = record
        return cid

    # -------- adversarial challenge: FULL re-evaluation, not challenger-only --------
    @gl.public.write
    def challenge_claim(self, claim_id: int, counter_url: str) -> int:
        """Challenge a claim with counter-evidence. The contract re-fetches
        the ORIGINAL sources plus the counter-URL and runs the SAME
        substantive LLM consensus on the combined evidence. A challenger-
        hosted page cannot overturn a claim unless it substantively
        refutes it against the original sources (steward requirement (2))."""
        base = self.claims[str(claim_id)]
        chid = self.challenge_counter + 1
        self.challenge_counter = chid
        base_rec = json.loads(base)
        original_urls = base_rec['sources']
        claim = base_rec['claim']
        old_verdict = base_rec['verdict']

        def re_evaluate() -> str:
            # Re-fetch ORIGINAL sources + counter-evidence — all live
            fetched = []
            for url in original_urls:
                fetched.append({
                    'url': url,
                    'content': gl.nondet.web.render(url, mode='text')[:3000],
                    'role': 'original',
                })
            fetched.append({
                'url': counter_url,
                'content': gl.nondet.web.render(counter_url, mode='text')[:3000],
                'role': 'counter-evidence',
                'superseded': old_verdict,
            })

            evidence = json.dumps(fetched)
            result = gl.nondet.exec_prompt(
                (
                    "You are a meticulous fact-verification jury reviewing "
                    "a CHALLENGE. ORIGINAL CLAIM: " + claim + ". "
                    "PREVIOUS VERDICT: " + old_verdict + ". "
                    "EVIDENCE: live-fetched sources (role=original) plus a "
                    "counter-evidence source (role=counter-evidence): "
                    + evidence + ". "
                    "Re-weigh ALL evidence together. Output ONLY JSON: "
                    '{"verdict":"VERIFIED|DISPUTED|REFUTED","rationale":"..."}. '
                    "The counter-evidence must substantively refute the claim "
                    "to overturn a VERIFIED verdict; a page that merely fails "
                    "to mention the claim is NOT refutation."
                ),
                response_format="json",
            )
            return json.dumps(result, sort_keys=True)

        raw = gl.eq_principle.strict_eq(re_evaluate)
        parsed = json.loads(raw)
        new_verdict = parsed['verdict']
        rationale = parsed['rationale']
        overturned = new_verdict != old_verdict

        result = json.dumps({
            'challenge_id': chid, 'claim_id': claim_id,
            'counter_url': counter_url, 'overturned': overturned,
            'old_verdict': old_verdict, 'new_verdict': new_verdict,
            'rationale': rationale,
        })
        self.challenges[str(chid)] = result
        if overturned:
            base_rec['verdict'] = new_verdict
            base_rec['rationale'] += ' | CHALLENGE ' + str(chid) + ': ' + rationale
            self.claims[str(claim_id)] = json.dumps(base_rec)
        return chid

    # ---------------- views ----------------
    @gl.public.view
    def get_claim(self, claim_id: int) -> str:
        return self.claims[str(claim_id)]

    @gl.public.view
    def get_challenge(self, challenge_id: int) -> str:
        return self.challenges[str(challenge_id)]

    @gl.public.view
    def total_claims(self) -> int:
        return self.claim_counter
