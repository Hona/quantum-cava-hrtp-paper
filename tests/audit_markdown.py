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
    blocks = re.findall(r"\$\$[\s\S]*?\$\$|\$[^$\n]+\$", text)
    g_total = sum(b.count("{") + 1 for b in blocks)
    assert g_total < 1500, f"GitHub MathJax budget exceeded in {path}: g_total={g_total} >= 1500"
    for b in blocks:
        for bad_tok in (r"\;", r"\,", r"\{", r"\}", r"[\![", r"]\!]", r"\llbracket", r"\rrbracket", r"\mathbin{\&}"):
            assert bad_tok not in b, f"CommonMark-unsafe token {bad_tok} in {path}: {b}"
    print(f"[AUDIT PASS] {path} ({len(lines)} lines, {len(blocks)} math blocks, g_total={g_total})")

tex_path = "C:/tmp/opencode/arxiv-upload/main.tex"
with open(tex_path, encoding="utf-8") as f:
    tex = f.read()

for idx, line in enumerate(tex.splitlines(), 1):
    clean = line.replace("\\%", "")
    assert "%" not in clean, f"Unescaped % comment on line {idx}: {line}"

clean_braces = tex.replace("\\{", "").replace("\\}", "")
assert clean_braces.count("{") == clean_braces.count("}"), "Unbalanced braces"

stack = []
for m in re.finditer(r"\\(begin|end)\{([^}]+)\}", tex):
    kind, env = m.group(1), m.group(2)
    if kind == "begin":
        stack.append(env)
    else:
        assert stack and stack[-1] == env, f"Mismatched end {env}"
        stack.pop()
assert not stack, f"Unclosed environments: {stack}"

bibitems = set(re.findall(r"\\bibitem\{([^}]+)\}", tex))
for m in re.finditer(r"\\cite\{([^}]+)\}", tex):
    for k in m.group(1).split(","):
        assert k.strip() in bibitems, f"Missing bibitem for {k}"

labels = set(re.findall(r"\\label\{([^}]+)\}", tex))
for m in re.finditer(r"\\ref\{([^}]+)\}", tex):
    assert m.group(1).strip() in labels, f"Missing label for {m.group(1)}"

print(f"[LATEX AUDIT PASS] {tex_path} ({len(tex.splitlines())} lines, {len(bibitems)} bibitems, {len(labels)} labels, 0 comments)")

