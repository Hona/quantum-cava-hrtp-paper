import re

files = [
    "C:/tmp/opencode/quantum-cava-hrtp-paper/paper/main.md",
    "C:/tmp/opencode/quantum-cava-hrtp-paper/README.md",
    "C:/tmp/opencode/cobble_pr_body.md",
    "C:/tmp/opencode/cobble_issue_body.md",
    "C:/tmp/opencode/tzap_pr_body.md",
    "C:/tmp/opencode/tzap_issue_body.md",
]

for path in files:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    assert "\\llbracket" not in text and "\\rrbracket" not in text, f"Found llbracket in {path}"
    in_code = False
    in_math_block = False
    for idx, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if line.strip() == "$$":
            in_math_block = not in_math_block
            continue
        if not in_math_block:
            clean = line.replace("\\$", "")
            # Strip single-line $$...$$ blocks before checking inline $
            clean_no_disp = re.sub(r"\$\$[^$]+\$\$", "", clean)
            cnt = clean_no_disp.count("$")
            assert cnt % 2 == 0, f"Unbalanced $ on line {idx} of {path}: {line}"
            for m in re.finditer(r"\$([^$]+)\$", clean_no_disp):
                assert "\\\\" not in m.group(1), f"Found \\\\ inside inline math on line {idx} of {path}: {m.group(0)}"
            for m in re.finditer(r"`([^`]+)`", clean):
                assert "\\land" not in m.group(1) and "\\oplus" not in m.group(1), f"LaTeX in backticks on line {idx} of {path}: {m.group(0)}"
    assert not in_code, f"Unclosed code block in {path}"
    assert not in_math_block, f"Unclosed $$ block in {path}"
    print(f"[AUDIT PASS] {path} ({len(lines)} lines)")
