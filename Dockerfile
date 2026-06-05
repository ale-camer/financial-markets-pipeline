FROM apache/airflow:2.10.5-python3.11

USER root
# Install essential build tools (useful for compiling some python packages if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy and install python dependencies
COPY --chown=airflow:root requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Add workspace directory to python path
ENV PYTHONPATH="/opt/airflow:/opt/airflow/src:${PYTHONPATH}"

# Workdir defaults to /opt/airflow
WORKDIR /opt/airflow
