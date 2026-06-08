import { NavLink, Outlet } from "react-router-dom"
import { LayoutDashboard, FilePlus2, Settings, LogOut, Scale } from "lucide-react"

import { useAuthStore } from "@/store/authStore"
import { cn } from "@/lib/utils"

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/cases/new", label: "New case", icon: FilePlus2 },
  { to: "/settings/notifications", label: "Settings", icon: Settings },
]

export function AppLayout() {
  const signOut = useAuthStore((s) => s.signOut)

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 flex-col border-r border-border bg-card px-4 py-6">
        <div className="mb-8 flex items-center gap-2 px-2">
          <Scale className="h-6 w-6 text-primary" />
          <span className="text-lg font-semibold">DepositShield</span>
        </div>

        <nav className="flex flex-1 flex-col gap-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <button
          onClick={() => signOut()}
          className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
