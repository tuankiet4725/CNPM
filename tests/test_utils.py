from src.utils import drop_contained, generate_tiles, iou, nms


def test_iou_identical_and_disjoint():
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


def test_iou_half_overlap():
    assert abs(iou((0, 0, 10, 10), (5, 0, 15, 10)) - 50 / 150) < 1e-9


def test_nms_removes_duplicates():
    boxes = [(0, 0, 10, 10), (1, 1, 11, 11), (50, 50, 60, 60)]
    keep = nms(boxes, [0.9, 0.8, 0.7], 0.5)
    assert sorted(keep) == [0, 2]


def test_nms_empty():
    assert nms([], [], 0.5) == []


def test_tiles_cover_image():
    tiles = generate_tiles(1920, 1080, 640, 0.2)
    assert max(t[2] for t in tiles) == 1920
    assert max(t[3] for t in tiles) == 1080
    assert all(t[2] - t[0] <= 640 and t[3] - t[1] <= 640 for t in tiles)


def test_tiles_small_image():
    assert generate_tiles(300, 200, 640, 0.2) == [(0, 0, 300, 200)]


def test_drop_contained_removes_partial_box():
    # Box "nửa người" do đường cắt ô nằm trong box đầy đủ
    boxes = [[50, 400, 245, 900], [58, 400, 202, 640], [600, 400, 800, 880]]
    assert sorted(drop_contained(boxes, [0, 1, 2])) == [0, 2]


def test_drop_contained_empty():
    assert drop_contained([], []) == []
