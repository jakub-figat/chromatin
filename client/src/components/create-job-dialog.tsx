import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCreateJob } from '@/hooks/use-jobs'
import { useSequences } from '@/hooks/use-sequences'
import type { JobType } from '@/types/job'
import { Card } from '@/components/ui/card'

const pairwiseAlignmentSchema = z.object({
  jobType: z.literal('PAIRWISE_ALIGNMENT'),
  sequenceId1: z.number({ required_error: 'First sequence is required' }),
  sequenceId2: z.number({ required_error: 'Second sequence is required' }),
})

type PairwiseAlignmentFormData = z.infer<typeof pairwiseAlignmentSchema>

interface CreateJobDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// Job type metadata
const jobTypes: Array<{ value: JobType; label: string; description: string }> = [
  {
    value: 'PAIRWISE_ALIGNMENT',
    label: 'Pairwise Alignment',
    description: 'Align two sequences to find similarities and differences',
  },
  // Add more job types here as they are implemented
]

// Component for selecting job type
function JobTypeSelector({
  onSelect,
  onCancel,
}: {
  onSelect: (type: JobType) => void
  onCancel: () => void
}) {
  return (
    <>
      <DialogHeader>
        <DialogTitle>Create New Job</DialogTitle>
      </DialogHeader>

      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Select the type of analysis job you want to run:
        </p>

        <div className="space-y-2">
          {jobTypes.map((jobType) => (
            <Card
              key={jobType.value}
              className="p-4 cursor-pointer hover:bg-accent transition-colors"
              onClick={() => onSelect(jobType.value)}
            >
              <h3 className="font-semibold mb-1">{jobType.label}</h3>
              <p className="text-sm text-muted-foreground">
                {jobType.description}
              </p>
            </Card>
          ))}
        </div>

        <div className="flex justify-end pt-4">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </div>
    </>
  )
}

// Component for pairwise alignment job form
function PairwiseAlignmentForm({
  onSubmit,
  onBack,
  isSubmitting,
}: {
  onSubmit: (data: PairwiseAlignmentFormData) => Promise<void>
  onBack: () => void
  isSubmitting: boolean
}) {
  const { data: sequences, isLoading: isLoadingSequences } = useSequences()

  const {
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
  } = useForm<PairwiseAlignmentFormData>({
    resolver: zodResolver(pairwiseAlignmentSchema),
    defaultValues: {
      jobType: 'PAIRWISE_ALIGNMENT',
    },
  })

  const sequenceId1 = watch('sequenceId1')
  const sequenceId2 = watch('sequenceId2')

  return (
    <>
      <DialogHeader>
        <DialogTitle>Create Pairwise Alignment Job</DialogTitle>
      </DialogHeader>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-2">
          <Label>First Sequence *</Label>
          <Select
            value={sequenceId1?.toString()}
            onValueChange={(value) => setValue('sequenceId1', parseInt(value))}
            disabled={isSubmitting || isLoadingSequences}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select first sequence" />
            </SelectTrigger>
            <SelectContent>
              {sequences?.map((seq) => (
                <SelectItem key={seq.id} value={seq.id.toString()}>
                  {seq.name} ({seq.sequenceType}, {seq.length} bp)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors.sequenceId1 && (
            <p className="text-sm text-red-500">{errors.sequenceId1.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label>Second Sequence *</Label>
          <Select
            value={sequenceId2?.toString()}
            onValueChange={(value) => setValue('sequenceId2', parseInt(value))}
            disabled={isSubmitting || isLoadingSequences}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select second sequence" />
            </SelectTrigger>
            <SelectContent>
              {sequences?.map((seq) => (
                <SelectItem key={seq.id} value={seq.id.toString()}>
                  {seq.name} ({seq.sequenceType}, {seq.length} bp)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors.sequenceId2 && (
            <p className="text-sm text-red-500">{errors.sequenceId2.message}</p>
          )}
        </div>

        {isLoadingSequences && (
          <p className="text-sm text-muted-foreground">Loading sequences...</p>
        )}

        {!isLoadingSequences && (!sequences || sequences.length === 0) && (
          <p className="text-sm text-muted-foreground">
            No sequences available. Please create some sequences first.
          </p>
        )}

        <div className="flex justify-between pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={onBack}
            disabled={isSubmitting}
          >
            Back
          </Button>
          <Button
            type="submit"
            disabled={
              isSubmitting ||
              isLoadingSequences ||
              !sequences ||
              sequences.length < 2
            }
          >
            {isSubmitting ? 'Creating...' : 'Create Job'}
          </Button>
        </div>
      </form>
    </>
  )
}

export function CreateJobDialog({ open, onOpenChange }: CreateJobDialogProps) {
  const [selectedJobType, setSelectedJobType] = useState<JobType | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const createJob = useCreateJob()

  const handleClose = () => {
    onOpenChange(false)
    setSelectedJobType(null)
  }

  const handleJobTypeSelect = (type: JobType) => {
    setSelectedJobType(type)
  }

  const handleBack = () => {
    setSelectedJobType(null)
  }

  const handleSubmitPairwiseAlignment = async (
    data: PairwiseAlignmentFormData
  ) => {
    setIsSubmitting(true)
    try {
      await createJob.mutateAsync({
        params: {
          jobType: data.jobType,
          sequenceId1: data.sequenceId1,
          sequenceId2: data.sequenceId2,
        },
      })
      handleClose()
    } catch (error) {
      console.error('Failed to create job:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        {!selectedJobType && (
          <JobTypeSelector onSelect={handleJobTypeSelect} onCancel={handleClose} />
        )}

        {selectedJobType === 'PAIRWISE_ALIGNMENT' && (
          <PairwiseAlignmentForm
            onSubmit={handleSubmitPairwiseAlignment}
            onBack={handleBack}
            isSubmitting={isSubmitting}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}