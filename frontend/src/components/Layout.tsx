import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b border-[hsl(var(--border))] px-6 py-3">
        <div className="flex items-center gap-6">
          <span className="font-semibold">Insights Picker</span>
          <nav className="flex gap-4 text-sm">
            <Link to="/upload" className="hover:underline">
              Upload
            </Link>
            <Link to="/dashboard" className="hover:underline">
              Dashboard
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-[hsl(var(--muted-foreground))]">{user?.shop_name}</span>
          <Button variant="outline" onClick={handleLogout}>
            Log out
          </Button>
        </div>
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
