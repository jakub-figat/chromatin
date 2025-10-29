import { useState } from 'react'
import { Plus, Trash2, XCircle, Eye, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Navbar } from '@/components/navbar'
import { CreateJobDialog } from '@/components/create-job-dialog'
import { JobDetailDialog } from '@/components/job-detail-dialog'
import { JobStatusBadge } from '@/components/job-status-badge'
import { useJobs, useJob, useCancelJob, useDeleteJob } from '@/hooks/use-jobs'
import type { JobListItem, JobStatus } from '@/types/job'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'

export function JobsPage() {
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false)
  const [selectedJobId, setSelectedJobId] = useState<number | undefined>()
  const [statusFilter, setStatusFilter] = useState<JobStatus | undefined>()

  const { data: jobs, isLoading, error, refetch } = useJobs({ status: statusFilter })
  const { data: selectedJob } = useJob(selectedJobId)
  const cancelJob = useCancelJob()
  const deleteJob = useDeleteJob()

  const handleCancel = async (id: number) => {
    if (confirm('Are you sure you want to cancel this job?')) {
      try {
        await cancelJob.mutateAsync(id)
      } catch (error) {
        console.error('Failed to cancel job:', error)
      }
    }
  }

  const handleDelete = async (id: number) => {
    if (confirm('Are you sure you want to delete this job?')) {
      try {
        await deleteJob.mutateAsync(id)
      } catch (error) {
        console.error('Failed to delete job:', error)
      }
    }
  }

  const canCancel = (job: JobListItem) => {
    return job.status === 'PENDING' || job.status === 'RUNNING'
  }

  const handleViewDetails = (jobId: number) => {
    setSelectedJobId(jobId)
    setIsDetailDialogOpen(true)
  }

  const handleCloseDetailDialog = () => {
    setIsDetailDialogOpen(false)
    setSelectedJobId(undefined)
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <p className="text-muted-foreground">Loading jobs...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <p className="text-red-500">Error loading jobs: {error.message}</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <Navbar />
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Jobs</h1>
            <p className="text-muted-foreground mt-2">
              Manage your bioinformatics analysis jobs
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              New Job
            </Button>
          </div>
        </div>

        {/* Filter by status */}
        <div className="mb-6 max-w-xs">
          <Label>Filter by Status</Label>
          <Select
            value={statusFilter || 'all'}
            onValueChange={(value) =>
              setStatusFilter(value === 'all' ? undefined : (value as JobStatus))
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="PENDING">Pending</SelectItem>
              <SelectItem value="RUNNING">Running</SelectItem>
              <SelectItem value="COMPLETED">Completed</SelectItem>
              <SelectItem value="FAILED">Failed</SelectItem>
              <SelectItem value="CANCELLED">Cancelled</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {!jobs || jobs.length === 0 ? (
          <Card className="p-12 text-center">
            <div className="max-w-md mx-auto">
              <h2 className="text-xl font-semibold mb-2">No jobs yet</h2>
              <p className="text-muted-foreground mb-6">
                Create your first job to start running bioinformatics analyses.
              </p>
              <Button onClick={() => setIsCreateDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Job
              </Button>
            </div>
          </Card>
        ) : (
          <div className="space-y-4">
            {jobs.map((job) => (
              <Card key={job.id} className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold">
                        {job.jobType.replace(/_/g, ' ')}
                      </h3>
                      <JobStatusBadge status={job.status} />
                    </div>

                    {/* Job parameters */}
                    {job.params && (
                      <div className="text-sm text-muted-foreground mb-2">
                        {job.jobType === 'PAIRWISE_ALIGNMENT' && (
                          <div>
                            Sequences: {job.params.sequenceId1} vs{' '}
                            {job.params.sequenceId2}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Error message */}
                    {job.errorMessage && (
                      <div className="text-sm text-red-500 mb-2">
                        Error: {job.errorMessage}
                      </div>
                    )}

                    {/* Timestamps */}
                    <div className="text-xs text-muted-foreground space-y-1">
                      <div>Created: {new Date(job.createdAt).toLocaleString()}</div>
                      {job.completedAt && (
                        <div>
                          Completed: {new Date(job.completedAt).toLocaleString()}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleViewDetails(job.id)}
                      title="View details"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    {canCancel(job) && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleCancel(job.id)}
                        disabled={cancelJob.isPending}
                        title="Cancel job"
                      >
                        <XCircle className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(job.id)}
                      disabled={deleteJob.isPending}
                      title="Delete job"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        <CreateJobDialog
          open={isCreateDialogOpen}
          onOpenChange={setIsCreateDialogOpen}
        />

        <JobDetailDialog
          job={selectedJob || null}
          open={isDetailDialogOpen}
          onOpenChange={handleCloseDetailDialog}
        />
      </div>
    </>
  )
}