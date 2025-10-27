import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { api } from '@/lib/api-client';
import { useAuthStore } from '@/stores/auth-store'
import type { SequenceListItem, SequenceDetail, SequenceInput, FastaUploadOutput } from '@/types/sequence';

// Fetch all sequences for the current user, optionally filtered by project
export function useSequences(skip: number = 0, limit: number = 100, projectId?: number) {
  return useQuery({
    queryKey: ['sequences', skip, limit, projectId],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('skip', skip.toString());
      params.append('limit', limit.toString());
      if (projectId !== undefined) {
        params.append('project_id', projectId.toString());
      }
      const data = await api.get<SequenceListItem[]>(`/sequences/?${params.toString()}`);
      return data;
    },
  });
}

// Fetch a single sequence by ID (includes sequence data)
export function useSequence(sequenceId: number | undefined) {
  return useQuery({
    queryKey: ['sequences', sequenceId],
    queryFn: async () => {
      if (!sequenceId) throw new Error('Sequence ID is required');
      const data = await api.get<SequenceDetail>(`/sequences/${sequenceId}`);
      return data;
    },
    enabled: !!sequenceId,
  });
}

// Create a new sequence
export function useCreateSequence() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: SequenceInput) => {
      const data = await api.post<SequenceDetail>('/sequences/', input);
      return data;
    },
    onSuccess: () => {
      // Invalidate sequences list to refetch
      queryClient.invalidateQueries({ queryKey: ['sequences'] });
      toast.success('Sequence created successfully!');
    },
    onError: (error: any) => {
      const message = error?.message || 'Failed to create sequence';
      toast.error(message);
    },
  });
}

// Update an existing sequence
export function useUpdateSequence() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: SequenceInput;
    }) => {
      const result = await api.patch<SequenceDetail>(
        `/sequences/${id}`,
        data
      );
      return result;
    },
    onSuccess: (_, variables) => {
      // Invalidate both the sequences list and the specific sequence
      queryClient.invalidateQueries({ queryKey: ['sequences'] });
      queryClient.invalidateQueries({ queryKey: ['sequences', variables.id] });
      toast.success('Sequence updated successfully!');
    },
    onError: (error: any) => {
      const message = error?.message || 'Failed to update sequence';
      toast.error(message);
    },
  });
}

// Delete a sequence
export function useDeleteSequence() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/sequences/${id}`);
    },
    onSuccess: () => {
      // Invalidate sequences list to refetch
      queryClient.invalidateQueries({ queryKey: ['sequences'] });
      toast.success('Sequence deleted successfully!');
    },
    onError: (error: any) => {
      const message = error?.message || 'Failed to delete sequence';
      toast.error(message);
    },
  });
}

// Upload FASTA file(s)
export function useUploadFasta() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      files,
      projectId,
      sequenceType,
    }: {
      files: File[];
      projectId: number;
      sequenceType?: string;
    }) => {
      const formData = new FormData();
      // Append all files with the same key 'files'
      files.forEach((file) => {
        formData.append('files', file);
      });
      formData.append('project_id', projectId.toString());
      if (sequenceType) {
        formData.append('sequence_type', sequenceType);
      }

      // Use fetch directly for file upload since we need FormData
      const { token } = useAuthStore.getState()
      const response = await fetch('/api/sequences/upload/fasta', {
        method: 'POST',
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to upload FASTA file');
      }

      return response.json() as Promise<FastaUploadOutput>;
    },
    onSuccess: (data) => {
      // Invalidate sequences list to refetch
      queryClient.invalidateQueries({ queryKey: ['sequences'] });
      toast.success(`Successfully uploaded ${data.sequencesCreated} sequence(s)!`);
    },
    onError: (error: any) => {
      const message = error?.message || 'Failed to upload FASTA file';
      toast.error(message);
    },
  });
}

// Download single sequence as FASTA
export function useDownloadSequence() {
  return useMutation({
    mutationFn: async (sequenceId: number) => {
      const { token } = useAuthStore.getState();
      const response = await fetch(`/api/sequences/${sequenceId}/download`, {
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
      });

      if (!response.ok) {
        throw new Error('Failed to download sequence');
      }

      const blob = await response.blob();
      const filename = `sequence_${sequenceId}.fasta`;

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
    onSuccess: () => {
      toast.success('Sequence downloaded successfully!');
    },
    onError: (error: any) => {
      const message = error?.message || 'Failed to download sequence';
      toast.error(message);
    },
  });
}

// Download multiple sequences as single FASTA
export function useDownloadBatch() {
  return useMutation({
    mutationFn: async (sequenceIds: number[]) => {
      const { token } = useAuthStore.getState();
      const response = await fetch('/api/sequences/download/batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify({ sequenceIds }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to download sequences');
      }

      const blob = await response.blob();
      const filename = `sequences_batch_${sequenceIds.length}.fasta`;

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
    onSuccess: (_, sequenceIds) => {
      toast.success(`${sequenceIds.length} sequence(s) downloaded successfully!`);
    },
    onError: (error: any) => {
      const message = error?.message || 'Failed to download sequences';
      toast.error(message);
    },
  });
}