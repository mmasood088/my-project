import { Link, useLocation } from 'react-router-dom';

function Navigation() {
  const location = useLocation();

  const isActive = (path) => {
    return location.pathname === path;
  };

  const linkClass = (path) => {
    return isActive(path)
      ? 'px-3 py-2 rounded-md text-sm font-medium bg-blue-500 text-white'
      : 'px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-200';
  };

  return (
    <nav className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <span className="text-2xl mr-4">🚀</span>
            <span className="text-xl font-bold text-gray-900">Trading Dashboard</span>
          </div>
          <div className="flex space-x-4">
            <Link to="/" className={linkClass('/')}>
              Dashboard
            </Link>
            <Link to="/signals" className={linkClass('/signals')}>
              Signals
            </Link>
            <Link to="/entries" className={linkClass('/entries')}>
              Entries
            </Link>
            <Link to="/symbols" className={linkClass('/symbols')}>
              Symbols
            </Link>
            <Link to="/settings" className={linkClass('/settings')}>
              Settings
            </Link> 
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navigation;