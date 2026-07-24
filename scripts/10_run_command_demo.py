from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.commands.language_stub import parse_language_command
from upkie_mujoco_course.commands.scripted_commands import forward_command, stand_command


def main() -> None:
    parser = argparse.ArgumentParser(description="高层命令接口 demo")
    parser.add_argument("--text", default="前进")
    args = parser.parse_args()
    print(f"站立命令: {stand_command()}")
    print(f"前进命令: {forward_command()}")
    print(f"语言命令: {parse_language_command(args.text)}")


if __name__ == "__main__":
    main()

