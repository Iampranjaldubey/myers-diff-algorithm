#!/usr/bin/env python3
import sys

def read_lines(path):
    """Read `path` as raw bytes and split into lines per the spec's
    rules: split on b'\\n', drop a single trailing empty piece (so a
    final newline adds no phantom empty line and an empty file has
    zero lines), and keep any b'\\r' as part of the line content.
    Returns None if the file cannot be opened/read."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None

    if data == b"":
        return []

    lines = data.split(b"\n")
    if lines[-1] == b"":
        lines.pop()
    return lines

def main():
    argv = sys.argv
    if len(argv) != 4 or argv[1] not in ("lines", "highlight"):
        sys.stderr.write("usage: main.py {lines|highlight} fileA fileB\n")
        sys.exit(2)

    mode, path_a, path_b = argv[1], argv[2], argv[3]

    a_lines = read_lines(path_a)
    if a_lines is None:
        sys.stderr.write(f"error: cannot read {path_a}\n")
        sys.exit(2)

    b_lines = read_lines(path_b)
    if b_lines is None:
        sys.stderr.write(f"error: cannot read {path_b}\n")
        sys.exit(2)

if __name__ == "__main__":
    main()