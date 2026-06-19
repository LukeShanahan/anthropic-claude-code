# Claude profile configuration — Shanahan Family Law

Version-controlled copies of the firm's Claude configuration, cleaned up from the
original `General instructions for Claude` document. Three layers, three
destinations. **None of these can be applied by editing files here** — each must
be pasted into the relevant Claude settings surface by a person.

| File | What it is | Where it goes | Who applies it |
|---|---|---|---|
| `organisation-instructions.md` | Firm-wide standing instructions — the single source of truth for posture, risk rule, voice, formatting, citation discipline | Organisation custom instructions in the **admin console** (Settings) | An org administrator — once; applies to all members automatically |
| `personal-instructions.md` | Individual working preferences (concision, directness, non-legal carve-out) | Each member's own **Claude account profile** settings | Each member, in their own account |
| `sfl-specialist/SKILL.md` | The `/sfl-specialist` operating-mode skill | Installed as a skill in each member's **Claude Desktop** | Each member (or distributed as a shared skill/plugin) |

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
