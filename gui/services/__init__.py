"""Cross-cutting service helpers (subprocess hardening, etc.).

These are intentionally tiny modules with no UI or domain
dependencies so they can be imported safely from anywhere in the
app, including from very early-startup code in ``gui/app.py``.
"""
