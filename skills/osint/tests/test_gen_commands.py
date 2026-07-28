"""Tests for osint gen_commands module."""

from __future__ import annotations

import pytest


class TestGenerateCommands:
    def test_basic_plan(self, gen_commands_module):
        plan = {
            "target_value": "example.com",
            "target_type": "domain",
            "depth": "standard",
            "phases": [
                {
                    "name": "Recon",
                    "estimated_time": "10 min",
                    "steps": [
                        {
                            "tool": "whois",
                            "command": "whois example.com",
                            "purpose": "Domain registration info",
                        }
                    ],
                }
            ],
            "total_phases": 1,
        }
        result = gen_commands_module.generate_commands(plan)
        assert "#!/bin/bash" in result
        assert "example.com" in result
        assert "whois example.com" in result
        assert "PHASE 1: Recon" in result

    def test_multiple_phases(self, gen_commands_module):
        plan = {
            "target_value": "test",
            "target_type": "person",
            "depth": "deep",
            "phases": [
                {"name": "Phase A", "estimated_time": "5m", "steps": [{"tool": "t1", "command": "cmd1", "purpose": "p1"}]},
                {"name": "Phase B", "estimated_time": "10m", "steps": [{"tool": "t2", "command": "cmd2", "purpose": "p2"}]},
            ],
            "total_phases": 2,
        }
        result = gen_commands_module.generate_commands(plan)
        assert "PHASE 1: Phase A" in result
        assert "PHASE 2: Phase B" in result
        assert "cmd1" in result
        assert "cmd2" in result

    def test_empty_phases(self, gen_commands_module):
        plan = {"target_value": "x", "target_type": "email", "phases": [], "total_phases": 0}
        result = gen_commands_module.generate_commands(plan)
        assert "#!/bin/bash" in result
        assert "Investigation complete." in result

    def test_condition_in_step(self, gen_commands_module):
        plan = {
            "target_value": "test",
            "target_type": "domain",
            "phases": [
                {
                    "name": "Test",
                    "estimated_time": "5m",
                    "steps": [
                        {
                            "tool": "nmap",
                            "command": "nmap -sV test.com",
                            "purpose": "Port scan",
                            "condition": "if domain resolves",
                        }
                    ],
                }
            ],
            "total_phases": 1,
        }
        result = gen_commands_module.generate_commands(plan)
        assert "Condition: if domain resolves" in result
        assert "nmap -sV test.com" in result

    def test_step_without_condition(self, gen_commands_module):
        plan = {
            "target_value": "test",
            "target_type": "phone",
            "phases": [
                {
                    "name": "Lookup",
                    "estimated_time": "2m",
                    "steps": [
                        {
                            "tool": "lookup",
                            "command": "echo test",
                            "purpose": "Basic lookup",
                        }
                    ],
                }
            ],
            "total_phases": 1,
        }
        result = gen_commands_module.generate_commands(plan)
        assert "Condition:" not in result

    def test_missing_fields_defaults(self, gen_commands_module):
        plan = {"phases": [{"steps": [{"command": "echo ok"}]}]}
        result = gen_commands_module.generate_commands(plan)
        assert "unknown" in result.lower() or "echo ok" in result

    def test_set_e_present(self, gen_commands_module):
        plan = {"phases": []}
        result = gen_commands_module.generate_commands(plan)
        assert "set -e" in result
