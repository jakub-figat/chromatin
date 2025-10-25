import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api-client'
import { useAuthStore } from '@/stores/auth-store'
import type { LoginRequest, RegisterRequest, AuthResponse, User } from '@/types/auth'

export function useLogin() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)

  return useMutation({
    mutationFn: async (data: LoginRequest) => {
      // OAuth2PasswordRequestForm expects form-encoded data, not JSON
      const formData = new URLSearchParams()
      formData.append('username', data.username)
      formData.append('password', data.password)

      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Login failed')
      }

      return response.json() as Promise<AuthResponse>
    },
    onSuccess: async (authResponse) => {
      // Fetch user data after login
      const user = await api.get<User>('/auth/me', {
        headers: {
          Authorization: `Bearer ${authResponse.accessToken}`,
        },
      })
      setAuth(user, authResponse.accessToken)
      navigate('/')
    },
  })
}

export function useRegister() {
  const navigate = useNavigate()

  return useMutation({
    mutationFn: (data: RegisterRequest) =>
      api.post<User>('/auth/register', data),
    onSuccess: () => {
      navigate('/login')
    },
  })
}

export function useLogout() {
  const navigate = useNavigate()
  const clearAuth = useAuthStore((state) => state.clearAuth)

  return () => {
    clearAuth()
    navigate('/login')
  }
}