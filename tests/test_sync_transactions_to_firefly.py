import pytest
from unittest.mock import MagicMock, patch
from domain.transaction import CanonicalTransaction
from application.use_cases.sync_transactions_to_firefly import SyncTransactionsToFirefly


def _make_txn(amount=100.50, bank_id="testbank", is_synced=False):
    return CanonicalTransaction(
        date="2024-01-15",
        description="TEST",
        amount=amount,
        bank_id=bank_id,
        account_id="ACC1",
        canonical_account_id="cc:test",
        transaction_type="withdrawal",
        is_synced=is_synced,
    )


class TestSyncTransactionsToFirefly:
    def test_no_transactions_returns_early(self):
        mock_repo = MagicMock()
        mock_repo.get_unsynced.return_value = []
        mock_port = MagicMock()

        use_case = SyncTransactionsToFirefly(mock_repo, mock_port)
        result = use_case.execute()

        assert result["status"] == "success"
        assert result["synced_count"] == 0
        mock_port.push_transactions.assert_not_called()

    def test_syncs_all_unsynced_transactions(self):
        mock_repo = MagicMock()
        txns = [_make_txn(), _make_txn(amount=50.0)]
        mock_repo.get_unsynced.return_value = txns
        mock_port = MagicMock()
        mock_port.push_transactions.return_value = {
            "synced_hashes": [txns[0].id, txns[1].id],
            "errors": []
        }

        use_case = SyncTransactionsToFirefly(mock_repo, mock_port)
        result = use_case.execute()

        assert result["status"] == "success"
        assert result["synced_count"] == 2
        mock_port.push_transactions.assert_called_once_with(txns)
        mock_repo.mark_as_synced.assert_called_once()

    def test_filters_by_bank_id(self):
        mock_repo = MagicMock()
        all_txns = [_make_txn(bank_id="bankA"), _make_txn(bank_id="bankB")]
        mock_repo.get_unsynced.return_value = all_txns
        mock_port = MagicMock()
        mock_port.push_transactions.return_value = {"synced_hashes": [], "errors": []}

        use_case = SyncTransactionsToFirefly(mock_repo, mock_port)
        result = use_case.execute(bank_id="bankA")

        called_txns = mock_port.push_transactions.call_args[0][0]
        assert all(t.bank_id == "bankA" for t in called_txns)

    def test_partial_success_status_when_errors(self):
        mock_repo = MagicMock()
        txns = [_make_txn(), _make_txn()]
        mock_repo.get_unsynced.return_value = txns
        mock_port = MagicMock()
        mock_port.push_transactions.return_value = {
            "synced_hashes": [txns[0].id],
            "errors": [{"hash": txns[1].id, "error": "some error"}]
        }

        use_case = SyncTransactionsToFirefly(mock_repo, mock_port)
        result = use_case.execute()

        assert result["status"] == "partial_success"
        assert result["synced_count"] == 1
        assert result["error_count"] == 1

    def test_mark_as_synced_called_with_synced_hashes_only(self):
        mock_repo = MagicMock()
        txns = [_make_txn(), _make_txn()]
        mock_repo.get_unsynced.return_value = txns
        mock_port = MagicMock()
        mock_port.push_transactions.return_value = {
            "synced_hashes": [txns[0].id],
            "errors": [{"hash": txns[1].id, "error": "fail"}]
        }

        use_case = SyncTransactionsToFirefly(mock_repo, mock_port)
        use_case.execute()

        mock_repo.mark_as_synced.assert_called_once_with([txns[0].id])

    def test_does_not_mark_as_synced_when_nothing_synced(self):
        mock_repo = MagicMock()
        txns = [_make_txn()]
        mock_repo.get_unsynced.return_value = txns
        mock_port = MagicMock()
        mock_port.push_transactions.return_value = {
            "synced_hashes": [],
            "errors": [{"hash": txns[0].id, "error": "fail"}]
        }

        use_case = SyncTransactionsToFirefly(mock_repo, mock_port)
        result = use_case.execute()

        mock_repo.mark_as_synced.assert_not_called()
