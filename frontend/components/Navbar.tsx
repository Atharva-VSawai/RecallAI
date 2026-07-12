"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Home, Activity, Search, LogIn, LogOut, Menu, X, Network } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { checkHealth } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui/button";

export default function Navbar() {
  const path = usePathname();
  const router = useRouter();
  const { user } = useAuth();
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const checkApiHealth = async () => {
      const isHealthy = await checkHealth();
      setHealthy(isHealthy);
    };
    
    checkApiHealth();
    const interval = setInterval(checkApiHealth, 10000);

    return () => clearInterval(interval);
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  const links = [
    { href: "/", label: "Home", icon: Home },
    { href: "/query", label: "Query", icon: Search },
    { href: "/graph", label: "Graph", icon: Network },
    { href: "/activity", label: "Activity", icon: Activity },
  ];

  return (
    <nav className="relative z-50 border-b border-white/10 backdrop-blur-md shadow-sm">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="flex items-center gap-2">
              <img 
                src="/logo2.png" 
                alt="Recall.AI" 
                className="h-10 w-auto object-contain"
              />
              <img 
                src="/logo1.png" 
                alt="Recall.AI" 
                className="h-8 w-auto object-contain"
              />
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-1">
            {links.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-all ${
                  path === href 
                    ? "bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-md" 
                    : "text-gray-700 hover:bg-blue-50 hover:text-blue-600"
                }`}
              >
                <Icon size={16} />
                {label}
              </Link>
            ))}
          </div>

          {/* Right Section */}
          <div className="hidden md:flex items-center gap-3">
            {/* API Status */}
            <motion.div 
              whileHover={{ scale: 1.05 }}
              onClick={async () => {
                setHealthy(null);
                const isHealthy = await checkHealth();
                setHealthy(isHealthy);
              }} 
              className="flex items-center gap-2 px-3 py-2 rounded-full bg-white border border-blue-200 cursor-pointer transition-all hover:border-blue-300 shadow-sm"
              title="Click to refresh API status"
            >
              <motion.span
                animate={healthy ? { scale: [1, 1.2, 1] } : {}}
                transition={{ duration: 2, repeat: Infinity }}
                className={`w-2 h-2 rounded-full ${
                  healthy === null
                    ? "bg-yellow-500"
                    : healthy
                    ? "bg-green-500"
                    : "bg-red-500"
                }`}
              />
              <span className="text-xs font-semibold text-gray-700">
                {healthy === null ? "Checking..." : healthy ? "API Online" : "API Offline"}
              </span>
            </motion.div>

            {/* Auth Button */}
            {user ? (
              <Button
                onClick={handleLogout}
                size="sm"
                variant="outline"
                className="gap-2"
              >
                <LogOut size={16} />
                Logout
              </Button>
            ) : (
              <Button
                asChild
                size="sm"
                className="gap-2"
              >
                <Link href="/login">
                  <LogIn size={16} />
                  Login
                </Link>
              </Button>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-lg hover:bg-blue-50 transition-colors"
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden border-t border-blue-200 py-4 space-y-2"
            >
              {links.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-semibold transition-all ${
                    path === href 
                      ? "bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-md" 
                      : "text-gray-700 hover:bg-blue-50"
                  }`}
                >
                  <Icon size={18} />
                  {label}
                </Link>
              ))}
              
              <div className="pt-2 border-t border-blue-200 space-y-2">
                <div className="flex items-center gap-2 px-4 py-2">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      healthy === null
                        ? "bg-yellow-500"
                        : healthy
                        ? "bg-green-500"
                        : "bg-red-500"
                    }`}
                  />
                  <span className="text-xs font-semibold text-gray-700">
                    {healthy === null ? "Checking..." : healthy ? "API Online" : "API Offline"}
                  </span>
                </div>

                {user ? (
                  <button
                    onClick={() => {
                      handleLogout();
                      setMobileMenuOpen(false);
                    }}
                    className="w-full flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-semibold text-gray-700 hover:bg-blue-50 transition-all"
                  >
                    <LogOut size={18} />
                    Logout
                  </button>
                ) : (
                  <Link
                    href="/login"
                    onClick={() => setMobileMenuOpen(false)}
                    className="flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-semibold bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-md"
                  >
                    <LogIn size={18} />
                    Login
                  </Link>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </nav>
  );
}
