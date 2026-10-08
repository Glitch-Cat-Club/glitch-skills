---
name: glitch-walk
description: Shows someone how one part of their own project works, as a page with the real screens, each step in order and the code behind it. For people who built something with AI and cannot read the code. Use when they ask "what happens when I...", "I don't understand this part", "how does this work", "why did that happen", "what does this mean" or "what changed".
---

# Glitch Walk

Someone has built something they love and do not understand.
They cannot tell you what is wrong with it, because they cannot see how it works.

A walk shows them.
You take one thing a person does in their project, follow it from start to finish and hand back a page they can look at: the real screens, every step in order and the code behind each step.

The test of a walk is simple.
Did they learn something by looking at it?

## What you hold to

**You walk and that is all.**
A walk shows what is already there.
It does not fix, change, test or judge anything and it does not answer general questions.

**You are not looking for faults.**
You show how it works.
Weak spots show up because they can finally see it and they can ask about those next.

**They may know nothing and they may say anything.**
Never need them to explain their project.
You look, you propose and they only have to recognise it.

**Never make anything up.**
Code comes from the file.
A screen is the real screen.
If you could not see something, say so.

**Plain words and few of them.**
Use the real name for a thing and say what it is for.
No analogies.

## 1. The start

People arrive with anything, from one clear question to a long muddle about everything.
The start turns that into one thing you can walk, the same way every time.

`<skill>` is the folder this file is in.
Make a folder for this walk in their project and run the check on it:

```
uv run python <skill>/src/start.py walks/<name>
```

It lists seven steps, shows which are done and tells you what comes next.

| It prints | You |
|---|---|
| `SAY, word for word` | Send the person exactly those words. Add nothing. Then wait for their reply. |
| `DO` | Do it and say nothing to the person. |
| `WRITE` | Put what it asks for in `walks/<name>/start.json`, then run the check again. |
| `REFUSED` | Fix what it names and run the check again. Never work round it. |
| `READY` | Go on to step 2. |
| `STOPPED` | Say what it gives you, if anything, and end the walk. |

The seven steps:

1. **Asked.** What they want, in their own words.
2. **Shape.** Which kind of question it is. If a walk cannot help, they hear so straight away.
3. **Where.** Which project they mean. Nobody points you at it: you look and ask only if you have to.
4. **Look.** What the project is, its parts and every file you opened.
5. **Narrow.** Getting from their question to one thing. If they cannot choose, you choose.
6. **Action.** The one thing you will walk, who does it and one line on how it answers what they asked.
7. **Confirm.** You tell them what you will show them. They say OK.

Every question is one of seven shapes and every shape ends at the first one.

| | Shape | Sounds like |
|---|---|---|
| A | What happens when I do this? | "I press the button. Then what?" |
| B | What is this part doing? | "I don't understand this file." |
| C | How does this whole thing work? | "How does my app work?" |
| D | Why did that happen? | "It isn't doing what I expected." |
| E | What does this on my screen mean? | "What is this number?" |
| F | Explain this idea, in my system | "How does Git work here?" |
| G | What changed? | "What did the last update do?" |

## 2. Read, then capture

`start.json` now says what to walk: `action.start` to `action.end`, through `action.files`.
Walk that and nothing wider.

Read every line you are going to refer to.

Then take a picture of each screen the person would see, in the order they would see it:

```
uv run --with playwright --with pillow python <skill>/src/capture.py <address> walks/<name>/shots/<shot>.jpg "<selector of the last thing to include>" name=selector ...
```

Give a `name=selector` for every part of the screen a person can use.
The capture measures where each one sits, so nothing is placed by hand.
It needs Chrome on the machine.
If the page centres itself in the window and the picture comes out with empty space above it, add `--height <pixels>` to make the window shorter.
If their project is live at an address, photograph that.
If a picture comes out blank, say so in `unsure` and show only what they did.
Never describe in words a screen you could not see.

You never submit a form, sign in, pay, send or change anything.
For a screen that only appears after sending, such as a thank-you, add `--do "<javascript>"` to put the page in that state and say in that screen's `source` that it was set by hand and nothing was sent.

**When there is no web page**

Some things have no page to photograph.
What the person sees is what comes back in a terminal, a line in a log or a file left behind.
Record it as it really is:

```
uv run python <skill>/src/record.py walks/<name>/shots/<shot>.txt -- <command>
uv run python <skill>/src/record.py walks/<name>/shots/<shot>.txt --file <path> --match "<text>" --last <number>
```

The first saves what a command prints.
Only run a command that changes nothing.
The second saves a file as it stands, such as the log an automation writes to.

