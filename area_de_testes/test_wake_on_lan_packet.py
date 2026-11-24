# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Suite de Testes Unitarios e de Integracao: Wake-on-LAN (WoL) Magic Packet.
Valida a construcao do Magic Packet (6x 0xFF + 16x MAC), portas padrao 9 e 7,
calculo de broadcast de sub-rede IPv4 e transmissao via socket UDP broadcast.
"""

import os
import sys
import socket
import unittest
from unittest.mock import patch, MagicMock

# Constantes canonicas do protocolo NectarLink para Wake-on-LAN
WOL_HEADER_BYTES = b"\xff" * 6
WOL_MAC_REPETITIONS = 16
WOL_PACKET_LENGTH = 102
WOL_DEFAULT_PORTS = (9, 7)
WOL_GLOBAL_BROADCAST = "255.255.255.255"


def parse_mac(mac_str: str) -> bytes:
    """
    Analisa e valida um endereco MAC em formato legivel (separado por : ou -).
    Rejeita enderecos nulos, de broadcast ou multicast (bit menos significativo do primeiro octeto ativo).
    """
    if not mac_str or not isinstance(mac_str, str):
        raise ValueError("Endereco MAC invalido ou vazio.")

    clean = mac_str.strip()
    sep = ":" if ":" in clean else "-"
    parts = clean.split(sep)
    if len(parts) != 6:
        raise ValueError(f"Endereco MAC deve possuir exatamente 6 octetos: {mac_str}")

    try:
        raw_bytes = bytes(int(p, 16) for p in parts if len(p) == 2)
    except ValueError as exc:
        raise ValueError(f"Octeto hexadecimal invalido no MAC: {mac_str}") from exc

    if len(raw_bytes) != 6:
        raise ValueError(f"Formato de octeto invalido no MAC: {mac_str}")

    if raw_bytes == b"\x00" * 6:
        raise ValueError("Endereco MAC nulo (00:00:00:00:00:00) nao e suportado.")

    if raw_bytes == b"\xff" * 6:
        raise ValueError("Endereco MAC de broadcast (FF:FF:FF:FF:FF:FF) nao e suportado.")

    if raw_bytes[0] & 1 == 1:
        raise ValueError("Endereco MAC multicast nao pode ser usado para Wake-on-LAN.")

    return raw_bytes


def format_mac(raw_bytes: bytes) -> str:
    """Formata bytes de MAC no formato canonico minusculo separado por dois pontos."""
    if len(raw_bytes) != 6:
        raise ValueError("MAC deve conter exatamente 6 bytes.")
    return ":".join(f"{b:02x}" for b in raw_bytes)


def build_magic_packet(mac_input) -> bytes:
    """
    Constroi o Magic Packet Wake-on-LAN padrao de 102 bytes:
    6 bytes de 0xFF seguidos por 16 repeticoes do MAC de 6 bytes.
    """
    if isinstance(mac_input, str):
        mac_bytes = parse_mac(mac_input)
    elif isinstance(mac_input, (bytes, bytearray)):
        if len(mac_input) != 6:
            raise ValueError("Bytes do MAC devem ter comprimento 6.")
        if mac_input == b"\x00" * 6 or mac_input == b"\xff" * 6 or (mac_input[0] & 1 == 1):
            raise ValueError("Endereco MAC invalido para Wake-on-LAN.")
        mac_bytes = bytes(mac_input)
    else:
        raise TypeError("Entrada de MAC deve ser str ou bytes.")

    return WOL_HEADER_BYTES + (mac_bytes * WOL_MAC_REPETITIONS)


def calculate_ipv4_broadcast(ip_str: str, prefix_len: int) -> str:
    """Calcula o endereco de broadcast direcionado para uma sub-rede IPv4."""
    if not (1 <= prefix_len <= 30):
        raise ValueError(f"Tamanho de prefixo invalido: {prefix_len}")

    parts = [int(p) for p in ip_str.strip().split(".")]
    if len(parts) != 4 or any(p < 0 or p > 255 for p in parts):
        raise ValueError(f"Endereco IPv4 invalido: {ip_str}")

    ip_num = (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]
    mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
    bcast_num = ip_num | (~mask & 0xFFFFFFFF)

    return f"{(bcast_num >> 24) & 0xFF}.{(bcast_num >> 16) & 0xFF}.{(bcast_num >> 8) & 0xFF}.{bcast_num & 0xFF}"


def dispatch_wake_packet(
    mac_str: str,
    target_ips: list,
    ports: tuple = WOL_DEFAULT_PORTS,
    bursts: int = 1,
    sock=None
) -> list:
    """
    Envia pacotes Wake-on-LAN via socket UDP broadcast para os alvos e portas especificados.
    Retorna lista de tuplas (ip, porta, tamanho) enviadas.
    """
    packet = build_magic_packet(mac_str)
    sent_log = []
    should_close = False

    if sock is None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        should_close = True

    try:
        for _ in range(max(1, bursts)):
            for ip in target_ips:
                for port in ports:
                    sock.sendto(packet, (ip, port))
                    sent_log.append((ip, port, len(packet)))
    finally:
        if should_close:
            sock.close()

    return sent_log


class TestWakeOnLanPacket(unittest.TestCase):
    """Testes unitarios e de transmissao de Magic Packet para Wake-on-LAN."""

    def setUp(self):
        self.valid_mac_colon = "00:11:22:33:44:55"
        self.valid_mac_hyphen = "AA-BB-CC-DD-EE-FF"
        self.sample_mac_bytes = bytes([0x00, 0x11, 0x22, 0x33, 0x44, 0x55])

    def test_mac_parser_valid_formats(self):
        """Valida que enderecos MAC com separadores : ou - sao interpretados corretamente."""
        bytes_colon = parse_mac(self.valid_mac_colon)
        self.assertEqual(bytes_colon, bytes([0x00, 0x11, 0x22, 0x33, 0x44, 0x55]))

        bytes_hyphen = parse_mac(self.valid_mac_hyphen)
        self.assertEqual(bytes_hyphen, bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF]))
        self.assertEqual(format_mac(bytes_hyphen), "aa:bb:cc:dd:ee:ff")

    def test_mac_parser_rejects_all_zeros(self):
        """Valida rejeicao de MAC nulo 00:00:00:00:00:00."""
        with self.assertRaises(ValueError):
            parse_mac("00:00:00:00:00:00")

    def test_mac_parser_rejects_broadcast_mac(self):
        """Valida rejeicao de MAC de broadcast ff:ff:ff:ff:ff:ff."""
        with self.assertRaises(ValueError):
            parse_mac("FF:FF:FF:FF:FF:FF")

    def test_mac_parser_rejects_multicast_mac(self):
        """Valida rejeicao de enderecos MAC multicast (bit 0 do primeiro octeto ativo)."""
        with self.assertRaises(ValueError):
            parse_mac("01:00:5e:00:00:01")
        with self.assertRaises(ValueError):
            parse_mac("03:aa:bb:cc:dd:ee")

    def test_mac_parser_rejects_malformed_inputs(self):
        """Valida tratamento seguro para formatos invalidos e octetos incorretos."""
        invalid_macs = [
            "",
            "invalid_mac",
            "00:11:22:33:44",
            "00:11:22:33:44:55:66",
            "00:11:22:33:44:GG",
            "0:11:22:33:44:55",
        ]
        for inv in invalid_macs:
            with self.assertRaises(ValueError):
                parse_mac(inv)

    def test_magic_packet_exact_dimensions(self):
        """Valida que o pacote WoL gerado tem exatamente 102 bytes."""
        packet = build_magic_packet(self.valid_mac_colon)
        self.assertEqual(len(packet), WOL_PACKET_LENGTH)

    def test_magic_packet_header_structure(self):
        """Valida que os primeiros 6 bytes do pacote sao exclusivamente 0xFF."""
        packet = build_magic_packet(self.valid_mac_colon)
        self.assertEqual(packet[:6], b"\xff\xff\xff\xff\xff\xff")

    def test_magic_packet_16_repetitions_integrity(self):
        """Valida que o endereco MAC e repetido exatamente 16 vezes consecutivas."""
        packet = build_magic_packet(self.valid_mac_colon)
        mac_expected = bytes([0x00, 0x11, 0x22, 0x33, 0x44, 0x55])

        for i in range(16):
            offset = 6 + (i * 6)
            chunk = packet[offset: offset + 6]
            self.assertEqual(chunk, mac_expected, f"Falha na repeticao {i} do MAC.")

    def test_default_wol_ports(self):
        """Valida que as portas canonicas Wake-on-LAN sao UDP 9 e UDP 7."""
        self.assertEqual(WOL_DEFAULT_PORTS, (9, 7))
        self.assertIn(9, WOL_DEFAULT_PORTS)
        self.assertIn(7, WOL_DEFAULT_PORTS)

    def test_ipv4_subnet_broadcast_calculation(self):
        """Valida calculo de broadcast para diferentes mascaras de rede (/24, /16, /28)."""
        bcast_24 = calculate_ipv4_broadcast("192.168.1.100", 24)
        self.assertEqual(bcast_24, "192.168.1.255")

        bcast_16 = calculate_ipv4_broadcast("10.0.50.25", 16)
        self.assertEqual(bcast_16, "10.0.255.255")

        bcast_28 = calculate_ipv4_broadcast("192.168.10.33", 28)
        self.assertEqual(bcast_28, "192.168.10.47")

    def test_dispatch_wake_packet_mock_socket(self):
        """Valida envio dos pacotes WoL via socket UDP com flag broadcast ativa."""
        mock_sock = MagicMock()
        target_ips = ["192.168.1.255", WOL_GLOBAL_BROADCAST]

        sent = dispatch_wake_packet(
            mac_str=self.valid_mac_colon,
            target_ips=target_ips,
            ports=(9, 7),
            bursts=2,
            sock=mock_sock
        )

        # 2 alvos * 2 portas * 2 bursts = 8 envios
        self.assertEqual(len(sent), 8)
        self.assertEqual(mock_sock.sendto.call_count, 8)

        for call_args in mock_sock.sendto.call_args_list:
            data, (ip, port) = call_args[0]
            self.assertEqual(len(data), 102)
            self.assertEqual(data[:6], b"\xff" * 6)
            self.assertIn(ip, target_ips)
            self.assertIn(port, [9, 7])

    def test_relay_payload_structure(self):
        """Valida estrutura de payload para requisicao de relay (wake.relay)."""
        mac_str = "00:11:22:33:44:55"
        mac_bytes = parse_mac(mac_str)
        relay_payload = {
            "mac": list(mac_bytes),
            "broadcast": "192.168.1.255"
        }
        self.assertEqual(len(relay_payload["mac"]), 6)
        self.assertEqual(relay_payload["broadcast"], "192.168.1.255")

    def test_no_emojis_in_source_code(self):
        """Garante ausencia estrita de emojis no arquivo de testes segundo diretriz global."""
        current_file = os.path.abspath(__file__)
        with open(current_file, "r", encoding="utf-8") as f:
            content = f.read()

        for char in content:
            code_point = ord(char)
            is_emoji = (
                (0x1F600 <= code_point <= 0x1F64F)
                or (0x1F300 <= code_point <= 0x1F5FF)
                or (0x1F680 <= code_point <= 0x1F6FF)
                or (0x2600 <= code_point <= 0x26FF)
                or (0x2700 <= code_point <= 0x27BF)
                or (0x1F900 <= code_point <= 0x1F9FF)
            )
            self.assertFalse(is_emoji, f"Emoji detectado no codigo fonte: code point {code_point}")


if __name__ == "__main__":
    unittest.main()
