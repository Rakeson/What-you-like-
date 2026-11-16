# What You Like

A 20-question interest quiz in the spirit of Akinator. Light questions quietly measure six Holland interest types (RIASEC) and four style axes, then the quiz makes a guess and suggests careers, hobbies and niche fields.

This repository holds two versions that share one question bank:

| Path | What it is |
|---|---|
| `skills/what-you-like/` | A Claude skill. Claude hosts the quiz in conversation and a small Python engine does the question picking and scoring. |
| `web/index.html` | A single-file web page. No sign-in, no server and no AI call: everything is computed in the browser. |

## What is in the bank

- About 100 questions: 36 object cards, 26 small scenes, 8 style questions and 30 forced choices, plus a reverse check and a preparation question. Each session draws 20.
- 182 occupations in 11 fields, each with a three-letter Holland code and a preparation level.
- 197 hobbies and 27 niche fields, each with a first step to try.

## Use the skill

Copy the `skills/what-you-like` folder into your skills directory (for Claude Code, `~/.claude/skills/`), or zip that folder and upload it wherever your Claude app accepts custom skills. Then ask Claude to run the What You Like quiz.

The engine needs Python 3.8 or later and no extra packages. You can also drive it by hand:

```bash
cd skills/what-you-like
python scripts/quiz.py start          # first question
python scripts/quiz.py answer 2       # pick option 2, get the next question
python scripts/quiz.py react partly   # after the guess: yes, partly or no
python scripts/quiz.py result         # reprint the reading
```

Each command prints one JSON object. Session state is saved to `wyl_state.json`; use `--state` to change the path and `--seed` to fix the question order.

## Use the web page

Open `web/index.html` in a browser, or host it on any static host such as GitHub Pages. The page loads its fonts from Google Fonts and needs nothing else.

## How it works

1. Eight object cards and nine short scenes build a first profile.
2. Three forced choices are picked to separate whichever interest types are running closest.
3. A reverse check asks what would wear the person out fastest and flags a contradiction if that is also their strongest type.
4. The quiz makes one guess. If the person says it is off, two more forced choices are asked.
5. Occupations, hobbies and niche fields are ranked by how closely their profile matches the person's.

To add questions or library entries, edit `skills/what-you-like/data/bank.json`. The format is described at the end of `skills/what-you-like/SKILL.md`. The web page carries its own copy of the same data inside `web/index.html`.

## Limits

This is a mirror, not a diagnosis. Twenty questions give a coarse profile, so treat the results as starting points.

The interest codes here are approximations written for this project in the style of O*NET interest codes. They are not official O*NET data. Job names link to [O*NET OnLine](https://www.onetonline.org/), where the official entries are.

## License

MIT. See `LICENSE`.
