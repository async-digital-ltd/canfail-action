# canfail-action

A GitHub Action that runs a [canfail](https://pypi.org/project/canfail/) declaration in one step: it plants each declared defect, checks that the check it targets notices, puts the file back, and fails when anything did not go as declared.

canfail is a separate MIT-licensed tool on PyPI and is not maintained here. This action installs a pinned version of it and wraps it with the parts every CI job running it ends up writing by hand.

## Usage

```yaml
- uses: actions/checkout@<sha> # v7
- uses: async-digital-ltd/canfail-action@<sha> # v1
  with:
    declaration: canfail.json   # default
    skip: needsXcode            # optional
```

Pin the action by its full commit SHA, with the tag in a comment, as with any action that runs in a job holding a token. A tag can be moved to other code; a SHA cannot.

The checkout must leave a clean tree. canfail edits real files and restores them, and the action refuses to start on a tree that is already changed, because a failed restore could not then be told apart from a change that was already there.

## Inputs

| Input | Default | What it does |
|---|---|---|
| `declaration` | `canfail.json` | The canfail declaration, relative to `working-directory`. |
| `working-directory` | `.` | Where the checks run, and where each break's `file` is relative to. |
| `skip` | empty | The name of a boolean field on a check. Checks that set it to `true` are dropped before the run, for checks this runner cannot run, such as `needsXcode` on Linux. |
| `fail-on-mismatch` | `true` | Fail when a verdict differs from the declaration. Set `false` to record every verdict and decide later, for example in a job that keeps a ledger of blind runs. |
| `python-version` | `3.13` | The Python canfail is installed under. |

A break expects the verdict `catches` unless it sets `expectedVerdict` to one of `catches`, `blind`, `wrong-failure` or `look`.

## Outputs

| Output | What it holds |
|---|---|
| `report` | Path to canfail's JSON report, for a later step to read or upload. |
| `declaration` | Path to the declaration actually run, after `skip`. |
| `result` | `passed`, or why it stopped: see below. |

The verdicts are also written to the job summary as a table.

## What each failure means

| `result` | Meaning |
|---|---|
| `dirty-before` | The tree had changes before anything was planted. Nothing ran. |
| `install` | pip refused to install canfail, most often because an archive did not match its pinned hash. Nothing ran. |
| `could-not-run` | canfail could not run the declaration (exit 2), or crashed, or wrote a report that cannot be read against the declaration. No check was graded. This is never a verdict. |
| `dirty-after` | A plant was not put back, or a check left a file behind. Every verdict after that point is about a tree nobody declared. |
| `mismatch` | Every plant ran and was restored, and at least one verdict differs from the declaration. The job summary names which. With `fail-on-mismatch: false` the step passes and `result` still says `mismatch`. |

canfail's own exit code is read only to recognise "could not run". It cannot say which verdicts were found (`blind` and `wrong-failure` both exit 1, and so does a crash), so verdicts come from the JSON report.

`NO_COLOR=1` is set for every check, because `expect` and `evidence` patterns are matched against plain text, and many tools colour their output when they see `CI` set, which puts escape codes inside the words a pattern looks for.

## What it installs

canfail and the two packages its verdicts depend on, didrun and restore-verified, each pinned by version and by archive hash in [`requirements.txt`](requirements.txt) and installed with `--require-hashes` into a virtual environment under `RUNNER_TEMP`.

Linux and macOS runners only.

## How it is tested

[`self-test.yml`](.github/workflows/self-test.yml) runs the action from each commit against the declarations in [`fixtures/`](fixtures), once per way it can end, including a copy of the action with one hash changed. Each case that should fail is asserted on its `result` as well as its failure, so a step that went red for another reason does not count.

## Licence

MIT. See [LICENSE](LICENSE).
