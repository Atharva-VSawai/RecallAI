"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Mail, Lock, ArrowRight, Eye, EyeOff, CheckCircle2, Sparkles } from "lucide-react";
import { supabase } from "@/lib/supabase";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords don't match");
      setLoading(false);
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      setLoading(false);
      return;
    }

    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/login`,
        },
      });

      if (error) {
        setError(error.message);
        setLoading(false);
      } else {
        setSuccess(true);
        setTimeout(() => router.push("/login"), 2500);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to authentication service";
      setError(msg);
      setLoading(false);
    }
  };

  const passwordStrength = (() => {
    if (!password) return 0;
    let score = 0;
    if (password.length >= 8) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    return score;
  })();

  const strengthColor = ["", "bg-danger", "bg-warning", "bg-accent", "bg-success"][passwordStrength];
  const strengthLabel = ["", "Weak", "Fair", "Good", "Strong"][passwordStrength];

  return (
    <div className="relative min-h-screen flex items-center justify-center px-6 py-24 overflow-hidden">
      {/* Ambient orbs */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="orb orb-violet w-[500px] h-[500px] -top-48 -right-32 animate-float-slow" />
        <div className="orb orb-cyan w-[500px] h-[500px] -bottom-48 -left-32 animate-float" style={{ animationDelay: "1.5s" }} />
        <div className="orb orb-pink w-[350px] h-[350px] top-1/3 left-1/4 animate-float-slow" style={{ animationDelay: "0.5s" }} />
      </div>

      {/* Grid overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(var(--card-border-strong) 1px, transparent 1px), linear-gradient(90deg, var(--card-border-strong) 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 32, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 w-full max-w-md"
      >
        <div className="glass-strong rounded-3xl border border-card-border-strong shadow-2xl shadow-black/30 overflow-hidden">
          {/* Top accent bar */}
          <div className="h-1 w-full bg-gradient-to-r from-accent-2 via-accent-3 to-accent animate-gradient" />

          <div className="p-10">
            {/* Logo mark */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.15, duration: 0.5, type: "spring", stiffness: 200 }}
              className="flex justify-center mb-8"
            >
              <motion.div
                whileHover={{ scale: 1.08, rotate: 4 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                className="relative"
              >
                <img
                  src="/logo2.png"
                  alt="Recall.AI"
                  className="h-16 w-auto object-contain relative z-10 drop-shadow-[0_0_24px_rgba(139,92,246,0.45)]"
                />
                <div className="absolute inset-0 bg-gradient-to-r from-accent-2/30 via-accent-3/30 to-accent/30 blur-2xl rounded-full" />
              </motion.div>
            </motion.div>

            {/* Heading */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.22, duration: 0.5 }}
              className="text-center mb-8"
            >
              <div className="inline-flex items-center gap-2 glass rounded-full px-4 py-1.5 text-xs font-semibold text-foreground-muted border border-card-border mb-4">
                <Sparkles size={12} className="text-accent-2" />
                AI Knowledge Platform
              </div>
              <h1 className="text-3xl font-black font-display text-foreground mb-2">
                Create Account
              </h1>
              <p className="text-foreground-muted text-sm">
                Join and start querying your knowledge
              </p>
            </motion.div>

            {/* Success state */}
            <AnimatePresence mode="wait">
              {success ? (
                <motion.div
                  key="success"
                  initial={{ opacity: 0, scale: 0.9, y: 12 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  transition={{ type: "spring", stiffness: 200 }}
                  className="flex flex-col items-center gap-4 py-8"
                >
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.1, type: "spring", stiffness: 300, damping: 20 }}
                  >
                    <CheckCircle2 size={56} className="text-success" />
                  </motion.div>
                  <div className="text-center">
                    <p className="text-foreground font-bold text-lg">Account created!</p>
                    <p className="text-foreground-muted text-sm mt-1">Redirecting to sign in…</p>
                  </div>
                  <div className="w-full bg-card-solid rounded-full h-1 overflow-hidden">
                    <motion.div
                      initial={{ width: "0%" }}
                      animate={{ width: "100%" }}
                      transition={{ duration: 2.5, ease: "linear" }}
                      className="h-full bg-gradient-to-r from-accent to-success rounded-full"
                    />
                  </div>
                </motion.div>
              ) : (
                <motion.form
                  key="form"
                  onSubmit={handleSignup}
                  className="space-y-5"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3, duration: 0.5 }}
                >
                  {/* Email */}
                  <div>
                    <label
                      htmlFor="signup-email"
                      className="block text-sm font-medium text-foreground-muted mb-2"
                    >
                      Email address
                    </label>
                    <div className="relative">
                      <Mail
                        size={16}
                        className="absolute left-4 top-1/2 -translate-y-1/2 text-foreground-dim pointer-events-none z-10"
                      />
                      <input
                        id="signup-email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@company.com"
                        className="glow-input w-full pl-11 pr-4 py-3.5 rounded-xl text-sm"
                        required
                        autoComplete="email"
                      />
                    </div>
                  </div>

                  {/* Password */}
                  <div>
                    <label
                      htmlFor="signup-password"
                      className="block text-sm font-medium text-foreground-muted mb-2"
                    >
                      Password
                    </label>
                    <div className="relative">
                      <Lock
                        size={16}
                        className="absolute left-4 top-1/2 -translate-y-1/2 text-foreground-dim pointer-events-none z-10"
                      />
                      <input
                        id="signup-password"
                        type={showPassword ? "text" : "password"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Min. 8 characters"
                        className="glow-input w-full pl-11 pr-12 py-3.5 rounded-xl text-sm"
                        required
                        autoComplete="new-password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-foreground-dim hover:text-foreground transition-colors"
                        aria-label={showPassword ? "Hide password" : "Show password"}
                      >
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>

                    {/* Password strength */}
                    {password && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        className="mt-2"
                      >
                        <div className="flex gap-1.5">
                          {[1, 2, 3, 4].map((i) => (
                            <div key={i} className="flex-1 h-1 rounded-full bg-card-solid overflow-hidden">
                              <motion.div
                                className={`h-full rounded-full transition-colors duration-300 ${i <= passwordStrength ? strengthColor : ""}`}
                                initial={{ width: 0 }}
                                animate={{ width: i <= passwordStrength ? "100%" : "0%" }}
                                transition={{ duration: 0.3 }}
                              />
                            </div>
                          ))}
                        </div>
                        <p className="text-xs text-foreground-dim mt-1">{strengthLabel}</p>
                      </motion.div>
                    )}
                  </div>

                  {/* Confirm password */}
                  <div>
                    <label
                      htmlFor="signup-confirm"
                      className="block text-sm font-medium text-foreground-muted mb-2"
                    >
                      Confirm password
                    </label>
                    <div className="relative">
                      <Lock
                        size={16}
                        className="absolute left-4 top-1/2 -translate-y-1/2 text-foreground-dim pointer-events-none z-10"
                      />
                      <input
                        id="signup-confirm"
                        type={showConfirm ? "text" : "password"}
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="••••••••"
                        className="glow-input w-full pl-11 pr-12 py-3.5 rounded-xl text-sm"
                        required
                        autoComplete="new-password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirm(!showConfirm)}
                        className="absolute right-4 top-1/2 -translate-y-1/2 text-foreground-dim hover:text-foreground transition-colors"
                        aria-label={showConfirm ? "Hide confirm password" : "Show confirm password"}
                      >
                        {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                    {/* Match indicator */}
                    {confirmPassword && (
                      <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className={`text-xs mt-1 ${password === confirmPassword ? "text-success" : "text-danger"}`}
                      >
                        {password === confirmPassword ? "✓ Passwords match" : "✗ Passwords don't match"}
                      </motion.p>
                    )}
                  </div>

                  {/* Error */}
                  <AnimatePresence>
                    {error && (
                      <motion.div
                        initial={{ opacity: 0, y: -8, height: 0 }}
                        animate={{ opacity: 1, y: 0, height: "auto" }}
                        exit={{ opacity: 0, y: -8, height: 0 }}
                        className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger"
                      >
                        {error}
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Submit */}
                  <motion.button
                    type="submit"
                    disabled={loading}
                    whileHover={{ scale: loading ? 1 : 1.02, y: loading ? 0 : -1 }}
                    whileTap={{ scale: 0.97 }}
                    className="btn-primary w-full py-4 rounded-xl text-sm font-bold flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <>
                        <motion.span
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                          className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                        />
                        <span>Creating account…</span>
                      </>
                    ) : (
                      <>
                        <span>Create Account</span>
                        <ArrowRight size={16} />
                      </>
                    )}
                  </motion.button>
                </motion.form>
              )}
            </AnimatePresence>

            {/* Footer link */}
            {!success && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                className="text-center text-sm text-foreground-muted mt-6"
              >
                Already have an account?{" "}
                <Link
                  href="/login"
                  className="text-accent hover:text-foreground font-semibold transition-colors duration-300"
                >
                  Sign in →
                </Link>
              </motion.p>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