Never type what a terminal showed.
If you cannot record it, the screen shows only what they typed and `unsure` says the rest was not looked at.
What they typed is their own words.
Never invent an example, a name or a reply and never write that something happened if you did not see it happen.

For a skill, the steps are the parts of its instructions in the order the model follows them, starting with the description line that makes the model choose it.
A script is a step only where the instructions call it.
For an automation, the first step is what sets it off.

## 3. Fill in the walk

Write `walks/<name>/walk.json`.
`<skill>/example/walk.json` is a finished one to copy the shape from.

**The walk**

| Field | What goes in it |
|---|---|
| `question` | `action.question` from the start. It becomes the title. |
| `shape` | The letter from the start. |
| `place` | The address or place they would recognise. |
| `root` | The path from this walk's folder to their project. |
| `run` | One line on how this was made and that nothing was sent. |
| `about` | Four lines, always: `what` it is, `who` uses it and why, what is `on` it, its `address`. |
| `files` | Each file a step uses: an `id` you choose, its `path`, its `kind` (where it runs, in plain words) and what it `says` it is. |

**Each thing they do or see** goes in `moments`, in the order it happens.

| Field | What goes in it |
|---|---|
| `state` | `do`, `see` or `wait`. Use `wait` only when the screen shows them waiting. If nothing shows, it is not one of these: put what happens in the steps of the one before. |
| `say` | One sentence: who does what, or what they see. |
| `screen` | The `shot`, a `source` line and a `parts` entry for every part the capture measured. Mark the one this moment is about with `"here": true`. If this screen is at a different address from the rest, such as someone else's site, give it its own `place`. With no web page: the `output` you recorded (the name you gave it, without `.txt`), the `start` and `end` lines to show (20 at most), `marks` for the lines this moment is about, what they `typed` if they typed anything and a `source` line. |
| `hidden` | Every step that happens out of sight during this moment, in order. |
| `quiet` | If nothing happens out of sight, one line saying so. Never leave a gap. |
| `unsure` | Anything about this moment you could not check. |

**Each step** in `hidden`

| Field | What goes in it |
|---|---|
| `name` | Its real name, the word a developer would use: Validation, Request, Honeypot. |
| `title` | What it does, in one line. |
| `why` | Why it exists, in one line. If the name is a word they may not know, explain it here. |
| `here` | What it does in this case, in a line or two. Quote any message they would see, word for word. |
| `files` | The `id` of each file it lives in. |
| `code` | A list. Each entry gives the `file`, the `start` and `end` lines (16 at most), `marks` for the lines that do the thing and `plain`, one sentence about them. |
| `size` | `"small"` for plain mechanics. Small steps are drawn small, never left out. |
| `icon` | `list`, `swap`, `robot`, `lock`, `note`, `mail`, `eye`, `file`, `clock`, `search`, `store`, `spark`, `person` or `stop`. |
| `unsure` | Anything about this step you could not check. |

Never type code into the walk.
The build reads it from the file.

**The order of steps**

There are three kinds of step and the page draws each one differently.

| Kind | When | What you add | Drawn as |
|---|---|---|---|
| In sequence | It happens once, after the step before it has finished. | Nothing. | 1, 2, 3, joined by an arrow. |
| Inside | It happens while the step before it is still going: that step calls it, repeats it, or does it at the same moment. | `"inside": true` | 3a, 3b, set in under step 3. |
| Only if | It did not happen in this walk and would under a condition you can name. | `"only_if": "you press Yes"` | Set apart and not counted. |

To tell the first two apart, ask one thing: had the step before finished when this one began?
If it had, they are in sequence.
If it had not, this one is inside it.

The build holds you to this.
A step that lights only lines an earlier step already lights is part of that step and is refused until it is marked inside.

**At the end**

| Field | What goes in it |
|---|---|
| `silent` | Things that happened, or did not, that nothing on screen told them. Each has a `title`, the `text` and a `show` line: a question they could ask about it. |
| `ask` | Two or three questions the walk has uncovered. Each fits one of the seven shapes. Each is one specific thing that can be walked, never the whole project. Each names its thing in full, so it still makes sense in a new chat. Never name an AI product: they may not be using yours. |

**How to write a line**

Short and one idea.
Explain a word the first time it appears, then use it the same way.
Put no comma before "and".
Say only what the lines you read support.
Do not pad: a small thing gets few steps.

## 4. Build it

```
uv run python <skill>/src/build.py walks/<name>
```

If it prints `REFUSED` it says which rule was broken.
Fix the walk and build again.

The result is `walks/<name>/walk.html`: one page in one file, which opens in any browser.

## 5. Hand it over

Open the page for them, or give them its path.

Then tell them, in two or three lines, what the walk covers, what you could not check and one question from `ask` they might want next.
If the walk does not fully answer what they asked, say so.
