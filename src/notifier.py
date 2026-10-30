"""Các kênh thông báo khi có cảnh báo: âm thanh, Telegram."""

import logging
import threading

log = logging.getLogger(__name__)


class SoundNotifier:
    BEEPS = {"low": (800, 150), "medium": (1000, 250), "high": (1300, 400), "critical": (1600, 700)}

    def notify(self, alert):
        threading.Thread(target=self._beep, args=(alert.level,), daemon=True).start()

    def _beep(self, level):
        try:
            import winsound
            freq, dur = self.BEEPS.get(level, (1000, 300))
            repeat = 3 if level == "critical" else 1
            for _ in range(repeat):
                winsound.Beep(freq, dur)
        except (ImportError, RuntimeError):
            print("\a", end="", flush=True)


class TelegramNotifier:
    def __init__(self, bot_token, chat_id):
        self.url = f"https://api.telegram.org/bot{bot_token}"
        self.chat_id = chat_id

    def notify(self, alert):
        threading.Thread(target=self._send, args=(alert,), daemon=True).start()

    def _send(self, alert):
        import requests

        caption = (
            f"⚠️ CẢNH BÁO [{alert.level.upper()}]\n"
            f"Phát hiện: {alert.label} ({alert.confidence:.0%})\n"
            f"{'Đang ở gần/trong tay người' if alert.near_person else ''}\n"
            f"Thời gian: {alert.timestamp}"
        )
        try:
            if alert.snapshot:
                with open(alert.snapshot, "rb") as f:
                    requests.post(f"{self.url}/sendPhoto", data={"chat_id": self.chat_id, "caption": caption},
                                  files={"photo": f}, timeout=15)
            else:
                requests.post(f"{self.url}/sendMessage", data={"chat_id": self.chat_id, "text": caption},
                              timeout=15)
        except Exception as e:  # mạng lỗi không được làm dừng hệ thống
            log.error("Gửi Telegram thất bại: %s", e)


def build_notifiers(alert_cfg):
    notifiers = []
    if alert_cfg.get("sound"):
        notifiers.append(SoundNotifier())
    tg = alert_cfg.get("telegram") or {}
    if tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id"):
        notifiers.append(TelegramNotifier(tg["bot_token"], tg["chat_id"]))
    return notifiers
