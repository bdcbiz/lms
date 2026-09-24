# Almadrasa local patches on top of frappe/lms

This branch (`almadrasa/version-16`) is `frappe/lms` upstream commit
`0cd844e212e9818feacdbcdfd44677f7504dea28` (pre-@framework/ui (2026-09-02), one commit before frappe/lms v2.63.0, on the `version-16`
line; all upstream check-runs green including Server Tests) with two local
functional patches re-applied on top, in their original chronological order.

## Origin of the patches

The internal `pin-g3` branch (`git.almadrasa.ai/almadrasa/lms`, mirrored at
`bdcbiz/gitalmadrasa-almadrasa-lms`) carries **two** local commits on top of
upstream tag `v2.58.1` (`18531e16023933ccc7e033e55fe5ebb337aee446`), not one:

1. `f892fae53276af1a0bd1516d3cd902ccb640fd02` — "feat(lms): show assignment
   attachments + Al-Madrasa teacher feedback" (author: `almadrasa-bridge
   <bridge@almadrasa.ai>`, 2026-07-20). Student-facing feature: renders
   assignment attachments and teacher feedback
   (`custom_almadrasa_grade`, `custom_almadrasa_teacher_comment`,
   `custom_almadrasa_attachments`, `custom_almadrasa_corrected_attachments`)
   on the LMS Assignment view. Touches only
   `frontend/src/components/Assignment.vue` (125 lines added). Explicitly
   marked in its own commit message as "not pushed to upstream frappe/lms".
2. `6f08e74b5dc29ae38525083cad6dd5c386f62c7e` — "fix(lms): forward sqlite
   index build options" (author: `BDC`, 2026-07-24 per the pin-g3 branch
   history; the live bench checkout only exposes this one as a squashed,
   single-commit snapshot with no ancestry). Touches `lms/sqlite.py`.

Both commits are cherry-picked onto this branch **in the same order** they
appear on `pin-g3`: `f892fae5` first, then `6f08e74b`.

A literal, byte-for-byte copy of the live pin-g3 bench content (as deployed
on `bench-0001-000035-app2`, source commit `6f08e74b`) is preserved on the
`almadrasa/snapshot-pin-g3` branch of this repository for audit and
rollback reference. That snapshot's git history was squashed to one commit
by the Press build context and does not by itself show the `f892fae5`
feature commit — the full two-commit history was recovered from the
`bdcbiz/gitalmadrasa-almadrasa-lms` mirror of `pin-g3`, not from the
snapshot.

## Patch 1: assignment attachments + teacher feedback (`f892fae5`)

Adds to `frontend/src/components/Assignment.vue`:
- An "Assignment Attachments" block that renders files/images decoded from
  `assignment.data.custom_almadrasa_attachments`.
- A "Teacher Feedback" block, visible when the submission has
  `custom_almadrasa_grade`, `custom_almadrasa_teacher_comment`, and/or
  `custom_almadrasa_corrected_attachments`, rendering the grade, a
  sanitized HTML comment, and corrected attachments.

This is purely a frontend Vue change — no server-side custom fields are
defined by this app; the `custom_almadrasa_*` fields it reads are expected
to already exist as Custom Fields on the relevant LMS doctype(s) in each
site's database (created by `almadrasa_bridge`'s fixtures/migrations, not
by this app). **Losing this patch removes teacher grading feedback and
assignment attachments from the student-facing UI even if the underlying
data/fields still exist.**

## Patch 2: forward sqlite index build options (`6f08e74b`)

`frappe.search.sqlite_search.SQLiteSearch.build_index` in frappe v16 gained
new keyword arguments (`batch_size`, `is_continuation`). LMS's
`LearningSearch.build_index()` override in `lms/sqlite.py` had a fixed
`(self)` signature and dropped any arguments passed by the v16 base class,
breaking incremental/background index builds. The fix changes the override
to accept and forward `*args, **kwargs`:

```python
def build_index(self, *args, **kwargs):
    try:
        super().build_index(*args, **kwargs)
    except Exception as e:
        frappe.throw(e)
```

A regression test, `lms/tests/test_sqlite_compatibility.py`, asserts that
`build_index(batch_size=17, is_continuation=True)` forwards both keyword
arguments to the parent implementation unchanged.

(Other differences seen when first diffing the live bench snapshot against
`v2.58.1` — missing top-level dev/lint/CI files such as `.flake8`,
`README.md`, `package.json`, and generated build artifacts such as
`lms/www/_lms.html` and `lms/public/dist/**` — are artifacts of how the
pin-g3 Docker build context was pruned for the live bench, not functional
modifications, and were not carried forward.)

## Re-basing this branch onto a newer upstream commit

1. Pick a new upstream base commit on `frappe/lms` (version-16 or later
   v16-compatible line) that is not older than the commit currently live in
   production, with green check-runs (especially `Server Tests`), and no
   broken imports.
2. `git checkout -b almadrasa/version-16-rebase <new-base-sha>`
3. `git cherry-pick -x f892fae53276af1a0bd1516d3cd902ccb640fd02` (fetch it
   first from `https://github.com/bdcbiz/gitalmadrasa-almadrasa-lms` branch
   `pin-g3` if not already present locally). Resolve conflicts in
   `frontend/src/components/Assignment.vue` if the surrounding component
   has changed upstream, keeping the attachments/feedback blocks intact.
4. Re-apply the sqlite patch above to `lms/sqlite.py` if the surrounding
   code in `LearningSearch.build_index` has changed (check whether the
   override is still present with the same signature; if upstream has
   since fixed this, the patch is no longer needed — drop it and note that
   here instead), and copy `lms/tests/test_sqlite_compatibility.py` over
   unchanged.
5. `python3 -m py_compile lms/sqlite.py lms/tests/test_sqlite_compatibility.py`
6. Push the new commits onto `almadrasa/version-16` (force-push only after
   review, since this branch is deployed to production), and update the
   Press App Source / Release Group accordingly.

## Note on base commit choice (2026-09-24 rebuild)

The first attempt at this branch used `frappe/lms@2ee61568` (v2.63.0,
2026-09-10) as the base. The Press build failed at `bench build --app lms`:

```
Error: @framework/ui at .../apps/lms/frontend/node_modules/@framework/ui
does not lead anywhere. package.json's `link:../../frappe/ui` only
resolves from apps/lms/frontend.
```

`frappe/lms` started depending on a local workspace package `@framework/ui`
(a symlink to `apps/frappe/ui`) at commit `fa9b69267ac7b4ad8ec64b5a3330de003d7cc860`
("chore: resolve @framework/ui for vite, vitest and tailwind", 2026-09-07).
That package does not exist in the pinned `frappe` App Source for this
release group (`frappe/frappe@v16.23.0`) — the same class of breakage seen
on the `builder` app (see the builder fork notes for `bdcbiz/builder`).

The base was moved back to `0cd844e212e9818feacdbcdfd44677f7504dea28`
(2026-09-02, the parent of the first `@framework/ui` commit), which still
has green check-runs (including Server Tests) and is an ancestor of
`frappe/lms@version-16`. If/when the `frappe` App Source for this group is
upgraded past the point where `apps/frappe/ui` exists, this branch should
be re-rebased onto a newer `frappe/lms` commit and the `@framework/ui`
symlink re-checked.
