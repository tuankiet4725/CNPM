"""Bảng điều khiển web: xem video trực tiếp, lịch sử cảnh báo, thống kê."""

import logging
import os
import threading
import time

import cv2
from flask import Flask, Response, abort, jsonify, render_template, request, send_from_directory

log = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SharedState:
    """Dữ liệu chia sẻ giữa luồng xử lý video và máy chủ web."""

    def __init__(self):
        self._lock = threading.Lock()
        self._jpeg = None
        self.status = {"fps": 0.0, "source": "", "running": False, "threats_now": 0}

    def set_frame(self, frame):
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if ok:
            with self._lock:
                self._jpeg = buf.tobytes()

    def get_jpeg(self):
        with self._lock:
            return self._jpeg


def create_app(state, db, snapshot_dir):
    app = Flask(__name__, template_folder=os.path.join(ROOT, "templates"))
    snapshot_dir = os.path.abspath(snapshot_dir)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/video_feed")
    def video_feed():
        def stream():
            while True:
                jpeg = state.get_jpeg()
                if jpeg is not None:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                time.sleep(0.05)

        return Response(stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.route("/api/events")
    def events():
        limit = min(int(request.args.get("limit", 50)), 500)
        rows = db.recent(limit)
        for r in rows:
            r["snapshot_url"] = f"/snapshots/{os.path.basename(r['snapshot'])}" if r.get("snapshot") else None
        return jsonify(rows)

    @app.route("/api/stats")
    def stats():
        return jsonify({**db.stats(), **state.status})

    @app.route("/snapshots/<path:name>")
    def snapshot(name):
        if not os.path.isdir(snapshot_dir):
            abort(404)
        return send_from_directory(snapshot_dir, name)

    return app


def run_in_background(app, host, port):
    t = threading.Thread(
        target=lambda: app.run(host=host, port=port, threaded=True, use_reloader=False),
        daemon=True,
    )
    t.start()
    log.info("Bảng điều khiển web: http://localhost:%s", port)
    return t
