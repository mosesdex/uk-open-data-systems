"""Groundtruth platform.

Resolves two missing joins in UK government data: place (where) and entity (who).
Every source used here must return data to a completely unauthenticated request.
That rule is enforced in code, not merely documented -- see fetch.py.
"""
__version__ = "0.1.0"
