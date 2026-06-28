#!/usr/bin/env python3
"""Generate N review prompts with randomized file ordering.

BugBot pattern (Cursor, 2026): presenting the same diff to multiple
reviewers with different file orderings exploits LLM positional bias —
files listed first get more attention. Randomizing ordering across N
agents ensures full coverage regardless of position.

Usage:
    # From git diff:
    git diff --name-only HEAD~1 | python3 shuffle-review-files.py 3

    # From file list:
    echo -e "a.py\nb.py\nc.py" | python3 shuffle-review-files.py 4

    # Output: N lines, each a pipe-separated randomized file list
    # Agent 1: c.py|a.py|b.py
    # Agent 2: b.py|c.py|a.py
    # Agent 3: a.py|b.py|c.py

Source: Cursor BugBot (cursor.com/blog/building-bugbot) — 8 parallel
passes with randomized diff ordering → majority voting → 52%→70%+
resolution rate.
"""

import sys
import random
import hashlib

def main():
    n_agents = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    files = [line.strip() for line in sys.stdin if line.strip()]

    if not files:
        print("No files provided on stdin", file=sys.stderr)
        sys.exit(1)

    # Use deterministic seeds per agent index for reproducibility
    # (same files + same N → same orderings, useful for debugging)
    base_seed = hashlib.md5("".join(sorted(files)).encode()).hexdigest()

    for i in range(n_agents):
        seed = f"{base_seed}-{i}"
        rng = random.Random(seed)
        shuffled = files.copy()
        rng.shuffle(shuffled)
        print("|".join(shuffled))

if __name__ == "__main__":
    main()
