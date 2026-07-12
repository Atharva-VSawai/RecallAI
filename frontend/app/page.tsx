"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { 
  ArrowRight, Database, Brain, Network, 
  MessageSquare, FileText, Mic, FileSpreadsheet, Search, Zap, GitBranch, Upload, FolderOpen
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import Aurora from "@/components/Aurora";
import FileSelector from "@/components/FileSelector";
import { MagicBentoCard, MagicBentoGrid } from "@/components/MagicBento";
import TextType from "@/components/TextType";
import BorderGlow from "@/components/BorderGlow";

const features = [
  {
    icon: MessageSquare,
    title: "Slack Integration",
    description: "Ingest channel conversations and extract structured decisions, people, and context automatically.",
    delay: 0.1,
  },
  {
    icon: FileText,
    title: "PDF Documents",
    description: "Upload PDF files to extract decisions and organizational knowledge using AI agents.",
    delay: 0.2,
  },
  {
    icon: FileSpreadsheet,
    title: "Excel Spreadsheets",
    description: "Process Excel files to capture structured decision data and store in knowledge graph.",
    delay: 0.3,
  },
  {
    icon: Mic,
    title: "Audio & Video",
    description: "Transcribe meetings and conversations using Whisper, then extract key decisions.",
    delay: 0.4,
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
  { name: "Neo4j AuraDB", description: "Graph database for decision relationships" },
  { name: "ChromaDB", description: "Vector database for semantic search" },
  { name: "Groq Llama 3.3 70B", description: "LLM for reasoning and extraction" },
  { name: "LangGraph", description: "Agent orchestration framework" },
];

export default function HomePage() {
  const { scrollYProgress } = useScroll();
  const y = useTransform(scrollYProgress, [0, 1], [0, -50]);
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
      {/* Hero Section with Aurora Background */}
      <motion.section 
        style={{ y }}
        className="relative min-h-[85vh] flex items-center justify-center px-6 py-20 overflow-hidden bg-gradient-to-b from-blue-900 via-purple-900 to-blue-900"
      >
        {/* Aurora Background */}
        <div className="absolute inset-0 z-0 mix-blend-screen">
          <Aurora
            colorStops={["#5c92ff","#B19EEF","#5227FF"]}
            blend={0.85}
            amplitude={1.0}
            speed={0.7}
          />
        </div>

        {/* Hero Content */}
        <div className="max-w-6xl mx-auto text-center space-y-8 relative z-10">
          {/* Main Heading */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="space-y-6"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, type: "spring" }}
              className="flex justify-center mb-8"
            >
              <img 
                src="/logo3.png" 
                alt="Recall.AI Logo" 
                className="h-32 md:h-40 lg:h-48 w-auto object-contain"
              />
            </motion.div>
            <TextType
              text={['Remember The "Why"', 'Remember The "Why"']}
              as="p"
              typingSpeed={100}
              pauseDuration={2000}
              deletingSpeed={50}
              loop={true}
              showCursor={true}
              cursorCharacter="|"
              cursorBlinkDuration={0.7}
              className="text-2xl md:text-3xl font-bold text-white"
            />
          </motion.div>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-wrap items-center justify-center gap-4"
          >
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <motion.div
                  whileHover={{ scale: 1.05, y: -2 }}
                  whileTap={{ scale: 0.95 }}
                  transition={{ type: "spring", stiffness: 400, damping: 17 }}
                >
                  <Button size="lg" variant="outline" className="border border-white text-white hover:bg-white/20">
                    <FolderOpen size={20} />
                    Select Existing File
                  </Button>
                </motion.div>
              </DialogTrigger>
              <DialogContent className="max-w-2xl bg-gradient-to-br from-white via-blue-50 to-cyan-50 p-0 gap-0 overflow-hidden h-[600px] flex flex-col">
                <div className="p-6 pb-3 flex-shrink-0">
                  <DialogHeader>
                    <DialogTitle className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
                      Select from Existing Files
                    </DialogTitle>
                    <DialogDescription className="text-base text-gray-700">
                      Choose a file you've already uploaded to query it directly
                    </DialogDescription>
                  </DialogHeader>
                </div>
                <div className="px-6 flex-1 overflow-hidden">
                  <div className="overflow-hidden bg-white rounded-xl p-3 shadow-inner h-full">
                    <FileSelector onSelectFile={handleFileSelect} selectedSource={selectedSource} />
                  </div>
                </div>
                <div className="flex justify-end gap-3 px-6 pb-4 pt-3 border-t border-blue-200 flex-shrink-0">
                  <Button 
                    onClick={() => {
                      handleQueryExisting();
                      setDialogOpen(false);
                    }}
                    disabled={!selectedSource}
                    className="px-6 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 disabled:opacity-50 shadow-lg"
                  >
                    Query Selected File
                  </Button>
                </div>
              </DialogContent>
            </Dialog>

            <motion.div
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              transition={{ type: "spring", stiffness: 400, damping: 17 }}
            >
              <Button asChild size="lg" variant="outline" className="border border-sky-500 text-sky-500 hover:bg-sky-500/20">
                <Link href="/query">
                  <Upload size={20} />
                  Upload New File
                </Link>
              </Button>
            </motion.div>

            <motion.div
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
              transition={{ type: "spring", stiffness: 400, damping: 17 }}
            >
              <Button asChild size="lg" variant="outline" className="border border-white text-white hover:bg-white/20">
                <Link href="/activity">
                  View Activity
                </Link>
              </Button>
            </motion.div>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto pt-8"
          >
            {[
              { label: "Data Sources", value: "4" },
              { label: "AI Agents", value: "4" },
              { label: "Databases", value: "2" },
              { label: "LLM Model", value: "70B" },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.6 + i * 0.1 }}
                whileHover={{ scale: 1.05, y: -5 }}
              >
                <BorderGlow
                  edgeSensitivity={40}
                  glowColor="200 80 80"
                  backgroundColor="rgba(255, 255, 255, 0.2)"
                  borderRadius={16}
                  glowRadius={30}
                  glowIntensity={1.2}
                  coneSpread={30}
                  colors={['#3b82f6', '#06b6d4', '#8b5cf6']}
                  fillOpacity={0.3}
                  className="h-full"
                >
                  <div className="backdrop-blur-md p-6 h-full flex flex-col items-center justify-center">
                    <div className="text-3xl font-bold text-white">{stat.value}</div>
                    <div className="text-xs text-white/80 uppercase tracking-wider mt-1">{stat.label}</div>
                  </div>
                </BorderGlow>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </motion.section>

      {/* Data Sources Section */}
      <section className="relative px-6 py-16 bg-white">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <Badge variant="secondary" className="mb-4 border-blue-300 bg-blue-50 text-blue-700">
              <Database size={14} />
              Data Ingestion
            </Badge>
            <h2 className="text-4xl md:text-5xl font-black text-gray-900 mb-4">
              Ingest from Multiple Sources
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Upload PDFs, Excel files, audio/video, or connect Slack channels. Our AI agents automatically extract decisions and store them in the knowledge graph.
            </p>
          </motion.div>

          <MagicBentoGrid
            enableSpotlight={true}
            spotlightRadius={400}
            glowColor="59, 130, 246"
          >
            <div className="grid md:grid-cols-2 gap-6">
              {features.map((feature, i) => (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, scale: 0.8, rotate: -5 }}
                  whileInView={{ opacity: 1, scale: 1, rotate: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: feature.delay, type: "spring" }}
                  whileHover={{ scale: 1.02, y: -5 }}
                >
                  <MagicBentoCard
                    enableStars={true}
                    enableBorderGlow={true}
                    enableTilt={true}
                    enableMagnetism={false}
                    clickEffect={true}
                    particleCount={12}
                    glowColor="59, 130, 246"
                    className="h-full"
                  >
                    <Card className="h-full border-2 border-blue-200 hover:border-blue-400 hover:shadow-xl transition-all group cursor-pointer bg-white/80 backdrop-blur-sm">
                      <CardHeader>
                        <div className="flex items-start gap-4">
                          <motion.div
                            whileHover={{ rotate: 360, scale: 1.1 }}
                            transition={{ duration: 0.6 }}
                            className="p-4 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 shadow-lg"
                          >
                            <feature.icon className="w-6 h-6 text-white" />
                          </motion.div>
                          <div className="flex-1">
                            <CardTitle className="group-hover:text-blue-600 transition-colors">
                              {feature.title}
                            </CardTitle>
                            <CardDescription className="mt-2">
                              {feature.description}
                            </CardDescription>
                          </div>
                        </div>
                      </CardHeader>
                    </Card>
                  </MagicBentoCard>
                </motion.div>
              ))}
            </div>
          </MagicBentoGrid>
        </div>
      </section>

      {/* AI Agents Section */}
      <section className="relative px-6 py-16 bg-gradient-to-b from-blue-50 to-white">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <Badge variant="secondary" className="mb-4 border-blue-300 bg-blue-50 text-blue-700">
              <Brain size={14} />
              AI Agents
            </Badge>
            <h2 className="text-4xl md:text-5xl font-black text-gray-900 mb-4">
              Intelligent Query Routing
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              A router agent automatically classifies your question and routes it to the specialized agent for optimal results.
            </p>
          </motion.div>

          <MagicBentoGrid
            enableSpotlight={true}
            spotlightRadius={400}
            glowColor="59, 130, 246"
          >
            <div className="grid md:grid-cols-2 gap-6">
              {agents.map((agent, i) => (
                <motion.div
                  key={agent.title}
                  initial={{ opacity: 0, y: 50, rotateX: -15 }}
                  whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: i * 0.15, type: "spring", stiffness: 100 }}
                  whileHover={{ scale: 1.05, y: -8, rotateY: 5 }}
                  style={{ transformStyle: "preserve-3d" }}
                >
                  <MagicBentoCard
                    enableStars={true}
                    enableBorderGlow={true}
                    enableTilt={true}
                    enableMagnetism={false}
                    clickEffect={true}
                    particleCount={12}
                    glowColor="59, 130, 246"
                    className="h-full"
                  >
                    <Card className="h-full border-2 border-blue-200 hover:border-blue-400 hover:shadow-2xl transition-all group cursor-pointer bg-white/80 backdrop-blur-sm">
                      <CardHeader>
                        <div className="flex items-start gap-4">
                          <motion.div
                            whileHover={{ rotate: 360, scale: 1.1 }}
                            transition={{ duration: 0.6 }}
                            className="p-4 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 shadow-lg"
                          >
                            <agent.icon className="w-6 h-6 text-white" />
                          </motion.div>
                          <div className="flex-1">
                            <CardTitle className="text-lg group-hover:text-blue-600 transition-colors mb-2">
                              {agent.title}
                            </CardTitle>
                            <CardDescription className="text-sm">
                              {agent.description}
                            </CardDescription>
                          </div>
                        </div>
                      </CardHeader>
                    </Card>
                  </MagicBentoCard>
                </motion.div>
              ))}
            </div>
          </MagicBentoGrid>
        </div>
      </section>

      {/* Tech Stack Section */}
      <section className="relative px-6 py-16 bg-white">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: -30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <Badge variant="secondary" className="mb-4 border-blue-300 bg-blue-50 text-blue-700">
              <Network size={14} />
              Technology Stack
            </Badge>
            <h2 className="text-4xl md:text-5xl font-black text-gray-900 mb-4">
              Built with Modern Technologies
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Powered by industry-leading databases and AI models for enterprise-grade knowledge management.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            {techStack.map((tech, i) => (
              <motion.div
                key={tech.name}
                initial={{ opacity: 0, x: i % 2 === 0 ? -50 : 50 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, type: "spring", stiffness: 100 }}
                whileHover={{ scale: 1.05, boxShadow: "0 20px 40px rgba(59, 130, 246, 0.3)" }}
                className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border-2 border-blue-200 hover:border-blue-400 transition-all shadow-sm"
              >
                <h3 className="text-xl font-bold text-gray-900 mb-2">{tech.name}</h3>
                <p className="text-sm text-gray-600">{tech.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative px-6 py-20 bg-gradient-to-br from-blue-600 via-cyan-600 to-blue-700 overflow-hidden">
        <motion.div
          animate={{ scale: [1, 1.2, 1], opacity: [0.1, 0.2, 0.1] }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-white/10 blur-3xl"
        />
        <motion.div
          animate={{ scale: [1, 1.3, 1], opacity: [0.1, 0.15, 0.1] }}
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
          className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full bg-white/10 blur-3xl"
        />
        
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="space-y-8"
          >
            <h2 className="text-4xl md:text-5xl font-black text-white">
              Ready to Query Your Knowledge Base?
            </h2>
            <p className="text-xl text-white/90 max-w-2xl mx-auto">
              Start ingesting data from Slack, PDFs, Excel, or audio files and query your organizational memory instantly.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4">
              <Button 
                asChild 
                size="lg" 
                className="bg-white hover:bg-gray-100 shadow-2xl border-2 border-white"
              >
                <Link href="/query" className="text-white">
                  Start Querying
                  <ArrowRight size={20} className="text-white" />
                </Link>
              </Button>
              <Button 
                asChild 
                size="lg" 
                variant="outline"
                className="border-2 border-white text-white hover:bg-white/10"
              >
                <Link href="/activity">
                  View Activity
                </Link>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
