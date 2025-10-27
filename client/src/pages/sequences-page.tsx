import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Plus, Edit, Trash2, Filter, Upload, Download, CheckSquare, Square, Eye, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Navbar } from '@/components/navbar';
import { SequenceFormDialog } from '@/components/sequence-form-dialog';
import { FastaUploadDialog } from '@/components/fasta-upload-dialog';
import { useSequences, useDeleteSequence, useDownloadSequence, useDownloadBatch } from '@/hooks/use-sequences';
import { useProjects } from '@/hooks/use-projects';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { SequenceListItem } from '@/types/sequence';

export function SequencesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const [editingSequenceId, setEditingSequenceId] = useState<number | undefined>();
  const [filterProjectId, setFilterProjectId] = useState<number | undefined>();
  const [filterSequenceType, setFilterSequenceType] = useState<string | undefined>();
  const [filterName, setFilterName] = useState<string>('');
  const [filterLengthGte, setFilterLengthGte] = useState<string>('');
  const [filterLengthLte, setFilterLengthLte] = useState<string>('');
  const [selectedSequenceIds, setSelectedSequenceIds] = useState<number[]>([]);

  // Read projectId from URL params on mount
  useEffect(() => {
    const projectIdParam = searchParams.get('projectId');
    if (projectIdParam) {
      const projectId = parseInt(projectIdParam);
      if (!isNaN(projectId)) {
        setFilterProjectId(projectId);
      }
    }
  }, [searchParams]);

  const { data: sequences, isLoading, error } = useSequences({
    skip: 0,
    limit: 100,
    projectId: filterProjectId,
    sequenceType: filterSequenceType,
    name: filterName || undefined,
    lengthGte: filterLengthGte ? parseInt(filterLengthGte) : undefined,
    lengthLte: filterLengthLte ? parseInt(filterLengthLte) : undefined,
  });
  const { data: projects } = useProjects();
  const deleteSequence = useDeleteSequence();
  const downloadSequence = useDownloadSequence();
  const downloadBatch = useDownloadBatch();

  const handleDelete = async (id: number) => {
    if (confirm('Are you sure you want to delete this sequence?')) {
      try {
        await deleteSequence.mutateAsync(id);
      } catch (error) {
        console.error('Failed to delete sequence:', error);
      }
    }
  };

  const handleDownload = async (id: number) => {
    try {
      await downloadSequence.mutateAsync(id);
    } catch (error) {
      console.error('Failed to download sequence:', error);
    }
  };

  const handleBatchDownload = async () => {
    if (selectedSequenceIds.length === 0) return;
    try {
      await downloadBatch.mutateAsync(selectedSequenceIds);
      setSelectedSequenceIds([]);
    } catch (error) {
      console.error('Failed to download sequences:', error);
    }
  };

  const toggleSequenceSelection = (id: number) => {
    setSelectedSequenceIds((prev) =>
      prev.includes(id) ? prev.filter((sid) => sid !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedSequenceIds.length === sequences?.length) {
      setSelectedSequenceIds([]);
    } else {
      setSelectedSequenceIds(sequences?.map((s) => s.id) || []);
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
            <p className="text-muted-foreground">Loading sequences...</p>
          </div>
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <Navbar />
        <div className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-center min-h-[400px]">
            <p className="text-red-500">
              Error loading sequences: {error.message}
            </p>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Sequences</h1>
          <p className="text-muted-foreground mt-2">
            Manage your biological sequences
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setIsUploadDialogOpen(true)}
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload FASTA
          </Button>
          <Button onClick={() => setIsCreateDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Sequence
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card className="p-4 mb-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {/* Project Filter */}
          <div className="space-y-2">
            <Label htmlFor="filter-project">Project</Label>
            <Select
              value={filterProjectId?.toString() || 'all'}
              onValueChange={(value) =>
                setFilterProjectId(value === 'all' ? undefined : parseInt(value))
              }
            >
              <SelectTrigger id="filter-project">
                <SelectValue placeholder="All projects" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All projects</SelectItem>
                {projects?.map((project) => (
                  <SelectItem key={project.id} value={project.id.toString()}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Type Filter */}
          <div className="space-y-2">
            <Label htmlFor="filter-type">Sequence Type</Label>
            <Select
              value={filterSequenceType || 'all'}
              onValueChange={(value) =>
                setFilterSequenceType(value === 'all' ? undefined : value)
              }
            >
              <SelectTrigger id="filter-type">
                <SelectValue placeholder="All types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All types</SelectItem>
                <SelectItem value="DNA">DNA</SelectItem>
                <SelectItem value="RNA">RNA</SelectItem>
                <SelectItem value="PROTEIN">Protein</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Name Filter */}
          <div className="space-y-2">
            <Label htmlFor="filter-name">Name</Label>
            <div className="relative">
              <Input
                id="filter-name"
                placeholder="Search by name..."
                value={filterName}
                onChange={(e) => setFilterName(e.target.value)}
              />
              {filterName && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-0 h-full"
                  onClick={() => setFilterName('')}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>

          {/* Length Range Filters */}
          <div className="space-y-2">
            <Label>Length (bp)</Label>
            <div className="flex gap-2">
              <Input
                placeholder="Min"
                type="number"
                value={filterLengthGte}
                onChange={(e) => setFilterLengthGte(e.target.value)}
                className="w-full"
              />
              <Input
                placeholder="Max"
                type="number"
                value={filterLengthLte}
                onChange={(e) => setFilterLengthLte(e.target.value)}
                className="w-full"
              />
            </div>
          </div>
        </div>

        {/* Clear Filters Button */}
        {(filterProjectId || filterSequenceType || filterName || filterLengthGte || filterLengthLte) && (
          <div className="mt-4 pt-4 border-t">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setFilterProjectId(undefined);
                setFilterSequenceType(undefined);
                setFilterName('');
                setFilterLengthGte('');
                setFilterLengthLte('');
              }}
            >
              <X className="h-4 w-4 mr-2" />
              Clear All Filters
            </Button>
          </div>
        )}
      </Card>

      {/* Batch actions */}
      {sequences && sequences.length > 0 && (
        <div className="mb-6 flex items-center justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleSelectAll}
          >
            {selectedSequenceIds.length === sequences.length ? (
              <>
                <CheckSquare className="h-4 w-4 mr-2" />
                Deselect All
              </>
            ) : (
              <>
                <Square className="h-4 w-4 mr-2" />
                Select All
              </>
            )}
          </Button>
          {selectedSequenceIds.length > 0 && (
            <Button
              onClick={handleBatchDownload}
              disabled={downloadBatch.isPending}
            >
              <Download className="h-4 w-4 mr-2" />
              Download {selectedSequenceIds.length} Selected
            </Button>
          )}
        </div>
      )}

      {!sequences || sequences.length === 0 ? (
        <Card className="p-12 text-center">
          <div className="max-w-md mx-auto">
            <h2 className="text-xl font-semibold mb-2">
              {filterProjectId ? 'No sequences in this project' : 'No sequences yet'}
            </h2>
            <p className="text-muted-foreground mb-6">
              {filterProjectId
                ? 'Create your first sequence in this project.'
                : 'Create your first sequence to get started.'}
            </p>
            <Button onClick={() => setIsCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Sequence
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {sequences.map((sequence) => (
            <Card key={sequence.id} className="p-6 relative">
              {/* Checkbox for batch selection */}
              <div className="absolute top-4 left-4">
                <Checkbox
                  checked={selectedSequenceIds.includes(sequence.id)}
                  onCheckedChange={() => toggleSequenceSelection(sequence.id)}
                />
              </div>

              <div className="flex items-start justify-between mb-4 ml-8">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold mb-2">
                    {sequence.name}
                  </h3>
                  <span
                    className={`inline-block px-2 py-1 text-xs rounded-full ${getSequenceTypeBadgeColor(
                      sequence.sequenceType
                    )}`}
                  >
                    {sequence.sequenceType}
                  </span>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDownload(sequence.id)}
                    disabled={downloadSequence.isPending}
                    title="Download"
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setEditingSequenceId(sequence.id)}
                    title="Edit"
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDelete(sequence.id)}
                    disabled={deleteSequence.isPending}
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div className="mb-4">
                <div className="text-xs text-muted-foreground space-y-1">
                  <div>Length: {sequence.length.toLocaleString()} bp</div>
                  {sequence.sequenceType !== 'PROTEIN' && sequence.gcContent !== null && (
                    <div>
                      GC Content: {(sequence.gcContent * 100).toFixed(1)}%
                    </div>
                  )}
                  {sequence.sequenceType === 'PROTEIN' && sequence.molecularWeight !== null && (
                    <div>
                      Molecular Weight: {sequence.molecularWeight.toFixed(2)} Da
                    </div>
                  )}
                  <div className="text-xs text-muted-foreground italic">
                    {sequence.usesFileStorage ? 'Stored in file' : 'Stored in database'}
                  </div>
                </div>
              </div>

              {sequence.description && (
                <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                  {sequence.description}
                </p>
              )}

              <div className="text-xs text-muted-foreground mb-4">
                <div>
                  Project:{' '}
                  {projects?.find((p) => p.id === sequence.projectId)?.name ||
                    `Project #${sequence.projectId}`}
                </div>
                <div className="mt-1">
                  Created {new Date(sequence.createdAt).toLocaleString()}
                </div>
              </div>

              <Button
                variant="outline"
                className="w-full"
                onClick={() => navigate(`/sequences/${sequence.id}`)}
              >
                <Eye className="h-4 w-4 mr-2" />
                View Sequence
              </Button>
            </Card>
          ))}
        </div>
      )}

      <SequenceFormDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        defaultProjectId={filterProjectId}
      />

      <FastaUploadDialog
        open={isUploadDialogOpen}
        onOpenChange={setIsUploadDialogOpen}
        defaultProjectId={filterProjectId}
      />

      {editingSequenceId && (
        <SequenceFormDialog
          open={!!editingSequenceId}
          onOpenChange={(open) => {
            if (!open) setEditingSequenceId(undefined);
          }}
          sequenceId={editingSequenceId}
        />
      )}
      </div>
    </>
  );
}