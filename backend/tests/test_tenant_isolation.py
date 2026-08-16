import pytest
from db.neo import _driver
from application.services.job_service import JobService
from infrastructure.repositories.job_repository import Neo4jJobRepository
from application.services.project_service import ProjectService
from application.services.auth_service import AuthenticatedUser
from domain.job import JobStatus, JobStage
from db.chroma import vector_store

@pytest.fixture(scope="module")
def setup_tenants():
    user1 = AuthenticatedUser(user_id="user-1", email="user1@example.com", organization_id="org-1", role="authenticated")
    user2 = AuthenticatedUser(user_id="user-2", email="user2@example.com", organization_id="org-2", role="authenticated")
    
    project_service = ProjectService()
    p1 = project_service.create_project("Project 1", user1)
    p2 = project_service.create_project("Project 2", user2)
    
    yield (user1, p1), (user2, p2)
    
    # Cleanup
    with _driver.session() as session:
        session.run("MATCH (n) WHERE n.organization_id IN ['org-1', 'org-2'] DETACH DELETE n")

def test_job_tenant_isolation(setup_tenants):
    (user1, p1), (user2, p2) = setup_tenants
    job_service = JobService(Neo4jJobRepository())
    
    # Create job for tenant 1
    job1 = job_service.create_job(
        organization_id=p1["organization_id"],
        project_id=p1["id"],
        user_id=user1.user_id,
        source_type="document",
        source_id="test_doc",
        input_payload_b64="dGVzdA=="
    )
    
    # Fetch job with wrong tenant should fail or return None
    fetched_job_wrong_org = job_service.get_job(job1.job_id, organization_id=p2["organization_id"])
    assert fetched_job_wrong_org is None
    
    # Fetch job with correct tenant
    fetched_job_correct = job_service.get_job(job1.job_id, organization_id=p1["organization_id"])
    assert fetched_job_correct is not None
    assert fetched_job_correct.job_id == job1.job_id

def test_job_lease_mechanics(setup_tenants):
    (user1, p1), _ = setup_tenants
    job_service = JobService(Neo4jJobRepository())
    
    job = job_service.create_job(
        organization_id=p1["organization_id"],
        project_id=p1["id"],
        user_id=user1.user_id,
        source_type="document",
        source_id="test_lease"
    )
    
    # Claim job
    worker_id_1 = "worker-1"
    success = job_service.mark_started(job.job_id, worker_id_1, lease_seconds=300)
    assert success is True
    
    # Second worker should not be able to claim it
    worker_id_2 = "worker-2"
    success_2 = job_service.mark_started(job.job_id, worker_id_2, lease_seconds=300)
    assert success_2 is False
    
    # Update progress with CAS check
    job_reloaded = job_service.get_job(job.job_id, p1["organization_id"])
    success_update = job_service.update_progress(
        job.job_id, 
        expected_version=job_reloaded.version, 
        worker_id=worker_id_1,
        progress=0.5
    )
    assert success_update is True
    
    # Update with wrong version
    success_wrong_version = job_service.update_progress(
        job.job_id,
        expected_version=job_reloaded.version, # Still old version
        worker_id=worker_id_1,
        progress=0.6
    )
    assert success_wrong_version is False
    
    # Complete job
    job_final = job_service.get_job(job.job_id, p1["organization_id"])
    job_service.mark_completed(job.job_id, worker_id_1, job_final.version)
    
    job_completed = job_service.get_job(job.job_id, p1["organization_id"])
    assert job_completed.status == JobStatus.COMPLETED

def test_chroma_tenant_isolation(setup_tenants):
    (user1, p1), (user2, p2) = setup_tenants
    
    # Add vectors to tenant 1
    vector_store.add_vectors(
        texts=["test content 1"],
        embeddings=[[0.1]*384], # Cohere embed-english-light-v3.0 size
        metadatas=[{"source": "doc1", "organization_id": p1["organization_id"], "project_id": p1["id"], "document_id": "doc1", "chunk_id": "c1", "content_hash": "hash1"}],
        ids=["id1"]
    )
    
    # Tenant 2 queries
    results = vector_store.query_vectors([0.1]*384, k=1, organization_id=p2["organization_id"], project_id=p2["id"])
    assert len(results) == 0 # Should not see tenant 1's data
    
    # Tenant 1 queries
    results_t1 = vector_store.query_vectors([0.1]*384, k=1, organization_id=p1["organization_id"], project_id=p1["id"])
    assert len(results_t1) == 1
    assert results_t1[0]["metadata"]["organization_id"] == p1["organization_id"]
