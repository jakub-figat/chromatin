import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Card } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { JobStatusBadge } from '@/components/job-status-badge'
import type { JobDetail, PairwiseAlignmentResult } from '@/types/job'

interface JobDetailDialogProps {
  job: JobDetail | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function PairwiseAlignmentResultDisplay({
  result,
}: {
  result: PairwiseAlignmentResult
}) {
  // Format alignment for display with line breaks every 60 characters
  const formatAlignment = (seq: string) => {
    const chunks: string[] = []
    for (let i = 0; i < seq.length; i += 60) {
      chunks.push(seq.slice(i, i + 60))
    }
    return chunks
  }

  const alignedSeq1Chunks = formatAlignment(result.alignedSeq1)
  const alignedSeq2Chunks = formatAlignment(result.alignedSeq2)

  // Create match indicator line showing matches (|), mismatches (.), and gaps ( )
  const createMatchLine = (seq1: string, seq2: string) => {
    let line = ''
    for (let i = 0; i < seq1.length; i++) {
      if (seq1[i] === '-' || seq2[i] === '-') {
        line += ' '
      } else if (seq1[i] === seq2[i]) {
        line += '|'
      } else {
        line += '.'
      }
    }
    return line
  }

  const matchLineChunks = formatAlignment(
    createMatchLine(result.alignedSeq1, result.alignedSeq2)
  )

  return (
    <div className="space-y-6">
      {/* Summary Statistics */}
      <Card className="p-4">
        <h3 className="font-semibold mb-3">Alignment Summary</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <Label className="text-muted-foreground">Sequences</Label>
            <p className="font-medium">
              {result.sequenceName1} vs {result.sequenceName2}
            </p>
          </div>
          <div>
            <Label className="text-muted-foreground">Alignment Type</Label>
            <p className="font-medium">{result.alignmentType}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Alignment Score</Label>
            <p className="font-medium">{result.alignmentScore.toFixed(2)}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Identity</Label>
            <p className="font-medium">{result.identityPercent.toFixed(1)}%</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Length</Label>
            <p className="font-medium">{result.alignmentLength} bp</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Matches</Label>
            <p className="font-medium">{result.matches}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Mismatches</Label>
            <p className="font-medium">{result.mismatches}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Gaps</Label>
            <p className="font-medium">{result.gaps}</p>
          </div>
        </div>
      </Card>

      {/* Alignment Visualization */}
      <Card className="p-4">
        <h3 className="font-semibold mb-3">Aligned Sequences</h3>
        <div className="bg-muted p-4 rounded-md overflow-x-auto">
          <pre className="font-mono text-xs leading-relaxed">
            {alignedSeq1Chunks.map((chunk, i) => (
              <div key={i} className="mb-4">
                <div>
                  <span className="text-muted-foreground mr-2">
                    {result.sequenceName1}:
                  </span>
                  {chunk}
                </div>
                <div className="text-muted-foreground">
                  <span className="mr-2 invisible">
                    {result.sequenceName1}:
                  </span>
                  {matchLineChunks[i]}
                </div>
                <div>
                  <span className="text-muted-foreground mr-2">
                    {result.sequenceName2}:
                  </span>
                  {alignedSeq2Chunks[i]}
                </div>
              </div>
            ))}
          </pre>
          <p className="text-xs text-muted-foreground mt-2">
            | = match, . = mismatch, - = gap
          </p>
        </div>
      </Card>

      {/* CIGAR String */}
      <Card className="p-4">
        <h3 className="font-semibold mb-2">CIGAR String</h3>
        <div className="bg-muted p-3 rounded-md font-mono text-sm break-all">
          {result.cigar}
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          M = match/mismatch, I = insertion, D = deletion
        </p>
      </Card>

      {/* Scoring Parameters */}
      <Card className="p-4">
        <h3 className="font-semibold mb-3">Scoring Parameters</h3>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <Label className="text-muted-foreground">Match Score</Label>
            <p className="font-medium">{result.scoringParams.matchScore}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Mismatch Score</Label>
            <p className="font-medium">{result.scoringParams.mismatchScore}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Gap Open Score</Label>
            <p className="font-medium">{result.scoringParams.gapOpenScore}</p>
          </div>
          <div>
            <Label className="text-muted-foreground">Gap Extend Score</Label>
            <p className="font-medium">{result.scoringParams.gapExtendScore}</p>
          </div>
        </div>
      </Card>
    </div>
  )
}

export function JobDetailDialog({
  job,
  open,
  onOpenChange,
}: JobDetailDialogProps) {
  if (!job) return null

  const isPairwiseAlignment =
    job.result && 'jobType' in job.result && job.result.jobType === 'PAIRWISE_ALIGNMENT'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <span>Job Details #{job.id}</span>
            <JobStatusBadge status={job.status} />
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Job Metadata */}
          <Card className="p-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <Label className="text-muted-foreground">Job Type</Label>
                <p className="font-medium">
                  {job.jobType.replace(/_/g, ' ')}
                </p>
              </div>
              <div>
                <Label className="text-muted-foreground">Status</Label>
                <p className="font-medium">{job.status}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Created</Label>
                <p className="font-medium">
                  {new Date(job.createdAt).toLocaleString()}
                </p>
              </div>
              {job.completedAt && (
                <div>
                  <Label className="text-muted-foreground">Completed</Label>
                  <p className="font-medium">
                    {new Date(job.completedAt).toLocaleString()}
                  </p>
                </div>
              )}
            </div>

            {job.errorMessage && (
              <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-md">
                <Label className="text-red-600 dark:text-red-400">Error</Label>
                <p className="text-sm text-red-600 dark:text-red-400">
                  {job.errorMessage}
                </p>
              </div>
            )}
          </Card>

          {/* Results */}
          {job.status === 'COMPLETED' && job.result && isPairwiseAlignment && (
            <PairwiseAlignmentResultDisplay
              result={job.result as PairwiseAlignmentResult}
            />
          )}

          {job.status === 'COMPLETED' && !job.result && (
            <Card className="p-6 text-center">
              <p className="text-muted-foreground">No results available</p>
            </Card>
          )}

          {job.status !== 'COMPLETED' && job.status !== 'FAILED' && (
            <Card className="p-6 text-center">
              <p className="text-muted-foreground">
                Job is {job.status.toLowerCase()}. Results will appear when
                completed.
              </p>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}