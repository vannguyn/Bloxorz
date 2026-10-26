"""Tests for JSON level loader (levels/level_loader.py)."""
from pathlib import Path
import pytest

from core.interfaces import BlockState, Level, Orientation, Switch, TileType
from levels.level_loader import (
    compute_initial_bridge_mask,
    load_all_levels,
    load_level,
)


class TestLoadLevel01:
    def test_load_level_01_metadata_and_structure(self):
        level = load_level("levels/level_01.json")
        assert isinstance(level, Level)
        assert level.id == "level_01"
        assert level.name == "First Steps"
        assert level.width == 8
        assert level.height == 7

    def test_load_level_01_start_and_goal(self):
        level = load_level("levels/level_01.json")
        assert level.start == BlockState(r=1, c=3, orientation=Orientation.STANDING)
        assert level.goal == (6, 3)
        assert level.tiles[(6, 3)] == TileType.GOAL
        assert level.tiles[(1, 3)] == TileType.FLOOR

    def test_load_level_01_tiles_fragile_and_bridges(self):
        level = load_level("levels/level_01.json")
        # Fragile tile at (3, 2)
        assert level.tiles[(3, 2)] == TileType.FRAGILE

        # Bridge tiles
        assert "north_bridge" in level.bridges
        assert level.bridges["north_bridge"] == [(4, 1), (5, 1)]
        assert level.tiles[(4, 1)] == TileType.BRIDGE
        assert level.tiles[(5, 1)] == TileType.BRIDGE

        # Void cell check
        assert (0, 0) not in level.tiles

    def test_load_level_01_switches(self):
        level = load_level("levels/level_01.json")
        assert len(level.switches) == 3

        # Soft switch
        soft_sw = next(s for s in level.switches if s.id == "soft_toggle")
        assert soft_sw.type == "soft"
        assert soft_sw.position == (2, 2)
        assert soft_sw.bridge_ids == ["north_bridge"]
        assert soft_sw.mode == "toggle"
        assert soft_sw.destinations is None

        # Heavy switch
        heavy_sw = next(s for s in level.switches if s.id == "heavy_permanent")
        assert heavy_sw.type == "heavy"
        assert heavy_sw.position == (4, 4)
        assert heavy_sw.bridge_ids == ["north_bridge"]
        assert heavy_sw.mode == "permanent"
        assert heavy_sw.destinations is None

        # Split switch
        split_sw = next(s for s in level.switches if s.id == "split_switch")
        assert split_sw.type == "split"
        assert split_sw.position == (5, 4)
        assert split_sw.bridge_ids == []
        assert split_sw.destinations == ((1, 5), (3, 5))

    def test_load_level_01_split_rules(self):
        level = load_level("levels/level_01.json")
        assert level.split_rules.get("control_switch_key") == "SPACE"
        assert level.split_rules.get("merge_when_adjacent") is True


class TestLoadLevelFlexibility:
    def test_load_by_id_string(self):
        level = load_level("level_01")
        assert level.id == "level_01"
        assert level.name == "First Steps"

    def test_load_by_path_object(self):
        level = load_level(Path("levels/level_01.json"))
        assert level.id == "level_01"

    def test_nonexistent_level_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_level("nonexistent_level_file_xyz")


class TestLoadAllLevels:
    def test_load_all_levels_count_and_order(self):
        levels = load_all_levels()
        assert len(levels) == 10
        expected_ids = [f"level_{i:02d}" for i in range(1, 11)]
        assert [lvl.id for lvl in levels] == expected_ids

    def test_all_10_levels_satisfy_invariants(self):
        levels = load_all_levels()
        for lvl in levels:
            # 1. Bounds
            assert lvl.width > 0
            assert lvl.height > 0

            # 2. Start position within bounds and on FLOOR
            assert 0 <= lvl.start.r < lvl.height
            assert 0 <= lvl.start.c < lvl.width
            assert lvl.tiles.get((lvl.start.r, lvl.start.c)) == TileType.FLOOR

            # 3. Goal within bounds and is GOAL tile
            assert 0 <= lvl.goal[0] < lvl.height
            assert 0 <= lvl.goal[1] < lvl.width
            assert lvl.tiles.get(lvl.goal) == TileType.GOAL

            # 4. Switches within bounds and on supported floor/fragile
            for sw in lvl.switches:
                assert 0 <= sw.position[0] < lvl.height
                assert 0 <= sw.position[1] < lvl.width
                assert lvl.tiles.get(sw.position) in (TileType.FLOOR, TileType.FRAGILE)
                if sw.type == "split" and sw.destinations:
                    for dest in sw.destinations:
                        assert 0 <= dest[0] < lvl.height
                        assert 0 <= dest[1] < lvl.width
                        assert lvl.tiles.get(dest) == TileType.FLOOR

            # 5. Bridges within bounds and registered as TileType.BRIDGE
            for b_id, b_tiles in lvl.bridges.items():
                for cell in b_tiles:
                    assert 0 <= cell[0] < lvl.height
                    assert 0 <= cell[1] < lvl.width
                    assert lvl.tiles.get(cell) == TileType.BRIDGE


class TestComputeInitialBridgeMask:
    def test_compute_initial_bridge_mask_closed(self):
        data = {
            "bridges": [
                {"id": "b1", "tiles": [[1, 1]], "initial_state": "closed"},
                {"id": "b2", "tiles": [[1, 2]], "initial_state": "closed"},
            ]
        }
        bridges = {"b1": [(1, 1)], "b2": [(1, 2)]}
        mask = compute_initial_bridge_mask(data, bridges)
        assert mask == 0

    def test_compute_initial_bridge_mask_mixed(self):
        data = {
            "bridges": [
                {"id": "b1", "tiles": [[1, 1]], "initial_state": "closed"},
                {"id": "b2", "tiles": [[1, 2]], "initial_state": "open"},
                {"id": "b3", "tiles": [[1, 3]], "initial_state": "open"},
            ]
        }
        bridges = {"b1": [(1, 1)], "b2": [(1, 2)], "b3": [(1, 3)]}
        mask = compute_initial_bridge_mask(data, bridges)
        # bit 0 = 0, bit 1 = 1, bit 2 = 1 -> 0b110 = 6
        assert mask == 6
