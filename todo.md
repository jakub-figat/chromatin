  Next Steps for Phase 2

1. camel and snake case in job route tests
2. Background task infrastructure (choose between Celery+Redis or FastAPI background tasks)
3. Alignment implementation (Biopython integration)
4. Job worker for processing alignments


• Implemented the groundwork for Phase 3 (ESMFold-based structure prediction) across backend and frontend types, with several key milestones in place:

  - Added configuration knobs for calling the public ESMFold API and expanded the job enum and schemas to cover the new STRUCTURE_PREDICTION flow.
  - Extended the sequence domain to persist predicted structures (new SequenceStructure model, storage helpers, API routes for metadata/download) and wired Celery workers to call ESMFold, cache results by sequence hash, and store PDB files plus confidence statistics.
  - Updated Alembic to migrate the new table and enum value.
  - Began adapting client types to handle the additional job kind before pausing on UI wiring, per request.

  This sets up the critical backend plumbing; remaining work includes finishing the client forms/detail views for structure jobs, polishing validation, and exercising the new endpoints. Let me know when you want to continue—next logical steps are shaping the UI for job creation/result display and running
  migrations/tests once code is finalized.