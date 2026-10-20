import re

AGENT_DIRS = (
    ".claude",
    ".agents",
    ".codex",
    ".cursor",
    ".windsurf",
    ".continue",
    ".impeccable",
    ".playwright-mcp",
    ".superdesign",
    ".aider.tags.cache.v3",
)
AGENT_FILES = (
    "AGENTS.md",
    "AGENTS.override.md",
    "CLAUDE.md",
    "CLAUDE.local.md",
    "GEMINI.md",
    ".mcp.json",
    ".cursorrules",
    ".windsurfrules",
    ".claudeignore",
    ".aider.conf.yml",
    ".aider.chat.history.md",
    ".aider.input.history",
)
AGENT_GLOBS = ("PROMPT-*.md", "TASK-*.md")
SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
IGNORE_FILES = {".gitignore", ".dockerignore", ".prettierignore", ".eslintignore"}
JSON_FILES = re.compile(r"^(biome\.jsonc?|tsconfig.*\.json|package\.json|\.eslintrc\.json)$")
AGENT_DIR_RE = "|".join(re.escape(d) for d in AGENT_DIRS)
IGNORE_LINE = re.compile(
    rf"^\s*!?/?(?:\*\*/)?(?:{AGENT_DIR_RE}|brief|context|work|skills)(?:/.*)?\s*$|(?:^|/)(?:CLAUDE|AGENTS|GEMINI)(?:\.local|\.override)?\.md|\.mcp\.json|\.cursorrules|\.windsurfrules|\.claudeignore"
)
JSON_ITEM = re.compile(rf'^\s*"!?(?:\*\*/)?(?:{AGENT_DIR_RE})[^"]*",?\s*$')
SCRUB_BLOCK = re.compile(r"[ \t]*<!-- scrub:start -->.*?<!-- scrub:end -->[ \t]*\n?(?:\n(?=\n))?", re.S)
LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SEP_BEFORE = re.compile(r"[ \t]*(?:·|,|;)[ \t]*\n?[ \t]*$")
SEP_AFTER = re.compile(r"^[ \t]*(?:·|,|;)[ \t]*\n?[ \t]*")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")
TRACE = re.compile(
    r"\.impeccable|claude[- ]?code|claude\.md|agents\.md|\bcodex\b|copilot|chatgpt|cursor[- ]?(?:ai|agent)|co-authored-by|generated (?:with|by) (?:claude|codex|chatgpt|an? ai)|ai[- ]generated|сгенерирован\S* (?:ии|нейросет)|\.claude/|\.agents/|scrub:(?:start|end)",
    re.I,
)
STYLE = re.compile(
    r"является|позволяет|уникальн|инновацион|в современном мире|играет ключевую роль|не просто [^,.]+, а|\bdelve|\bleverag|seamless|cutting-edge|game-changer|in today.s",
    re.I,
)
STYLE_LISTS = re.compile(r"(?:^|/)locales/[^/]+/video\.json$")
AGENT_PERSON = re.compile(
    r"claude|anthropic|codex|openai|chatgpt|copilot|cursor|devin|aider|gemini|\bgpt\b", re.I
)
TRAILER = re.compile(
    r"^(?:co-authored-by|signed-off-by|generated-by|assisted-by|helped-by|reviewed-by|on-behalf-of):",
    re.I | re.M,
)
TEXT_LIMIT = 2_000_000


SOURCE_RENAMES = {
    "frontend/scripts/checks/files.ts": {".impeccable": ".design-cache"},
    "frontend/tests/scripts/checks/engine.test.ts": {".impeccable": ".design-cache"},
}
