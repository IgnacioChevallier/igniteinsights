# WindNinja (USFS Missoula Fire Sciences Lab, dominio público): sólo la CLI del solver de
# conservación de masa, sin GUI, sin OpenFOAM, sin NOMADS. La usa el benchmark para bajar el
# viento del GFS al terreno (RESULTADOS-CSS-BAP, H4).
#   docker build -t windninja-cli:3.12.2 tools/windninja
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates git cmake g++ make pkg-config \
      libgdal-dev libnetcdf-dev libcurl4-gnutls-dev libfontconfig1-dev libgeos-dev \
      libsqlite3-dev libboost-program-options-dev libboost-date-time-dev libboost-test-dev \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch 3.12.2 https://github.com/firelab/windninja.git /opt/windninja
RUN mkdir /opt/windninja/build && cd /opt/windninja/build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DNINJA_QTGUI=OFF -DNINJA_CLI=ON -DNINJAFOAM=OFF \
             -DWITH_NOMADS_SUPPORT=OFF -DPHONE_HOME_QUERIES=OFF -DENABLE_GMTED=OFF \
             -DWITH_LCP_CLIENT=OFF -DOPENMP_SUPPORT=ON && \
    make -j2 WindNinja_cli && cp src/cli/WindNinja_cli /usr/local/bin/
ENV WINDNINJA_DATA=/opt/windninja/data
WORKDIR /data
ENTRYPOINT ["WindNinja_cli"]
