"""Retired on 2026-11-01 with the ledger: state/ is plain files now.

A running session snapshots its hook list and would run this path on every tool
call, so the file stays as a no-op until no such session is left. settings.json
no longer names it.
"""
