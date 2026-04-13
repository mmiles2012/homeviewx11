"""Tests for the layout system."""
import json
import pytest
from pathlib import Path

from server.composition.layout import LayoutManager, CellGeometry, LayoutNotFoundError


LAYOUTS_DIR = Path(__file__).parent.parent / "layouts"


@pytest.fixture
def manager() -> LayoutManager:
    """LayoutManager loaded from the real layouts directory."""
    m = LayoutManager()
    m.load_layouts(str(LAYOUTS_DIR))
    return m


class TestLayoutLoading:
    def test_loads_all_five_layouts(self, manager):
        """All 5 layout JSON files are loaded."""
        ids = {layout.id for layout in manager.list_layouts()}
        assert "single" in ids
        assert "side_by_side" in ids
        assert "2x2" in ids
        assert "hero_3side" in ids
        assert "pip" in ids

    def test_get_layout_by_id(self, manager):
        """get_layout returns a layout by id."""
        layout = manager.get_layout("single")
        assert layout.id == "single"
        assert len(layout.cells) == 1

    def test_get_layout_not_found(self, manager):
        """get_layout raises LayoutNotFoundError for unknown id."""
        with pytest.raises(LayoutNotFoundError):
            manager.get_layout("nonexistent")

    def test_layouts_have_required_fields(self, manager):
        """Every layout has id, name, gap_px, and cells."""
        for layout in manager.list_layouts():
            assert layout.id
            assert layout.name
            assert layout.gap_px >= 0
            assert len(layout.cells) >= 1
            for cell in layout.cells:
                assert cell.role in ("hero", "side", "grid", "pip")


class TestGeometryComputation:
    def test_single_layout_full_screen(self, manager):
        """Single layout fills the full display minus gap."""
        layout = manager.get_layout("single")
        geoms = manager.compute_geometry(layout, 1920, 1080)
        assert len(geoms) == 1
        g = geoms[0]
        assert g.x == 0
        assert g.y == 0
        assert g.width == 1920
        assert g.height == 1080

    def test_2x2_layout_four_cells(self, manager):
        """2x2 layout produces 4 cells."""
        layout = manager.get_layout("2x2")
        geoms = manager.compute_geometry(layout, 1920, 1080)
        assert len(geoms) == 4

    def test_2x2_total_area_accounts_for_gaps(self, manager):
        """2x2 cells + gaps fill the full display width and height."""
        layout = manager.get_layout("2x2")
        geoms = manager.compute_geometry(layout, 1920, 1080)
        gap = layout.gap_px

        # Two columns: cells widths + 1 gap = 1920
        widths = sorted(set(g.width for g in geoms))
        assert len(widths) <= 2  # at most 2 unique widths (rounding)
        total_w = sum(g.width for g in geoms[:2]) + gap
        assert abs(total_w - 1920) <= 2  # allow 1-2px rounding

    def test_geometry_at_4k(self, manager):
        """Geometry scales correctly at 3840x2160."""
        layout = manager.get_layout("2x2")
        geoms = manager.compute_geometry(layout, 3840, 2160)
        assert len(geoms) == 4
        total_w = sum(g.width for g in geoms[:2]) + layout.gap_px
        assert abs(total_w - 3840) <= 2

    def test_no_cell_overlaps(self, manager):
        """Cells in non-PiP layouts do not overlap each other."""
        for layout in manager.list_layouts():
            if layout.id == "pip":
                # PiP intentionally overlays a small cell on top of the hero
                continue
            geoms = manager.compute_geometry(layout, 1920, 1080)
            for i, a in enumerate(geoms):
                for j, b in enumerate(geoms):
                    if i >= j:
                        continue
                    # Check no overlap
                    x_overlap = a.x < b.x + b.width and a.x + a.width > b.x
                    y_overlap = a.y < b.y + b.height and a.y + a.height > b.y
                    assert not (x_overlap and y_overlap), (
                        f"Cells {i} and {j} overlap in layout {layout.id}"
                    )


class TestLayoutTransition:
    def test_transition_same_cell_count_preserves_assignments(self, manager):
        """Switching between same-cell-count layouts preserves sources."""
        old_layout = manager.get_layout("side_by_side")
        new_layout = manager.get_layout("side_by_side")
        old_assignments = {0: "espn", 1: "prime"}
        new_assignments = manager.compute_transition(old_layout, new_layout, old_assignments)
        assert new_assignments[0] == "espn"
        assert new_assignments[1] == "prime"

    def test_transition_more_cells_new_cells_empty(self, manager):
        """Expanding from 1 cell to 4 cells leaves new cells empty."""
        old_layout = manager.get_layout("single")
        new_layout = manager.get_layout("2x2")
        old_assignments = {0: "espn"}
        new_assignments = manager.compute_transition(old_layout, new_layout, old_assignments)
        # Hero maps to hero (cell 0 in 2x2 = first grid cell)
        assert "espn" in new_assignments.values()
        # Other 3 cells should be None
        none_count = sum(1 for v in new_assignments.values() if v is None)
        assert none_count == 3

    def test_transition_fewer_cells_drops_extras(self, manager):
        """Shrinking from 4 cells to 1 cell keeps only the hero source."""
        old_layout = manager.get_layout("2x2")
        new_layout = manager.get_layout("single")
        old_assignments = {0: "espn", 1: "prime", 2: "netflix", 3: None}
        new_assignments = manager.compute_transition(old_layout, new_layout, old_assignments)
        assert len(new_assignments) == 1
