export type SequenceType = 'DNA' | 'RNA' | 'PROTEIN'

export interface Sequence {
  id: number
  name: string
  sequenceData: string
  sequenceType: SequenceType
  description?: string
  userId: number
  projectId: number
  length: number
  gcContent: number
  molecularWeight: number
  createdAt: string
  updatedAt: string
}

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
  sequences: Sequence[]
}