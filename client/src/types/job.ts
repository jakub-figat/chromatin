export type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
export type JobType = 'PAIRWISE_ALIGNMENT'

// Job-specific parameter types
export interface PairwiseAlignmentParams {
  jobType: 'PAIRWISE_ALIGNMENT'
  sequenceId1: number
  sequenceId2: number
}

// Union of all job params (extend as more job types are added)
export type JobParams = PairwiseAlignmentParams

// List response - excludes large result data
export interface JobListItem {
  id: number
  status: JobStatus
  jobType: JobType
  params: Record<string, any> | null
  createdAt: string
  completedAt: string | null
  errorMessage: string | null
}

// Detail response - includes full result
export interface JobDetail {
  id: number
  status: JobStatus
  jobType: JobType
  params: Record<string, any> | null
  result: Record<string, any> | null
  createdAt: string
  updatedAt: string
  completedAt: string | null
  errorMessage: string | null
  userId: number
}

// Input for creating a new job
export interface JobInput {
  params: JobParams
}