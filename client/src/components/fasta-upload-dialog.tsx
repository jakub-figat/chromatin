import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Upload, X, AlertCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useUploadFasta } from '@/hooks/use-sequences';
import { useProjects } from '@/hooks/use-projects';

const MEGABYTE = 1024 * 1024;
const MAX_FILE_SIZE = 100 * MEGABYTE; // 100MB per file
const MAX_TOTAL_SIZE = 500 * MEGABYTE; // 500MB total
const ACCEPTED_FILE_TYPES = ['.fasta', '.fa', '.fna', '.ffn', '.faa', '.frn'];

const uploadSchema = z.object({
  projectId: z.number({
    required_error: 'Project is required',
    invalid_type_error: 'Project is required',
  }),
  sequenceType: z.enum(['DNA', 'RNA', 'PROTEIN']).optional(),
  files: z
    .array(z.instanceof(File))
    .min(1, 'Please select at least one file')
    .refine((files) => files.every((file) => file.size > 0), 'Files cannot be empty')
    .refine(
      (files) => files.every((file) => file.size <= MAX_FILE_SIZE),
      'Each file must be less than 100MB'
    )
    .refine(
      (files) => files.reduce((sum, file) => sum + file.size, 0) <= MAX_TOTAL_SIZE,
      'Total upload size must be less than 500MB'
    )
    .refine((files) => {
      return files.every((file) => {
        const extension = '.' + file.name.split('.').pop()?.toLowerCase();
        return ACCEPTED_FILE_TYPES.includes(extension);
      });
    }, 'All files must be FASTA files (.fasta, .fa, .fna, .ffn, .faa, .frn)'),
});

type UploadFormData = z.infer<typeof uploadSchema>;

interface FastaUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultProjectId?: number;
}

export function FastaUploadDialog({
  open,
  onOpenChange,
  defaultProjectId,
}: FastaUploadDialogProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const uploadFasta = useUploadFasta();
  const { data: projects } = useProjects();

  const {
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
    watch,
    setValue,
  } = useForm<UploadFormData>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      projectId: defaultProjectId,
      sequenceType: undefined,
    },
  });

  const projectId = watch('projectId');
  const sequenceType = watch('sequenceType');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setSelectedFiles(files);
      setValue('files', files, { shouldValidate: true });
    }
  };

  const removeFile = (index: number) => {
    const newFiles = selectedFiles.filter((_, i) => i !== index);
    setSelectedFiles(newFiles);
    setValue('files', newFiles, { shouldValidate: true });
  };

  const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);

  const onSubmit = async (data: UploadFormData) => {
    try {
      await uploadFasta.mutateAsync({
        files: data.files,
        projectId: data.projectId,
        sequenceType: data.sequenceType,
      });
      onOpenChange(false);
      reset();
      setSelectedFiles([]);
    } catch (error) {
      console.error('Failed to upload FASTA file:', error);
    }
  };

  const handleClose = () => {
    onOpenChange(false);
    reset();
    setSelectedFiles([]);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Upload FASTA File</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="projectId">Project *</Label>
            <Select
              value={projectId?.toString()}
              onValueChange={(value) => setValue('projectId', parseInt(value))}
              disabled={isSubmitting}
            >
              <SelectTrigger id="projectId">
                <SelectValue placeholder="Select project" />
              </SelectTrigger>
              <SelectContent>
                {projects?.map((project) => (
                  <SelectItem key={project.id} value={project.id.toString()}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.projectId && (
              <p className="text-sm text-red-500">{errors.projectId.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="sequenceType">Sequence Type (Optional)</Label>
            <Select
              value={sequenceType || 'auto'}
              onValueChange={(value) =>
                setValue(
                  'sequenceType',
                  value === 'auto' ? undefined : (value as 'DNA' | 'RNA' | 'PROTEIN')
                )
              }
              disabled={isSubmitting}
            >
              <SelectTrigger id="sequenceType">
                <SelectValue placeholder="Auto-detect" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">Auto-detect</SelectItem>
                <SelectItem value="DNA">DNA</SelectItem>
                <SelectItem value="RNA">RNA</SelectItem>
                <SelectItem value="PROTEIN">Protein</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Leave as auto-detect to automatically determine sequence type
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="files">FASTA Files *</Label>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => document.getElementById('file-input')?.click()}
                disabled={isSubmitting}
              >
                <Upload className="h-4 w-4 mr-2" />
                {selectedFiles.length > 0
                  ? `${selectedFiles.length} file(s) selected`
                  : 'Choose Files'}
              </Button>
              <input
                id="file-input"
                type="file"
                accept={ACCEPTED_FILE_TYPES.join(',')}
                onChange={handleFileChange}
                className="hidden"
                disabled={isSubmitting}
                multiple
              />
            </div>
            {errors.files && (
              <p className="text-sm text-red-500">{errors.files.message as string}</p>
            )}

            {selectedFiles.length > 0 && !errors.files && (
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {selectedFiles.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between bg-muted p-2 rounded text-sm"
                  >
                    <span className="truncate flex-1">{file.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {(file.size / 1024).toFixed(2)} KB
                      </span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0"
                        onClick={() => removeFile(index)}
                        disabled={isSubmitting}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
                <p className="text-xs text-muted-foreground">
                  Total size: {(totalSize / MEGABYTE).toFixed(2)} MB
                </p>
              </div>
            )}
          </div>

          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="text-sm">
              <strong>Note:</strong> If sequences with the same name already exist, they will be overwritten with the new data.
            </AlertDescription>
          </Alert>

          <div className="bg-muted p-3 rounded-md text-sm">
            <p className="font-medium mb-1">Accepted formats:</p>
            <ul className="list-disc list-inside text-muted-foreground space-y-1">
              <li>FASTA files (.fasta, .fa, .fna, .ffn, .faa, .frn)</li>
              <li>Maximum file size: 100MB per file</li>
              <li>Maximum total size: 500MB</li>
              <li>Multiple files and sequences per file supported</li>
            </ul>
          </div>

          <div className="flex justify-end space-x-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Uploading...' : 'Upload'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}