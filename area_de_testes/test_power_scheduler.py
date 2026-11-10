#!/usr/bin/env python3
"""
Suite de Testes de Integridade e Lógica para Energia e Agendador (Power Scheduler)
do NectarLink / Conexão Móvel.

Cobre:
- Teste 1: Validação das ações de energia expandidas (lock, sleep, shutdown, reboot) e rejeição de ações inválidas.
- Teste 2: Cálculo de próximo disparo de agendamento (next_trigger) considerando horários no passado do mesmo dia,
           recorrência por dias da semana selecionados (ex.: Seg-Sex vs Fim de Semana) e mudança de dia.
- Teste 3: Serialização e desserialização de PowerSchedule para JSON, garantindo integridade dos campos
           (dias, horas, minutos, acao, flags).
- Teste 4: Validação dos pacotes Magic Packet de Wake-on-LAN (102 bytes: 6x 0xFF + 16x MAC).
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timedelta

# Garante importação tanto local quanto se executado a partir de outros diretórios
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from power_scheduler import (
        PowerAction,
        PowerSchedule,
        calculate_next_trigger,
        create_magic_packet,
        validate_magic_packet,
        parse_mac,
        format_mac,
        normalize_days,
        WOL_MAGIC_PACKET_LENGTH,
        WOL_HEADER,
        WOL_REPETITIONS,
    )
except ImportError:
    # Fallback caso executado em ambiente isolado
    from .power_scheduler import (  # type: ignore
        PowerAction,
        PowerSchedule,
        calculate_next_trigger,
        create_magic_packet,
        validate_magic_packet,
        parse_mac,
        format_mac,
        normalize_days,
        WOL_MAGIC_PACKET_LENGTH,
        WOL_HEADER,
        WOL_REPETITIONS,
    )


class TestPowerActions(unittest.TestCase):
    """
    Teste 1: Validação das ações de energia expandidas (lock, sleep, shutdown, reboot)
    e rejeição de ações inválidas.
    """

    def test_expanded_valid_actions(self):
        """Garante suporte a lock, sleep, shutdown e reboot."""
        valid_expected = {"lock", "sleep", "shutdown", "reboot"}
        actions_found = {a.value for a in PowerAction}
        self.assertEqual(
            actions_found,
            valid_expected,
            f"As ações de energia devem incluir exatamente {valid_expected}, mas foi encontrado {actions_found}",
        )

        for act in valid_expected:
            parsed = PowerAction.parse(act)
            self.assertEqual(parsed.value, act)
            self.assertTrue(PowerAction.is_valid(act))

    def test_action_case_insensitivity_and_aliases(self):
        """Garante que sinônimos técnicos e variações de caixa alta/baixa sejam normalizados."""
        cases = [
            ("LOCK", PowerAction.LOCK),
            ("Lock", PowerAction.LOCK),
            ("SLEEP", PowerAction.SLEEP),
            ("suspend", PowerAction.SLEEP),
            ("Suspend", PowerAction.SLEEP),
            ("SHUTDOWN", PowerAction.SHUTDOWN),
            ("poweroff", PowerAction.SHUTDOWN),
            ("power_off", PowerAction.SHUTDOWN),
            ("REBOOT", PowerAction.REBOOT),
            ("restart", PowerAction.REBOOT),
        ]
        for raw, expected in cases:
            parsed = PowerAction.parse(raw)
            self.assertEqual(parsed, expected, f"Falha ao normalizar '{raw}' para '{expected.value}'")
            self.assertTrue(PowerAction.is_valid(raw))

    def test_invalid_actions_rejected(self):
        """Garante que ações inválidas e valores anômalos sejam rejeitados com ValueError."""
        invalid_cases = [
            "hibernate",
            "logoff",
            "signout",
            "explode",
            "format_c",
            "destroy",
            "",
            "   ",
            "sleep_now!",
            "reboot --force",
            "shutdown -s -t 0",
            123,
            None,
            [],
            {},
        ]
        for invalid in invalid_cases:
            with self.subTest(invalid=invalid):
                self.assertFalse(
                    PowerAction.is_valid(invalid),
                    f"PowerAction.is_valid deveria retornar False para: {invalid!r}",
                )
                with self.assertRaises(ValueError):
                    PowerAction.parse(invalid)


class TestScheduleNextTrigger(unittest.TestCase):
    """
    Teste 2: Cálculo de próximo disparo de agendamento (next_trigger) considerando:
    - Horários no passado do mesmo dia
    - Recorrência por dias da semana selecionados (ex.: Seg-Sex vs Fim de Semana)
    - Mudança de dia, mês e virada de ano
    """

    def test_past_time_same_day_triggers_next_occurrence(self):
        """
        Se o horário de hoje já passou, o próximo disparo DEVE ser no próximo dia
        habilitado, e não hoje no passado.
        """
        # Terça-feira (weekday=1), 15:30:00
        base_time = datetime(2026, 11, 10, 15, 30, 0)
        self.assertEqual(base_time.weekday(), 1)  # Confirma Terça-feira

        # Schedule diário às 10:00 (já passou hoje)
        sched = PowerSchedule(
            action=PowerAction.LOCK,
            hour=10,
            minute=0,
            days=["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        )

        next_dt = sched.next_trigger(base_time=base_time)
        self.assertIsNotNone(next_dt)
        # Deve ser Quarta-feira (2026-11-11) às 10:00
        self.assertEqual(next_dt, datetime(2026, 11, 11, 10, 0, 0))
        self.assertGreater(next_dt, base_time)

    def test_future_time_same_day_triggers_today(self):
        """
        Se o horário de hoje ainda não chegou e hoje está na lista,
        o disparo deve ocorrer no mesmo dia.
        """
        # Terça-feira, 08:15:00
        base_time = datetime(2026, 11, 10, 8, 15, 0)

        # Schedule às 10:00 para Terça-feira
        sched = PowerSchedule(
            action=PowerAction.SLEEP,
            hour=10,
            minute=0,
            days=["tue"],
        )

        next_dt = sched.next_trigger(base_time=base_time)
        self.assertEqual(next_dt, datetime(2026, 11, 10, 10, 0, 0))

    def test_exact_same_minute_advances_to_next_occurrence(self):
        """
        Se base_time for exatamente igual ao horário do evento no segundo 0,
        o próximo disparo não pode ser retroativo ou coincidente no mesmo instante.
        """
        base_time = datetime(2026, 11, 10, 10, 0, 0)
        sched = PowerSchedule(
            action=PowerAction.SHUTDOWN,
            hour=10,
            minute=0,
            days=["tue", "wed"],
        )

        next_dt = sched.next_trigger(base_time=base_time)
        # Como 10:00 já é o instante atual, o próximo disparo deve ser quarta-feira às 10:00
        self.assertEqual(next_dt, datetime(2026, 11, 11, 10, 0, 0))

    def test_weekdays_only_recurrence(self):
        """
        Valida recorrência Seg-Sex:
        - Na sexta-feira após o horário, salta para Segunda-feira (pula sábado e domingo).
        - No sábado ou domingo, salta para Segunda-feira.
        """
        weekdays = ["mon", "tue", "wed", "thu", "fri"]
        sched = PowerSchedule(
            action=PowerAction.SHUTDOWN,
            hour=18,
            minute=30,
            days=weekdays,
        )

        # 1. Sexta-feira às 19:00 (13/11/2026) -> deve disparar na Segunda-feira (16/11/2026) às 18:30
        friday_night = datetime(2026, 11, 13, 19, 0, 0)
        self.assertEqual(friday_night.weekday(), 4)  # Sexta
        next_dt = sched.next_trigger(base_time=friday_night)
        self.assertEqual(next_dt, datetime(2026, 11, 16, 18, 30, 0))
        self.assertEqual(next_dt.weekday(), 0)  # Segunda

        # 2. Sábado às 11:00 (14/11/2026) -> deve disparar na Segunda-feira (16/11/2026) às 18:30
        saturday = datetime(2026, 11, 14, 11, 0, 0)
        self.assertEqual(saturday.weekday(), 5)
        next_dt = sched.next_trigger(base_time=saturday)
        self.assertEqual(next_dt, datetime(2026, 11, 16, 18, 30, 0))

        # 3. Domingo às 22:00 (15/11/2026) -> deve disparar na Segunda-feira (16/11/2026) às 18:30
        sunday = datetime(2026, 11, 15, 22, 0, 0)
        self.assertEqual(sunday.weekday(), 6)
        next_dt = sched.next_trigger(base_time=sunday)
        self.assertEqual(next_dt, datetime(2026, 11, 16, 18, 30, 0))

        # 4. Segunda-feira antes do horário às 08:00 (16/11/2026) -> dispara hoje às 18:30
        monday_morning = datetime(2026, 11, 16, 8, 0, 0)
        next_dt = sched.next_trigger(base_time=monday_morning)
        self.assertEqual(next_dt, datetime(2026, 11, 16, 18, 30, 0))

    def test_weekend_only_recurrence(self):
        """
        Valida recorrência Fim de Semana (Sáb-Dom):
        - Em dias de semana, salta para o próximo Sábado.
        - No domingo após o horário, salta para o Sábado seguinte (+6 dias).
        """
        weekend = ["sat", "sun"]
        sched = PowerSchedule(
            action=PowerAction.SLEEP,
            hour=23,
            minute=0,
            days=weekend,
        )

        # Quarta-feira às 14:00 (11/11/2026) -> próximo é Sábado (14/11/2026) às 23:00
        wednesday = datetime(2026, 11, 11, 14, 0, 0)
        next_dt = sched.next_trigger(base_time=wednesday)
        self.assertEqual(next_dt, datetime(2026, 11, 14, 23, 0, 0))
        self.assertEqual(next_dt.weekday(), 5)  # Sábado

        # Sábado às 10:00 (14/11/2026) -> dispara no mesmo dia às 23:00
        saturday_morning = datetime(2026, 11, 14, 10, 0, 0)
        next_dt = sched.next_trigger(base_time=saturday_morning)
        self.assertEqual(next_dt, datetime(2026, 11, 14, 23, 0, 0))

        # Domingo às 23:30 (15/11/2026) -> já passou de 23:00, próximo é Sábado (21/11/2026)
        sunday_late = datetime(2026, 11, 15, 23, 30, 0)
        next_dt = sched.next_trigger(base_time=sunday_late)
        self.assertEqual(next_dt, datetime(2026, 11, 21, 23, 0, 0))
        self.assertEqual(next_dt.weekday(), 5)

    def test_midnight_and_day_turnover(self):
        """
        Testa viradas de dia:
        - Às 23:59:50 agendado para 00:05 (mudança de dia após alguns segundos).
        - Mudança de mês (ex.: 31 de Janeiro para 1 de Fevereiro).
        - Mudança de ano (ex.: 31 de Dezembro para 1 de Janeiro).
        """
        # 1. Virada de dia comum: 23:59:50 -> 00:05:00
        late_night = datetime(2026, 5, 10, 23, 59, 50)
        sched = PowerSchedule(
            action=PowerAction.REBOOT,
            hour=0,
            minute=5,
            days=list(range(7)),
        )
        next_dt = sched.next_trigger(base_time=late_night)
        self.assertEqual(next_dt, datetime(2026, 5, 11, 0, 5, 0))

        # 2. Virada de mês: 31 de Janeiro às 23:45 -> 1 de Fevereiro às 07:00
        end_of_jan = datetime(2026, 1, 31, 23, 45, 0)
        sched_morning = PowerSchedule(
            action=PowerAction.LOCK,
            hour=7,
            minute=0,
            days=list(range(7)),
        )
        next_dt = sched_morning.next_trigger(base_time=end_of_jan)
        self.assertEqual(next_dt, datetime(2026, 2, 1, 7, 0, 0))

        # 3. Virada de ano: 31 de Dezembro às 23:55 -> 1 de Janeiro às 08:00
        new_year_eve = datetime(2026, 12, 31, 23, 55, 0)
        sched_ny = PowerSchedule(
            action=PowerAction.SHUTDOWN,
            hour=8,
            minute=0,
            days=list(range(7)),
        )
        next_dt = sched_ny.next_trigger(base_time=new_year_eve)
        self.assertEqual(next_dt, datetime(2027, 1, 1, 8, 0, 0))

    def test_disabled_schedule_returns_none(self):
        """Agendamentos desabilitados nunca devem retornar disparo."""
        sched = PowerSchedule(
            action=PowerAction.LOCK,
            hour=12,
            minute=0,
            enabled=False,
        )
        self.assertIsNone(sched.next_trigger(base_time=datetime(2026, 11, 10, 10, 0, 0)))


class TestPowerScheduleSerialization(unittest.TestCase):
    """
    Teste 3: Serialização e desserialização de PowerSchedule para JSON,
    garantindo integridade dos campos (dias, horas, minutos, acao, flags).
    """

    def test_full_roundtrip_json_serialization(self):
        """Verifica serialização e desserialização completa e roundtrip sem perda de campos."""
        original = PowerSchedule(
            id="sched-test-uuid-001",
            name="Bloqueio Noturno Escritório",
            action=PowerAction.SHUTDOWN,
            hour=22,
            minute=45,
            days=["mon", "wed", "fri"],
            enabled=True,
            notify_before=True,
            warning_seconds=120,
            force=True,
            repeat=True,
            one_shot=False,
        )

        json_output = original.to_json(indent=2)
        self.assertIsInstance(json_output, str)

        parsed_data = json.loads(json_output)
        self.assertEqual(parsed_data["id"], "sched-test-uuid-001")
        self.assertEqual(parsed_data["name"], "Bloqueio Noturno Escritório")
        self.assertEqual(parsed_data["action"], "shutdown")
        self.assertEqual(parsed_data["hour"], 22)
        self.assertEqual(parsed_data["minute"], 45)
        self.assertEqual(parsed_data["days"], [0, 2, 4])  # mon=0, wed=2, fri=4
        self.assertTrue(parsed_data["enabled"])
        self.assertTrue(parsed_data["notify_before"])
        self.assertEqual(parsed_data["warning_seconds"], 120)
        self.assertTrue(parsed_data["force"])
        self.assertTrue(parsed_data["repeat"])
        self.assertFalse(parsed_data["one_shot"])

        # Desserialização a partir do JSON
        rebuilt = PowerSchedule.from_json(json_output)
        self.assertEqual(original, rebuilt)
        self.assertEqual(original.to_dict(), rebuilt.to_dict())

    def test_serialization_all_actions(self):
        """Valida integridade da ação em todas as ações de energia possíveis."""
        for action in [PowerAction.LOCK, PowerAction.SLEEP, PowerAction.SHUTDOWN, PowerAction.REBOOT]:
            sched = PowerSchedule(
                action=action,
                hour=14,
                minute=30,
                days=["sat"],
            )
            raw_json = sched.to_json()
            restored = PowerSchedule.from_json(raw_json)
            self.assertEqual(restored.action, action.value)

    def test_deserialization_validation_errors(self):
        """Garante que payloads JSON corrompidos ou com valores ilegais sejam rejeitados."""
        # 1. Hora inválida (> 23)
        bad_hour = json.dumps({"action": "lock", "hour": 25, "minute": 0, "days": [0]})
        with self.assertRaises(ValueError):
            PowerSchedule.from_json(bad_hour)

        # 2. Minuto inválido (< 0)
        bad_minute = json.dumps({"action": "lock", "hour": 10, "minute": -5, "days": [0]})
        with self.assertRaises(ValueError):
            PowerSchedule.from_json(bad_minute)

        # 3. Ação inválida
        bad_action = json.dumps({"action": "invalid_mode", "hour": 10, "minute": 0, "days": [0]})
        with self.assertRaises(ValueError):
            PowerSchedule.from_json(bad_action)

        # 4. Campo obrigatório faltando
        missing_fields = json.dumps({"action": "lock"})
        with self.assertRaises(KeyError):
            PowerSchedule.from_json(missing_fields)

        # 5. Tipo inválido para flags booleanas
        bad_flag = json.dumps({"action": "lock", "hour": 10, "minute": 0, "days": [0], "enabled": "not_a_bool"})
        with self.assertRaises(TypeError):
            PowerSchedule.from_json(bad_flag)


class TestWakeOnLanMagicPacket(unittest.TestCase):
    """
    Teste 4: Validação dos pacotes Magic Packet de Wake-on-LAN
    (102 bytes: 6x 0xFF + 16x MAC).
    """

    def test_magic_packet_structure_and_length(self):
        """
        Valida que o pacote Magic Packet tem rigorosamente 102 bytes,
        inicia com 6 bytes de 0xFF e segue com 16 repetições do MAC.
        """
        test_macs = [
            "00:11:22:33:44:55",
            "AA:BB:CC:DD:EE:FF",
            "bc-24-11-99-aa-bb",
            "02123456789a",
        ]

        for mac_str in test_macs:
            with self.subTest(mac=mac_str):
                packet = create_magic_packet(mac_str)
                mac_bytes = parse_mac(mac_str)

                # Tamanho exato
                self.assertEqual(len(packet), 102)
                self.assertEqual(len(packet), WOL_MAGIC_PACKET_LENGTH)

                # Cabeçalho: 6 bytes 0xFF
                self.assertEqual(packet[:6], b"\xff\xff\xff\xff\xff\xff")
                self.assertEqual(packet[:6], WOL_HEADER)

                # Corpo: 16 repetições consecutivas do MAC (16 * 6 = 96 bytes)
                body = packet[6:]
                self.assertEqual(len(body), 96)
                self.assertEqual(body, mac_bytes * 16)

                # Validação completa do método de validação
                self.assertTrue(validate_magic_packet(packet))
                self.assertTrue(validate_magic_packet(packet, expected_mac=mac_str))
                self.assertTrue(validate_magic_packet(packet, expected_mac=mac_bytes))

    def test_magic_packet_rejects_corrupted_payloads(self):
        """Testa rejeição de pacotes com payload alterado, tamanho errado ou cabeçalho incorreto."""
        valid_packet = bytearray(create_magic_packet("00:11:22:33:44:55"))

        # 1. Tamanho menor (101 bytes)
        truncated = bytes(valid_packet[:-1])
        self.assertFalse(validate_magic_packet(truncated))

        # 2. Tamanho maior (103 bytes)
        enlarged = bytes(valid_packet + b"\x00")
        self.assertFalse(validate_magic_packet(enlarged))

        # 3. Cabeçalho alterado (primeiro byte não é 0xFF)
        bad_header = bytearray(valid_packet)
        bad_header[0] = 0xFE
        self.assertFalse(validate_magic_packet(bytes(bad_header)))

        # 4. Byte interno corrompido em uma das 16 repetições (ex.: byte no índice 45)
        corrupted_body = bytearray(valid_packet)
        corrupted_body[45] ^= 0x01
        self.assertFalse(validate_magic_packet(bytes(corrupted_body)))

        # 5. MAC diferente do esperado
        self.assertFalse(validate_magic_packet(bytes(valid_packet), expected_mac="AA:BB:CC:DD:EE:FF"))

    def test_mac_parser_and_filter_rules(self):
        """
        Valida que endereços especiais proibidos pelo protocolo sejam rejeitados:
        - Broadcast: FF:FF:FF:FF:FF:FF
        - Nulo: 00:00:00:00:00:00
        - Multicast: primeiro byte ímpar (ex.: 01:00:5E:00:00:01)
        """
        forbidden_macs = [
            "FF:FF:FF:FF:FF:FF",
            "00:00:00:00:00:00",
            "01:00:5E:00:00:01",  # IPv4 Multicast
            "33:33:00:00:00:01",  # IPv6 Multicast
            "01:80:C2:00:00:00",  # Spanning tree multicast
            "invalid-mac-address",
            "12:34:56:78",        # Curto
            "12:34:56:78:90:AB:CD", # Longo
        ]
        for bad_mac in forbidden_macs:
            with self.subTest(bad_mac=bad_mac):
                with self.assertRaises(ValueError):
                    parse_mac(bad_mac)
                with self.assertRaises(ValueError):
                    create_magic_packet(bad_mac)

    def test_format_mac_consistency(self):
        """Garante formatação consistente e idempotência de formatação."""
        raw_mac = bytes([0x00, 0x1A, 0x2B, 0x3C, 0x4D, 0x5E])
        formatted = format_mac(raw_mac)
        self.assertEqual(formatted, "00:1a:2b:3c:4d:5e")
        self.assertEqual(parse_mac(formatted), raw_mac)


def print_suite_banner():
    print("=" * 78)
    print("  NECTARLINK / CONEXÃO MÓVEL - BATERIA DE TESTES DE ENERGIA E AGENDADOR")
    print("=" * 78)


if __name__ == "__main__":
    print_suite_banner()
    unittest.main(verbosity=2)
