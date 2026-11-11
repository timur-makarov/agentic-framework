"""The guard hook (plan, section 15): what depends on a flag or a refspec anywhere in a Bash command.

Guards prevent mistakes; they are not a boundary. Permission rules in .claude/settings.json cover what a rule
can express, and this hook covers the rest.
"""

import shlex

WRAPPERS = {"sudo", "env", "command", "exec", "time", "nohup", "nice"}
SEPARATORS = {";", "&&", "||", "|", "&", "|&"}


def commands(line):
    """The simple commands in a command line, as word lists: split on ;, &&, ||, | and newlines outside quotes."""
    found = []
    for part in line.splitlines():
        lexer = shlex.shlex(part, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        try:
            tokens = list(lexer)
        except ValueError:  # an unclosed quote: judge the words we have
            tokens = part.split()
        words = []
        for token in tokens:
            if token in SEPARATORS:
                if words:
                    found.append(words)
                words = []
            elif not set(token) <= set("()"):
                words.append(token)
        if words:
            found.append(words)
    return [_unwrap(words) for words in found]


def _unwrap(words):
    """Drop `sudo`, `env`, VAR=value and the like, so `sudo git push -f` is still a push."""
    while words and (words[0] in WRAPPERS or ("=" in words[0] and not words[0].startswith("-"))):
        words = words[1:]
    return words


def _git(words):
    """(subcommand, its arguments) for a git command, skipping git's own options such as -C path."""
    i = 1
    while i < len(words) and words[i].startswith("-"):
        i += 2 if words[i] in ("-C", "-c", "--git-dir", "--work-tree") else 1
    return (words[i], words[i + 1:]) if i < len(words) else (None, [])


# Options that take a value: their value is not a flag or a positional argument.
VALUED = {
    "commit": {"-m", "-F", "-c", "-C", "-t", "--message", "--file", "--template", "--author", "--date"},
    "push": {"-o", "--push-option", "--repo", "--receive-pack", "--exec"},
}


def _short_flags(args, sub):
    """The single-letter flags in args. A letter that takes a value ends its group: -m"now" is -m, not -n."""
    letters = []
    for a in args:
        if not a.startswith("-") or a.startswith("--"):
            continue
        for ch in a[1:]:
            letters.append(ch)
            if f"-{ch}" in VALUED.get(sub, ()):
                break
    return "".join(letters)


def _positional(args, sub):
    """Arguments that are not options or option values."""
    found, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a.startswith("-"):
            skip = a in VALUED.get(sub, ())
        else:
            found.append(a)
    return found


def _push(args, base, branch):
    if "--no-verify" in args:
        return "git push --no-verify skips the project's hooks"
    if any(a in ("--force", "--force-with-lease", "--force-if-includes") or a.startswith("--force-with-lease=")
           for a in args) or "f" in _short_flags(args, "push"):
        return "a force push rewrites history others may have"
    if "--all" in args or "--mirror" in args:
        return f"git push --all pushes {base}, which only the engine's merge changes"
    positional = _positional(args, "push")
    if any(a.startswith("+") for a in positional[1:]):
        return "a +refspec is a force push"
    for refspec in positional[1:]:
        target = refspec.split(":", 1)[-1].removeprefix("refs/heads/")
        if target == base or (":" not in refspec and refspec in ("HEAD", "@") and branch == base):
            return f"a push to {base}: only the engine's merge changes it"
    if len(positional) <= 1 and branch == base:
        return f"a push from {base}: only the engine's merge changes it"
    return None


def deny(line, base, branch):
    """Why a command line is denied, or None (plan, section 15)."""
    for words in commands(line):
        if not words:
            continue
        if words[0] == "git":
            sub, args = _git(words)
            if sub == "push":
                reason = _push(args, base, branch)
                if reason:
                    return reason
            elif sub == "commit" and ("--no-verify" in args or "n" in _short_flags(args, "commit")):
                return "git commit --no-verify skips the project's hooks"
            elif sub == "merge" and branch == base:
                return f"a merge into {base} goes through the engine: rail advance merges a shipped ticket"
        elif words[0] == "gh":
            if words[1:3] == ["pr", "merge"]:
                return "gh pr merge merges outside the engine: rail advance merges a shipped ticket"
            if len(words) > 1 and words[1] == "api" and any("/merge" in w and "/pulls/" in w for w in words[2:]):
                return "a merge through gh api goes around the engine: rail advance merges a shipped ticket"
    return None
