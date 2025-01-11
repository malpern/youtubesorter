"""Pylint plugin to check for command class inheritance."""

from typing import TYPE_CHECKING
from astroid import nodes
from pylint.checkers import BaseChecker

if TYPE_CHECKING:
    from pylint.lint import PyLinter


class CommandChecker(BaseChecker):
    """Checker for command class inheritance rules."""

    name = "command-checker"
    priority = -1
    msgs = {
        "W5001": (
            "Command class %s should inherit from YouTubeCommand in src.commands",
            "invalid-command-inheritance",
            "All command classes should inherit from YouTubeCommand in src.commands",
        ),
        "W5002": (
            "Creating new abstract base class %s in commands package is not allowed",
            "new-command-base-class",
            "Do not create new abstract base classes in the commands package. Use YouTubeCommand.",
        ),
    }

    def visit_classdef(self, node: nodes.ClassDef) -> None:
        """Visit class definitions."""
        # Only check classes in the commands package
        if not node.root().file.endswith(".py") or "src/commands" not in node.root().file:
            return

        # Skip the YouTubeCommand class itself
        if node.name == "YouTubeCommand":
            return

        # Check if class is abstract
        if any(
            base.name in ("ABC", "ABCMeta") for base in node.bases if hasattr(base, "name")
        ) or any(
            decorator.name == "abstractmethod"
            for decorator in node.decorators.nodes
            if hasattr(decorator, "name")
        ):
            self.add_message(
                "new-command-base-class",
                node=node,
                args=node.name,
            )

        # Check inheritance
        bases = [base.as_string() for base in node.bases]
        if "YouTubeCommand" not in " ".join(bases):
            self.add_message(
                "invalid-command-inheritance",
                node=node,
                args=node.name,
            )


def register(linter: "PyLinter") -> None:
    """Register the checker with pylint."""
    linter.register_checker(CommandChecker(linter))
