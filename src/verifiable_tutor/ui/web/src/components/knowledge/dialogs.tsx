import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { KnowledgeFolder } from "@/lib/api/knowledge";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function NewFolderDialog({
  open,
  parentName,
  onCancel,
  onCreate,
}: {
  open: boolean;
  parentName: string;
  onCancel: () => void;
  onCreate: (name: string) => void;
}) {
  const t = useT();
  const [name, setName] = useState("");

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          onCancel();
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t.knowledge.newFolder}</DialogTitle>
          <DialogDescription>{parentName}</DialogDescription>
        </DialogHeader>
        <Input
          aria-label={t.knowledge.folderName}
          placeholder={t.knowledge.folderName}
          value={name}
          maxLength={64}
          onChange={(event) => setName(event.target.value)}
        />
        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onCancel}>
            {t.knowledge.cancel}
          </Button>
          <Button
            type="button"
            disabled={name.trim().length === 0}
            onClick={() => {
              onCreate(name.trim());
              setName("");
            }}
          >
            {t.knowledge.create}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ConfirmDeleteDialog({
  open,
  title,
  description,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  title: string;
  description: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const t = useT();
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          onCancel();
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onCancel}>
            {t.knowledge.cancel}
          </Button>
          <Button type="button" variant="destructive" onClick={onConfirm}>
            {t.knowledge.confirmDelete}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Pick the destination folder; a folder cannot move into its own subtree. */
export function MoveDialog({
  open,
  title,
  folders,
  excluded,
  onCancel,
  onConfirm,
}: {
  open: boolean;
  title: string;
  folders: KnowledgeFolder[];
  excluded: string[];
  onCancel: () => void;
  onConfirm: (folderId: string | null) => void;
}) {
  const t = useT();
  const [target, setTarget] = useState<string | null>(null);
  const excludedSet = new Set(excluded);
  const options = folders.filter((folder) => !excludedSet.has(folder.id));

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          onCancel();
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{t.knowledge.moveBody}</DialogDescription>
        </DialogHeader>
        <div role="group" aria-label={t.knowledge.moveTo} className="max-h-72 space-y-1 overflow-y-auto">
          <button
            type="button"
            aria-pressed={target === null}
            className={cn(
              "block w-full rounded-md border px-3 py-2 text-left text-sm",
              target === null ? "bg-muted" : "hover:bg-muted/60",
            )}
            onClick={() => setTarget(null)}
          >
            {t.knowledge.rootFolder}
          </button>
          {options.map((folder) => (
            <button
              key={folder.id}
              type="button"
              aria-pressed={target === folder.id}
              className={cn(
                "block w-full rounded-md border px-3 py-2 text-left text-sm",
                target === folder.id ? "bg-muted" : "hover:bg-muted/60",
              )}
              onClick={() => setTarget(folder.id)}
            >
              {folder.path.map((segment) => segment.name).join(" / ")}
            </button>
          ))}
        </div>
        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onCancel}>
            {t.knowledge.cancel}
          </Button>
          <Button type="button" onClick={() => onConfirm(target)}>
            {t.knowledge.moveTo}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
