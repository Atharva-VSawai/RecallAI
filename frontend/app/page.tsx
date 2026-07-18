"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Database,
  Brain,
  Network,
  MessageSquare,
  FileText,
  Mic,
  FileSpreadsheet,
  Search,
  Zap,
  GitBranch,
  Upload,
  FolderOpen,
  Sparkles,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import FileSelector from "@/components/FileSelector";
import TextType from "@/components/TextType";
import { AnimatedSection, StaggerContainer, StaggerItem } from "@/components/AnimatedSection";

const features = [
  {
    icon: MessageSquare,
    title: "Slack Integration",
    description: "Ingest channel conversations and extract structured decisions, people, and context automatically.",
  },
  {
    icon: FileText,
    title: "PDF Documents",
    description: "Upload PDF files to extract decisions and organizational knowledge using AI agents.",
  },
  {
    icon: FileSpreadsheet,
    title: "Excel Spreadsheets",
    description: "Process Excel files to capture structured decision data and store in knowledge graph.",
  },
  {
    icon: Mic,
    title: "Audio & Video",
    description: "Transcribe meetings and conversations using Whisper, then extract key decisions.",
  },
];

const agents = [
  {
    icon: GitBranch,
    title: "Router Agent",
    description: "Automatically classifies incoming queries and routes them to the appropriate specialized agent.",
  },
  {
    icon: Search,
    title: "Query Agent",
    description: "Answers questions about history, decisions, and people using Neo4j and ChromaDB.",
  },
  {
    icon: Zap,
    title: "Impact Agent",
    description: "Performs what-if analysis and risk assessment by finding related decisions.",
  },
  {
    icon: FileText,
    title: "Ingestion Agent",
    description: "Extracts structured decisions, people, and context from documents automatically.",
  },
];

const techStack = [
  { name: "Neo4j AuraDB", description: "Graph database for decision relationships", color: "from-emerald-400 to-emerald-600" },
  { name: "ChromaDB", description: "Vector database for semantic search", color: "from-blue-400 to-indigo-600" },
  { name: "Groq Llama 3.3 70B", description: "LLM for reasoning and extraction", color: "from-violet-400 to-purple-600" },
  { name: "LangGraph", description: "Agent orchestration framework", color: "from-pink-400 to-rose-600" },
];

const stats = [
  { label: "Data Sources", value: "4" },
  { label: "AI Agents", value: "4" },
  { label: "Databases", value: "2" },
  { label: "LLM Model", value: "70B" },
];

