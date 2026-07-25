# Issue #17: GCS Raw Archive Uploader - Paso a Paso

## 🛠️ 1. Implementación

- [x] **Paso 1: Dependencias**
  - Añadir `google-cloud-storage` al `requirements.txt` (si no está).
  - **Control:** Ejecutar `pip show google-cloud-storage` en tu entorno para asegurar que está instalada.

- [x] **Paso 2: Crear el Loader**
  - Crear el archivo `src/loaders/gcs_loader.py`.
  - Crear la clase `GCSLoader` con el método `upload_raw_payload(bucket, blob_name, json_data)`.
  - Usar un bloque `try-except` para capturar errores de subida y hacer que la falla sea "silenciosa".
  - **Control:** Correr tu linter (ej. `flake8 src/loaders/gcs_loader.py`) y asegurar que no haya errores de sintaxis.

- [x] **Paso 3: Integrar en el DAG**
  - Editar `dags/dag_main.py`, específicamente la función `extract_and_stage_daily_prices`.
  - Instanciar `GCSLoader`.
  - Justo después de obtener los `records` de las APIs, llamar a la función de subida.
  - **Control:** Ejecutar `python dags/dag_main.py` localmente. No debe fallar la compilación del archivo.

- [x] **Paso 4: Credenciales GCP**
  - Asegurar que la Service Account tiene permisos de escritura en el bucket.
  - Configurar `GOOGLE_APPLICATION_CREDENTIALS` en el entorno donde corre Airflow.
  - **Control:** Escribir un pequeño script en python (`python -c "from google.cloud import storage; print(storage.Client())"`) para verificar que toma las credenciales.

---

## 🔍 2. Verificación y Testing

- [ ] **Control 1: Logs de Airflow**
  - Disparar manualmente el DAG en la UI de Airflow.
  - **Check:** En los logs de la tarea `extract_and_stage_daily_prices`, debes ver un mensaje de éxito indicando que el archivo se subió.

- [ ] **Control 2: Listar archivos en el Bucket**
  - Abrir la terminal y ejecutar: `gcloud storage ls -r gs://<TU_BUCKET_NAME>/`
  - **Check:** Debes ver los archivos `.json` recién subidos.

- [ ] **Control 3: Prueba de Resiliencia (Opcionalidad)**
  - Romper a propósito la conexión (ej. cambiando el nombre del bucket en el código por uno falso).
  - Ejecutar el DAG nuevamente.
  - **Check:** La tarea en Airflow **no debe fallar** (terminar en `SUCCESS`), pero el log debe mostrar un `WARNING/ERROR` advirtiendo que no se pudo subir a GCS. Esto asegura que la base de datos principal siga funcionando.
