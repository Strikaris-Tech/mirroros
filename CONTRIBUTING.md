# Contributing to MirrorOS

Thank you for contributing. MirrorOS is AGPL-3.0 — by submitting a pull request you agree your changes will be released under the same license.

---

## Ways to Contribute

- **New adapters** — build integrations with real systems (accounting, HR, CI/CD, ERP). See `adapters/mock_bank.py` as a template.
- **Domain rule sets** — write Prolog compliance rules for your domain. See `examples/accounting_demo/accounting_compliance.pl`.
- **Bug reports** — open an issue with reproduction steps.
- **Documentation** — improve `docs/` or add examples.

Issues labelled `good-first-pulse` are a good entry point.

---

## Development Setup

```bash
git clone https://github.com/your-org/mirroros
cd mirroros
pip install -r forge/requirements.txt
```

Run the test suite:

```bash
pytest
```

Run a single demo pulse:

```bash
cd forge && python -c "
from mrs.bridge.mrs_bridge import MRSBridge
bridge = MRSBridge()
result = bridge.check_authorization('clerk', 'approve_payment', {'amount': 200})
print(result)
"
```

---

## Pull Request Guidelines

1. All public methods need docstrings: Purpose, Args, Returns, Violations.
2. Every MRS interaction must be logged to `memory/reasoning_log.json` via `MRSBridge`.
3. Never assert facts directly to Prolog — always use `MRSBridge.assert_fact()`.
4. Never modify `mrs/prolog/Codex_Laws.pl` or `mrs/prolog/concordance.pl` without a paired change to `mrs/verifier/essence_runes.py` and a passing boot check.
5. Keep the authority hierarchy intact: Prolog → Z3 → Python → Agents. Never invert it.

---

## Adapter Contract

An adapter is a Python module that translates external system actions into MRS-verifiable pulses.

```python
class MyAdapter:
    def describe_actions(self) -> list[dict]:
        """Return list of action definitions the adapter can execute."""
        ...

    def execute(self, action: str, params: dict, authorization: dict) -> dict:
        """
        Execute an action only after MRS authorization is confirmed.

        Args:
            action: Action name (must match a Prolog action_in_domain fact)
            params: Action parameters
            authorization: MRS authorization result (must be permitted)

        Returns:
            Execution result dict

        Violations:
            - Must raise if authorization['permitted'] is False
        """
        ...
```

---

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
