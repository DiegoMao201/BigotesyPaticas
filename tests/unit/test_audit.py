"""Tests para bp_common.audit."""

from __future__ import annotations

from unittest.mock import MagicMock

from bp_common.audit import AUDIT_HEADERS, AUDIT_TAB, _ensure_audit_tab, log_event
from bp_common.flags import reset_overrides, set_flag


def _setup_enabled():
    reset_overrides()
    set_flag("AUDIT_LOG_ENABLED", True)


def _setup_disabled():
    reset_overrides()
    set_flag("AUDIT_LOG_ENABLED", False)


def test_log_event_disabled_returns_false():
    _setup_disabled()
    result = log_event(None, action="create", entity="product", entity_id="123")
    assert result is False


def test_log_event_returns_false_on_sheet_error():
    _setup_enabled()
    sh = MagicMock()
    sh.worksheet.side_effect = Exception("network error")
    sh.add_worksheet.side_effect = Exception("quota exceeded")
    result = log_event(sh, action="create", entity="product")
    assert result is False


def test_log_event_success():
    _setup_enabled()
    sh = MagicMock()
    ws = MagicMock()
    ws.row_values.return_value = AUDIT_HEADERS
    sh.worksheet.return_value = ws
    result = log_event(sh, action="update", entity="order", entity_id="42", summary="paid")
    assert result is True
    ws.append_row.assert_called_once()
    row = ws.append_row.call_args[0][0]
    assert row[2] == "update"
    assert row[3] == "order"
    assert row[4] == "42"
    assert row[5] == "paid"


def test_log_event_with_payload():
    _setup_enabled()
    sh = MagicMock()
    ws = MagicMock()
    ws.row_values.return_value = AUDIT_HEADERS
    sh.worksheet.return_value = ws
    result = log_event(sh, action="delete", entity="product", payload={"sku": "ABC"})
    assert result is True
    row = ws.append_row.call_args[0][0]
    assert '"sku": "ABC"' in row[6]


def test_ensure_audit_tab_creates_if_missing():
    sh = MagicMock()
    sh.worksheet.side_effect = Exception("worksheet not found")
    new_ws = MagicMock()
    sh.add_worksheet.return_value = new_ws
    result = _ensure_audit_tab(sh)
    sh.add_worksheet.assert_called_once_with(title=AUDIT_TAB, rows=1000, cols=len(AUDIT_HEADERS))
    new_ws.append_row.assert_called_once_with(AUDIT_HEADERS, value_input_option="USER_ENTERED")
    assert result is new_ws


def test_ensure_audit_tab_returns_existing_with_correct_headers():
    sh = MagicMock()
    ws = MagicMock()
    ws.row_values.return_value = AUDIT_HEADERS
    sh.worksheet.return_value = ws
    result = _ensure_audit_tab(sh)
    sh.add_worksheet.assert_not_called()
    assert result is ws


def test_ensure_audit_tab_fixes_wrong_headers():
    sh = MagicMock()
    ws = MagicMock()
    ws.row_values.return_value = ["wrong", "headers"]
    sh.worksheet.return_value = ws
    result = _ensure_audit_tab(sh)
    ws.update.assert_called_once_with("A1", [AUDIT_HEADERS])
    assert result is ws


def test_ensure_audit_tab_ignores_header_check_error():
    sh = MagicMock()
    ws = MagicMock()
    ws.row_values.side_effect = Exception("API error")
    sh.worksheet.return_value = ws
    result = _ensure_audit_tab(sh)
    assert result is ws
