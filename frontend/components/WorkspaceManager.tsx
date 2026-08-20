"use client";

import { useState } from "react";
import { Pencil, Plus, Trash2, X } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { createProject, deleteProject, listProjectMembers, updateProject, updateProjectMember, type Project, type ProjectMember } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export default function WorkspaceManager({ onClose }: { onClose: () => void }) {
  const { projects, activeProject, can, refreshProjects } = useAuth();
  const [editing, setEditing] = useState<Project | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [membersOpen, setMembersOpen] = useState(false);
  const [membersBusy, setMembersBusy] = useState(false);

  const submit = async () => {
    if (!name.trim()) return;
    setBusy(true); setError(null);
    try {
      const saved = editing ? await updateProject(editing.id, name.trim()) : await createProject(name.trim());
      await refreshProjects(saved.id);
      setEditing(null); setName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Workspace operation failed");
    } finally { setBusy(false); }
  };

  const requestDelete = (project: Project) => {
    if (project.id === "main-workspace") return;
    setProjectToDelete(project);
    setDeleteConfirmText("");
  };

  const confirmDelete = async () => {
    if (!projectToDelete || deleteConfirmText !== "DELETE") return;
    setBusy(true); setError(null);
    try {
      await deleteProject(projectToDelete.id);
      setProjectToDelete(null); setDeleteConfirmText("");
      await refreshProjects();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete workspace");
    } finally { setBusy(false); }
  };

  const toggleMembers = async () => {
    if (!activeProject || !can("project:manage")) return;
    setMembersOpen((open) => !open);
    if (membersOpen) return;
    setMembersBusy(true);
    try { setMembers(await listProjectMembers(activeProject.id)); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to load project members"); }
    finally { setMembersBusy(false); }
  };

  const changeRole = async (member: ProjectMember, role: ProjectMember["role"]) => {
    if (!activeProject || member.role === "OWNER") return;
    setMembersBusy(true); setError(null);
    try {
      const updated = await updateProjectMember(activeProject.id, member.user_id, role);
      setMembers((current) => current.map((item) => item.user_id === updated.user_id ? updated : item));
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to update member role"); }
    finally { setMembersBusy(false); }
  };

  return <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 p-4" role="dialog" aria-modal="true" aria-labelledby="workspace-manager-title">
    <div className="w-full max-w-lg rounded-xl border border-card-border bg-background p-5 shadow-2xl">
      <div className="mb-4 flex items-start justify-between"><div><h2 id="workspace-manager-title" className="text-lg font-semibold">Manage workspaces</h2><p className="mt-1 text-sm text-foreground-muted">Create, rename, or remove project workspaces.</p></div><button onClick={onClose} aria-label="Close" className="rounded-md p-1 text-foreground-muted hover:bg-card"><X size={18}/></button></div>
      {can("project:manage") && <div className="mb-4 rounded-lg border border-card-border bg-card p-3"><p className="mb-2 text-xs font-medium">{editing ? "Rename workspace" : "New workspace"}</p><div className="flex gap-2"><Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Workspace name" maxLength={120} disabled={busy} onKeyDown={(event) => { if (event.key === "Enter") void submit(); }}/><Button size="sm" onClick={() => void submit()} disabled={busy || !name.trim()}>{editing ? "Save" : <><Plus size={14}/>Create</>}</Button>{editing && <Button size="sm" variant="ghost" onClick={() => { setEditing(null); setName(""); }}>Cancel</Button>}</div></div>}
      <div className="max-h-64 space-y-2 overflow-y-auto">{projects.map((project) => <div key={project.id} className={`flex items-center gap-3 rounded-lg border p-3 ${project.id === activeProject?.id ? "border-accent/50 bg-accent/5" : "border-card-border"}`}><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{project.name}</p><p className="text-xs text-foreground-dim">{project.role} · {project.slug}</p></div>{project.permissions.includes("project:manage") && <><Button size="icon" variant="ghost" aria-label={`Rename ${project.name}`} onClick={() => { setEditing(project); setName(project.name); }} disabled={busy}><Pencil size={14}/></Button>{project.id !== "main-workspace" && <Button size="icon" variant="ghost" aria-label={`Delete ${project.name}`} onClick={() => requestDelete(project)} disabled={busy}><Trash2 size={14}/></Button>}</>}</div>)}</div>
      {can("project:manage") && activeProject && <div className="mt-4 rounded-lg border border-card-border bg-card p-3"><div className="flex items-center justify-between gap-3"><div><p className="text-xs font-medium">Project members</p><p className="mt-1 text-xs text-foreground-dim">Control who can view or add knowledge.</p></div><Button size="sm" variant="outline" onClick={() => void toggleMembers()} disabled={membersBusy}>{membersOpen ? "Hide" : "Manage"}</Button></div>{membersOpen && <div className="mt-3 space-y-2">{membersBusy && <p className="text-xs text-foreground-dim">Loading members…</p>}{members.map((member) => <div key={member.user_id} className="flex items-center gap-2 rounded-md border border-card-border p-2"><div className="min-w-0 flex-1"><p className="truncate text-xs font-medium">{member.email || member.user_id}</p><p className="truncate text-[11px] text-foreground-dim">{member.user_id}</p></div>{member.role === "OWNER" ? <span className="text-[11px] font-medium text-foreground-dim">OWNER</span> : <select value={member.role} onChange={(event) => void changeRole(member, event.target.value as ProjectMember["role"])} disabled={membersBusy} className="rounded border border-card-border bg-background px-2 py-1 text-[11px] text-foreground"><option>ADMIN</option><option>MANAGER</option><option>CONTRIBUTOR</option><option>VIEWER</option></select>}</div>)}</div>}</div>}
      {error && <p className="mt-3 text-sm text-danger">{error}</p>}
    </div>
    <Dialog open={!!projectToDelete} onOpenChange={(open) => { if (!open && !busy) { setProjectToDelete(null); setDeleteConfirmText(""); } }}>
      <DialogContent className="z-[90]">
        <DialogHeader><DialogTitle className="text-red-600">Delete workspace permanently</DialogTitle><DialogDescription>This will permanently delete <strong>{projectToDelete?.name}</strong> and all of its indexed knowledge, graph data, vectors, and activity. This action cannot be undone.</DialogDescription></DialogHeader>
        <div className="py-2"><p className="mb-2 text-sm font-medium text-gray-900">Type <strong className="font-bold text-red-600 select-none">DELETE</strong> to confirm.</p><Input value={deleteConfirmText} onChange={(event) => setDeleteConfirmText(event.target.value)} placeholder="Type DELETE" className="border-red-200 focus:border-red-500" disabled={busy}/></div>
        <DialogFooter><Button variant="ghost" onClick={() => { setProjectToDelete(null); setDeleteConfirmText(""); }} disabled={busy}>Cancel</Button><Button onClick={() => void confirmDelete()} disabled={busy || deleteConfirmText !== "DELETE"} className="bg-red-600 text-white hover:bg-red-700"><Trash2 size={14}/>{busy ? "Deleting..." : "Delete permanently"}</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  </div>;
}
