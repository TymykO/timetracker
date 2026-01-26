"""
Outbox Pattern - publiczne API.

Export głównych funkcji dla łatwego importowania:
    from timetracker_app.outbox import enqueue, run_once, run_forever
"""

from timetracker_app.outbox.dispatcher import (
    enqueue,
    run_once,
    run_forever,
    request_shutdown,
    is_shutdown_requested,
)

__all__ = [
    'enqueue',
    'run_once',
    'run_forever',
    'request_shutdown',
    'is_shutdown_requested',
]
