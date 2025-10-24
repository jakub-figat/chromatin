export interface Project {
  id: number
  name: string
  description?: string
  isPublic: boolean
  userId: number
  createdAt: string
  updatedAt: string
}

export interface ProjectInput {
  name: string
  description?: string
  isPublic?: boolean
}