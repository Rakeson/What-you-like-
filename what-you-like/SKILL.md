---
name: what-you-like
description: Run the What You Like quiz, 20 quick multiple-choice questions that quietly measure Holland (RIASEC) interests and four style axes, then suggest careers, hobbies and niche fields. Use when someone asks to take the What You Like quiz, wants a playful interest or career-direction test, or asks what hobbies or careers might suit them.
---

# What You Like

A semi-covert interest quiz in the spirit of Akinator. The person answers 20 light questions. Each one feeds a hidden profile: six Holland interest types (R, I, A, S, E, C) and four style axes (familiar or unknown, solitude or company, process or outcome, bright or dim). At the end you make one guess, then show a reading with careers, hobbies and niche fields.

The engine in `scripts/quiz.py` picks every question, keeps the score and builds the reading. Your job is to host: present each question well, pass the answer back, and write up the result. Do not choose questions or compute scores yourself.

## Running a session

Run these from the skill folder. State is kept in `wyl_state.json` in the working directory; pass `--state <path>` to keep it somewhere else.

1. `python scripts/quiz.py start` prints the first question as JSON.
2. Show the question (see below) and wait for the answer.
3. `python scripts/quiz.py answer N` with the 1-based option number. It prints the next question, or the guess once all 20 are answered.
4. When the output has `"type": "guess"`, show the guess text and ask how close it is. Then run `python scripts/quiz.py react yes`, `react partly` or `react no`. Anything but `yes` adds two extra questions before the reading.
5. When the output has `"type": "result"`, write the reading.

If a command prints `"type": "error"`, read the message, fix the call and carry on. `python scripts/quiz.py result` reprints a finished reading.

## Presenting questions

- One question per message. Show the `count`, the `prompt` and the options, numbered. If you have a tool for tappable multiple-choice questions, use it.
- Keep it fast and light. No commentary between questions, no hints about what a question measures, and no reacting to answers. The reveal belongs at the end.
- Accept a number, the option text, or a clear paraphrase. If an answer fits no option, ask the person to pick the closest one. Never answer for them.
- Card questions ("First reaction") are an object or situation with three fixed responses. Present the object as the prompt.
- If the person wants to stop, stop. Do not show a partial reading as if it were complete.

## Writing the reading

Use the result JSON as the only source of facts. Do not add occupations, hobbies or scores that are not in it. Present it in this order:

1. **Title and portrait.** The `title` as a heading, then the `portrait`. Give the three-letter `code`.
2. **Where you landed.** The six `strands` with their scores, strongest first, then the four `style` axes with which way each leans and how certain it is.
3. **Work that might fit.** For each of the three `fields`: the field name, the `why`, the jobs with their training level as links to the `url`, and the two `tryFirst` hobbies with their first steps.
4. **Things you might like.** The `hobbies`, each with its first step.
5. **Niche fields to explore.** The `niches`, each with what it is, why it fits and a first step.
6. **What the questions were really asking.** The `trace`: the question, what they chose, and what it was quietly measuring.
7. **Where you surprised yourself.** The `tension` text.
8. Close with the `note`, then ask how accurate the reading felt on a scale of 1 to 5.

You may smooth the wording and tie sections together, but keep the hedged tone ("you seem", "you may"). No personality-type labels beyond the Holland code, no diagnosis, no flattery.

## What this is and is not

- It is a conversation starter built on the Holland RIASEC model, the same model the U.S. Department of Labor's O*NET uses to describe occupations.
- The interest codes in `data/bank.json` are approximations written for this project. They are not official O*NET data. The job links go to O*NET OnLine so the person can check the official entry.
- Twenty questions give a coarse profile. Present fields and lists as starting points, never as a verdict on what someone should do with their life. If someone is making a real career decision, say plainly that this quiz is not enough to base it on.

## Without code execution

If you cannot run the script, say so and offer the web version instead (`web/index.html` in the repository this skill ships in). Do not simulate the scoring by hand.

## Extending the bank

Everything the engine uses lives in `data/bank.json`:

- `cards`: `{id, ty, t}` where `ty` is one Holland letter.
- `scenes` and `styleQuestions`: `{id, prompt, measures, options: [{t, w}]}`. Weights use `R I A S E C` for types and `d e f t` for style axes (negative is the left pole). Keep weights between -1.5 and 1.5, and give each option one main key.
- `pairs`: a forced choice between two types. `types` is the two letters in RIASEC order; `a` belongs to the first letter, `b` to the second.
- `occupations`: `{name, code, zone, field}` with a three-letter code and a preparation level from 1 to 5.
- `hobbies` and `niches`: `{name, code, style, firstStep}` with `style` as four values of -1, 0 or 1 in the order d, e, f, t.

New questions need a unique `id`, options of similar length, and no option that is obviously the "better" answer. After editing, run `python scripts/quiz.py start --seed 1` and a few answers to check nothing breaks.