export default function HomePage() {
  const { scrollYProgress } = useScroll();
  const y = useTransform(scrollYProgress, [0, 1], [0, -80]);
  const router = useRouter();
  const [selectedSource, setSelectedSource] = useState<string>("");
  const [selectedFilename, setSelectedFilename] = useState<string>("");
  const [dialogOpen, setDialogOpen] = useState(false);

  const handleFileSelect = (source: string, filename: string) => {
    setSelectedSource(source);
    setSelectedFilename(filename);
  };

  const handleQueryExisting = () => {
    if (selectedSource) {
      router.push(`/query?source=${encodeURIComponent(selectedSource)}&filename=${encodeURIComponent(selectedFilename)}`);
    }
  };

  return (
    <div className="relative overflow-x-hidden">
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center px-6 pt-32 pb-20 overflow-hidden">
        {/* Ambient orbs */}
        <motion.div
          style={{ y }}
          className="absolute inset-0 pointer-events-none overflow-hidden"
        >
          <div className="orb orb-cyan w-[500px] h-[500px] -top-32 -left-32 animate-float-slow" />
          <div className="orb orb-violet w-[600px] h-[600px] top-1/4 -right-40 animate-float" style={{ animationDelay: "1s" }} />
          <div className="orb orb-pink w-[400px] h-[400px] bottom-0 left-1/3 animate-float-slow" style={{ animationDelay: "2s" }} />
        </motion.div>

        {/* Grid overlay */}
        <div
          className="absolute inset-0 pointer-events-none opacity-[0.03]"
          style={{
            backgroundImage: `linear-gradient(var(--card-border-strong) 1px, transparent 1px), linear-gradient(90deg, var(--card-border-strong) 1px, transparent 1px)`,
            backgroundSize: "60px 60px",
          }}
        />

        <div className="max-w-6xl mx-auto text-center relative z-10">
          {/* Eyebrow */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <Badge className="glass border-card-border text-foreground-muted px-4 py-1.5 text-xs font-semibold tracking-wide mb-8">
              <Sparkles size={14} className="text-accent mr-2" />
              AI-Powered Knowledge Graph
            </Badge>
          </motion.div>

          {/* Logo + Headline */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, type: "spring", stiffness: 100 }}
            className="mb-8"
          >
            <div className="relative inline-block">
              <img
                src="/logo3.png"
                alt="Recall.AI Logo"
                className="h-28 md:h-36 lg:h-44 w-auto object-contain relative z-10 drop-shadow-[0_0_40px_rgba(6,182,212,0.35)]"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-accent via-accent-2 to-accent-3 opacity-20 blur-3xl rounded-full" />
            </div>
          </motion.div>

          {/* Tagline */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.25 }}
            className="mb-8"
          >
            <TextType
              text={['Remember The "Why"', 'Remember The "Why"']}
              as="h1"
              typingSpeed={100}
              pauseDuration={2500}
              deletingSpeed={50}
              loop={true}
              showCursor={true}
              cursorCharacter="|"
              cursorBlinkDuration={0.7}
              className="text-4xl md:text-6xl lg:text-7xl font-black font-display text-gradient-shine"
            />
          </motion.div>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="text-lg md:text-xl text-foreground-muted max-w-2xl mx-auto mb-12 leading-relaxed"
          >
            Query your company&apos;s institutional knowledge across Slack, PDFs, Excel, and meetings.
            Understand why decisions were made and what breaks if they change.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.55 }}
            className="flex flex-wrap items-center justify-center gap-4 mb-20"
          >
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button size="lg" variant="outline" className="btn-secondary rounded-full px-7">
                  <FolderOpen size={20} />
                  Select Existing File
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl p-0 gap-0 overflow-hidden h-[600px] flex flex-col glass-strong border-card-border-strong">
                <div className="p-6 pb-3 flex-shrink-0">
                  <DialogHeader>
                    <DialogTitle className="text-2xl font-bold font-display text-gradient">
                      Select from Existing Files
                    </DialogTitle>
                    <DialogDescription className="text-base text-foreground-muted">
                      Choose a file you&apos;ve already uploaded to query it directly
                    </DialogDescription>
                  </DialogHeader>
                </div>
                <div className="px-6 flex-1 overflow-hidden">
                  <div className="overflow-hidden glass rounded-xl p-3 h-full">
                    <FileSelector onSelectFile={handleFileSelect} selectedSource={selectedSource} />
                  </div>
                </div>
                <div className="flex justify-end gap-3 px-6 pb-4 pt-3 border-t border-card-border-strong flex-shrink-0">
                  <Button
                    onClick={() => {
                      handleQueryExisting();
                      setDialogOpen(false);
                    }}
                    disabled={!selectedSource}
                    className="px-6 btn-primary rounded-full"
                  >
                    Query Selected File
                  </Button>
                </div>
              </DialogContent>
            </Dialog>

            <Button asChild size="lg" className="btn-primary rounded-full px-7">
              <Link href="/query">
                <Upload size={20} />
                Upload New File
              </Link>
            </Button>

            <Button asChild size="lg" variant="outline" className="btn-secondary rounded-full px-7">
              <Link href="/activity">View Activity</Link>
            </Button>
          </motion.div>

          {/* Stats */}
          <StaggerContainer className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto" stagger={0.1}>
            {stats.map((stat) => (
              <StaggerItem key={stat.label}>
                <motion.div
                  whileHover={{ y: -6, scale: 1.02 }}
                  transition={{ type: "spring", stiffness: 300, damping: 20 }}
                  className="glass neon-border rounded-2xl p-6 h-full card-hover"
                >
                  <div className="text-3xl md:text-4xl font-black font-display text-gradient mb-1">{stat.value}</div>
                  <div className="text-xs font-semibold uppercase tracking-wider text-foreground-muted">{stat.label}</div>
                </motion.div>
              </StaggerItem>
            ))}
          </StaggerContainer>
        </div>

        {/* Scroll hint */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            className="w-6 h-10 rounded-full border-2 border-card-border-strong flex justify-center pt-2"
          >
            <div className="w-1 h-2 rounded-full bg-foreground-muted" />
          </motion.div>
        </motion.div>
      </section>

      {/* Data Sources Section */}
      <section className="relative px-6 py-24">
        <div className="max-w-6xl mx-auto">
          <AnimatedSection className="text-center mb-16" direction="up">
            <Badge className="glass border-card-border text-foreground-muted mb-4">
              <Database size={14} className="text-accent mr-2" />
              Data Ingestion
            </Badge>
            <h2 className="text-4xl md:text-5xl font-black font-display text-foreground mb-4">
              Ingest from <span className="text-gradient">Multiple Sources</span>
            </h2>
            <p className="text-lg text-foreground-muted max-w-2xl mx-auto">
              Upload PDFs, Excel files, audio/video, or connect Slack channels. Our AI agents automatically extract decisions and store them in the knowledge graph.
            </p>
          </AnimatedSection>

          <StaggerContainer className="grid md:grid-cols-2 gap-6" stagger={0.12}>
            {features.map((feature) => (
              <StaggerItem key={feature.title}>
                <motion.div
                  whileHover={{ y: -8, scale: 1.015 }}
                  transition={{ type: "spring", stiffness: 200, damping: 20 }}
                  className="glass neon-border rounded-2xl p-6 h-full card-hover group cursor-pointer"
                >
                  <div className="flex items-start gap-5">
                    <div className="flex-shrink-0 p-4 rounded-xl bg-gradient-to-br from-accent to-accent-2 shadow-lg shadow-accent/25 group-hover:shadow-accent/40 transition-shadow">
                      <feature.icon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold font-display text-foreground mb-2 group-hover:text-accent transition-colors">
                        {feature.title}
                      </h3>
                      <p className="text-foreground-muted leading-relaxed">{feature.description}</p>
                    </div>
                  </div>
                </motion.div>
              </StaggerItem>
            ))}
          </StaggerContainer>
        </div>
      </section>

      {/* AI Agents Section */}
      <section className="relative px-6 py-24">
        {/* Background accent */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="orb orb-violet w-[600px] h-[600px] -right-48 top-1/2 -translate-y-1/2" />
        </div>

        <div className="max-w-6xl mx-auto relative z-10">
          <AnimatedSection className="text-center mb-16" direction="up">
            <Badge className="glass border-card-border text-foreground-muted mb-4">
              <Brain size={14} className="text-accent-2 mr-2" />
              AI Agents
            </Badge>
            <h2 className="text-4xl md:text-5xl font-black font-display text-foreground mb-4">
              Intelligent <span className="text-gradient">Query Routing</span>
            </h2>
            <p className="text-lg text-foreground-muted max-w-2xl mx-auto">
              A router agent automatically classifies your question and routes it to the specialized agent for optimal results.
            </p>
          </AnimatedSection>

          <StaggerContainer className="grid md:grid-cols-2 gap-6" stagger={0.12}>
            {agents.map((agent) => (
              <StaggerItem key={agent.title}>
                <motion.div
                  whileHover={{ y: -8, scale: 1.015, rotateX: 2, rotateY: 2 }}
                  transition={{ type: "spring", stiffness: 200, damping: 20 }}
                  style={{ transformStyle: "preserve-3d", perspective: 1000 }}
                  className="glass neon-border rounded-2xl p-6 h-full card-hover group cursor-pointer"
                >
                  <div className="flex items-start gap-5">
                    <div className="flex-shrink-0 p-4 rounded-xl bg-gradient-to-br from-accent-2 to-accent-3 shadow-lg shadow-accent-2/25 group-hover:shadow-accent-2/40 transition-shadow">
                      <agent.icon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold font-display text-foreground mb-2 group-hover:text-accent-2 transition-colors">
                        {agent.title}
                      </h3>
                      <p className="text-foreground-muted leading-relaxed">{agent.description}</p>
                    </div>
                  </div>
                </motion.div>
              </StaggerItem>
            ))}
          </StaggerContainer>
        </div>
      </section>

      {/* Tech Stack Section */}
      <section className="relative px-6 py-24">
        <div className="max-w-6xl mx-auto">
          <AnimatedSection className="text-center mb-16" direction="up">
            <Badge className="glass border-card-border text-foreground-muted mb-4">
              <Network size={14} className="text-accent-3 mr-2" />
              Technology Stack
            </Badge>
            <h2 className="text-4xl md:text-5xl font-black font-display text-foreground mb-4">
              Built with <span className="text-gradient">Modern Tech</span>
            </h2>
            <p className="text-lg text-foreground-muted max-w-2xl mx-auto">
              Powered by industry-leading databases and AI models for enterprise-grade knowledge management.
            </p>
          </AnimatedSection>

          <StaggerContainer className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto" stagger={0.1}>
            {techStack.map((tech) => (
              <StaggerItem key={tech.name}>
                <motion.div
                  whileHover={{ scale: 1.03 }}
                  transition={{ type: "spring", stiffness: 200, damping: 20 }}
                  className="glass neon-border rounded-2xl p-6 card-hover group cursor-default"
                >
                  <div className="flex items-center gap-4 mb-3">
                    <div className={`h-10 w-1.5 rounded-full bg-gradient-to-b ${tech.color}`} />
                    <h3 className="text-xl font-bold font-display text-foreground">{tech.name}</h3>
                  </div>
                  <p className="text-foreground-muted pl-6">{tech.description}</p>
                </motion.div>
              </StaggerItem>
            ))}
          </StaggerContainer>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative px-6 py-28 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-accent/10 via-accent-2/10 to-accent-3/10" />
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <motion.div
            animate={{ scale: [1, 1.2, 1], opacity: [0.15, 0.25, 0.15] }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            className="orb orb-cyan w-[500px] h-[500px] -top-40 -right-40"
          />
          <motion.div
            animate={{ scale: [1, 1.3, 1], opacity: [0.1, 0.2, 0.1] }}
            transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
            className="orb orb-pink w-[500px] h-[500px] -bottom-40 -left-40"
          />
        </div>

        <div className="max-w-4xl mx-auto text-center relative z-10">
          <AnimatedSection className="space-y-8" direction="up">
            <h2 className="text-4xl md:text-5xl lg:text-6xl font-black font-display text-foreground">
              Ready to Query Your <span className="text-gradient">Knowledge Base</span>?
            </h2>
            <p className="text-xl text-foreground-muted max-w-2xl mx-auto">
              Start ingesting data from Slack, PDFs, Excel, or audio files and query your organizational memory instantly.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
              <Button asChild size="lg" className="btn-primary rounded-full px-8">
                <Link href="/query">
                  Start Querying
                  <ArrowRight size={20} />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="btn-secondary rounded-full px-8">
                <Link href="/activity">
                  View Activity
                  <ChevronRight size={20} />
                </Link>
              </Button>
            </div>
          </AnimatedSection>
        </div>
      </section>
    </div>
  );
}
