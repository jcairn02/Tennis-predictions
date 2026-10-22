"""Process classification shared by the fit guard and the notebook's GPU warning."""
from __future__ import annotations

import re


# Match the helper as the script being executed, not a mention in a training job's arguments.
# Both CIM and subprocess.list2cmdline use double quotes around Windows paths with spaces.
_INTERRUPT_HELPER = re.compile(
    r'\s*(?:"[^"]+"|[^\s"]+)\s+'
    r'(?:"[^"]*[\\/]vscode_datascience_helpers[\\/]kernel_interrupt_daemon\.py"'
    r'|[^\s"]*[\\/]vscode_datascience_helpers[\\/]kernel_interrupt_daemon\.py)'
    r'\s+--ppid(?:\s+|=)[1-9][0-9]*\s*',
    re.IGNORECASE,
)


def is_jupyter_interrupt_helper(commandline: str | None) -> bool:
    """Only the known VS Code interrupt-helper invocation; kernels/unknown commands still block."""
    return bool(_INTERRUPT_HELPER.fullmatch(commandline or ""))
