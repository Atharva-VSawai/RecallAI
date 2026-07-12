"use client";

import Link from "next/link";
import { Brain, Mail, ArrowRight, MessageSquare, Search, Zap } from "lucide-react";

export default function Footer() {
  return (
    <footer className="relative bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 text-white overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full bg-cyan-500/20 blur-3xl" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-6 py-16">
        
        {/* Top Section */}
        <div className="grid md:grid-cols-2 gap-12 mb-12">
          
          {/* Brand Section */}
          <div>
            <div className="flex items-center gap-3 mb-6">
              <img 
                src="/logo2.png" 
                alt="Recall.AI" 
                className="h-12 w-auto object-contain"
              />
              <img 
                src="/logo1.png" 
                alt="Recall.AI" 
                className="h-10 w-auto object-contain"
              />
            </div>
            <p className="text-gray-300 text-base leading-relaxed mb-6">
              Query your company's institutional knowledge. Understand why decisions were made, who was involved, and what breaks if things change.
            </p>
            
            {/* Social Links */}
            <div className="flex gap-3">
              <a href="#" className="p-3 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-sm transition-all border border-white/20">
                <Mail size={20} />
              </a>
              <a href="#" className="p-3 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-sm transition-all border border-white/20">
                <MessageSquare size={20} />
              </a>
              <a href="#" className="p-3 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-sm transition-all border border-white/20">
                <Search size={20} />
              </a>
              <a href="#" className="p-3 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-sm transition-all border border-white/20">
                <Zap size={20} />
              </a>
            </div>
          </div>

          {/* Newsletter Section */}
          <div>
            <h3 className="text-xl font-bold mb-4">Stay Updated</h3>
            <p className="text-gray-300 text-sm mb-6">
              Get the latest updates on new features and improvements.
            </p>
            <div className="flex gap-2">
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 px-4 py-3 rounded-lg bg-white/10 border border-white/20 backdrop-blur-sm text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
              />
              <button className="px-6 py-3 rounded-lg bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 font-semibold shadow-lg transition-all flex items-center gap-2">
                Subscribe
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>

        {/* Links Section */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12 pb-12 border-b border-white/10">
          <div>
            <h3 className="font-bold mb-4 text-blue-400">Product</h3>
            <ul className="space-y-3 text-gray-300 text-sm">
              <li>
                <Link href="/" className="hover:text-blue-400 transition-colors inline-flex items-center gap-1 group">
                  <span>Home</span>
                  <ArrowRight size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                </Link>
              </li>
              <li>
                <Link href="/query" className="hover:text-blue-400 transition-colors inline-flex items-center gap-1 group">
                  <span>Query</span>
                  <ArrowRight size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                </Link>
              </li>
              <li>
                <Link href="/activity" className="hover:text-blue-400 transition-colors inline-flex items-center gap-1 group">
                  <span>Activity</span>
                  <ArrowRight size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="font-bold mb-4 text-blue-400">Features</h3>
            <ul className="space-y-3 text-gray-300 text-sm">
              <li>Slack Integration</li>
              <li>PDF Upload</li>
              <li>Excel Processing</li>
              <li>Audio Transcription</li>
            </ul>
          </div>

          <div>
            <h3 className="font-bold mb-4 text-blue-400">Technology</h3>
            <ul className="space-y-3 text-gray-300 text-sm">
              <li>Neo4j AuraDB</li>
              <li>ChromaDB</li>
              <li>LangGraph</li>
              <li>Groq Llama 3.3</li>
            </ul>
          </div>

          <div>
            <h3 className="font-bold mb-4 text-blue-400">Company</h3>
            <ul className="space-y-3 text-gray-300 text-sm">
              <li>
                <Link href="#" className="hover:text-blue-400 transition-colors">
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link href="#" className="hover:text-blue-400 transition-colors">
                  Terms of Service
                </Link>
              </li>
              <li>
                <Link href="#" className="hover:text-blue-400 transition-colors">
                  Contact Us
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Section */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-gray-400">
          <p>© 2025 Recall.AI. All rights reserved.</p>
          <p className="flex items-center gap-2">
            Built with <span className="text-red-500">❤</span> using Next.js & LangGraph
          </p>
        </div>

      </div>
    </footer>
  );
}
