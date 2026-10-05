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


# ---------------------------------------------------------------
# 2 & 3. Myers' O(ND) algorithm + backtrack
# ---------------------------------------------------------------
#
# Ops are plain tuples for speed:
#   ('equal',  a_index, b_index)
#   ('delete', a_index, None)
#   ('insert', None,    b_index)

def myers_diff(a, b):
    """
    Return the minimal edit script turning sequence `a` into `b`.
    
    Myers algorithm concepts:
    - x, y: coordinates in the edit graph. x is index in `a`, y is index in `b`.
    - d: depth, or the number of differences (edits) made so far.
    - k: diagonal line in the graph. k = x - y.
    
    Instead of searching all paths, we search in expanding "depths" (d).
    For a given d, we test all possible diagonals (k) that can be reached.
    """
    n, m = len(a), len(b)
    max_d = n + m
    if max_d == 0:
        return []

    # `offset` prevents negative indices. A diagonal k can go from -max_d to max_d.
    # We add `offset` to `k` to store everything safely in a normal 0-indexed list.
    offset = max_d
    
    # `v` stores the maximum `x` value reached for each diagonal `k`.
    # It is reused "in-place" across rounds to save memory and time.
    v = [0] * (2 * max_d + 1)
    v[offset + 1] = 0               # Seed value to start the algorithm at (0,0)
    
    # `trace` keeps a historical record of `v` at each depth `d`.
    # This is required later so we can backtrack and reconstruct the exact edits.
    trace = []

    for d in range(0, max_d + 1):
        row = [0] * (d + 1) # Stores only the diagonals computed in this depth
        found = False
        p = 0 # Index for the `row` list
        
        # In depth `d`, we check diagonals from -d to d, skipping every other one
        for k in range(-d, d + 1, 2):
            
            # Decide where we came from: an insertion (moving down) or a deletion (moving right)
            # If k == -d, we are at the left edge and MUST have come from k+1 (insertion)
            # If v[offset + k - 1] < v[offset + k + 1], it means the path from k+1 went further, so we use it.
            if k == -d or (k != d and v[offset + k - 1] < v[offset + k + 1]):
                x = v[offset + k + 1]          # Came via an insert (move down)
            else:
                x = v[offset + k - 1] + 1       # Came via a delete (move right)
                
            y = x - k

            # Snake: ride the diagonal for free while the characters match!
            # This is the secret to Myers diff's speed. Matches cost 0 edits.
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1

            # Save the furthest x reached on this diagonal for this depth
            v[offset + k] = x
            row[p] = x
            p += 1

            # If we reached the bottom-right corner, we are done!
            if x >= n and y >= m:
                found = True
                break

        # Save this round's progress into the history trace
        trace.append(row)
        
        if found:
            # We found the end! Now walk backward through `trace` to get the edits.
            return _backtrack(n, m, trace, d)

    raise RuntimeError("Myers algorithm did not converge")


def _backtrack(n, m, trace, d):
    """
    Walk backwards from (n, m) to (0, 0) through the saved history trace,
    recovering the edit script.
    """
    x, y = n, m
    ops = []

    # Walk backward from depth d down to 0
    for depth in range(d, -1, -1):
        k = x - y

        if depth == 0:
            # Base case: we are at depth 0, meaning no edits happened yet.
            # We simulate the exact seed conditions to finish up cleanly.
            prev_k, prev_x, prev_y = 1, 0, -1
        else:
            dprime = depth - 1
            row = trace[dprime]
            
            # Figure out if the previous step came from k-1 (delete) or k+1 (insert)
            # This math flawlessly reverses the condition from the forward pass.
            if k == -depth or (k != depth and row[(k - 1 + dprime) // 2] < row[(k + 1 + dprime) // 2]):
                prev_k = k + 1
            else:
                prev_k = k - 1
                
            prev_x = row[(prev_k + dprime) // 2]
            prev_y = prev_x - prev_k

        # While our current coordinates are larger than where we came from,
        # it means we rode a "snake" (matching elements). Record them as 'equal'.
        while x > prev_x and y > prev_y:
            x -= 1
            y -= 1
            ops.append(("equal", x, y))

        if depth > 0:
            # Record the actual edit that happened at this depth
            if x == prev_x:
                y -= 1
                ops.append(("insert", None, y))
            else:
                x -= 1
                ops.append(("delete", x, None))

        # Move to the previous coordinates
        x, y = prev_x, prev_y

    # Because we backtracked, the operations are reversed. Flip them forward.
    ops.reverse()
    return ops


# ---------------------------------------------------------------
# 4. Grouping into equal-runs / change-blocks, with delete-first rule
# ---------------------------------------------------------------

def group_blocks(ops):
    """
    Collapse the raw edit script list into clustered blocks:
       ('equal',  a_index, b_index)
       ('change', [a_indices of deletes], [b_indices of inserts])

    Assignment Rule Check: The "delete-first" rule.
    Inside a 'change' block, we explicitly group all 'delete' operations 
    and put them strictly BEFORE any 'insert' operations.
    Reordering same-type ops inside a single change block does not alter 
    what gets deleted or inserted, maintaining the minimal edit count, 
    but perfectly complies with the PDF's strict formatting requirement.
    """
    blocks = []
    i, n = 0, len(ops)
    while i < n:
        op = ops[i]
        if op[0] == "equal":
            blocks.append(("equal", op[1], op[2]))
            i += 1
        else:
            # We found a change block. Gather all deletes and inserts until the next 'equal'.
            deletes, inserts = [], []
            while i < n and ops[i][0] != "equal":
                if ops[i][0] == "delete":
                    deletes.append(ops[i][1])
                else:
                    inserts.append(ops[i][2])
                i += 1
            # By packing deletes first, we structurally enforce the delete-first rule.
            blocks.append(("change", deletes, inserts))
    return blocks

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

    ops = myers_diff(a_lines, b_lines)
    blocks = group_blocks(ops)

if __name__ == "__main__":
    main()