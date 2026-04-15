"""
Compile .po translation files into .mo binary catalogs.

Usage:
    cd thesis/unilabs
    python compile_translations.py

This uses the babel library directly (no CLI / subprocess needed),
so it works on restricted machines without pybabel on PATH.
"""

import os
import sys


def main():
    # Ensure we run from the unilabs/ directory regardless of cwd
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    translations_dir = os.path.join('app', 'translations')

    if not os.path.isdir(translations_dir):
        print(f"ERROR: translations directory not found at {translations_dir}")
        sys.exit(1)

    try:
        from babel.messages.mofile import write_mo
        from babel.messages.pofile import read_po
    except ImportError:
        print("ERROR: babel is not installed.  Run:  pip install Flask-Babel")
        sys.exit(1)

    compiled = 0
    for root, _dirs, files in os.walk(translations_dir):
        for fname in files:
            if not fname.endswith('.po'):
                continue

            po_path = os.path.join(root, fname)
            mo_path = po_path[:-3] + '.mo'

            print(f"  Compiling {po_path} -> {mo_path}")

            with open(po_path, 'rb') as po_file:
                catalog = read_po(po_file)

            with open(mo_path, 'wb') as mo_file:
                write_mo(mo_file, catalog)

            compiled += 1

    if compiled == 0:
        print("WARNING: No .po files found to compile.")
    else:
        print(f"\nDone - compiled {compiled} catalog(s) successfully.")


if __name__ == '__main__':
    main()
