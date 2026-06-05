from airflow.models import DagBag


def test_dag_loaded_without_errors():
    """Verify that the DAG is loaded successfully with no import errors."""
    dag_bag = DagBag(dag_folder="dags/", include_examples=False)
    assert not dag_bag.import_errors, (
        f"DAG import errors: {dag_bag.import_errors}"
    )

    dag = dag_bag.get_dag(dag_id="market_data_pipeline")
    assert dag is not None, "DAG 'market_data_pipeline' not found"
    assert len(dag.tasks) == 3, "Expected exactly 3 tasks in the DAG"

    # Verify task IDs
    task_ids = set(dag.task_ids)
    expected_task_ids = {
        "init_db",
        "extract_and_load_daily",
        "load_to_postgres",
    }
    assert task_ids == expected_task_ids, (
        f"Expected tasks {expected_task_ids}, but got {task_ids}"
    )

    # Verify dependencies
    init_db_task = dag.get_task("init_db")
    assert (
        "extract_and_load_daily" in init_db_task.downstream_task_ids
    ), "Dependency init_db >> extract_and_load_daily is missing"

    extract_task = dag.get_task("extract_and_load_daily")
    assert (
        "load_to_postgres" in extract_task.downstream_task_ids
    ), "Dependency extract_and_load_daily >> load_to_postgres is missing"
