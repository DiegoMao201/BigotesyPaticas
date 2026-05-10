"""Tests para flags + version_info + logging."""
from __future__ import annotations

import logging
import os

from bp_common.flags import all_flags, get_flag, reset_overrides, set_flag
from bp_common.logging_setup import get_logger, setup_logging
from bp_common.version_info import get_build_info


def test_flag_default():
    reset_overrides()
    assert get_flag("USE_PG_POS") is False
    assert get_flag("DUAL_WRITE_SHEETS") is True


def test_flag_runtime_override():
    reset_overrides()
    set_flag("USE_PG_POS", True)
    assert get_flag("USE_PG_POS") is True
    reset_overrides()
    assert get_flag("USE_PG_POS") is False


def test_flag_env_override(monkeypatch):
    reset_overrides()
    monkeypatch.setenv("FF_USE_PG_POS", "true")
    assert get_flag("USE_PG_POS") is True
    monkeypatch.setenv("FF_USE_PG_POS", "no")
    assert get_flag("USE_PG_POS") is False


def test_all_flags_returns_dict():
    reset_overrides()
    flags = all_flags()
    assert isinstance(flags, dict)
    assert "DUAL_WRITE_SHEETS" in flags


def test_build_info_keys():
    info = get_build_info()
    assert "version" in info
    assert "git_sha" in info
    assert "env" in info


def test_logging_setup_idempotent(capsys):
    setup_logging()
    setup_logging()
    # Si setup_logging no fuera idempotente, habría 2+ handlers y el mensaje
    # se duplicaría en stderr.
    log = get_logger("bp_test")
    log.info("hello-bp-idem")
    captured = capsys.readouterr()
    assert captured.err.count("hello-bp-idem") == 1
