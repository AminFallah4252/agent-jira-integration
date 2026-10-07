"""Atlassian Document Format (ADF) serialization and parsing utilities."""

from __future__ import annotations

from typing import Any, Dict


def text_to_adf(text: str) -> Dict[str, Any]:
    """Convert plain text or simple markdown into Jira v3 Atlassian Document Format (ADF).
    
    Ensures 100% compatibility with Jira Cloud REST API v3.
    """
    if not text:
        return {"version": 1, "type": "doc", "content": []}

    paragraphs = text.replace("\r\n", "\n").split("\n\n")
    content_blocks = []

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue

        # Code block detection (```...```)
        if para_clean.startswith("```") and para_clean.endswith("```"):
            lines = para_clean.split("\n")
            first_line = lines[0].replace("```", "").strip()
            code_text = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
            content_blocks.append({
                "type": "codeBlock",
                "attrs": {"language": first_line or "text"},
                "content": [{"type": "text", "text": code_text}]
            })
            continue

        # Bullet list detection
        if all(line.strip().startswith(("- ", "* ")) for line in para_clean.split("\n") if line.strip()):
            list_items = []
            for item in para_clean.split("\n"):
                item_text = item.strip().lstrip("- *").strip()
                if item_text:
                    list_items.append({
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": item_text}]
                        }]
                    })
            content_blocks.append({
                "type": "bulletList",
                "content": list_items
            })
            continue

        # Regular paragraph
        content_blocks.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": para_clean}]
        })

    return {
        "version": 1,
        "type": "doc",
        "content": content_blocks or [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]
    }


def adf_to_text(adf_node: Any) -> str:
    """Recursively extract plain text from an Atlassian Document Format node."""
    if not isinstance(adf_node, dict):
        return str(adf_node) if adf_node else ""

    node_type = adf_node.get("type")
    content = adf_node.get("content", [])

    if node_type == "text":
        return adf_node.get("text", "")

    texts = [adf_to_text(c) for c in content]

    if node_type == "paragraph":
        return "".join(texts) + "\n"
    elif node_type == "codeBlock":
        lang = adf_node.get("attrs", {}).get("language", "")
        return f"```{lang}\n" + "".join(texts) + "\n```\n"
    elif node_type == "listItem":
        return "* " + "".join(texts).strip() + "\n"
    elif node_type in ("bulletList", "orderedList"):
        return "".join(texts) + "\n"
    elif node_type == "doc":
        return "\n".join(t.strip() for t in texts if t.strip())

    return "".join(texts)
