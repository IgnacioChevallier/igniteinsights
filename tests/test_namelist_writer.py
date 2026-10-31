import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import rasterio
from rasterio.transform import from_origin

from app.elmfire.builder.namelist_writer import resolve_dtdump_s, validate_namelist, write_namelist


class NamelistWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.inputs_dir = self.root / "inputs"
        self.inputs_dir.mkdir()
        with rasterio.open(
            self.inputs_dir / "dem.tif",
            "w",
            driver="GTiff",
            height=2,
            width=2,
            count=1,
            dtype="float32",
            crs="EPSG:32719",
            transform=from_origin(500000, 6000000, 30, 30),
        ) as dataset:
            dataset.write(np.zeros((1, 2, 2), dtype="float32"))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_write_namelist_contains_required_groups_and_state_parameters(self) -> None:
        output_path, dtdump_s, _ = write_namelist(
            self.inputs_dir,
            self.root / "outputs",
            simulation_hours=2,
            output_path=self.root / "elmfire.data",
            dtdump_s=1800,
            dt_meteorology_s=1800,
            simulation_tstart_s=600,
        )
        content = output_path.read_text(encoding="utf-8")

        for group in ("INPUTS", "COMPUTATIONAL_DOMAIN", "TIME_CONTROL", "SIMULATOR", "OUTPUTS"):
            self.assertIn(f"&{group}", content)
        self.assertIn("A_SRS                           = 'EPSG:32719'", content)
        self.assertIn("COMPUTATIONAL_DOMAIN_XLLCORNER  = 500000.00", content)
        self.assertIn("COMPUTATIONAL_DOMAIN_YLLCORNER  = 5999940.00", content)
        self.assertIn("COMPUTATIONAL_DOMAIN_CELLSIZE   = 30.0", content)
        self.assertIn("DT_METEOROLOGY                  = 1800.0", content)
        self.assertIn("SIMULATION_TSTART               = 600.0", content)
        self.assertIn("SIMULATION_TSTOP                = 7800.0", content)
        self.assertIn("MODE                            = 1", content)
        self.assertEqual(dtdump_s, 1800.0)
        validate_namelist(content)

    def test_elmfire_skill_lists_exactly_the_keywords_written(self) -> None:
        # The elmfire skill's "What this repo emits today" table is what agents read
        # before touching this file; it silently drifted once (MODE, CROWN_FIRE_MODEL).
        output_path, _, _ = write_namelist(
            self.inputs_dir,
            self.root / "outputs",
            simulation_hours=2,
            output_path=self.root / "elmfire.data",
            phis_adj=0.5,
        )
        namelist = output_path.read_text(encoding="utf-8")
        written = set(re.findall(r"^\s+([A-Z][A-Z0-9_]*)\s*=", namelist, re.M))

        skill = Path(__file__).parents[1] / ".claude/skills/elmfire"
        reference = (skill / "references/namelist-reference.md").read_text(encoding="utf-8")
        emits_section = reference.split("## What this repo emits today")[1].split("\n## ")[0]
        rows = [row for row in emits_section.splitlines() if row.startswith("| `&")]
        keyword_cells = "".join(row.split("|")[2] for row in rows)
        documented = set(re.findall(r"`([A-Z][A-Z0-9_]*)`", keyword_cells))

        self.assertEqual(written, documented)

    def test_write_namelist_uses_raster_basenames_and_normalized_paths(self) -> None:
        output_path, _, _ = write_namelist(
            self.inputs_dir, self.root / "output's", 2, self.root / "elmfire.data"
        )
        content = output_path.read_text(encoding="utf-8")

        self.assertIn("DEM_FILENAME                    = 'dem'", content)
        self.assertIn("PHI_FILENAME                    = 'phi'", content)
        self.assertIn("OUTPUTS_DIRECTORY               = '", content)
        self.assertIn("output''s/", content)

    def test_resolve_dtdump_s_keeps_a_pre_final_checkpoint(self) -> None:
        cases = ((7200, 3600, 3600), (7200, 7200, 3600), (7200, 9000, 3600))
        for duration_s, dtdump_s, expected in cases:
            with self.subTest(duration_s=duration_s, dtdump_s=dtdump_s):
                self.assertEqual(resolve_dtdump_s(duration_s, dtdump_s), expected)

    def test_write_namelist_rejects_invalid_timesteps(self) -> None:
        with self.assertRaisesRegex(ValueError, "dt_s must not exceed dtmax_s"):
            write_namelist(
                self.inputs_dir, self.root / "outputs", 2, self.root / "elmfire.data", 60, 30
            )

    def test_phis_adj_only_written_when_recipe_changes_default(self) -> None:
        default_path, _, _ = write_namelist(
            self.inputs_dir, self.root / "outputs", 2, self.root / "default.data"
        )
        adjusted_path, _, _ = write_namelist(
            self.inputs_dir, self.root / "outputs", 2, self.root / "adjusted.data", phis_adj=0.5
        )

        self.assertNotIn("PHIS_ADJ", default_path.read_text())
        simulator = adjusted_path.read_text().split("&SIMULATOR")[1].split("/")[0]
        self.assertIn("PHIS_ADJ                        = 0.5", simulator)


def test_spotting_ausente_por_defecto_y_con_min_igual_max_si_se_pide():
    from app.elmfire.builder.namelist_writer import spotting_group
    assert spotting_group(None) == ""
    g = spotting_group({"CROWN_FIRE_SPOTTING_PERCENT": 1.2})
    linea = {ln.split("=")[0].strip(): ln.split("=")[1].strip()
             for ln in g.splitlines() if "=" in ln}
    assert linea["ENABLE_SPOTTING"] == ".TRUE."
    assert linea["CROWN_FIRE_SPOTTING_PERCENT_MIN"] == "1.2"
    assert linea["CROWN_FIRE_SPOTTING_PERCENT_MAX"] == "1.2"
    assert linea["NEMBERS_MAX_LO"] == linea["NEMBERS_MIN"] == "1"
    assert linea["MEAN_SPOTTING_DIST_MIN"] == "10.0"


def test_spotting_rechaza_keywords_inventados():
    import pytest

    from app.elmfire.builder.namelist_writer import spotting_group
    with pytest.raises(ValueError):
        spotting_group({"EMBER_MAGIC": 1.0})


def test_supresion_ausente_por_defecto_y_plantilla_del_proveedor_si_se_pide():
    import pytest

    from app.elmfire.builder.namelist_writer import suppression_group
    assert suppression_group(None) == ""
    g = suppression_group({"MAX_CONTAINMENT_PER_DAY": 60.0})
    linea = {ln.split("=")[0].strip(): ln.split("=")[1].strip()
             for ln in g.splitlines() if "=" in ln}
    assert linea["ENABLE_EXTENDED_ATTACK"] == ".TRUE."
    assert linea["ENABLE_INITIAL_ATTACK"] == ".FALSE."
    assert linea["MAX_CONTAINMENT_PER_DAY"] == "60.0"
    assert linea["AREA_NO_CONTAINMENT_CHANGE"] == "15000.0"
    with pytest.raises(ValueError):
        suppression_group({"CREWS": 3})
