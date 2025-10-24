export interface User {
  id: number
  email: string
  username: string
  isSuperuser: boolean
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
}

export interface AuthResponse {
  accessToken: string
  tokenType: string
}