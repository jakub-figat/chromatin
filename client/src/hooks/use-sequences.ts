import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api-client';
import type { Sequence, SequenceInput, FastaUploadOutput } from '@/types/sequence';

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
      const data = await api.get<Sequence[]>(`/sequences/?${params.toString()}`);
      return data;
    },
  });
}

// Fetch a single sequence by ID
export function useSequence(sequenceId: number | undefined) {
  return useQuery({
    queryKey: ['sequences', sequenceId],
    queryFn: async () => {
      if (!sequenceId) throw new Error('Sequence ID is required');
      const data = await api.get<Sequence>(`/sequences/${sequenceId}`);
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
      const data = await api.post<Sequence>('/sequences/', input);
      return data;
    },
    onSuccess: () => {
      // Invalidate sequences list to refetch
      queryClient.invalidateQueries({ queryKey: ['sequences'] });
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
      const result = await api.patch<Sequence>(
        `/sequences/${id}`,
        data
      );
      return result;
    },
    onSuccess: (_, variables) => {
      // Invalidate both the sequences list and the specific sequence
      queryClient.invalidateQueries({ queryKey: ['sequences'] });
      queryClient.invalidateQueries({ queryKey: ['sequences', variables.id] });
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
    },
  });
}

// Upload FASTA file
export function useUploadFasta() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      file,
      projectId,
      sequenceType,
    }: {
      file: File;
      projectId: number;
      sequenceType?: string;
    }) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('project_id', projectId.toString());
      if (sequenceType) {
        formData.append('sequence_type', sequenceType);
      }

      // Use fetch directly for file upload since we need FormData
      const token = localStorage.getItem('token');
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
    onSuccess: () => {
      // Invalidate sequences list to refetch
      queryClient.invalidateQueries({ queryKey: ['sequences'] });
    },
  });
}