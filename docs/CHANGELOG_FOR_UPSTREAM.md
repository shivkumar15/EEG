# Upstream Change Log — Mirror to Original Repository

**Working copy:** https://github.com/shivkumar15/EEG  
**Original repository:** https://github.com/student-anshu/EEG-seizure-detection

This ledger tracks changes developed here that the team must also apply to the original repository.

## 2026-11-02 — Documentation baseline (working copy)

### Files added
- `README.md` — repository overview and navigation.
- `docs/PROJECT_MASTER_PLAN.md` — research architecture, roadmap, evaluation protocol and working rules.
- `docs/DEVELOPMENT_LOG.md` — verified repository baseline and next actions.
- `docs/AI_HANDOFF.md` — context for teammates and future AI sessions.
- `docs/CHANGELOG_FOR_UPSTREAM.md` — this upstream mirror ledger.

### Code/data changes
None. No source code, dataset or model artifact was changed in this documentation-only update.

### What to mirror upstream
Copy these five documentation paths/files to the original repository. There is no code patch for this update.

### Pending implementation changes (not yet applied)
- Fix CHB-MIT annotation parsing to support actual summary-file key variants and add tests.
- Fix dataset path resolution for the sibling `dataset` directory.
- Normalize import/package execution conventions.
- Add tests and validate preprocessing, channel handling and normalization.
- Correct `.gitignore` scope and decide raw EDF storage policy.

For each later implementation fix, append exact paths, behavior before/after, test command/results and an upstream-ready patch. Do not mark upstream changes complete until confirmed by the user or verified from an upstream commit.
