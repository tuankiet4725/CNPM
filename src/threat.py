"""Đánh giá mức độ đe doạ của các vật thể phát hiện được."""

from .entities import LEVELS, Threat, level_rank


def escalate(level):
    return LEVELS[min(level_rank(level) + 1, len(LEVELS) - 1)]


def is_near(weapon_box, person_box, margin):
    """Vũ khí giao với vùng người đã mở rộng thêm `margin` (tỉ lệ kích thước người)."""
    px1, py1, px2, py2 = person_box
    mx, my = (px2 - px1) * margin, (py2 - py1) * margin
    ex1, ey1, ex2, ey2 = px1 - mx, py1 - my, px2 + mx, py2 + my
    wx1, wy1, wx2, wy2 = weapon_box
    return wx1 < ex2 and wx2 > ex1 and wy1 < ey2 and wy2 > ey1


class ThreatAssessor:
    def __init__(self, threat_classes, person_class="person", proximity=0.3):
        self.threat_classes = threat_classes
        self.person_class = person_class
        self.proximity = proximity

    def assess(self, detections):
        """Trả về (threats, persons)."""
        persons = [d for d in detections if d.class_name == self.person_class]
        threats = []
        for d in detections:
            info = self.threat_classes.get(d.class_name)
            if info is None:
                continue
            level = info.get("level", "medium")
            near = any(is_near(d.box, p.box, self.proximity) for p in persons)
            if near:
                level = escalate(level)
            threats.append(Threat(
                detection=d,
                label=info.get("label", d.class_name),
                display=info.get("display", d.class_name.upper()),
                level=level,
                near_person=near,
            ))
        return threats, persons
