from src.alert import AlertManager
from src.database import EventDatabase
from src.entities import Detection
from src.threat import ThreatAssessor, escalate, is_near
from src.tracker import IoUTracker

THREATS = {
    "knife": {"label": "Dao", "display": "KNIFE", "level": "high"},
    "scissors": {"label": "Kéo", "display": "SCISSORS", "level": "low"},
}


def test_escalate():
    assert escalate("medium") == "high"
    assert escalate("critical") == "critical"


def test_is_near():
    person = (100, 100, 150, 250)
    assert is_near((140, 150, 170, 160), person, 0.3)
    assert not is_near((400, 400, 420, 420), person, 0.3)


def test_weapon_near_person_escalated():
    a = ThreatAssessor(THREATS)
    dets = [Detection("person", 0.9, (100, 100, 150, 250)), Detection("knife", 0.8, (140, 150, 170, 160))]
    threats, persons = a.assess(dets)
    assert len(persons) == 1
    assert threats[0].level == "critical" and threats[0].near_person


def test_unknown_class_ignored():
    threats, _ = ThreatAssessor(THREATS).assess([Detection("car", 0.9, (0, 0, 10, 10))])
    assert threats == []


def _run(manager, frames, name="knife"):
    tracker, assessor = IoUTracker(), ThreatAssessor(THREATS)
    alerts = []
    for _ in range(frames):
        dets = [Detection(name, 0.9, (0, 0, 10, 10))]
        tracks = tracker.update(dets)
        threats, _ = assessor.assess(dets)
        alerts += manager.process(None, threats, {t.track_id: t for t in tracks})
    return alerts


def test_alert_requires_consecutive_frames_and_fires_once():
    db = EventDatabase(":memory:")
    m = AlertManager({"min_consecutive_frames": 3, "cooldown_seconds": 0, "snapshot_dir": None}, db)
    assert _run(m, 2) == []
    m2 = AlertManager({"min_consecutive_frames": 3, "cooldown_seconds": 0, "snapshot_dir": None}, db)
    alerts = _run(m2, 10)
    assert len(alerts) == 1
    assert db.stats()["total"] == 1


def test_alert_below_min_level_ignored():
    m = AlertManager({"min_level": "medium", "min_consecutive_frames": 1, "snapshot_dir": None})
    assert _run(m, 5, "scissors") == []


def test_flickering_detection_does_not_alert():
    # Nhận nhầm chập chờn (thấy 1 khung, mất 1 khung) không được cộng dồn thành "liên tiếp"
    m = AlertManager({"min_consecutive_frames": 3, "cooldown_seconds": 0, "snapshot_dir": None})
    tracker, assessor = IoUTracker(), ThreatAssessor(THREATS)
    alerts = []
    for i in range(10):
        dets = [Detection("knife", 0.9, (0, 0, 10, 10))] if i % 2 == 0 else []
        tracks = tracker.update(dets)
        threats, _ = assessor.assess(dets)
        alerts += m.process(None, threats, {t.track_id: t for t in tracks})
    assert alerts == []
