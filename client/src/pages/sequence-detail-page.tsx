import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, Edit, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Navbar } from '@/components/navbar';
import { SequenceFormDialog } from '@/components/sequence-form-dialog';
import { useSequence, useDeleteSequence, useDownloadSequence } from '@/hooks/use-sequences';
import { useProjects } from '@/hooks/use-projects';
import { useState } from 'react';

export function SequenceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const sequenceId = id ? parseInt(id) : undefined;

  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);

  const { data: sequence, isLoading, error } = useSequence(sequenceId);
  const { data: projects } = useProjects();
  const deleteSequence = useDeleteSequence();
  const downloadSequence = useDownloadSequence();

  const handleDelete = async () => {
    if (!sequenceId) return;
    if (confirm('Are you sure you want to delete this sequence?')) {
      try {
        await deleteSequence.mutateAsync(sequenceId);
        navigate('/sequences');
      } catch (error) {
        console.error('Failed to delete sequence:', error);
      }
    }
  };

  const handleDownload = async () => {
    if (!sequenceId) return;
    try {
      await downloadSequence.mutateAsync(sequenceId);
    } catch (error) {
      console.error('Failed to download sequence:', error);
    }
  };

  const getSequenceTypeBadgeColor = (type: string) => {
    switch (type) {
      case 'DNA':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'RNA':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'PROTEIN':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  if (isLoading) {
    return (
      <>
        <Navbar />
        <div className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-center min-h-[400px]">
            <p className="text-muted-foreground">Loading sequence...</p>
          </div>
        </div>
      </>
    );
  }

  if (error || !sequence) {
    return (
      <>
        <Navbar />
        <div className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-center min-h-[400px]">
            <p className="text-red-500">
              {error ? `Error: ${error.message}` : 'Sequence not found'}
            </p>
          </div>
        </div>
      </>
    );
  }

  const project = projects?.find((p) => p.id === sequence.projectId);

  return (
    <>
      <Navbar />
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={() => navigate('/sequences')}
            className="mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Sequences
          </Button>
        </div>

        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold mb-2">{sequence.name}</h1>
            <span
              className={`inline-block px-3 py-1 text-sm rounded-full ${getSequenceTypeBadgeColor(
                sequence.sequenceType
              )}`}
            >
              {sequence.sequenceType}
            </span>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleDownload}
              disabled={downloadSequence.isPending}
            >
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
            <Button
              variant="outline"
              onClick={() => setIsEditDialogOpen(true)}
            >
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteSequence.isPending}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Metadata Card */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">Metadata</h2>
            <div className="space-y-3">
              <div>
                <p className="text-sm text-muted-foreground">Length</p>
                <p className="text-lg font-medium">
                  {sequence.length.toLocaleString()} bp
                </p>
              </div>

              {sequence.sequenceType !== 'PROTEIN' && sequence.gcContent !== null && (
                <div>
                  <p className="text-sm text-muted-foreground">GC Content</p>
                  <p className="text-lg font-medium">
                    {(sequence.gcContent * 100).toFixed(2)}%
                  </p>
                </div>
              )}

              {sequence.sequenceType === 'PROTEIN' && sequence.molecularWeight !== null && (
                <div>
                  <p className="text-sm text-muted-foreground">Molecular Weight</p>
                  <p className="text-lg font-medium">
                    {sequence.molecularWeight.toFixed(2)} Da
                  </p>
                </div>
              )}

              <div>
                <p className="text-sm text-muted-foreground">Storage</p>
                <p className="text-lg font-medium">
                  {sequence.usesFileStorage ? 'File storage' : 'Database storage'}
                </p>
              </div>

              <div>
                <p className="text-sm text-muted-foreground">Project</p>
                <p className="text-lg font-medium">
                  {project?.name || `Project #${sequence.projectId}`}
                </p>
              </div>

              <div>
                <p className="text-sm text-muted-foreground">Created</p>
                <p className="text-lg font-medium">
                  {new Date(sequence.createdAt).toLocaleString()}
                </p>
              </div>

              <div>
                <p className="text-sm text-muted-foreground">Last Updated</p>
                <p className="text-lg font-medium">
                  {new Date(sequence.updatedAt).toLocaleString()}
                </p>
              </div>
            </div>
          </Card>

          {/* Description Card */}
          <Card className="p-6">
            <h2 className="text-xl font-semibold mb-4">Description</h2>
            {sequence.description ? (
              <p className="text-muted-foreground">{sequence.description}</p>
            ) : (
              <p className="text-muted-foreground italic">No description provided</p>
            )}
          </Card>
        </div>

        {/* Sequence Data Card */}
        <Card className="p-6 mt-6">
          <h2 className="text-xl font-semibold mb-4">Sequence Data</h2>
          {sequence.sequenceData ? (
            <div className="bg-muted p-4 rounded-lg font-mono text-sm break-all whitespace-pre-wrap">
              {sequence.sequenceData}
            </div>
          ) : (
            <div className="bg-muted p-4 rounded-lg text-center">
              <p className="text-muted-foreground mb-2">
                Sequence data is stored in a file and not displayed for safety/size reasons.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownload}
                disabled={downloadSequence.isPending}
              >
                <Download className="h-4 w-4 mr-2" />
                Download to view full sequence
              </Button>
            </div>
          )}
        </Card>
      </div>

      {isEditDialogOpen && sequenceId && (
        <SequenceFormDialog
          open={isEditDialogOpen}
          onOpenChange={setIsEditDialogOpen}
          sequenceId={sequenceId}
        />
      )}
    </>
  );
}