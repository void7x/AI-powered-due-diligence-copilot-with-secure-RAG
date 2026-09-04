from app.core.jobs import JobManager


def test_jobs_are_owned_by_the_creating_user():
    manager = JobManager()
    job = manager.create("document_process", ["EXTRACTING"], owner_user_id="user-a")

    assert job.owner_user_id == "user-a"
    assert manager.get(job.id) is job


def test_job_ownership_is_not_shared_between_users():
    manager = JobManager()
    first = manager.create("document_process", ["EXTRACTING"], owner_user_id="user-a")
    second = manager.create("document_process", ["EXTRACTING"], owner_user_id="user-b")

    assert first.owner_user_id != second.owner_user_id
