"""Standalone control regression tests: python3 <this file>. No live writes."""
import ast
import asyncio
import logging
from pathlib import Path
import runpy
import unittest
from unittest.mock import AsyncMock
from types import SimpleNamespace

ROOT = Path(__file__).parent


class MemoryStore:
    values = {}

    def __init__(self, hass, version, key, **kwargs):
        self.key = key

    async def async_load(self):
        return self.values.get(self.key)

    async def async_save(self, value):
        self.values[self.key] = value.copy()


def load_class(filename, classname):
    tree = ast.parse((ROOT / filename).read_text())
    tree.body = [ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)] + [
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == classname
    ]
    env = runpy.run_path(str(ROOT / 'const.py'))
    env.update(asyncio=asyncio, Store=MemoryStore, callback=lambda f: f,
               LOGGER=logging.getLogger('regression'),
               async_track_state_change_event=lambda *args: lambda: None)
    import time
    import math
    env['time'] = time
    env['math'] = math
    exec(compile(ast.fix_missing_locations(tree), filename, 'exec'), env)
    return env[classname]


Demand = load_class('demand.py', 'WavinCalefaDemandTracker')
Standby = load_class('auto_standby.py', 'WavinCalefaAutoStandbyManager')


class Controls(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        MemoryStore.values.clear()
        self.entry = SimpleNamespace(entry_id='test', options={
            'auto_standby_enabled': True,
            'heat_call_climate_entities': ['climate.test'],
            'heat_call_restart_delay_minutes': 0,
        })
        self.coordinator = SimpleNamespace(
            data={'standby': 0},
            last_update_success=True, async_add_listener=lambda *args: lambda: None,
            async_write_holding_registers=AsyncMock(),
            async_write_holding_register=AsyncMock())
        self.demand = Demand(SimpleNamespace(), self.entry)
        self.demand.evaluate_demand = lambda: (True, True)
        self.demand.evaluate_all_warm = lambda: (True, False)

    async def test_owned_standby_survives_new_manager(self):
        first = Standby(SimpleNamespace(), self.entry, self.coordinator, self.demand)
        await first._async_engage()
        self.coordinator.data['standby'] = 1
        second = Standby(SimpleNamespace(), self.entry, self.coordinator, self.demand)
        await second.async_setup()
        self.coordinator.async_write_holding_register.assert_awaited_with(26, 0)
        self.assertFalse(second._engaged)
        self.assertFalse((await second._store.async_load())['engaged'])

    async def test_unowned_standby_is_not_released(self):
        self.coordinator.data['standby'] = 1
        manager = Standby(SimpleNamespace(), self.entry, self.coordinator, self.demand)
        await manager.async_setup()
        self.coordinator.async_write_holding_register.assert_not_awaited()

    async def test_manual_choice_clears_saved_ownership(self):
        manager = Standby(SimpleNamespace(), self.entry, self.coordinator, self.demand)
        await manager._async_engage()
        await manager.async_manual_standby(True)
        self.assertFalse(manager._engaged)
        self.assertFalse((await manager._store.async_load())['engaged'])

    async def test_concurrent_standby_evaluations_only_engage_once(self):
        self.demand.evaluate_demand = lambda: (True, False)
        self.demand.evaluate_all_warm = lambda: (True, True)
        self.entry.options['auto_standby_delay_minutes'] = 0
        async def write(address, value):
            await asyncio.sleep(0)
            self.coordinator.data['standby'] = value
        self.coordinator.async_write_holding_register.side_effect = write
        manager = Standby(SimpleNamespace(), self.entry, self.coordinator, self.demand)
        await asyncio.gather(*(manager._async_evaluate() for _ in range(20)))
        self.assertEqual(self.coordinator.async_write_holding_register.await_count, 1)

    async def test_missing_standby_read_does_not_forget_ownership(self):
        manager = Standby(SimpleNamespace(), self.entry, self.coordinator, self.demand)
        await manager._async_engage()
        self.demand.evaluate_demand = lambda: (True, False)
        self.demand.evaluate_all_warm = lambda: (True, True)
        self.coordinator.data.pop('standby')
        await manager._async_evaluate()
        self.assertTrue(manager._engaged)

    async def test_late_safe_stop_clears_latched_fault(self):
        manager = Standby(SimpleNamespace(), self.entry, self.coordinator, self.demand)
        manager._pumpstop_error = True
        manager._engaged = True
        self.coordinator.data.update(
            standby=1, itc_pump_demand=0, itc_pump_status=0,
            cvv_valve_position=0.0)
        await manager._async_check_pumpstop_safe()
        self.assertTrue(manager._pumpstop_confirmed)
        self.assertFalse(manager._pumpstop_error)

    async def test_running_pump_keeps_real_fault_latched(self):
        manager = Standby(SimpleNamespace(), self.entry, self.coordinator, self.demand)
        manager._pumpstop_error = True
        manager._engaged = True
        self.coordinator.data.update(
            standby=1, itc_pump_demand=0, itc_pump_status=1,
            cvv_valve_position=0.0)
        await manager._async_check_pumpstop_safe()
        self.assertFalse(manager._pumpstop_confirmed)
        self.assertTrue(manager._pumpstop_error)

    async def test_binary_afterheat_blocks_standby(self):
        self.entry.options['heat_call_climate_entities'] = []
        self.entry.options['heat_call_valve_entities'] = ['binary_sensor.afterheat']
        self.entry.options['heat_call_sensor_rooms'] = 'sensor.room:22'
        self.demand.hass = SimpleNamespace(states={
            'binary_sensor.afterheat': SimpleNamespace(state='on'),
            'sensor.room': SimpleNamespace(state='23'),
        })
        self.assertEqual(self.demand.evaluate_demand(), (True, True))
        self.assertEqual(self.demand.evaluate_all_warm(), (True, False))


if __name__ == '__main__':
    unittest.main()
