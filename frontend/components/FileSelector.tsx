"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Search, Calendar, CheckCircle2, Loader2, FileSpreadsheet, Music, Film, Image as ImageIcon, MessageSquare, File, RefreshCw, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { listFiles, deleteFile, FileMetadata } from "@/lib/api";
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
    window.addEventListener("focus", refreshOnFocus);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.removeEventListener("recallai:files-changed", refreshFiles);
      window.removeEventListener("focus", refreshOnFocus);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, []);

  const loadFiles = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listFiles();
      setFiles(data);
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
        setError('Cannot reach the backend. Make sure the server is running on port 8000.');
      } else {
        setError(msg);
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
      alert("Failed to delete file. Check console for details.");
    }
  };

  const filteredFiles = files.filter(
    (f) =>
      f.filename.toLowerCase().includes(search.toLowerCase()) ||
      f.type.toLowerCase().includes(search.toLowerCase())
  );

  const getFileIcon = (type: string) => {
    const iconMap: Record<string, any> = {
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
    <div className="flex flex-col h-full space-y-4">
      {/* Search Bar with Refresh */}
      <div className="flex gap-2 flex-shrink-0">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="Search by filename or type..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10 h-12 text-base border-2 focus:border-[var(--warm-orange)] rounded-xl"
          />
        </div>
        <button
          onClick={loadFiles}
          disabled={loading}
          className="px-4 h-12 rounded-xl border-2 border-gray-200 hover:border-[var(--warm-orange)] hover:bg-[var(--warm-orange)]/10 transition-all disabled:opacity-50"
          title="Refresh files"
        >
          <RefreshCw className={`w-5 h-5 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Loading State */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-4 flex-1">
          <Loader2 className="w-8 h-8 text-[var(--warm-orange)] animate-spin" />
          <p className="text-sm text-gray-500">Loading your files...</p>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-4 flex-1 text-center">
          <p className="text-sm text-red-500">{error}</p>
          <button
            onClick={loadFiles}
            className="px-4 py-2 rounded-xl border border-gray-300 hover:border-[var(--warm-orange)] transition-colors"
          >
            Try again
          </button>
        </div>
      ) : filteredFiles.length === 0 ? (
        /* Empty State */
        <div className="flex flex-col items-center justify-center py-16 space-y-4 flex-1">
          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center">
            <FileText className="w-8 h-8 text-gray-400" />
          </div>
          <div className="text-center">
            <p className="text-base font-semibold text-gray-900">
              {search ? "No files match your search" : "No files uploaded yet"}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              {search ? "Try a different search term" : "Upload your first file to get started"}
            </p>
          </div>
        </div>
      ) : (
        /* File Grid */
        <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
          <div className="grid gap-1.5 pb-2">
            <AnimatePresence>
              {filteredFiles.map((file, i) => {
              const Icon = getFileIcon(file.type);
              const isSelected = selectedSource === file.source;
              
              return (
                <motion.div
                  key={file.source}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ delay: i * 0.05 }}
                  whileHover={{ scale: 1.02, y: -2 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Card
                    className={`cursor-pointer transition-all duration-200 ${
                      isSelected
                        ? "border-2 border-[var(--warm-orange)] bg-[var(--warm-orange)]/10 shadow-lg"
                        : "border-2 border-gray-200 hover:border-[var(--warm-orange-light)] hover:shadow-md"
                    }`}
                    onClick={() => onSelectFile(file.source, file.filename)}
                  >
                    <CardContent className="p-2.5">
                      <div className="flex items-center gap-3">
                        {/* Icon */}
                        <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${getFileColor(file.type)} flex items-center justify-center flex-shrink-0 shadow-md`}>
                          <Icon className="w-4 h-4 text-white" />
                        </div>
                        
                        {/* File Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            <h4 className="font-semibold text-xs text-gray-900 truncate">
                              {file.filename}
                            </h4>
                            {isSelected && (
                              <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ type: "spring", stiffness: 500, damping: 30 }}
                              >
                                <CheckCircle2 className="w-4 h-4 text-[var(--warm-orange)] flex-shrink-0" />
                              </motion.div>
                            )}
                          </div>
                          
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge variant="outline" className="text-xs font-medium py-0 px-1.5">
                              {file.type.toUpperCase()}
                            </Badge>
                            {file.uploaded_at && (
                              <span className="flex items-center gap-1 text-xs text-gray-500">
                                <Calendar className="w-3 h-3" />
                                {new Date(file.uploaded_at).toLocaleDateString('en-US', {
                                  month: 'short',
                                  day: 'numeric',
                                  year: 'numeric'
                                })}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Delete Button */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setFileToDelete(file);
                            setDeleteConfirmText("");
                          }}
                          className="p-2 rounded-full text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                          title="Delete file"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </AnimatePresence>
          </div>
        </div>
      )}

      {/* File Count */}
      {!loading && filteredFiles.length > 0 && (
        <div className="text-center pt-2 border-t flex-shrink-0">
          <p className="text-xs text-gray-500">
            {filteredFiles.length} {filteredFiles.length === 1 ? 'file' : 'files'} available
            {search && ` matching "${search}"`}
          </p>
        </div>
      )}

      {/* Strict Delete Confirmation Modal */}
      <Dialog open={!!fileToDelete} onOpenChange={(open) => !open && setFileToDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-600">Delete File Permanently</DialogTitle>
            <DialogDescription>
              This action cannot be undone. This will permanently delete <strong>{fileToDelete?.filename}</strong> and all decisions, alternatives, people, and extracted metadata associated with it from the knowledge graph and Chroma DB.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm font-medium mb-2 text-gray-900">
              Please type <strong className="text-red-600 font-bold select-none">DELETE</strong> to confirm.
            </p>
            <Input
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              placeholder="Type DELETE"
              className="border-red-200 focus:border-red-500"
            />
          </div>
          <DialogFooter>
            <button
              onClick={() => setFileToDelete(null)}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
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
