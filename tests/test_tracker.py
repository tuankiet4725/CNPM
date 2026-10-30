from src.entities import Detection
from src.tracker import IoUTracker


def det(box, name="knife"):
    return Detection(name, 0.9, box)


def test_same_object_keeps_id():
    tr = IoUTracker(iou_threshold=0.3)
    d1 = det((0, 0, 10, 10))
    tr.update([d1])
    d2 = det((1, 1, 11, 11))
    tracks = tr.update([d2])
    assert d1.track_id == d2.track_id
    assert tracks[0].hits == 2


def test_different_class_new_id():
    tr = IoUTracker()
    a = det((0, 0, 10, 10), "knife")
    tr.update([a])
    b = det((0, 0, 10, 10), "gun")
    tr.update([b])
    assert a.track_id != b.track_id


def test_track_removed_after_max_missed():
    tr = IoUTracker(max_missed=2)
    tr.update([det((0, 0, 10, 10))])
    for _ in range(3):
        tr.update([])
    assert tr.tracks == {}


def test_track_survives_short_gap():
    tr = IoUTracker(max_missed=5)
    a = det((0, 0, 10, 10))
    tr.update([a])
    tr.update([])
    b = det((0, 0, 10, 10))
    tr.update([b])
    assert a.track_id == b.track_id


def test_streak_resets_after_miss():
    tr = IoUTracker()
    tr.update([det((0, 0, 10, 10))])
    tr.update([det((0, 0, 10, 10))])
    tr.update([])
    tracks = tr.update([det((0, 0, 10, 10))])
    assert tracks[0].hits == 3
    assert tracks[0].streak == 1
