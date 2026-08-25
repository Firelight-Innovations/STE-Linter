"""ste100 -- an ASD-STE100 Simplified Technical English linter.

Analyses Markdown and CSV for the writing failures that make technical
documents imprecise: replaceable words, unfalsifiable claims, hedges,
dangling references, non-atomic sentences and zero-information filler.

Standard library only. Import submodules directly; this module deliberately
pulls in nothing, so no import order is ever forced between the submodules.
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
