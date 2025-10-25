import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { api } from '@/lib/api-client';
import type { Project } from '@/types/project';

interface CreateProjectInput {
  name: string;
  description?: string;
  isPublic?: boolean;
}

interface UpdateProjectInput {
  name?: string;
  description?: string;
  isPublic?: boolean;
}

// Fetch all projects for the current user
export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const data = await api.get<Project[]>('/projects/');
      return data;
    },
  });
}

// Fetch a single project by ID
export function useProject(projectId: number | undefined) {
  return useQuery({
    queryKey: ['projects', projectId],
    queryFn: async () => {
      if (!projectId) throw new Error('Project ID is required');
      const data = await api.get<Project>(`/projects/${projectId}`);
      return data;
    },
    enabled: !!projectId,
  });
}

// Create a new project
export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: CreateProjectInput) => {
      const data = await api.post<Project>('/projects/', input);
      return data;
    },
    onSuccess: () => {
      // Invalidate projects list to refetch
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      toast.success('Project created successfully!');
    },
    onError: (error: any) => {
      const message = error?.message || 'Failed to create project';
      toast.error(message);
    },
  });
}

// Update an existing project
export function useUpdateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: UpdateProjectInput;
    }) => {
      const result = await api.patch<Project>(
        `/projects/${id}`,
        data
      );
      return result;
    },
    onSuccess: (_, variables) => {
      // Invalidate both the projects list and the specific project
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['projects', variables.id] });
      toast.success('Project updated successfully!');
    },
    onError: (error: any) => {
      const message = error?.message || 'Failed to update project';
      toast.error(message);
    },
  });
}

// Delete a project
export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/projects/${id}`);
    },
    onSuccess: () => {
      // Invalidate projects list to refetch
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      toast.success('Project deleted successfully!');
    },
    onError: (error: any) => {
      const message = error?.message || 'Failed to delete project';
      toast.error(message);
    },
  });
}