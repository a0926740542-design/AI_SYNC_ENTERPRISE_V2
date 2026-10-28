"""Regression tests for SyncEngine lifecycle cleanup (R5 Batch 12.2-G)."""
import pytest

from app.core.sync_engine import SyncEngine


def make_engine(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    return SyncEngine(source, tmp_path / "backup")


def test_reconcile_failure_stops_observer_and_worker(tmp_path):
    engine = make_engine(tmp_path)

    def fail_reconcile():
        raise RuntimeError("INJECTED_RECONCILE_FAILURE")

    engine.reconcile_startup = fail_reconcile
    try:
        with pytest.raises(RuntimeError, match="INJECTED_RECONCILE_FAILURE"):
            engine.start()
        assert not engine.observer_manager.running
        assert not engine.observer_manager.observer.is_alive()
        assert not engine.worker_pool.running
    finally:
        engine.stop()


def test_stop_always_stops_worker_if_observer_stop_raises(tmp_path, monkeypatch):
    engine = make_engine(tmp_path)
    engine.start()
    original_stop = engine.observer_manager.stop

    def stop_then_fail():
        original_stop()
        raise RuntimeError("INJECTED_OBSERVER_STOP_FAILURE")

    monkeypatch.setattr(engine.observer_manager, "stop", stop_then_fail)
    with pytest.raises(RuntimeError, match="INJECTED_OBSERVER_STOP_FAILURE"):
        engine.stop()
    assert not engine.worker_pool.running
    assert not engine.observer_manager.observer.is_alive()


def test_reconcile_failure_stops_worker_even_if_observer_cleanup_raises(tmp_path, monkeypatch):
    engine = make_engine(tmp_path)
    original_stop = engine.observer_manager.stop

    def stop_then_fail():
        original_stop()
        raise RuntimeError("INJECTED_OBSERVER_STOP_FAILURE")

    monkeypatch.setattr(engine.observer_manager, "stop", stop_then_fail)

    def fail_reconcile():
        raise RuntimeError("INJECTED_RECONCILE_FAILURE")

    engine.reconcile_startup = fail_reconcile
    with pytest.raises(RuntimeError, match="INJECTED_OBSERVER_STOP_FAILURE"):
        engine.start()
    assert not engine.worker_pool.running
    assert not engine.observer_manager.observer.is_alive()
