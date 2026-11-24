#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validação e Homologação de Sons de Notificação e Canais de Alerta (Android).
Testa a integridade de canais, NotificationSoundHelper, atributos de áudio,
padrões de vibração e aplicação em construtores de notificação.
"""

import os
import re
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ANDROID_DIR = os.path.join(BASE_DIR, "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android")


class TestNotificationSoundChannels(unittest.TestCase):
    """Bateria de testes para canais de notificação com som e vibração."""

    def test_notification_sound_helper_exists_and_configured(self):
        """Verifica a presença e configuração correta do NotificationSoundHelper."""
        helper_path = os.path.join(ANDROID_DIR, "notifications", "NotificationSoundHelper.kt")
        self.assertTrue(os.path.isfile(helper_path), "NotificationSoundHelper.kt deve existir")

        with open(helper_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verifica tipo de som e fallback
        self.assertIn("RingtoneManager.TYPE_NOTIFICATION", content)
        self.assertIn("RingtoneManager.TYPE_RINGTONE", content)

        # Verifica atributos de audio
        self.assertIn("AudioAttributes.USAGE_NOTIFICATION", content)
        self.assertIn("AudioAttributes.CONTENT_TYPE_SONIFICATION", content)

        # Verifica vibracao
        self.assertIn("defaultVibrationPattern", content)
        self.assertIn("channel.enableVibration(true)", content)
        self.assertIn("channel.vibrationPattern = defaultVibrationPattern", content)
        self.assertIn("channel.enableLights(true)", content)

        # Verifica overloads para NotificationCompat e Notification nativo
        self.assertIn("applyBuilderSound(builder: NotificationCompat.Builder", content)
        self.assertIn("applyBuilderSound(builder: Notification.Builder", content)

    def test_channel_versions_and_helper_integration(self):
        """Verifica se todos os canais de alerta foram versionados para v2 e usam o helper."""
        channel_checks = [
            (
                os.path.join(ANDROID_DIR, "files", "TransferNotifications.kt"),
                "received_v2",
                "NotificationSoundHelper.configureChannel",
            ),
            (
                os.path.join(ANDROID_DIR, "notifications", "PcNotificationPoster.kt"),
                "pc_notifications_v2",
                "NotificationSoundHelper.configureChannel",
            ),
            (
                os.path.join(ANDROID_DIR, "notifications", "PcNotificationPoster.kt"),
                "peer_notifications_v2",
                "NotificationSoundHelper.configureChannel",
            ),
            (
                os.path.join(ANDROID_DIR, "links", "LinkNotifications.kt"),
                "links_v2",
                "NotificationSoundHelper.configureChannel",
            ),
            (
                os.path.join(ANDROID_DIR, "mirror", "MirrorRequest.kt"),
                "mirror_requests_v2",
                "NotificationSoundHelper.configureChannel",
            ),
            (
                os.path.join(ANDROID_DIR, "notifications", "TaskNotifications.kt"),
                "pc_tasks_v2",
                "NotificationSoundHelper.configureChannel",
            ),
            (
                os.path.join(ANDROID_DIR, "webcam", "WebcamRequest.kt"),
                "webcam_requests_v2",
                "NotificationSoundHelper.configureChannel",
            ),
            (
                os.path.join(ANDROID_DIR, "camera", "ContinuityCameraRequest.kt"),
                "continuity_camera_requests_v2",
                "NotificationSoundHelper.configureChannel",
            ),
            (
                os.path.join(ANDROID_DIR, "mic", "MicRequests.kt"),
                "mic_requests_v2",
                "NotificationSoundHelper.configureChannel",
            ),
            (
                os.path.join(ANDROID_DIR, "elevated", "PairingNotification.kt"),
                "elevated_v2",
                "NotificationSoundHelper.configureChannel",
            ),
            (
                os.path.join(ANDROID_DIR, "power", "PowerScheduleReceiver.kt"),
                "power_schedule_v2",
                "NotificationSoundHelper.configureChannel",
            ),
        ]

        for file_path, expected_channel, expected_helper_call in channel_checks:
            self.assertTrue(os.path.isfile(file_path), f"Arquivo não encontrado: {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            self.assertIn(
                expected_channel,
                text,
                f"Canal versionado {expected_channel} não encontrado em {os.path.basename(file_path)}",
            )
            self.assertIn(
                expected_helper_call,
                text,
                f"Chamada de configuração de som {expected_helper_call} não encontrada em {os.path.basename(file_path)}",
            )

    def test_notification_builders_apply_sound(self):
        """Verifica se os construtores de notificação acionam applyBuilderSound."""
        builder_checks = [
            os.path.join(ANDROID_DIR, "files", "TransferNotifications.kt"),
            os.path.join(ANDROID_DIR, "notifications", "PcNotificationPoster.kt"),
            os.path.join(ANDROID_DIR, "links", "LinkNotifications.kt"),
            os.path.join(ANDROID_DIR, "mirror", "MirrorRequest.kt"),
            os.path.join(ANDROID_DIR, "notifications", "TaskNotifications.kt"),
            os.path.join(ANDROID_DIR, "webcam", "WebcamRequest.kt"),
            os.path.join(ANDROID_DIR, "camera", "ContinuityCameraRequest.kt"),
            os.path.join(ANDROID_DIR, "mic", "MicRequests.kt"),
            os.path.join(ANDROID_DIR, "elevated", "PairingNotification.kt"),
            os.path.join(ANDROID_DIR, "power", "PowerScheduleReceiver.kt"),
        ]

        for file_path in builder_checks:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            self.assertIn(
                "applyBuilderSound",
                text,
                f"applyBuilderSound deve estar presente em {os.path.basename(file_path)}",
            )

    def test_no_emojis_in_notification_code(self):
        """Garante que nenhum emoji foi introduzido no código de notificações."""
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0]"
        )

        target_files = [
            os.path.join(ANDROID_DIR, "notifications", "NotificationSoundHelper.kt"),
            os.path.join(ANDROID_DIR, "files", "TransferNotifications.kt"),
            os.path.join(ANDROID_DIR, "notifications", "PcNotificationPoster.kt"),
            os.path.join(ANDROID_DIR, "links", "LinkNotifications.kt"),
            os.path.join(ANDROID_DIR, "mirror", "MirrorRequest.kt"),
            os.path.join(ANDROID_DIR, "notifications", "TaskNotifications.kt"),
            os.path.join(ANDROID_DIR, "webcam", "WebcamRequest.kt"),
            os.path.join(ANDROID_DIR, "camera", "ContinuityCameraRequest.kt"),
            os.path.join(ANDROID_DIR, "mic", "MicRequests.kt"),
            os.path.join(ANDROID_DIR, "elevated", "PairingNotification.kt"),
            os.path.join(ANDROID_DIR, "power", "PowerScheduleReceiver.kt"),
        ]

        for file_path in target_files:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            matches = emoji_pattern.findall(text)
            self.assertEqual(matches, [], f"Emojis encontrados em {os.path.basename(file_path)}: {matches}")


if __name__ == "__main__":
    unittest.main()

