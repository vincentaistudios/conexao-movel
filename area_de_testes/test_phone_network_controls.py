#!/usr/bin/env python3
"""
Suite de Testes Automatizados para os Controles Avancados de Wi-Fi e Bluetooth.
Valida compatibilidade retroativa, serializacao, sanitizacao, normalizacao de sinal,
categorias de dispositivos Bluetooth e geracao de payloads de comando de rede.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

# Adiciona o diretorio atual ao sys.path para garantir importacao correta
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from phone_network_controls import (
        BtDeviceCategory,
        BtDeviceInfo,
        PhoneToggles,
        WifiNetworkInfo,
        clamp_and_normalize_wifi_signal,
        create_bt_connect_command,
        create_bt_disconnect_command,
        create_wifi_connect_command,
        create_wifi_scan_command,
        normalize_mac,
        sanitize_wifi_ssid,
        validate_mac,
        validate_network_command,
    )
except ImportError:
    from .phone_network_controls import (  # type: ignore
        BtDeviceCategory,
        BtDeviceInfo,
        PhoneToggles,
        WifiNetworkInfo,
        clamp_and_normalize_wifi_signal,
        create_bt_connect_command,
        create_bt_disconnect_command,
        create_wifi_connect_command,
        create_wifi_scan_command,
        normalize_mac,
        sanitize_wifi_ssid,
        validate_mac,
        validate_network_command,
    )


class TestPhoneNetworkControls(unittest.TestCase):
    """Bateria de testes para validacao de controles de rede Wi-Fi e Bluetooth."""

    def test_phone_toggles_backward_compatibility(self):
        """
        Garante que payloads JSON legados (sem campos de Wi-Fi e BT expandidos)
        sejam desserializados perfeitamente com valores padrao ou None.
        """
        legacy_payload_full = {
            "dnd": False,
            "ringer": "ring",
            "flashlight": True,
            "volume": 75,
            "brightness": 80,
            "wifi": True,
            "bluetooth": False,
        }
        legacy_json_str = json.dumps(legacy_payload_full)
        toggles = PhoneToggles.from_json(legacy_json_str)

        self.assertFalse(toggles.dnd)
        self.assertEqual(toggles.ringer, "ring")
        self.assertTrue(toggles.flashlight)
        self.assertEqual(toggles.volume, 75)
        self.assertEqual(toggles.brightness, 80)
        self.assertTrue(toggles.wifi)
        self.assertFalse(toggles.bluetooth)

        # Campos expandidos devem assumir None ou colecoes vazias
        self.assertIsNone(toggles.wifi_ssid)
        self.assertIsNone(toggles.wifi_signal)
        self.assertEqual(toggles.wifi_networks, [])
        self.assertEqual(toggles.bt_devices, [])
        self.assertTrue(toggles.is_valid())

        # Teste com payload legado sem flashlight (opcional no protocolo v0)
        legacy_payload_minimal = {
            "dnd": True,
            "ringer": "silent",
            "volume": 0,
            "brightness": 10,
            "wifi": False,
            "bluetooth": True,
        }
        toggles_minimal = PhoneToggles.from_dict(legacy_payload_minimal)
        self.assertTrue(toggles_minimal.dnd)
        self.assertEqual(toggles_minimal.ringer, "silent")
        self.assertIsNone(toggles_minimal.flashlight)
        self.assertEqual(toggles_minimal.volume, 0)
        self.assertEqual(toggles_minimal.brightness, 10)
        self.assertFalse(toggles_minimal.wifi)
        self.assertTrue(toggles_minimal.bluetooth)
        self.assertIsNone(toggles_minimal.wifi_ssid)
        self.assertIsNone(toggles_minimal.wifi_signal)
        self.assertEqual(toggles_minimal.wifi_networks, [])
        self.assertEqual(toggles_minimal.bt_devices, [])
        self.assertTrue(toggles_minimal.is_valid())

    def test_phone_toggles_with_wifi_and_bluetooth(self):
        """
        Valida a serializacao e desserializacao completa de wifi_ssid, wifi_signal,
        lista de redes wifi_networks (WifiNetworkInfo) e lista de dispositivos bt_devices (BtDeviceInfo).
        """
        net1 = WifiNetworkInfo(
            ssid="Nectar_Corp_5G",
            signal=92,
            bssid="AA:BB:CC:DD:EE:01",
            security="WPA3",
            is_connected=True,
            is_saved=True,
            frequency=5180,
        )
        net2 = WifiNetworkInfo(
            ssid="Visitantes",
            signal=64,
            bssid="AA:BB:CC:DD:EE:02",
            security="WPA2",
            is_connected=False,
            is_saved=False,
            frequency=2412,
        )

        dev1 = BtDeviceInfo(
            mac="11:22:33:44:55:66",
            name="Fone Sem Fio",
            category=BtDeviceCategory.AUDIO,
            is_connected=True,
            is_paired=True,
            battery_level=85,
        )
        dev2 = BtDeviceInfo(
            mac="66:55:44:33:22:11",
            name="Teclado Mecanico",
            category=BtDeviceCategory.INPUT,
            is_connected=False,
            is_paired=True,
            battery_level=None,
        )

        toggles = PhoneToggles(
            dnd=False,
            ringer="vibrate",
            flashlight=False,
            volume=50,
            brightness=70,
            wifi=True,
            bluetooth=True,
            wifi_ssid="Nectar_Corp_5G",
            wifi_signal=92,
            wifi_networks=[net1, net2],
            bt_devices=[dev1, dev2],
        )

        # Serializa para JSON
        serialized_json = toggles.to_json()
        self.assertIsInstance(serialized_json, str)

        # Desserializa de volta
        deserialized = PhoneToggles.from_json(serialized_json)

        # Valida igualdade exata
        self.assertEqual(toggles, deserialized)
        self.assertEqual(deserialized.wifi_ssid, "Nectar_Corp_5G")
        self.assertEqual(deserialized.wifi_signal, 92)
        self.assertEqual(len(deserialized.wifi_networks), 2)
        self.assertEqual(deserialized.wifi_networks[0].ssid, "Nectar_Corp_5G")
        self.assertEqual(deserialized.wifi_networks[0].signal, 92)
        self.assertEqual(deserialized.wifi_networks[0].bssid, "AA:BB:CC:DD:EE:01")
        self.assertTrue(deserialized.wifi_networks[0].is_connected)

        self.assertEqual(len(deserialized.bt_devices), 2)
        self.assertEqual(deserialized.bt_devices[0].mac, "11:22:33:44:55:66")
        self.assertEqual(deserialized.bt_devices[0].name, "Fone Sem Fio")
        self.assertEqual(deserialized.bt_devices[0].category, BtDeviceCategory.AUDIO)
        self.assertEqual(deserialized.bt_devices[0].battery_level, 85)
        self.assertTrue(deserialized.bt_devices[0].is_connected)

    def test_wifi_signal_clamping_and_normalization(self):
        """
        Garante que niveis de sinal fora do intervalo 0..100 sejam normalizados
        ou tratados com seguranca (clamping defensivo e conversao de dBm).
        """
        # Valores superiores a 100 devem ser limitados a 100
        self.assertEqual(clamp_and_normalize_wifi_signal(120), 100)
        self.assertEqual(clamp_and_normalize_wifi_signal(255), 100)
        self.assertEqual(clamp_and_normalize_wifi_signal(999), 100)

        # Valores na faixa normal permanecem inalterados
        self.assertEqual(clamp_and_normalize_wifi_signal(0), 0)
        self.assertEqual(clamp_and_normalize_wifi_signal(50), 50)
        self.assertEqual(clamp_and_normalize_wifi_signal(100), 100)

        # Valores em dBm (negativos): conversao 2 * (dBm + 100)
        self.assertEqual(clamp_and_normalize_wifi_signal(-50), 100)
        self.assertEqual(clamp_and_normalize_wifi_signal(-30), 100)
        self.assertEqual(clamp_and_normalize_wifi_signal(-75), 50)
        self.assertEqual(clamp_and_normalize_wifi_signal(-100), 0)
        self.assertEqual(clamp_and_normalize_wifi_signal(-120), 0)

        # Strings numericas e floats
        self.assertEqual(clamp_and_normalize_wifi_signal("85"), 85)
        self.assertEqual(clamp_and_normalize_wifi_signal("150"), 100)
        self.assertEqual(clamp_and_normalize_wifi_signal("-60"), 80)
        self.assertEqual(clamp_and_normalize_wifi_signal(78.6), 79)

        # Valor nulo retorna None
        self.assertIsNone(clamp_and_normalize_wifi_signal(None))

        # Valores invalidos lancam ValueError
        with self.assertRaises(ValueError):
            clamp_and_normalize_wifi_signal("sinal_invalido")
        with self.assertRaises(ValueError):
            clamp_and_normalize_wifi_signal([])

    def test_wifi_ssid_sanitization(self):
        """
        Garante remocao de aspas duplas adicionadas pelo Android (\"MinhaRede\" -> MinhaRede)
        e filtragem adequada de marcadores invalidos como <unknown ssid>.
        """
        # Aspas adicionadas pelo Android
        self.assertEqual(sanitize_wifi_ssid('"MinhaRede"'), "MinhaRede")
        self.assertEqual(sanitize_wifi_ssid('""RedeDupla""'), "RedeDupla")
        self.assertEqual(sanitize_wifi_ssid(r'\"RedeEscapada\"'), "RedeEscapada")
        self.assertEqual(sanitize_wifi_ssid("'RedeAspasSimples'"), "RedeAspasSimples")

        # Filtragem de SSID desconhecido retornado quando sem permissao/desconectado
        self.assertIsNone(sanitize_wifi_ssid("<unknown ssid>"))
        self.assertIsNone(sanitize_wifi_ssid("<UNKNOWN SSID>"))
        self.assertIsNone(sanitize_wifi_ssid("<unknown>"))
        self.assertIsNone(sanitize_wifi_ssid("unknown"))
        self.assertIsNone(sanitize_wifi_ssid("0x"))
        self.assertIsNone(sanitize_wifi_ssid(""))
        self.assertIsNone(sanitize_wifi_ssid("   "))
        self.assertIsNone(sanitize_wifi_ssid(None))

        # SSIDs validos com espacos, hifens e acentuacao
        self.assertEqual(sanitize_wifi_ssid("Escritorio 5G"), "Escritorio 5G")
        self.assertEqual(sanitize_wifi_ssid("Rede-Visitante_Ext"), "Rede-Visitante_Ext")
        self.assertEqual(sanitize_wifi_ssid("Café São Paulo"), "Café São Paulo")

    def test_bt_device_categories_and_mac_validation(self):
        """
        Valida mapeamento de categorias de dispositivo (audio, input, relogio, celular)
        e formatacao/validacao de enderecos MAC.
        """
        # Mapeamento de categorias de audio
        self.assertEqual(BtDeviceCategory.parse("audio"), BtDeviceCategory.AUDIO)
        self.assertEqual(BtDeviceCategory.parse("headset"), BtDeviceCategory.AUDIO)
        self.assertEqual(BtDeviceCategory.parse("headphones"), BtDeviceCategory.AUDIO)
        self.assertEqual(BtDeviceCategory.parse("speaker"), BtDeviceCategory.AUDIO)

        # Mapeamento de dispositivos de entrada (input)
        self.assertEqual(BtDeviceCategory.parse("input"), BtDeviceCategory.INPUT)
        self.assertEqual(BtDeviceCategory.parse("mouse"), BtDeviceCategory.INPUT)
        self.assertEqual(BtDeviceCategory.parse("keyboard"), BtDeviceCategory.INPUT)
        self.assertEqual(BtDeviceCategory.parse("gamepad"), BtDeviceCategory.INPUT)
        self.assertEqual(BtDeviceCategory.parse("teclado/controle"), BtDeviceCategory.INPUT)
        self.assertEqual(BtDeviceCategory.parse("periferico"), BtDeviceCategory.INPUT)

        # Mapeamento de relogios e vestiveis (watch)
        self.assertEqual(BtDeviceCategory.parse("watch"), BtDeviceCategory.WATCH)
        self.assertEqual(BtDeviceCategory.parse("smartwatch"), BtDeviceCategory.WATCH)
        self.assertEqual(BtDeviceCategory.parse("wearable"), BtDeviceCategory.WATCH)
        self.assertEqual(BtDeviceCategory.parse("relogio"), BtDeviceCategory.WATCH)

        # Mapeamento de telefones/celulares (phone)
        self.assertEqual(BtDeviceCategory.parse("phone"), BtDeviceCategory.PHONE)
        self.assertEqual(BtDeviceCategory.parse("smartphone"), BtDeviceCategory.PHONE)
        self.assertEqual(BtDeviceCategory.parse("celular"), BtDeviceCategory.PHONE)

        # Mapeamento de outros/computadores (other)
        self.assertEqual(BtDeviceCategory.parse("computer"), BtDeviceCategory.OTHER)
        self.assertEqual(BtDeviceCategory.parse("computador"), BtDeviceCategory.OTHER)
        self.assertEqual(BtDeviceCategory.parse("desktop"), BtDeviceCategory.OTHER)
        self.assertEqual(BtDeviceCategory.parse("unknown"), BtDeviceCategory.OTHER)

        # Validacao e normalizacao de enderecos MAC
        valid_macs = [
            ("aa:bb:cc:dd:ee:ff", "AA:BB:CC:DD:EE:FF"),
            ("AA:BB:CC:DD:EE:FF", "AA:BB:CC:DD:EE:FF"),
            ("00-11-22-33-44-55", "00:11:22:33:44:55"),
            ("AABBCCDDEEFF", "AA:BB:CC:DD:EE:FF"),
            ("001122334455", "00:11:22:33:44:55"),
        ]
        for raw, expected in valid_macs:
            self.assertTrue(validate_mac(raw), f"MAC '{raw}' deve ser considerado valido")
            self.assertEqual(normalize_mac(raw), expected)

        invalid_macs = [
            "invalido",
            "00:11:22:33:44",        # 5 octetos
            "00:11:22:33:44:55:66",  # 7 octetos
            "GG:HH:II:JJ:KK:LL",     # Caracteres fora de hex
            "",
            "   ",
        ]
        for invalid in invalid_macs:
            self.assertFalse(validate_mac(invalid), f"MAC '{invalid}' deve ser invalido")
            with self.assertRaises(ValueError):
                normalize_mac(invalid)

    def test_network_toggle_command_payloads(self):
        """
        Valida a formacao de payloads para wifi_scan, wifi_connect, bt_connect, bt_disconnect.
        """
        # Comando wifi_scan
        cmd_scan = create_wifi_scan_command()
        self.assertEqual(cmd_scan["id"], "wifi_scan")
        self.assertEqual(cmd_scan["action"], "scan")
        self.assertEqual(cmd_scan["target"], "wifi")
        self.assertTrue(validate_network_command(cmd_scan))

        # Comando wifi_connect (com sanitizacao automatica de SSID)
        cmd_connect = create_wifi_connect_command(
            ssid='"MinhaRedeDomestica"',
            password="SenhaForte123",
            bssid="00-11-22-33-44-55",
            hidden=False,
        )
        self.assertEqual(cmd_connect["id"], "wifi_connect")
        self.assertEqual(cmd_connect["action"], "connect")
        self.assertEqual(cmd_connect["target"], "wifi")
        self.assertEqual(cmd_connect["ssid"], "MinhaRedeDomestica")
        self.assertEqual(cmd_connect["password"], "SenhaForte123")
        self.assertEqual(cmd_connect["bssid"], "00:11:22:33:44:55")
        self.assertFalse(cmd_connect["hidden"])
        self.assertTrue(validate_network_command(cmd_connect))

        # Rejeicao de wifi_connect com SSID invalido
        with self.assertRaises(ValueError):
            create_wifi_connect_command("<unknown ssid>")
        with self.assertRaises(ValueError):
            create_wifi_connect_command("")

        # Comando bt_connect
        cmd_bt_conn = create_bt_connect_command("aa:bb:cc:dd:ee:ff")
        self.assertEqual(cmd_bt_conn["id"], "bt_connect")
        self.assertEqual(cmd_bt_conn["action"], "connect")
        self.assertEqual(cmd_bt_conn["target"], "bluetooth")
        self.assertEqual(cmd_bt_conn["mac"], "AA:BB:CC:DD:EE:FF")
        self.assertTrue(validate_network_command(cmd_bt_conn))

        # Comando bt_disconnect
        cmd_bt_disc = create_bt_disconnect_command("00-11-22-33-44-55")
        self.assertEqual(cmd_bt_disc["id"], "bt_disconnect")
        self.assertEqual(cmd_bt_disc["action"], "disconnect")
        self.assertEqual(cmd_bt_disc["target"], "bluetooth")
        self.assertEqual(cmd_bt_disc["mac"], "00:11:22:33:44:55")
        self.assertTrue(validate_network_command(cmd_bt_disc))

        # Comandos malformados rejeitados por validate_network_command
        self.assertFalse(validate_network_command({"id": "invalido"}))
        self.assertFalse(validate_network_command({"id": "bt_connect", "target": "wifi"}))
        self.assertFalse(validate_network_command({"id": "bt_connect", "target": "bluetooth", "action": "connect", "mac": "invalido"}))
        self.assertFalse(validate_network_command("nao_e_dicionario"))


if __name__ == "__main__":
    unittest.main()
