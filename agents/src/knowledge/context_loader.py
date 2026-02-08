import os
import subprocess
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# In Docker, repo root is mounted at /workspace
# Otherwise, calculate from file location
# File is at: agents/src/knowledge/context_loader.py
# dirname: /...../agents/src/knowledge
# dirname x 3: /...../AI-Agent-demo (repo root)

if os.path.exists("/workspace"):
    BASE_DIR = "/workspace"
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

DOCS_DIR = os.path.join(BASE_DIR, "agents", "docs")


def _read(path: str) -> str:
    """Read file safely, return empty string if not found."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            size_kb = len(content) / 1024
            logger.debug(f"Loaded {path}: {size_kb:.1f}KB")
            return content
    except Exception as e:
        logger.warning(f"Failed to load {path}: {e}")
        return ""


def load_static_docs(include_demo_domain: bool = True) -> Dict[str, str]:
    """Load static documentation with selective loading option."""
    docs = {
        "system_context": _read(os.path.join(DOCS_DIR, "SYSTEM_CONTEXT.md")),
        "api_contracts": _read(os.path.join(DOCS_DIR, "API_CONTRACTS.md")),
        "code_patterns": _read(os.path.join(DOCS_DIR, "CODE_PATTERNS.md")),
        "architecture": _read(os.path.join(DOCS_DIR, "ARCHITECTURE.md")),
        "decisions": _read(os.path.join(DOCS_DIR, "DECISIONS.md")),
    }
    
    # Load demo-domain documentation only if requested
    if include_demo_domain:
        demo_domain_dir = os.path.join(BASE_DIR, "demo-domain", "docs")
        docs["demo_domain_api"] = _read(os.path.join(demo_domain_dir, "API_EXAMPLES.md"))
        docs["demo_domain_setup"] = _read(os.path.join(demo_domain_dir, "demo-setup", "README.md"))
    else:
        docs["demo_domain_api"] = ""
        docs["demo_domain_setup"] = ""
    
    return docs


def get_recent_commits(limit: int = 5) -> str:
    try:
        out = subprocess.check_output(
            ["git", "--no-pager", "log", f"-n{limit}", "--oneline"],
            cwd=BASE_DIR,
        )
        return out.decode("utf-8")
    except Exception:
        return ""


def scan_code_structure(paths: Optional[List[str]] = None) -> str:
    targets = paths or [
        os.path.join(BASE_DIR, "agents", "src"),
        os.path.join(BASE_DIR, "ai-management", "src"),
        os.path.join(BASE_DIR, "demo-domain", "src"),
    ]
    lines: List[str] = []
    for t in targets:
        try:
            for root, dirs, files in os.walk(t):
                rel = os.path.relpath(root, BASE_DIR)
                lines.append(f"- {rel}/")
                for fn in sorted(files):
                    lines.append(f"  - {os.path.join(rel, fn)}")
        except Exception:
            continue
    return "\n".join(lines)


def build_ai_prompt(
    task_title: str,
    task_description: str,
    labels: Optional[List[str]] = None,
    include_demo_domain: bool = True,
) -> str:
    """Build AI prompt with token optimization.
    
    Args:
        task_title: Task title
        task_description: Task description
        labels: Optional task labels
        include_demo_domain: Whether to include demo-domain docs (default: True for backward compat)
    """
    docs = load_static_docs(include_demo_domain=include_demo_domain)
    recent = get_recent_commits(limit=5)
    structure = scan_code_structure()
    labels_str = ", ".join(labels) if labels else ""

    # Build system prompt with demo-domain docs only if requested
    system_parts = [
        f"{docs['system_context']}\n\n---\n",
        f"{docs['architecture']}\n\n---\n",
        f"{docs['decisions']}\n\n---\n",
        f"{docs['code_patterns']}\n\n---\n\n",
    ]
    
    if include_demo_domain:
        system_parts.append("## Demo-Domain Architecture (Campaign Management)\n")
        if docs.get('demo_domain_setup'):
            system_parts.append(f"{docs.get('demo_domain_setup', '')}\n\n---\n\n")
        system_parts.append("## Demo-Domain API Examples\n")
        if docs.get('demo_domain_api'):
            system_parts.append(f"{docs.get('demo_domain_api', '')}\n")
    
    system = "".join(system_parts)
    
    # Log prompt size for debugging
    system_size_kb = len(system) / 1024
    logger.info(f"Built AI prompt: {system_size_kb:.1f}KB (demo_domain={include_demo_domain})")

    user = (
        f"TASK TITLE: {task_title}\n"
        f"TASK DESC: {task_description}\n"
        f"TASK LABELS: {labels_str}\n\n"
        f"RECENT COMMITS:\n{recent}\n\n"
        f"CODE STRUCTURE:\n{structure}\n\n"
        f"IMPORTANT: This task is about implementing features in the demo-domain service.\n"
        f"Based on the demo-domain API and schema above, generate the necessary code changes.\n"
        f"Include database schema updates, API endpoints, and business logic.\n"
    )

    return system + "\n" + user
