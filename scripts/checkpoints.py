#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Checkpoints CLI - Complement for Multi-Agent Team Workflow
Automates the creation of handoff documentation and session snapshots.
"""

import argparse
import datetime
import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional

CHECKPOINTS_DIR = Path("docs")
CLAUDE_MD = Path("CLAUDE.md")
PHASE_PLAN = Path("docs/phase1-continuation-plan.md")

def run_command(cmd: List[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

def get_git_summary():
    status = run_command(["git", "status", "--short"])
    diff = run_command(["git", "diff", "HEAD", "--stat"])
    return status, diff

def create_checkpoint(name: str, notes: str, next_steps: str):
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    filename = f"checkpoint-{timestamp}-{name.replace(' ', '_')}.md"
    filepath = CHECKPOINTS_DIR / filename
    
    status, diff = get_git_summary()
    
    content = f"""# Session Checkpoint: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
## 🏷️ Name: {name}

## 📝 Session Notes
{notes}

## 🎯 Next Steps for Agent
{next_steps}

## 🛠️ Git State Summary
### Modified Files
```
{status if status else "No changes"}
```

### Stats
```
{diff if diff else "No changes"}
```

## 🔄 How to Continue
1. Read this file: `{filepath}`
2. Review `{PHASE_PLAN}`
3. Run tests: `pytest tests/ -q`
"""
    
    filepath.write_text(content, encoding="utf-8")
    print(f"✅ Checkpoint created: {filepath}")
    
    # Update CLAUDE.md
    if CLAUDE_MD.exists():
        original = CLAUDE_MD.read_text(encoding="utf-8")
        pattern = r"## 📍 Current Project State \(HANDOFF\).*?---"
        new_state = f"""## 📍 Current Project State (HANDOFF)

**Last Updated**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
**Latest Checkpoint**: `{filepath}`
**Next Steps**: {next_steps.split('.')[0] if next_steps else "See checkpoint"}

---"""
        updated = re.sub(pattern, new_state, original, flags=re.DOTALL)
        CLAUDE_MD.write_text(updated, encoding="utf-8")
        print(f"✅ CLAUDE.md updated with latest state.")

    return filepath

def main():
    parser = argparse.ArgumentParser(description="Checkpoints CLI for Agent Handoff")
    subparsers = parser.add_subparsers(dest="command")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new session checkpoint")
    create_parser.add_argument("name", help="Brief name for the checkpoint (e.g. Task2-Done)")
    create_parser.add_argument("--notes", "-n", default="Work completed in this session.", help="Detailed notes about work done")
    create_parser.add_argument("--next", "-s", default="Continue with the next task in the plan.", help="Specific next steps for the next agent")

    # Status command
    subparsers.add_parser("status", help="Show current project handoff status")

    args = parser.parse_args()

    if args.command == "create":
        create_checkpoint(args.name, args.notes, args.next)
    elif args.command == "status":
        if CLAUDE_MD.exists():
            content = CLAUDE_MD.read_text(encoding="utf-8")
            match = re.search(r"## 📍 Current Project State \(HANDOFF\)(.*?)---", content, re.DOTALL)
            if match:
                print("📍 Current Handoff Status:")
                print(match.group(1).strip())
            else:
                print("❌ No handoff state found in CLAUDE.md")
        else:
            print("❌ CLAUDE.md not found")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
