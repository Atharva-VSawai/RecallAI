"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { Mail, ArrowRight, ArrowLeft, MailCheck, Sparkles } from "lucide-react";
import { supabase } from "@/lib/supabase";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/login`,
      });

      if (error) {
        setError(error.message);
        setLoading(false);
      } else {
        setSuccess(true);
        setLoading(false);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to authentication service";
      setError(msg);
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center px-6 py-24 overflow-hidden">
      {/* Ambient orbs */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="orb orb-cyan w-[500px] h-[500px] -top-40 -right-32 animate-float-slow" />
        <div className="orb orb-violet w-[400px] h-[400px] -bottom-40 -left-32 animate-float" style={{ animationDelay: "1s" }} />
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
          <div className="h-1 w-full bg-gradient-to-r from-accent via-accent-2 to-accent-3 animate-gradient" />

          <div className="p-10">
            {/* Logo */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.15, duration: 0.5, type: "spring", stiffness: 200 }}
              className="flex justify-center mb-8"
            >
              <motion.div
                whileHover={{ scale: 1.08, rotate: -4 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                className="relative"
              >
                <img
                  src="/logo2.png"
                  alt="Recall.AI"
                  className="h-16 w-auto object-contain relative z-10 drop-shadow-[0_0_24px_rgba(6,182,212,0.45)]"
                />
                <div className="absolute inset-0 bg-gradient-to-r from-accent/30 via-accent-2/30 to-accent-3/30 blur-2xl rounded-full" />
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
                <Sparkles size={12} className="text-accent" />
                Account Recovery
              </div>
              <h1 className="text-3xl font-black font-display text-foreground mb-2">
                Reset Password
              </h1>
              <p className="text-foreground-muted text-sm">
                Enter your email to receive a reset link
              </p>
            </motion.div>

            {/* Content */}
            <AnimatePresence mode="wait">
              {success ? (
                <motion.div
                  key="success"
                  initial={{ opacity: 0, scale: 0.9, y: 12 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  transition={{ type: "spring", stiffness: 200 }}
                  className="flex flex-col items-center gap-5 py-6"
                >
                  <motion.div
                    initial={{ scale: 0, rotate: -45 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ delay: 0.1, type: "spring", stiffness: 300, damping: 20 }}
                    className="p-5 rounded-2xl bg-gradient-to-br from-accent to-accent-2 shadow-lg shadow-accent/25"
                  >
                    <MailCheck size={36} className="text-white" />
                  </motion.div>

                  <div className="text-center">
                    <p className="text-foreground font-bold text-lg mb-1">Check your inbox!</p>
                    <p className="text-foreground-muted text-sm">
                      We&apos;ve sent a reset link to{" "}
                      <span className="text-accent font-semibold">{email}</span>
                    </p>
                  </div>

                  <div className="glass rounded-xl border border-card-border px-5 py-4 text-xs text-foreground-muted text-center">
                    Didn&apos;t receive it? Check your spam folder or{" "}
                    <button
                      onClick={() => setSuccess(false)}
                      className="text-accent hover:text-foreground transition-colors font-medium"
                    >
                      try again
                    </button>
                    .
                  </div>

                  <Link
                    href="/login"
                    className="flex items-center gap-2 text-sm text-foreground-muted hover:text-foreground transition-colors duration-300 group"
                  >
                    <ArrowLeft size={14} className="group-hover:-translate-x-1 transition-transform duration-300" />
                    Back to sign in
                  </Link>
                </motion.div>
              ) : (
                <motion.form
                  key="form"
                  onSubmit={handleReset}
                  className="space-y-5"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3, duration: 0.5 }}
                >
                  {/* Email */}
                  <div>
                    <label
                      htmlFor="reset-email"
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
                        id="reset-email"
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
                        <span>Sending…</span>
                      </>
                    ) : (
                      <>
                        <span>Send Reset Link</span>
                        <ArrowRight size={16} />
                      </>
                    )}
                  </motion.button>

                  <Link
                    href="/login"
                    className="flex items-center justify-center gap-2 text-sm text-foreground-muted hover:text-foreground transition-colors duration-300 group"
                  >
                    <ArrowLeft size={14} className="group-hover:-translate-x-1 transition-transform duration-300" />
                    Back to sign in
                  </Link>
                </motion.form>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
