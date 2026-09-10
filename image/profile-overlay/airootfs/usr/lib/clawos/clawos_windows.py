"""Stable identity for the shell-owned conversation window, independent of title."""
import re

AGENT_MARK = "clawos-agent-canvas"
BOOTSTRAP_APP_ID = re.compile(r"^chrome-.*clawos-control-ui-bootstrap-agent\.html-.*$")


def is_agent_window(node):
    app = node.get("app_id") or node.get("window_properties", {}).get("class", "")
    return (AGENT_MARK in node.get("marks", []) or app == "clawos-agent"
            or bool(BOOTSTRAP_APP_ID.fullmatch(app)))


def windows(tree):
    if tree.get("type") == "con" and (tree.get("app_id") or tree.get("window_properties")):
        yield tree
    for child in tree.get("nodes", []) + tree.get("floating_nodes", []):
        yield from windows(child)


def find_agent_window(tree):
    matches = [node for node in windows(tree) if is_agent_window(node)]
    if len(matches) != 1:
        raise ValueError(f"Expected one Agent window, found {len(matches)}")
    return matches[0]
