import type { JobStatus } from '@/types/job'

interface JobStatusBadgeProps {
  status: JobStatus
}

const statusStyles: Record<JobStatus, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  RUNNING: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  COMPLETED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  FAILED: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  CANCELLED: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
}

const statusLabels: Record<JobStatus, string> = {
  PENDING: 'Pending',
  RUNNING: 'Running',
  COMPLETED: 'Completed',
  FAILED: 'Failed',
  CANCELLED: 'Cancelled',
}

export function JobStatusBadge({ status }: JobStatusBadgeProps) {
  return (
    <span
      className={`inline-block px-2 py-1 text-xs rounded-full ${statusStyles[status]}`}
    >
      {statusLabels[status]}
    </span>
  )
}