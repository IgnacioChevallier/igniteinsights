import logging
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from time import sleep

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
    # Model terrain height: t2m/rh are valid at this elevation, not at the DEM's.
    "orog": (":HGT:surface:", "gfs_orog", "orog"),
}

# GFS cycles are published at 00, 06, 12, 18 UTC.
# We try cycles from most-recent backwards (NOMADS keeps ~48 h of availability).
CYCLE_HOURS = [18, 12, 6, 0]
FETCH_ATTEMPTS = 5
FETCH_BACKOFF_S = 10.0
MAX_LOOKBACK_DAYS = 2

# Forecast hours fetched per cycle. Each becomes one band of the output GeoTIFF, and
# ELMFIRE reads band n as the weather at TSTART + n × DT_METEOROLOGY (3600 s). Fetching
# only fxx=0 produces a single-band raster that silently freezes weather for the whole
# simulation — no diurnal wind peak, no afternoon RH minimum. 24 h of hourly bands
# covers the default 12 h horizon with headroom; GFS publishes hourly out to f120.
DEFAULT_FORECAST_HOURS = list(range(25))


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
        forecast_hours: list[int] | None = None,
    ) -> GFSVariableMetadata:
        """Download one GFS variable as a multiband GeoTIFF — one band per forecast hour.

        Band order follows `forecast_hours` ascending, which is what ELMFIRE's
        DT_METEOROLOGY band indexing expects.
        """
        try:
            import numpy as np
            import rasterio
            import rioxarray  # noqa: F401 — registers .rio accessor on xarray
        except ImportError as exc:
            raise GFSDownloadError(f"Required library not installed: {exc}") from exc

        requested = forecast_hours if forecast_hours is not None else DEFAULT_FORECAST_HOURS
        hours = sorted(set(requested))
        if not hours:
            raise GFSDownloadError("forecast_hours must contain at least one hour")

        search_string, asset_type, field_name = VARIABLES[var_key]
        cycle_str = f"{cycle.date.replace('-', '')}{cycle.cycle_hour:02d}"

        logger.info(
            "Downloading GFS variable=%s cycle=%s fxx=%d..%d (%d bands)",
            var_key, cycle_str, hours[0], hours[-1], len(hours),
        )

        # ponytail: serial per-hour fetch. herbie's FastHerbie parallelises this if
        # ingestion wall-clock ever matters; plain Herbie is the API already proven here.
        bands, transform = [], None
        for fxx in hours:
            clipped = self._fetch_clipped(
                cycle, fxx, var_key, search_string, field_name,
                bbox_west, bbox_south, bbox_east, bbox_north,
            )
            if transform is None:
                transform = clipped.rio.transform()
            elif clipped.shape != bands[0].shape:
                raise GFSDownloadError(
                    f"GFS {var_key} fxx={fxx} clipped to {clipped.shape}, expected "
                    f"{bands[0].shape} — forecast hours must share a grid"
                )
            bands.append(clipped.values.astype("float32"))

        stack = np.stack(bands)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(
            output_path, "w", driver="GTiff",
            height=stack.shape[1], width=stack.shape[2], count=stack.shape[0],
            dtype="float32", crs="EPSG:4326", transform=transform,
        ) as dst:
            dst.write(stack)
        logger.info("Saved GFS %s → %s (%d bands)", var_key, output_path, stack.shape[0])

        return GFSVariableMetadata(
            variable=var_key,
            asset_type=asset_type,
            file_path=str(output_path),
            crs="EPSG:4326",
            resolution_deg=0.25,
            band_count=stack.shape[0],
            dtype="float32",
            file_size_bytes=output_path.stat().st_size,
            cycle=cycle_str,
            search_string=search_string,
        )

    def download_analysis_series(
        self,
        var_key: str,
        start: datetime,
        hours: int,
        bbox_west: float,
        bbox_south: float,
        bbox_east: float,
        bbox_north: float,
        output_path: Path,
    ) -> Path:
        """Hourly bands for [start, start + hours], each from the latest cycle at or before
        it (f000–f005 of successive 6-hourly cycles).

        For hindcasts: the closest thing to observed weather GFS offers, so a validation run
        measures fire-spread skill rather than forecast error. `start` must be on the hour.
        """
        import numpy as np
        import rasterio

        if start.minute or start.second:
            raise GFSDownloadError(f"start {start} is not on the hour")
        search_string, _, field_name = VARIABLES[var_key]
        bands, transform = [], None
        for h in range(hours + 1):
            valid = start + timedelta(hours=h)
            cycle_hour = valid.hour - valid.hour % 6
            cycle = GFSCycleInfo(date=valid.date().isoformat(), cycle_hour=cycle_hour)
            clipped = self._fetch_clipped(
                cycle, valid.hour - cycle_hour, var_key, search_string, field_name,
                bbox_west, bbox_south, bbox_east, bbox_north,
            )
            if transform is None:
                transform = clipped.rio.transform()
            bands.append(clipped.values.astype("float32"))
        stack = np.stack(bands)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(
            output_path, "w", driver="GTiff",
            height=stack.shape[1], width=stack.shape[2], count=stack.shape[0],
            dtype="float32", crs="EPSG:4326", transform=transform,
        ) as dst:
            dst.write(stack)
        logger.info("Saved GFS analysis series %s → %s (%d bands)",
                    var_key, output_path, len(bands))
        return output_path

    def _fetch_clipped(
        self,
        cycle: GFSCycleInfo,
        fxx: int,
        var_key: str,
        search_string: str,
        field_name: str,
        bbox_west: float,
        bbox_south: float,
        bbox_east: float,
        bbox_north: float,
    ):
        """Fetch one forecast hour of one variable, clipped to the AOI bbox."""
        from herbie import Herbie

        date_str = f"{cycle.date} {cycle.cycle_hour:02d}:00"
        # The public buckets drop connections now and then; a multi-day hindcast makes
        # hundreds of requests, so one transient failure must not lose the whole series.
        for intento in range(FETCH_ATTEMPTS):
            try:
                H = Herbie(date_str, model="gfs", product="pgrb2.0p25", fxx=fxx, verbose=False)
                ds = H.xarray(search_string)
                break
            except Exception as exc:
                if intento == FETCH_ATTEMPTS - 1:
                    raise GFSDownloadError(
                        f"Failed to fetch GFS variable {var_key} at fxx={fxx}: {exc}"
                    ) from exc
                logger.warning("GFS %s fxx=%d attempt %d failed: %s", var_key, fxx,
                               intento + 1, exc)
                sleep(FETCH_BACKOFF_S * (intento + 1))

        # Extract the DataArray — field name varies, fall back to first data variable
        if field_name in ds:
            da = ds[field_name]
        else:
            data_vars = list(ds.data_vars)
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
            return da.rio.clip_box(
                minx=bbox_west, miny=bbox_south, maxx=bbox_east, maxy=bbox_north
            )
        except Exception as exc:
            raise GFSDownloadError(
                f"Failed to clip GFS variable {var_key} at fxx={fxx} to bbox: {exc}"
            ) from exc
