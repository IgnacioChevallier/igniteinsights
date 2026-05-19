

Microservicio ELMFIRE — PENDING VERIFICATION

El contrato del microservicio ELMFIRE-runner debe definirse. Como punto de partida se propone:

POST http://elmfire-runner:8001/simulate
Content-Type: application/json

{
    "elmfire_data_path": "/data/elmfire/inputs/{run_id}/elmfire.data",
    "inputs_dir": "/data/elmfire/inputs/{run_id}/",
    "outputs_dir": "/data/elmfire/outputs/{run_id}/",
    "simulation_hours": 3
}

Response 200:
{
    "status": "success",
    "run_id": "...",
    "outputs": {
        "isochrones_shp": "/data/elmfire/outputs/{run_id}/hourly_isochrones.shp",
        "time_of_arrival_tif": "/data/elmfire/outputs/{run_id}/toa_*.tif",
        "flame_length_tifs": [...]
    }
}

PENDING VERIFICATION: validar que los paths sean compartidos entre ambos microservicios vía volumen Docker montado, o definir un mecanismo alternativo (objeto storage, SFTP, etc.).