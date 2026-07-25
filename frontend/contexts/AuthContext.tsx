"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { User } from "@supabase/supabase-js";
import { listProjects, type Project, uniqueProjects } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  projects: Project[];
  activeProject: Project | null;
  refreshProjects: () => Promise<void>;
  setActiveProjectId: (projectId: string) => void;
  can: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  projects: [],
  activeProject: null,
  refreshProjects: async () => {},
  setActiveProjectId: () => {},
  can: () => false,
});

export const useAuth = () => useContext(AuthContext);

const publicRoutes = ["/login", "/signup", "/forgot-password"];

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  const setActiveProjectId = (projectId: string) => {
    localStorage.setItem("recallai_active_project_id", projectId);
    setActiveProject(projects.find((project) => project.id === projectId) ?? null);
    window.dispatchEvent(new Event("recallai:project-changed"));
    window.dispatchEvent(new Event("recallai:files-changed"));
  };

  const refreshProjects = async () => {
    try {
      const data = uniqueProjects(await listProjects());
      setProjects(() => data);
      const storedId = localStorage.getItem("recallai_active_project_id");
      const selected = data.find((project) => project.id === storedId) ?? data[0] ?? null;
      if (selected) localStorage.setItem("recallai_active_project_id", selected.id);
      setActiveProject(selected);
    } catch {
      setProjects([]);
      setActiveProject(null);
    }
  };

  const can = (permission: string) => activeProject?.permissions.includes(permission) ?? false;

  useEffect(() => {
    const checkUser = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setUser(session?.user ?? null);
      if (session?.user) {
        await refreshProjects();
      } else {
        setProjects([]);
        setActiveProject(null);
      }
      setLoading(false);

      if (!session?.user && !publicRoutes.includes(pathname)) {
        router.push("/login");
      }
    };

    checkUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) {
        refreshProjects();
      } else {
        setProjects([]);
        setActiveProject(null);
        localStorage.removeItem("recallai_active_project_id");
      }
      
      if (!session?.user && !publicRoutes.includes(pathname)) {
        router.push("/login");
      } else if (session?.user && publicRoutes.includes(pathname)) {
        router.push("/");
      }
    });

    return () => subscription.unsubscribe();
  }, [pathname, router]);

  return (
    <AuthContext.Provider value={{ user, loading, projects, activeProject, refreshProjects, setActiveProjectId, can }}>
      {loading ? (
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-orange-500 border-t-transparent"></div>
        </div>
      ) : (
        children
      )}
    </AuthContext.Provider>
  );
}
