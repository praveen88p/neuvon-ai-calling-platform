import { 
  LayoutDashboard, 
  Bot,
  Megaphone, 
  Upload, 
  Radio, 
  History, 
  BarChart3, 
  Calendar,
  Settings,
  Phone,
  LogOut,
  Shield,
  FileText,
} from "lucide-react";
import { NavLink } from "@/components/NavLink";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
  useSidebar,
  SidebarHeader,
} from "@/components/ui/sidebar";
 

const mainItems = [
  { title: "Dashboard", url: "/", icon: LayoutDashboard },
  { title: "Agents", url: "/agents", icon: Bot },
  { title: "Campaigns", url: "/campaigns", icon: Megaphone },
  { title: "Upload Leads", url: "/upload", icon: Upload },
  { title: "Live Calls", url: "/live-calls", icon: Radio },
  { title: "Call History", url: "/call-history", icon: History },
  { title: "Analytics", url: "/analytics", icon: BarChart3 },
  { title: "Appointments", url: "/appointments", icon: Calendar },
  { title: "Phone Numbers", url: "/phone-numbers", icon: Phone },
  { title: "Settings", url: "/settings", icon: Settings },
];

const adminItems = [
  { title: "Audit Trail", url: "/admin/audit", icon: Shield },
  { title: "System Logs", url: "/admin/logs", icon: FileText },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const currentPath = location.pathname;
  const collapsed = state === "collapsed";

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const isActive = (path: string) => {
    if (path === "/") return currentPath === "/";
    return currentPath.startsWith(path);
  };

  // Show admin items only for platform_admin and owner roles
  const showAdmin = user?.role === "platform_admin" || user?.role === "owner";

  return (
    <Sidebar className={collapsed ? "w-16" : "w-64"} collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border px-3 py-3">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary shadow-sm">
              <Phone className="h-4 w-4 text-primary-foreground" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-semibold leading-5 text-sidebar-foreground">Neuvon</span>
              <span className="text-[11px] leading-4 text-muted-foreground">AI Calling Platform</span>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary shadow-sm mx-auto">
            <Phone className="h-4 w-4 text-primary-foreground" />
          </div>
        )}
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className={collapsed ? "sr-only" : ""}>Main</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    tooltip={item.title}
                    isActive={isActive(item.url)}
                    className={collapsed ? "justify-center" : ""}
                  >
                    <NavLink
                      to={item.url}
                      end={item.url === "/"}
                      className={
                        "flex w-full items-center gap-2 rounded-md px-2 py-2 transition-colors focus-visible:outline-none"
                      }
                    >
                      <item.icon className="h-4 w-4" />
                      {!collapsed && <span className="truncate">{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Admin Section — role-gated */}
        {showAdmin && (
          <SidebarGroup>
            <SidebarGroupLabel className={collapsed ? "sr-only" : ""}>Admin</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {adminItems.map((item) => (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      tooltip={item.title}
                      isActive={isActive(item.url)}
                      className={collapsed ? "justify-center" : ""}
                    >
                      <NavLink
                        to={item.url}
                        className={
                          "flex w-full items-center gap-2 rounded-md px-2 py-2 transition-colors focus-visible:outline-none"
                        }
                      >
                        <item.icon className="h-4 w-4" />
                        {!collapsed && <span className="truncate">{item.title}</span>}
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <div className="mt-auto border-t border-sidebar-border px-3 py-3">
        {!collapsed && user && (
          <div className="mb-2 rounded-lg bg-sidebar-accent/30 px-2 py-2">
            <p className="text-xs font-medium text-sidebar-foreground truncate">{user.full_name}</p>
            <p className="text-[11px] text-muted-foreground truncate">{user.email}</p>
          </div>
        )}
        <div className={collapsed ? "flex items-center justify-center gap-2" : "flex items-center justify-between"}>
          <SidebarTrigger />
          <Button
            variant="ghost"
            size="icon"
            onClick={handleLogout}
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
            title="Logout"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </Sidebar>
  );
}
