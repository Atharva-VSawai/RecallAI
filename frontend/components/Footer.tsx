"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Mail, ArrowRight, MessageSquare, Globe, ExternalLink, Sparkles } from "lucide-react";
import { AnimatedSection } from "@/components/AnimatedSection";

const productLinks = [
  { href: "/", label: "Home" },
  { href: "/query", label: "Query" },
  { href: "/graph", label: "Graph" },
  { href: "/activity", label: "Activity" },
];

const featureLinks = [
  { href: "#", label: "Slack Integration" },
  { href: "#", label: "PDF Upload" },
  { href: "#", label: "Excel Processing" },
  { href: "#", label: "Audio Transcription" },
];

const techLinks = [
  { href: "#", label: "Neo4j AuraDB" },
  { href: "#", label: "ChromaDB" },
  { href: "#", label: "LangGraph" },
  { href: "#", label: "Groq Llama 3.3" },
];

const companyLinks = [
  { href: "#", label: "Privacy Policy" },
  { href: "#", label: "Terms of Service" },
  { href: "#", label: "Contact Us" },
];

const socialLinks = [
  { icon: Globe, href: "#", label: "Website" },
  { icon: ExternalLink, href: "#", label: "Portfolio" },
  { icon: MessageSquare, href: "#", label: "Discord" },
  { icon: Mail, href: "#", label: "Email" },
];

function FooterLinkGroup({
  title,
  links,
}: {
  title: string;
  links: { href: string; label: string }[];
}) {
  return (
    <div>
      <h3 className="font-bold mb-5 text-sm uppercase tracking-widest text-gradient">
        {title}
      </h3>
      <ul className="space-y-3">
        {links.map((link) => (
          <li key={link.label}>
            <Link
              href={link.href}
              className="text-sm text-foreground-muted hover:text-foreground transition-colors duration-300 inline-flex items-center gap-1.5 group"
            >
              <span className="w-0 group-hover:w-3 overflow-hidden transition-all duration-300 text-accent">
                ›
              </span>
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Footer() {
  return (
    <footer className="relative border-t border-card-border overflow-hidden">
      {/* Ambient background */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="orb orb-violet w-[500px] h-[500px] -top-48 -right-48 opacity-20" />
        <div className="orb orb-cyan w-[400px] h-[400px] -bottom-32 -left-32 opacity-15" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 pt-20 pb-10">
        {/* Top grid */}
        <div className="grid lg:grid-cols-6 md:grid-cols-3 gap-12 mb-16">
          {/* Brand — takes 2 cols on large screens */}
          <div className="lg:col-span-2">
            <AnimatedSection direction="up" delay={0}>
              <Link href="/" className="inline-flex items-center gap-3 mb-6 group">
                <motion.div
                  whileHover={{ scale: 1.08, rotate: -4 }}
                  transition={{ type: "spring", stiffness: 300, damping: 20 }}
                >
                  <img
                    src="/logo2.png"
                    alt="Recall.AI"
                    className="h-10 w-auto object-contain drop-shadow-[0_0_12px_rgba(6,182,212,0.4)]"
                  />
                </motion.div>
                <span className="font-display text-xl font-bold text-gradient hidden sm:block">
                  Recall.AI
                </span>
              </Link>

              <p className="text-foreground-muted text-sm leading-relaxed mb-8 max-w-xs">
                Query your company&apos;s institutional knowledge. Understand why decisions were made,
                who was involved, and what breaks if things change.
              </p>

              {/* Social icons */}
              <div className="flex gap-3">
                {socialLinks.map(({ icon: Icon, href, label }) => (
                  <motion.a
                    key={label}
                    href={href}
                    aria-label={label}
                    whileHover={{ scale: 1.12, y: -2 }}
                    whileTap={{ scale: 0.92 }}
                    className="h-9 w-9 rounded-full glass border-card-border flex items-center justify-center text-foreground-muted hover:text-foreground hover:border-accent/50 transition-colors duration-300 glow-accent"
                  >
                    <Icon size={16} />
                  </motion.a>
                ))}
              </div>
            </AnimatedSection>
          </div>

          {/* Link columns */}
          {[
            { title: "Product", links: productLinks },
            { title: "Features", links: featureLinks },
            { title: "Technology", links: techLinks },
          ].map((group, i) => (
            <AnimatedSection key={group.title} direction="up" delay={i * 0.08}>
              <FooterLinkGroup title={group.title} links={group.links} />
            </AnimatedSection>
          ))}
        </div>

        {/* Newsletter bar */}
        <AnimatedSection direction="up" delay={0.2}>
          <div className="glass rounded-2xl border border-card-border p-8 mb-16 flex flex-col md:flex-row items-center gap-6">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles size={16} className="text-accent" />
                <h3 className="font-display font-bold text-foreground">Stay Updated</h3>
              </div>
              <p className="text-sm text-foreground-muted">
                Get the latest updates on new features and improvements.
              </p>
            </div>
            <div className="flex gap-3 w-full md:w-auto">
              <input
                type="email"
                placeholder="Enter your email"
                className="glow-input flex-1 md:w-64 px-4 py-3 rounded-xl text-sm"
                aria-label="Email for newsletter"
              />
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className="btn-primary rounded-xl px-5 py-3 text-sm font-semibold flex items-center gap-2 whitespace-nowrap"
              >
                <span>Subscribe</span>
                <ArrowRight size={16} />
              </motion.button>
            </div>
          </div>
        </AnimatedSection>

        {/* Bottom bar */}
        <div className="border-t border-card-border pt-8 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-foreground-dim">
          <p>© {new Date().getFullYear()} Recall.AI. All rights reserved.</p>
          <p className="flex items-center gap-2">
            Built with{" "}
            <span className="text-accent-3" aria-label="love">
              ♥
            </span>{" "}
            using Next.js &amp; LangGraph
          </p>
          <div className="flex items-center gap-4">
            {companyLinks.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                className="text-foreground-dim hover:text-foreground-muted transition-colors duration-300 text-xs"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
