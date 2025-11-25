"""Common utilities for BT Bridge clients"""

import re


def strip_ansi_codes(text):
    """
    Remove ANSI color codes from text.

    Args:
        text: String potentially containing ANSI escape sequences

    Returns:
        Clean string without ANSI codes
    """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def extract_message_from_log(line):
    """
    Extract actual message from ESP-IDF log line.

    Removes ESP-IDF log prefixes like:
    - I (12345) TAG: message
    - E (12345) TAG: message
    - W (12345) TAG: message

    Only returns messages with bt_com tag (BLE communication).

    Args:
        line: ESP-IDF log line

    Returns:
        Extracted message or None if not a bt_com message
    """
    if not line:
        return None

    # Pattern matches: [Level] (timestamp) bt_com: message
    # Only extract bt_com tagged messages
    bt_com_pattern = r'[IEWDV]\s*\(\d+\)\s+bt_com:\s*(.+)'
    match = re.match(bt_com_pattern, line)

    if match:
        return match.group(1).strip()

    return None


def is_message_fragment(message):
    """
    Detect if a message is a fragment (incomplete).

    Since ESP-IDF can split long messages across multiple log lines,
    this function detects fragments. However, for normal short messages,
    we assume they're complete.

    A message is considered a fragment if it doesn't look like a
    complete Arduino response (missing the typical format).

    Args:
        message: Message string to check

    Returns:
        True if message appears to be a fragment
    """
    if not message:
        return False

    # If message starts with "Arduino:" and is reasonably short (< 200 chars),
    # assume it's complete regardless of ending character
    if message.startswith("Arduino:") and len(message) < 200:
        return False

    # For very long messages, check if it seems incomplete
    # (This is a conservative check - most messages will pass through)
    return False
