export type SequenceType = 'DNA' | 'RNA' | 'PROTEIN'

// List response - no sequence data, just metadata
export interface SequenceListItem {
  id: number
  name: string
  sequenceType: SequenceType
  description?: string
  userId: number
  projectId: number
  length: number
  gcContent: number | null
  molecularWeight: number | null
  usesFileStorage: boolean
  createdAt: string
  updatedAt: string
}

// Detail response - includes sequence data if stored in DB
export interface SequenceDetail {
  id: number
  name: string
  sequenceData: string | null  // Null if stored in file
  sequenceType: SequenceType
  description?: string
  userId: number
  projectId: number
  length: number
  gcContent: number | null
  molecularWeight: number | null
  usesFileStorage: boolean
  createdAt: string
  updatedAt: string
}

// Alias for backwards compatibility
export type Sequence = SequenceDetail

export interface SequenceInput {
  name: string
  sequenceData: string
  sequenceType: SequenceType
  description?: string
  projectId: number
}

export interface FastaUploadInput {
  projectId: number
  sequenceType?: SequenceType
}

export interface FastaUploadOutput {
  sequencesCreated: number
}