"""Analytics stubs.

This fork sends no usage data. The functions keep their upstream signatures so
call sites in cli.py stay unchanged, but none of them touch the network, the
filesystem, or other processes.
"""


def _is_enabled():
    return False


def detect_invocation_context():
    return {
        "is_agent": False,
        "traffic_type": "unknown",
        "category": "unknown",
        "reason": "analytics-disabled",
        "signals": [],
        "stdin_tty": False,
        "is_interactive": False,
    }


def track_event(event_name, url="/cli-anything-hub", data=None):
    return None


def track_install(cli_name, version):
    return None


def track_uninstall(cli_name):
    return None


def track_launch(cli_name):
    return None


def track_matrix_install(matrix_name, scope="full", status="ok",
                         installed=0, skipped=0, failed=0, dry_run=False):
    return None


def track_matrix_preflight(matrix_name, scope="full", covered=0, capabilities=0, gaps=0):
    return None


def track_matrix_discover(kind, query="", results=0):
    return None


def track_matrix_info(matrix_name, kind="info"):
    return None


def track_visit(is_agent=False, command="root", detection=None):
    return None


def track_first_run():
    return None
