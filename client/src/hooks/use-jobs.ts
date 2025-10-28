import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '@/lib/api-client'
import type { JobListItem, JobDetail, JobInput, JobStatus } from '@/types/job'

interface ListJobsParams {
  skip?: number
  limit?: number
  status?: JobStatus
}

// Fetch all jobs for the current user with optional filters
export function useJobs(params?: ListJobsParams) {
  const { skip = 0, limit = 100, status } = params || {}

  return useQuery({
    queryKey: ['jobs', { skip, limit, status }],
    queryFn: async () => {
      const queryParams = new URLSearchParams()
      if (skip) queryParams.append('skip', skip.toString())
      if (limit) queryParams.append('limit', limit.toString())
      if (status) queryParams.append('status', status)

      const endpoint = `/jobs/${queryParams.toString() ? `?${queryParams.toString()}` : ''}`
      const data = await api.get<JobListItem[]>(endpoint)
      return data
    },
  })
}

// Fetch a single job by ID
export function useJob(jobId: number | undefined) {
  return useQuery({
    queryKey: ['jobs', jobId],
    queryFn: async () => {
      if (!jobId) throw new Error('Job ID is required')
      const data = await api.get<JobDetail>(`/jobs/${jobId}`)
      return data
    },
    enabled: !!jobId,
  })
}

// Create a new job
export function useCreateJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (input: JobInput) => {
      const data = await api.post<JobDetail>('/jobs/', input)
      return data
    },
    onSuccess: () => {
      // Invalidate jobs list to refetch
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      toast.success('Job created successfully!')
    },
    onError: (error: any) => {
      const message = error?.data?.detail || error?.message || 'Failed to create job'
      toast.error(message)
    },
  })
}

// Cancel a job
export function useCancelJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (jobId: number) => {
      const data = await api.post<JobDetail>(`/jobs/${jobId}/cancel`)
      return data
    },
    onSuccess: (_, jobId) => {
      // Invalidate both the jobs list and the specific job
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['jobs', jobId] })
      toast.success('Job cancelled successfully!')
    },
    onError: (error: any) => {
      const message = error?.data?.detail || error?.message || 'Failed to cancel job'
      toast.error(message)
    },
  })
}

// Delete a job
export function useDeleteJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (jobId: number) => {
      await api.delete(`/jobs/${jobId}`)
    },
    onSuccess: () => {
      // Invalidate jobs list to refetch
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      toast.success('Job deleted successfully!')
    },
    onError: (error: any) => {
      const message = error?.data?.detail || error?.message || 'Failed to delete job'
      toast.error(message)
    },
  })
}