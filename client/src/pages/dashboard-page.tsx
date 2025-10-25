import { useAuthStore } from '@/stores/auth-store'
import { Link } from 'react-router-dom'
import { Navbar } from '@/components/navbar'

export function DashboardPage() {
  const user = useAuthStore((state) => state.user)

  return (
    <>
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          <div>
            <h2 className="text-3xl font-bold">Welcome back, {user?.username}!</h2>
            <p className="text-muted-foreground">
              Manage your biological sequences and projects
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Link
              to="/projects"
              className="rounded-lg border p-6 hover:bg-accent transition-colors"
            >
              <h3 className="text-xl font-semibold">Projects</h3>
              <p className="text-sm text-muted-foreground">
                Organize your work into projects
              </p>
            </Link>
            <Link
              to="/sequences"
              className="rounded-lg border p-6 hover:bg-accent transition-colors"
            >
              <h3 className="text-xl font-semibold">Sequences</h3>
              <p className="text-sm text-muted-foreground">
                View and manage your biological sequences
              </p>
            </Link>
          </div>
        </div>
      </main>
    </>
  )
}