#!/bin/sh
set -eu

if [ "$#" -ne 3 ]; then
  echo "usage: $0 CASE_ROOT CYCLE FORECAST_START" >&2
  exit 2
fi

case_root=$1
cycle=$2
forecast_start=$3
repo_root=/Users/ichevallier/Projects/university/tesis/igniteinsights
cli="$repo_root/scripts/weather_ensemble_poc.py"
uv_cache=/private/tmp/igniteinsights-uv-cache

case "$case_root" in
  "$repo_root"/data/ensemble-poc/backtest-lote-a/*) ;;
  *) echo "refusing unexpected case root: $case_root" >&2; exit 2 ;;
esac

mkdir -p "$case_root/member-manifests" "$case_root/inputs" "$case_root/runs"

for member in c00 $(jot -w 'p%02d' 30 1); do
  input_dir="$case_root/inputs/$member"
  run_dir="$case_root/runs/$member"
  manifest="$case_root/member-manifests/$member.json"

  if [ -f "$run_dir/run-metrics.json" ] && \
     [ "$(jq -r '.status' "$run_dir/run-metrics.json")" = success ] && \
     find "$run_dir" -maxdepth 1 -name 'time_of_arrival_*.tif' -print -quit | grep -q .; then
    echo "$member already successful; skipping"
  else
    if [ -d "$run_dir" ]; then
      rm -rf "$run_dir"
    fi
    if [ ! -d "$input_dir" ]; then
      UV_CACHE_DIR="$uv_cache" uv run python "$cli" materialize \
        --source "$case_root/sources/$member" \
        --frozen-inputs "$case_root/base-p24-modelo-v0-inputs" \
        --output "$input_dir"
    fi
    cp "$input_dir/ensemble-member.json" "$manifest"
    ELMFIRE_RUNNER_URL=http://localhost:8001 \
      ELMFIRE_RUNNER_TRANSFER_FILES=false \
      UV_CACHE_DIR="$uv_cache" \
      uv run python "$cli" run \
        --inputs "$input_dir" --outputs "$run_dir" --horizon 24
  fi

  cp "$input_dir/ensemble-member.json" "$manifest" 2>/dev/null || true
  rm -rf "$input_dir"
  rm -f "$case_root/sources/$member/u10.tif" \
        "$case_root/sources/$member/v10.tif" \
        "$case_root/sources/$member/t2m.tif" \
        "$case_root/sources/$member/rh.tif"
  rm -f "$run_dir"/flin_*.tif "$run_dir"/vs_*.tif \
        "$run_dir"/hourly_isochrones.dbf "$run_dir"/hourly_isochrones.prj \
        "$run_dir"/hourly_isochrones.shp "$run_dir"/hourly_isochrones.shx \
        "$run_dir"/fire_size_stats.csv
  echo "$member retained and cleaned"
done

for horizon in 12 24; do
  agreement="$case_root/agreement/h$(printf '%02d' "$horizon")"
  if [ ! -f "$agreement/ensemble_agreement.json" ]; then
    UV_CACHE_DIR="$uv_cache" uv run python "$cli" aggregate \
      --runs "$case_root/runs" --expected-members 31 --min-valid-members 31 \
      --cycle-label "$cycle" --forecast-start "$forecast_start" \
      --horizon "$horizon" --output "$agreement"
  fi
done

UV_CACHE_DIR="$uv_cache" uv run python "$cli" evaluate-backtest \
  --base-inputs "$case_root/base-p24-modelo-v0-inputs" \
  --runs "$case_root/runs" --agreement-root "$case_root/agreement" \
  --output "$case_root/backtest-metrics.json"

echo "case complete: $case_root"
