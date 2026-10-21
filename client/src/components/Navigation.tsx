import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from './ui/button';
import { useAuth } from '../contexts/AuthContext';
import { 
  Home,
  Building,
  FileText,
  Users,
  User,
  LogOut,
  ChevronDown,
  BarChart3
} from 'lucide-react';
import { useState } from 'react';

export default function Navigation() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, signOut } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const isActive = (path: string) => {
    if (path === '/' && location.pathname === '/') return true;
    if (path !== '/' && location.pathname.startsWith(path)) return true;
    return false;
  };

  const handleSignOut = async () => {
    const { error } = await signOut();
    if (!error) {
      navigate('/login');
    }
  };

  return (
    <div className="border-b bg-white">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between py-3">
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2">
              <Building className="w-6 h-6 text-blue-600" />
              <span className="font-bold text-lg">TLD Platform</span>
            </div>
            
            <nav className="flex items-center space-x-1">
              <Button
                variant={isActive('/') ? 'default' : 'ghost'}
                size="sm"
                onClick={() => navigate('/')}
                className="flex items-center space-x-2"
              >
                <Home className="w-4 h-4" />
                <span>Dashboard</span>
              </Button>
              
              <Button
                variant={isActive('/applicants') ? 'default' : 'ghost'}
                size="sm"
                onClick={() => navigate('/applicants')}
                className="flex items-center space-x-2"
              >
                <Users className="w-4 h-4" />
                <span>Applicants</span>
              </Button>
              
              <Button
                variant={isActive('/applications') ? 'default' : 'ghost'}
                size="sm"
                onClick={() => navigate('/applications')}
                className="flex items-center space-x-2"
              >
                <FileText className="w-4 h-4" />
                <span>Applications</span>
              </Button>
              
              <Button
                variant={isActive('/scoreboard') ? 'default' : 'ghost'}
                size="sm"
                onClick={() => navigate('/scoreboard')}
                className="flex items-center space-x-2"
              >
                <BarChart3 className="w-4 h-4" />
                <span>Scoreboard</span>
              </Button>
            </nav>
          </div>

          <div className="flex items-center space-x-4">
            <span className="text-sm text-muted-foreground hidden md:block">
              gTLD Application Management
            </span>
            
            {user && (
              <div className="relative">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center space-x-2"
                >
                  <User className="w-4 h-4" />
                  <span className="hidden sm:block">{user.email}</span>
                  <ChevronDown className="w-4 h-4" />
                </Button>
                
                {showUserMenu && (
                  <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-200 rounded-md shadow-lg z-50">
                    <div className="py-1">
                      <div className="px-4 py-2 text-sm text-gray-700 border-b">
                        <div className="font-medium">{user.email}</div>
                        <div className="text-xs text-gray-500">Signed in</div>
                      </div>
                      <button
                        onClick={handleSignOut}
                        className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                      >
                        <LogOut className="w-4 h-4 mr-2" />
                        Sign Out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}