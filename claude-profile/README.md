# Claude profile configuration — Shanahan Family Law

Version-controlled copies of the firm's Claude configuration, cleaned up from the
original `General instructions for Claude` document. Three layers, three
destinations. **None of these can be applied by editing files here** — each must
be pasted into the relevant Claude settings surface by a person.

| File | What it is | Where it goes | Who applies it |
|---|---|---|---|
| `organisation-instructions.md` | Firm-wide standing instructions — the single source of truth for posture, risk rule, voice, formatting, citation discipline | Organisation custom instructions in the **admin console** (Settings) | An org administrator — once; applies to all members automatically |
| `personal-instructions.md` | Individual working preferences (concision, directness, non-legal carve-out) | Each member's own **Claude account profile** settings | Each member, in their own account |
| `sfl-specialist/SKILL.md` | The `/sfl-specialist` operating-mode skill — the firm's **single authoritative** specialist skill | Installed as a skill in each member's **Claude Desktop** | Each member (or distributed as a shared skill/plugin) |

There is no mechanism for anyone — including an admin — to push instructions into
another member's *personal* profile. Firm-wide reach is achieved through the
organisation layer; the personal layer is each individual's own.

## What changed from the original

- **Non-legal carve-out moved to the organisation layer.** As originally drafted,
  the carve-out sat only in the personal instructions, where it was overridden by
  the organisation rule "apply this to every conversation." It now lives at the
  organisation level (scope reworded), so it actually takes effect.
- **Concision reconciled with the risk rule.** Personal concision now explicitly
  yields to the hardwired risk rule for substantive legal analysis.
- **Skill de-duplicated against the organisation layer.** Posture, risk rule,
  voice, audience flex and formatting are stated once (organisation) and
  referenced by the skill, to stop the three layers drifting apart. The skill
  keeps only what is genuinely skill-specific: the load workflow, the
  read-every-document discipline, the length budget, and the python-docx code.
- **Skill folder loading generalised.** No longer hardcoded to "Luke's Desktop";
  it points to each practitioner's local copy of `01 Family Law Resources`
  (synced from the firm's SharePoint library), so the skill works for any member
  on Claude Desktop with Cowork, not just the Principal.
- **Citation sources widened** to include the Federal Register of Legislation
  alongside AustLII and the FCFCOA site, with the `[unverified — check before
  sending]` flag carried into both the organisation block and the skill.
- **Skill is now a valid `SKILL.md`** with YAML frontmatter (`name`,
  `description`) so it can be installed directly.
- **python-docx snippet** now sets single line spacing and justification on the
  `Normal` style so every paragraph inherits the house style.
- **Precedence stated explicitly** in the personal block (organisation
  instructions prevail on conflict).

## Consolidation of the two skills

The firm previously had two overlapping skill definitions for the same practice:
the older `australian-family-law.md` (held in Google Drive / SharePoint under
`Family Law Resources/`) and this `sfl-specialist` skill. They have been merged
into **one authoritative skill — `sfl-specialist/SKILL.md`**. Decisions made in
the merge:

- **Name:** `sfl-specialist` kept (it is the slash command in use);
  `australian-family-law` is **superseded**.
- **Persona:** the old "Tony" persona was dropped — the operating-mode framing
  carries the role without it.
- **Folded in from the old skill:** the three task workflows (property,
  parenting, DV), the tiered-corpus concept, and the known-gaps/limitations
  section.
- **Corpus handling improved:** the old skill hard-listed specific editions
  (e.g. the 38th-ed Act current to October 2023) that had already drifted from
  the current corpus. The consolidated skill keeps the tiered-priority *concept*
  but defers to the live `references/firm_material_index.md` for what is actually
  present, so it does not go stale.
- **FCFCOA forms rule landed.** The original request — that whenever a family law
  form is prepared, the current official pro forma from
  https://www.fcfcoa.gov.au/fl/forms is used — is now built into the skill's
  "Court forms (pro formas)" section, rather than living only in the old Drive
  file.

**Still outstanding (needs you):** the old `australian-family-law.md` in Google
Drive / SharePoint should be **retired** so the two do not diverge again. I can
read but not delete or overwrite files in Drive/SharePoint from here, so that
removal is a manual step in your account.
