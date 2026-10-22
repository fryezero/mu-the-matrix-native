# reconstructed/skill (NATIVE-SKILL-001)

The client's skill table loader, the game side of the skill bar and the skill tooltip, restated in C from the
pinned restored text (capture09 `2bd5f2e9…3724`) and second section (run10 `c985e2e6…a0672f`). Finding:
[docs/research/client-skills.md](../../docs/research/client-skills.md).

| Function | Client routine | Status |
|---|---|---|
| `mu_skill_parse_row` | Skill(Kor) row parser `0x01170ca5` (vtable `0x01ac1d7c` slot 2), lexical casts `0x00cd8314` / `0x010c2ce2`, name `0x010bb278` | verified |
| `mu_skill_stats_ok` | stat requirements `0x0109228f` | verified |
| `mu_skill_mana_ok` | mana / AG check `0x01091692` | verified |
| `mu_skill_delay_start`, `mu_skill_ready`, `mu_skill_delay_tick` | StartSkillDelay `0x01696aca` (+ `0x01696ca6`), IsSkillReady `0x016969e9`, tick `0x01696e06` | verified |
| `mu_skill_special_ok` | the class special cases of the bar's isUse `0x01096e55` | verified |
| `mu_skill_bar_feed` | the bar feed `0x00c58797` (SetSkillSlot) | verified |
| `mu_skill_icon_of` | the skill icon draw `0x01097130` (bitmap and cell) | verified |
| `mu_skill_tooltip_build`, `mu_skill_wrap`, `mu_skill_tooltip_html` | the tooltip builder `0x0117da56`, the wrap `0x011ff794`/`0x01193941`, the popup `0x00c1f2b0` | verified (sprintf and the GDI width are modelled boundaries) |
| `mu_skill_select` | main onSelectSkill `0x00c70f4b` | static |

```sh
make -C reconstructed/skill                                   # libclientskill
python -m unittest discover -s reconstructed/skill -p 'test_*.py'
tools/python/bin/python scripts/validate_skill.py --snapshot "$SNAP" --mutations   # Unicorn
```

No client bytes or game data: the routines take the records the caller loaded.
