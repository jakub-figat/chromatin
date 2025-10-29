export type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
export type JobType = 'PAIRWISE_ALIGNMENT'
export type AlignmentType = 'LOCAL' | 'GLOBAL'

// Job-specific parameter types
export interface PairwiseAlignmentParams {
  jobType: 'PAIRWISE_ALIGNMENT'
  sequenceId1: number
  sequenceId2: number
  alignmentType?: AlignmentType
  matchScore?: number
  mismatchScore?: number
  gapOpenScore?: number
  gapExtendScore?: number
}

// Union of all job params (extend as more job types are added)
export type JobParams = PairwiseAlignmentParams

// Job-specific result types
export interface ScoringParamsResult {
  matchScore: number
  mismatchScore: number
  gapOpenScore: number
  gapExtendScore: number
}

export interface PairwiseAlignmentResult {
  jobType: 'PAIRWISE_ALIGNMENT'
  sequenceId1: number
  sequenceId2: number
  sequenceName1: string
  sequenceName2: string
  alignmentType: string
  alignmentScore: number
  alignedSeq1: string
  alignedSeq2: string
  alignmentLength: number
  matches: number
  mismatches: number
  gaps: number
  identityPercent: number
  cigar: string
  scoringParams: ScoringParamsResult
}

// Union of all job results (extend as more job types are added)
export type JobResult = PairwiseAlignmentResult

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
  result: JobResult | null
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