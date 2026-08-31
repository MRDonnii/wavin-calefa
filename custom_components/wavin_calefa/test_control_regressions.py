"""Standalone control regression tests: python3 <this file>. No live writes."""
import ast
import asyncio
import logging
from pathlib import Path
import runpy
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

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
    env.update(asyncio=asyncio, time=time, Store=MemoryStore, callback=lambda f: f,
               LOGGER=logging.getLogger('regression'),
               async_track_state_change_event=lambda *args: lambda: None)
    import math
    env['math'] = math
    exec(compile(ast.fix_missing_locations(tree), filename, 'exec'), env)
    return env[classname]


Heat = load_class('heat_call.py', 'WavinCalefaHeatCallManager')
Standby = load_class('auto_standby.py', 'WavinCalefaAutoStandbyManager')


class Controls(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        MemoryStore.values.clear()
        self.entry = SimpleNamespace(entry_id='test', options={
            'heat_call_enabled': True, 'auto_standby_enabled': True,
            'heat_call_climate_entities': ['climate.test'],
            'heat_call_restart_delay_minutes': 0,
        })
        self.coordinator = SimpleNamespace(
            data={'standby': 0, 'outdoor_temperature': 12., 'itc_max_outdoor_temp': 18.},
            last_update_success=True, async_add_listener=lambda *args: lambda: None,
            async_write_holding_registers=AsyncMock(),
            async_write_holding_register=AsyncMock())
        self.heat = Heat(SimpleNamespace(), self.entry, self.coordinator)
        self.heat.evaluate_demand = lambda: (True, True)
        self.heat.evaluate_all_warm = lambda: (True, False)

    async def test_poll_feedback_does_not_write_again(self):
        await self.heat._async_evaluate()
        for _ in range(100):
            await self.heat._async_evaluate()
        self.assertEqual(self.coordinator.async_write_holding_registers.await_count, 1)
        self.heat._last_refresh -= 1801
        self.heat._last_write_attempt -= 1801
        await self.heat._async_evaluate()
        self.assertEqual(self.coordinator.async_write_holding_registers.await_count, 2)

    async def test_summerstop_stops_immediately_and_never_writes_threshold(self):
        await self.heat._async_evaluate()
        self.coordinator.data['outdoor_temperature'] = 18.
        await self.heat._async_evaluate()
        self.assertFalse(self.heat.call_active)
        for call in self.coordinator.async_write_holding_registers.await_args_list:
            self.assertNotIn(38, call.args[0])

    async def test_waiting_standby_keeps_demand_visible(self):
        self.coordinator.data['standby'] = 1
        await self.heat._async_evaluate()
        self.assertTrue(self.heat.demand)
        self.assertEqual(self.heat.status_text(False), 'Blocked by standby')
        self.coordinator.async_write_holding_registers.assert_not_awaited()

    async def test_owned_standby_survives_new_manager(self):
        first = Standby(SimpleNamespace(), self.entry, self.coordinator, self.heat)
        await first._async_engage()
        self.coordinator.data['standby'] = 1
        second = Standby(SimpleNamespace(), self.entry, self.coordinator, self.heat)
        await second.async_setup()
        self.coordinator.async_write_holding_register.assert_awaited_with(26, 0)
        self.assertFalse(second._engaged)
        self.assertFalse((await second._store.async_load())['engaged'])

    async def test_unowned_standby_is_not_released(self):
        self.coordinator.data['standby'] = 1
        manager = Standby(SimpleNamespace(), self.entry, self.coordinator, self.heat)
        await manager.async_setup()
        self.coordinator.async_write_holding_register.assert_not_awaited()

    async def test_manual_choice_clears_saved_ownership(self):
        manager = Standby(SimpleNamespace(), self.entry, self.coordinator, self.heat)
        await manager._async_engage()
        await manager.async_manual_standby(True)
        self.assertFalse(manager._engaged)
        self.assertFalse((await manager._store.async_load())['engaged'])

    async def test_unloaded_manager_does_not_write(self):
        self.heat.async_unload()
        await self.heat._async_evaluate()
        self.coordinator.async_write_holding_registers.assert_not_awaited()

    async def test_failed_writes_are_rate_limited(self):
        self.coordinator.async_write_holding_registers.side_effect = OSError('test offline')
        with self.assertLogs('regression', level='ERROR'):
            await self.heat._async_evaluate()
        await self.heat._async_evaluate()
        self.assertEqual(self.coordinator.async_write_holding_registers.await_count, 1)
        self.assertTrue(self.heat.fault)

    async def test_concurrent_standby_evaluations_only_engage_once(self):
        self.heat.evaluate_demand = lambda: (True, False)
        self.heat.evaluate_all_warm = lambda: (True, True)
        self.entry.options['auto_standby_delay_minutes'] = 0
        async def write(address, value):
            await asyncio.sleep(0)
            self.coordinator.data['standby'] = value
        self.coordinator.async_write_holding_register.side_effect = write
        manager = Standby(SimpleNamespace(), self.entry, self.coordinator, self.heat)
        await asyncio.gather(*(manager._async_evaluate() for _ in range(20)))
        self.assertEqual(self.coordinator.async_write_holding_register.await_count, 1)

    async def test_missing_standby_read_does_not_forget_ownership(self):
        manager = Standby(SimpleNamespace(), self.entry, self.coordinator, self.heat)
        await manager._async_engage()
        self.heat.evaluate_demand = lambda: (True, False)
        self.heat.evaluate_all_warm = lambda: (True, True)
        self.coordinator.data.pop('standby')
        await manager._async_evaluate()
        self.assertTrue(manager._engaged)

    async def test_late_safe_stop_clears_latched_fault(self):
        manager = Standby(SimpleNamespace(), self.entry, self.coordinator, self.heat)
        manager._pumpstop_error = True
        manager._engaged = True
        self.coordinator.data.update(
            standby=1, itc_pump_demand=0, itc_pump_status=0,
            cvv_valve_position=0.0)
        await manager._async_check_pumpstop_safe()
        self.assertTrue(manager._pumpstop_confirmed)
        self.assertFalse(manager._pumpstop_error)

    async def test_running_pump_keeps_real_fault_latched(self):
        manager = Standby(SimpleNamespace(), self.entry, self.coordinator, self.heat)
        manager._pumpstop_error = True
        manager._engaged = True
        self.coordinator.data.update(
            standby=1, itc_pump_demand=0, itc_pump_status=1,
            cvv_valve_position=0.0)
        await manager._async_check_pumpstop_safe()
        self.assertFalse(manager._pumpstop_confirmed)
        self.assertTrue(manager._pumpstop_error)

    async def test_binary_afterheat_blocks_standby(self):
        self.entry.options['heat_call_valve_entities'] = ['binary_sensor.afterheat']
        self.heat.hass = SimpleNamespace(states={
            'binary_sensor.afterheat': SimpleNamespace(state='on'),
        })
        self.heat.climate_entities.clear()
        self.entry.options['heat_call_sensor_rooms'] = 'sensor.room:22'
        self.heat.hass.states['sensor.room'] = SimpleNamespace(state='23')
        self.assertEqual(self.heat.evaluate_demand(), (True, True))
        self.assertEqual(self.heat.evaluate_all_warm(), (True, False))


if __name__ == '__main__':
    unittest.main()
