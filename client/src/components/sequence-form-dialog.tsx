import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useCreateSequence, useUpdateSequence } from '@/hooks/use-sequences';
import { useProjects } from '@/hooks/use-projects';
import { isValidSequence, getSequenceValidationError, getAllowedChars } from '@/lib/sequence-validation';
import type { Sequence } from '@/types/sequence';

const sequenceSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255, 'Name too long'),
  sequenceData: z.string().min(1, 'Sequence data is required'),
  sequenceType: z.enum(['DNA', 'RNA', 'PROTEIN'], {
    required_error: 'Sequence type is required',
  }),
  description: z.string().max(255, 'Description too long').optional(),
  projectId: z.number("Project is required"),
}).superRefine((data, ctx) => {
  if (!isValidSequence(data.sequenceData, data.sequenceType)) {
    ctx.addIssue({
      code: "custom", 
      message: getSequenceValidationError(data.sequenceType),
      path: ["sequenceData"],
    });
  }

});

type SequenceFormData = z.infer<typeof sequenceSchema>;

interface SequenceFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sequence?: Sequence;
  defaultProjectId?: number;
}

export function SequenceFormDialog({
  open,
  onOpenChange,
  sequence,
  defaultProjectId,
}: SequenceFormDialogProps) {
  const isEditing = !!sequence;
  const createSequence = useCreateSequence();
  const updateSequence = useUpdateSequence();
  const { data: projects } = useProjects();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
    watch,
    setValue,
  } = useForm<SequenceFormData>({
    resolver: zodResolver(sequenceSchema),
    defaultValues: {
      name: sequence?.name || '',
      sequenceData: sequence?.sequenceData || '',
      sequenceType: sequence?.sequenceType || 'DNA',
      description: sequence?.description || '',
      projectId: sequence?.projectId || defaultProjectId,
    },
  });

  const sequenceType = watch('sequenceType');
  const projectId = watch('projectId');

  const onSubmit = async (data: SequenceFormData) => {
    try {
      if (isEditing) {
        await updateSequence.mutateAsync({
          id: sequence.id,
          data,
        });
      } else {
        await createSequence.mutateAsync(data);
      }
      onOpenChange(false);
      reset();
    } catch (error) {
      console.error('Failed to save sequence:', error);
    }
  };

  const handleClose = () => {
    onOpenChange(false);
    reset();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edit Sequence' : 'Create New Sequence'}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              {...register('name')}
              placeholder="my_sequence"
              disabled={isSubmitting}
            />
            {errors.name && (
              <p className="text-sm text-red-500">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="sequenceType">Sequence Type *</Label>
            <Select
              value={sequenceType}
              onValueChange={(value) =>
                setValue('sequenceType', value as 'DNA' | 'RNA' | 'PROTEIN')
              }
              disabled={isSubmitting}
            >
              <SelectTrigger id="sequenceType">
                <SelectValue placeholder="Select sequence type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="DNA">DNA</SelectItem>
                <SelectItem value="RNA">RNA</SelectItem>
                <SelectItem value="PROTEIN">Protein</SelectItem>
              </SelectContent>
            </Select>
            {errors.sequenceType && (
              <p className="text-sm text-red-500">
                {errors.sequenceType.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="sequenceData">Sequence Data *</Label>
            <Textarea
              id="sequenceData"
              {...register('sequenceData')}
              placeholder="ATGCATGC..."
              className="font-mono text-sm"
              rows={6}
              disabled={isSubmitting}
            />
            {errors.sequenceData && (
              <p className="text-sm text-red-500">
                {errors.sequenceData.message}
              </p>
            )}
            {!errors.sequenceData && (
              <p className="text-xs text-muted-foreground">
                Allowed characters: {getAllowedChars(sequenceType)}
              </p>
            )}
          </div>

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
              <p className="text-sm text-red-500">
                {errors.projectId.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="A brief description of the sequence..."
              disabled={isSubmitting}
            />
            {errors.description && (
              <p className="text-sm text-red-500">
                {errors.description.message}
              </p>
            )}
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
              {isSubmitting
                ? isEditing
                  ? 'Updating...'
                  : 'Creating...'
                : isEditing
                  ? 'Update Sequence'
                  : 'Create Sequence'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}