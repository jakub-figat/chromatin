import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Upload } from 'lucide-react';
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
import { useUploadFasta } from '@/hooks/use-sequences';
import { useProjects } from '@/hooks/use-projects';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ACCEPTED_FILE_TYPES = ['.fasta', '.fa', '.fna', '.ffn', '.faa', '.frn'];

const uploadSchema = z.object({
  projectId: z.number({
    required_error: 'Project is required',
    invalid_type_error: 'Project is required',
  }),
  sequenceType: z.enum(['DNA', 'RNA', 'PROTEIN']).optional(),
  file: z
    .instanceof(File, { message: 'Please select a file' })
    .refine((file) => file.size > 0, 'File cannot be empty')
    .refine(
      (file) => file.size <= MAX_FILE_SIZE,
      'File size must be less than 10MB'
    )
    .refine((file) => {
      const extension = '.' + file.name.split('.').pop()?.toLowerCase();
      return ACCEPTED_FILE_TYPES.includes(extension);
    }, 'File must be a FASTA file (.fasta, .fa, .fna, .ffn, .faa, .frn)'),
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
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
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
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      setValue('file', file, { shouldValidate: true });
    }
  };

  const onSubmit = async (data: UploadFormData) => {
    try {
      await uploadFasta.mutateAsync({
        file: data.file,
        projectId: data.projectId,
        sequenceType: data.sequenceType,
      });
      onOpenChange(false);
      reset();
      setSelectedFile(null);
    } catch (error) {
      console.error('Failed to upload FASTA file:', error);
    }
  };

  const handleClose = () => {
    onOpenChange(false);
    reset();
    setSelectedFile(null);
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
            <Label htmlFor="file">FASTA File *</Label>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => document.getElementById('file-input')?.click()}
                disabled={isSubmitting}
              >
                <Upload className="h-4 w-4 mr-2" />
                {selectedFile ? selectedFile.name : 'Choose File'}
              </Button>
              <input
                id="file-input"
                type="file"
                accept={ACCEPTED_FILE_TYPES.join(',')}
                onChange={handleFileChange}
                className="hidden"
                disabled={isSubmitting}
              />
            </div>
            {errors.file && (
              <p className="text-sm text-red-500">{errors.file.message as string}</p>
            )}
            {selectedFile && !errors.file && (
              <p className="text-xs text-muted-foreground">
                Size: {(selectedFile.size / 1024).toFixed(2)} KB
              </p>
            )}
          </div>

          <div className="bg-muted p-3 rounded-md text-sm">
            <p className="font-medium mb-1">Accepted formats:</p>
            <ul className="list-disc list-inside text-muted-foreground space-y-1">
              <li>FASTA files (.fasta, .fa, .fna, .ffn, .faa, .frn)</li>
              <li>Maximum file size: 10MB</li>
              <li>Multiple sequences per file supported</li>
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