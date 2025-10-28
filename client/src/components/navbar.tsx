import { Link, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { LogOut, Dna } from 'lucide-react';
import { useLogout } from '@/hooks/use-auth';
import { useAuthStore } from '@/stores/auth-store';

export function Navbar() {
  const location = useLocation();
  const logout = useLogout();
  const user = useAuthStore((state) => state.user);

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  const handleLogout = () => {
    logout.mutate();
  };

  return (
    <header className="border-b bg-background sticky top-0 z-50">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2 font-bold text-xl">
            <Dna className="h-6 w-6" />
            <span>Chromatin</span>
          </Link>

          <nav className="flex items-center gap-1">
            <Link to="/">
              <Button
                variant={isActive('/') ? 'secondary' : 'ghost'}
                size="sm"
              >
                Dashboard
              </Button>
            </Link>
            <Link to="/projects">
              <Button
                variant={isActive('/projects') ? 'secondary' : 'ghost'}
                size="sm"
              >
                Projects
              </Button>
            </Link>
            <Link to="/sequences">
              <Button
                variant={isActive('/sequences') ? 'secondary' : 'ghost'}
                size="sm"
              >
                Sequences
              </Button>
            </Link>
            <Link to="/jobs">
              <Button
                variant={isActive('/jobs') ? 'secondary' : 'ghost'}
                size="sm"
              >
                Jobs
              </Button>
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-4">
          {user && (
            <span className="text-sm text-muted-foreground">
              {user.email}
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            disabled={logout.isPending}
          >
            <LogOut className="h-4 w-4 mr-2" />
            {logout.isPending ? 'Logging out...' : 'Logout'}
          </Button>
        </div>
      </div>
    </header>
  );
}