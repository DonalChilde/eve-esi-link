"""Tests for logging configuration and deferred startup buffering."""

import logging
from pathlib import Path

from pfmsoft.eve_link.logging_config import (
    DeferredHandler,
    flush_deferred_handler,
    init_deferred_handler,
    setup_logging,
)


def _restore_root_logger(*, handlers: list[logging.Handler], level: int) -> None:
    """Restore root logger handlers and level after a test mutation."""
    root_logger = logging.getLogger()

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    for handler in handlers:
        root_logger.addHandler(handler)

    root_logger.setLevel(level)


def test_setup_logging_preserves_deferred_records(tmp_path: Path) -> None:
    """Replay startup records emitted before dictConfig into configured files."""
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    try:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)

        init_deferred_handler()
        logging.getLogger("eve_esi_link.test").info("early startup log message")

        setup_logging(log_dir=tmp_path)
        flush_deferred_handler()

        for handler in logging.getLogger().handlers:
            handler.flush()

        info_log_path = tmp_path / "rotating_info.log"
        assert info_log_path.exists()
        assert "early startup log message" in info_log_path.read_text(encoding="utf-8")
    finally:
        _restore_root_logger(handlers=original_handlers, level=original_level)


def test_init_deferred_handler_is_idempotent() -> None:
    """Avoid installing duplicate deferred handlers during repeated initialization."""
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    try:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)

        init_deferred_handler()
        init_deferred_handler()

        deferred_count = sum(
            isinstance(handler, DeferredHandler) for handler in root_logger.handlers
        )
        assert deferred_count == 1
    finally:
        _restore_root_logger(handlers=original_handlers, level=original_level)
