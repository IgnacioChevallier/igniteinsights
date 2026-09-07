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
