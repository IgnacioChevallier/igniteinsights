import logging
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from .errors import GFSCycleResolutionError, GFSDownloadError
from .schemas import GFSCycleInfo, GFSVariableMetadata

logger = logging.getLogger(__name__)

# GRIB2 search strings and output variable names
# Each entry: (search_string, asset_type, xarray_field_name)
VARIABLES: dict[str, tuple[str, str, str]] = {
    "u10": (":UGRD:10 m above ground:", "gfs_u10", "u10"),
    "v10": (":VGRD:10 m above ground:", "gfs_v10", "v10"),
    "t2m": (":TMP:2 m above ground:", "gfs_t2m", "t2m"),
    "rh":  (":RH:2 m above ground:", "gfs_rh", "r2"),
}

# GFS cycles are published at 00, 06, 12, 18 UTC.
# We try cycles from most-recent backwards (NOMADS keeps ~48 h of availability).
CYCLE_HOURS = [18, 12, 6, 0]
MAX_LOOKBACK_DAYS = 2


class GFSClient:
    def resolve_cycle(self, target_date: date | None = None) -> GFSCycleInfo:
        """
        Resolve the most-recent available GFS cycle on or before `target_date`
        (or on/before "now" if target_date is None — the live/current-weather path).

        AWS (noaa-gfs-bdp-pds) and Google Cloud (global-forecast-system) both mirror
        the full GFS archive back to 2021-01-01 — Herbie's default source priority
        already tries them before nomads/azure, so any date from then onward works
        with no extra configuration.
        """
        try:
            from herbie import Herbie
        except ImportError as exc:
            raise GFSCycleResolutionError("herbie-data is not installed") from exc

        now_utc = datetime.now(UTC)
        base_date = target_date or now_utc.date()

        for days_back in range(MAX_LOOKBACK_DAYS + 1):
            candidate_date = base_date - timedelta(days=days_back)
            for cycle_hour in CYCLE_HOURS:
                candidate = datetime.combine(
                    candidate_date, time(hour=cycle_hour), tzinfo=UTC
                )
                if candidate > now_utc - timedelta(hours=4):
                    # GFS data typically available ~4 h after cycle time. This guard
                    # is always against the *real* now, not target_date — for any
                    # historical target_date it's always False and never skips.
                    continue
                date_str = candidate.strftime("%Y-%m-%d %H:%M")
                try:
                    H = Herbie(date_str, model="gfs", product="pgrb2.0p25", fxx=0, verbose=False)
                    H.grib  # triggers availability check
                    logger.info("Resolved GFS cycle: %s %02dz", candidate.date(), cycle_hour)
                    return GFSCycleInfo(
                        date=candidate.strftime("%Y-%m-%d"),
                        cycle_hour=cycle_hour,
                        fxx=0,
                    )
                except Exception:
                    logger.debug(
                        "GFS cycle %s %02dz not available, trying earlier",
                        candidate.date(),
                        cycle_hour,
                    )
                    continue

        raise GFSCycleResolutionError(
            f"No GFS cycle available within {MAX_LOOKBACK_DAYS} days of {base_date.isoformat()}"
        )

    def resolve_latest_cycle(self) -> GFSCycleInfo:
        """Thin wrapper preserved for call-site clarity / backward compatibility."""
        return self.resolve_cycle(target_date=None)

    def download_variable(
        self,
        cycle: GFSCycleInfo,
        var_key: str,
        bbox_west: float,
        bbox_south: float,
        bbox_east: float,
        bbox_north: float,
        output_path: Path,
    ) -> GFSVariableMetadata:
        try:
            import rioxarray  # noqa: F401 — registers .rio accessor on xarray
            from herbie import Herbie
        except ImportError as exc:
            raise GFSDownloadError(f"Required library not installed: {exc}") from exc

        search_string, asset_type, field_name = VARIABLES[var_key]
        cycle_str = f"{cycle.date.replace('-', '')}{cycle.cycle_hour:02d}"
        date_str = f"{cycle.date} {cycle.cycle_hour:02d}:00"

        logger.info("Downloading GFS variable=%s cycle=%s", var_key, cycle_str)
        try:
            H = Herbie(date_str, model="gfs", product="pgrb2.0p25", fxx=cycle.fxx, verbose=False)
            ds = H.xarray(search_string)
        except Exception as exc:
            raise GFSDownloadError(f"Failed to fetch GFS variable {var_key}: {exc}") from exc

        # Extract the DataArray — field name varies, fall back to first data variable
        if field_name in ds:
            da = ds[field_name]
        else:
            data_vars = [v for v in ds.data_vars]
            if not data_vars:
                raise GFSDownloadError(f"No data variables found in GFS dataset for {var_key}")
            da = ds[data_vars[0]]

        # Identify spatial dimension names (herbie uses 'latitude'/'longitude')
        lat_dim = "latitude" if "latitude" in da.dims else "y"
        lon_dim = "longitude" if "longitude" in da.dims else "x"

        # GFS uses 0–360° longitudes; normalize to -180/180 so bbox clipping works
        if float(da[lon_dim].max()) > 180:
            lon_norm = (da[lon_dim].values + 180) % 360 - 180
            da = da.assign_coords({lon_dim: lon_norm}).sortby(lon_dim)

        da = da.rio.set_spatial_dims(x_dim=lon_dim, y_dim=lat_dim)
        da = da.rio.write_crs("EPSG:4326")

        try:
            clipped = da.rio.clip_box(
                minx=bbox_west, miny=bbox_south, maxx=bbox_east, maxy=bbox_north
            )
        except Exception as exc:
            raise GFSDownloadError(f"Failed to clip GFS variable {var_key} to bbox: {exc}") from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        clipped.rio.to_raster(str(output_path))
        logger.info("Saved GFS %s → %s", var_key, output_path)

        return GFSVariableMetadata(
            variable=var_key,
            asset_type=asset_type,
            file_path=str(output_path),
            crs="EPSG:4326",
            resolution_deg=0.25,
            band_count=1,
            dtype=str(clipped.dtype),
            file_size_bytes=output_path.stat().st_size,
            cycle=cycle_str,
            search_string=search_string,
        )
