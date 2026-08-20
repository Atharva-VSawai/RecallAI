"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Search, Calendar, CheckCircle2, Loader2, FileSpreadsheet, Music, Film, Image as ImageIcon, MessageSquare, File, RefreshCw, Trash2, type LucideIcon } from "lucide-react";
import { Input } from "@/components/ui/input";
import { listFiles, deleteFile, FileMetadata } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface FileSelectorProps {
  onSelectFile: (source: string, filename: string) => void;
  selectedSource?: string;
}

export default function FileSelector({ onSelectFile, selectedSource }: FileSelectorProps) {
  const { activeProject, can } = useAuth();
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [fileToDelete, setFileToDelete] = useState<FileMetadata | null>(null);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  // Debounce ref: prevents spamming the API on every focus/visibility event.
  // The initial load is immediate; subsequent background refreshes are throttled.
  const lastRefreshRef = useRef<number>(0);

  useEffect(() => {
    loadFiles();

    const debounced = (minIntervalMs: number) => () => {
      const now = Date.now();
      if (now - lastRefreshRef.current >= minIntervalMs) {
        lastRefreshRef.current = now;
        loadFiles();
      }
    };

    // Immediate on custom event (user just uploaded a file).
    const refreshFiles = () => loadFiles();
    // Throttle focus/visibility refreshes to at most once every 10 s.
    const refreshWhenVisible = debounced(10_000);
    const refreshOnFocus = debounced(10_000);

    window.addEventListener("recallai:files-changed", refreshFiles);
    window.addEventListener("recallai:project-changed", refreshFiles);
    window.addEventListener("focus", refreshOnFocus);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.removeEventListener("recallai:files-changed", refreshFiles);
      window.removeEventListener("recallai:project-changed", refreshFiles);
      window.removeEventListener("focus", refreshOnFocus);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, []);

  const loadFiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listFiles();
      setFiles(data.files);
    } catch (error) {
      console.error('Error loading files:', error);
      setFiles([]);
      const msg = error instanceof Error ? error.message : 'Failed to fetch files';
      const isSessionError =
        msg.toLowerCase().includes('session') ||
        msg.toLowerCase().includes('sign in') ||
        msg.toLowerCase().includes('expired');
      const isOffline =
        msg.toLowerCase().includes('cannot reach') ||
        msg.toLowerCase().includes('failed to fetch') ||
        msg.toLowerCase().includes('networkerror');
      if (isSessionError) {
        setError('Your session has expired. Please sign in again.');
      } else if (isOffline) {
        setError('We couldn’t reach your knowledge sources. Please try again.');
      } else {
        setError('We couldn’t load your knowledge sources. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!fileToDelete) return;
    if (deleteConfirmText !== "DELETE") return;
    
    setIsDeleting(true);
    const success = await deleteFile(fileToDelete.source);
    setIsDeleting(false);
    
    if (success) {
      setFileToDelete(null);
      setDeleteConfirmText("");
      loadFiles();
      if (selectedSource === fileToDelete.source) {
        onSelectFile("", "");
      }
    } else {
      setError("We couldn’t delete this source. Please try again.");
    }
  };

  const filteredFiles = files.filter(
    (f) =>
      f.filename.toLowerCase().includes(search.toLowerCase()) ||
      (f.type ?? "").toLowerCase().includes(search.toLowerCase())
  );

  const getFileIcon = (type: string) => {
    const iconMap: Record<string, LucideIcon> = {
      pdf: FileText,
      xlsx: FileSpreadsheet,
      xls: FileSpreadsheet,
      png: ImageIcon,
      jpg: ImageIcon,
      jpeg: ImageIcon,
      gif: ImageIcon,
      webp: ImageIcon,
      mp3: Music,
      wav: Music,
      m4a: Music,
      mp4: Film,
      mov: Film,
      avi: Film,
      slack: MessageSquare,
    };
    return iconMap[type] || File;
  };

  const getFileColor = (type: string) => {
    if (['pdf'].includes(type)) return 'from-red-500 to-red-600';
    if (['xlsx', 'xls'].includes(type)) return 'from-green-500 to-green-600';
    if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(type)) return 'from-purple-500 to-purple-600';
    if (['mp3', 'wav', 'm4a'].includes(type)) return 'from-orange-500 to-orange-600';
    if (['mp4', 'mov', 'avi'].includes(type)) return 'from-pink-500 to-pink-600';
    return 'from-gray-500 to-gray-600';
  };

  return (
    <div className="flex h-full min-h-0 flex-col space-y-3">
      <div className="rounded-xl border border-card-border bg-card/40 p-3">
        <p className="text-xs font-bold uppercase tracking-widest text-foreground-dim">Sources in workspace</p>
        <div className="mt-1 flex items-center justify-between gap-3">
          <p className="min-w-0 truncate text-sm font-semibold text-foreground">
            {activeProject?.name ?? "Active project"}
          </p>
          <span className="rounded-md border border-card-border px-2 py-1 text-[10px] font-bold text-foreground-dim">
            {files.length} {files.length === 1 ? "source" : "sources"}
          </span>
        </div>
      </div>

      <div className="flex flex-shrink-0 gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground-dim" />
          <Input
            placeholder="Search sources..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="glow-input h-11 rounded-lg border-card-border bg-card/50 pl-10 text-sm"
          />
        </div>
        <button
          onClick={loadFiles}
          disabled={loading}
          className="h-11 rounded-lg border border-card-border px-3 text-foreground-muted transition-colors hover:bg-card-hover hover:text-foreground disabled:opacity-50"
          title="Refresh files"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading ? (
        <div className="flex flex-1 flex-col items-center justify-center space-y-3 py-16">
          <Loader2 className="h-6 w-6 animate-spin text-accent" />
          <p className="text-sm text-foreground-muted">Loading project sources...</p>
        </div>
      ) : error ? (
        <div className="flex flex-1 flex-col items-center justify-center space-y-4 py-16 text-center">
          <p className="text-sm text-danger">{error}</p>
          <button
            onClick={loadFiles}
            className="rounded-lg border border-card-border px-4 py-2 text-sm text-foreground-muted transition-colors hover:bg-card-hover hover:text-foreground"
          >
            Try again
          </button>
        </div>
      ) : filteredFiles.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center space-y-4 py-16">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-card-border bg-card">
            <FileText className="h-6 w-6 text-foreground-dim" />
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-foreground">
              {search ? "No files match your search" : "No files uploaded yet"}
            </p>
            <p className="mt-1 text-xs text-foreground-dim">
              {search ? "Try another filename or source type." : "Sources added here stay isolated to this project."}
            </p>
          </div>
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto pr-1 custom-scrollbar">
          <div className="overflow-hidden rounded-xl border border-card-border">
            <AnimatePresence>
              {filteredFiles.map((file, i) => {
              const safeType = file.type ?? "";
              const Icon = getFileIcon(safeType);
              const isSelected = selectedSource === file.source;
              
              return (
                <motion.div
                  key={file.source}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ delay: Math.min(i * 0.02, 0.12) }}
                >
                  <div
                    className={`group flex w-full items-center gap-3 border-b border-card-border px-3 py-3 text-left transition-colors last:border-b-0 ${
                      isSelected ? "bg-accent/10" : "bg-card/25 hover:bg-card-hover"
                    }`}
                  >
                    <button
                      onClick={() => onSelectFile(file.source, file.filename)}
                      className="flex min-w-0 flex-1 items-center gap-3 text-left"
                    >
                      <div className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${getFileColor(safeType)}`}>
                        <Icon className="h-4 w-4 text-white" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="truncate text-sm font-semibold text-foreground">
                            {file.filename}
                          </p>
                          {isSelected && (
                            <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-accent" />
                          )}
                        </div>
                        <div className="mt-1 flex items-center gap-2 text-[11px] text-foreground-dim">
                          {safeType && (
                          <span className="rounded border border-card-border px-1.5 py-0.5 font-bold">
                            {safeType.toUpperCase()}
                          </span>
                          )}
                          {file.uploaded_at && (
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {new Date(file.uploaded_at).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric'
                              })}
                            </span>
                          )}
                        </div>
                      </div>
                    </button>

                    {can("knowledge:delete") && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setFileToDelete(file);
                          setDeleteConfirmText("");
                        }}
                        className="rounded-lg p-2 text-foreground-dim opacity-0 transition-all hover:bg-danger/10 hover:text-danger group-hover:opacity-100"
                        title="Delete file"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
                        </div>
        </div>
      )}

      {!loading && filteredFiles.length > 0 && (
        <div className="flex-shrink-0 border-t border-card-border pt-2 text-center">
          <p className="text-xs text-foreground-dim">
            {filteredFiles.length} {filteredFiles.length === 1 ? 'file' : 'files'} available
            {search && ` matching "${search}"`}
          </p>
        </div>
      )}

      {/* Strict Delete Confirmation Modal */}
      <Dialog open={!!fileToDelete} onOpenChange={(open) => !open && setFileToDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-danger">Delete source permanently</DialogTitle>
            <DialogDescription>
              This action cannot be undone. This will permanently delete <strong>{fileToDelete?.filename}</strong> and all decisions, alternatives, people, and extracted metadata associated with it from the knowledge graph and Chroma DB.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm font-medium mb-2 text-foreground">
              Please type <strong className="text-danger font-bold select-none">DELETE</strong> to confirm.
            </p>
            <Input
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              placeholder="Type DELETE"
              className="border-danger/40 focus:border-danger"
            />
          </div>
          <DialogFooter>
            <button
              onClick={() => setFileToDelete(null)}
              className="px-4 py-2 text-sm font-medium text-foreground-muted hover:bg-surface-elevated hover:text-foreground rounded-md transition-colors"
              disabled={isDeleting}
            >
              Cancel
            </button>
            <button
              onClick={handleDelete}
              disabled={deleteConfirmText !== "DELETE" || isDeleting}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              {isDeleting ? "Deleting..." : "Delete Permanently"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
