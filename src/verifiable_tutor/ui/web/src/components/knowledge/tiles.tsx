import { EllipsisIcon, FileTextIcon, FolderIcon, MoveIcon, TrashIcon } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Spinner } from "@/components/ui/spinner";
import type { KnowledgeDocument, KnowledgeFolder } from "@/lib/api/knowledge";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/** The status chip a file tile and the info pane both render. */
export function StatusBadge({ status }: { status: KnowledgeDocument["status"] }) {
  const t = useT();
  const label = {
    uploading: t.knowledge.statusUploading,
    uploaded: t.knowledge.statusUploaded,
    upload_failed: t.knowledge.statusFailed,
    processing: t.knowledge.statusProcessing,
    ready: t.knowledge.statusReady,
    failed: t.knowledge.statusFailed,
  }[status];
  if (status === "ready") {
    return null;
  }
  if (status === "processing" || status === "uploaded" || status === "uploading") {
    return (
      <Badge variant="secondary" className="gap-1">
        <Spinner className="size-3" />
        {label}
      </Badge>
    );
  }
  return <Badge variant="destructive">{label}</Badge>;
}

function TileActions({
  label,
  onMove,
  onDelete,
  canDelete,
  moveLabel,
  deleteLabel,
}: {
  label: string;
  onMove: () => void;
  onDelete: () => void;
  canDelete: boolean;
  moveLabel: string;
  deleteLabel: string;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label={label}
          className="flex size-6 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
          onClick={(event) => event.stopPropagation()}
        >
          <EllipsisIcon className="size-4" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={onMove}>
          <MoveIcon />
          {moveLabel}
        </DropdownMenuItem>
        {canDelete ? (
          <DropdownMenuItem variant="destructive" onSelect={onDelete}>
            <TrashIcon />
            {deleteLabel}
          </DropdownMenuItem>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** One file: its real first page as the icon, its name, and its status. */
export function FileTile({
  document,
  selected,
  preview,
  canDelete,
  onSelect,
  onOpen,
  onMove,
  onDelete,
}: {
  document: KnowledgeDocument;
  selected: boolean;
  preview: boolean;
  canDelete: boolean;
  onSelect: () => void;
  onOpen: () => void;
  onMove: () => void;
  onDelete: () => void;
}) {
  const t = useT();
  const [thumbnailFailed, setThumbnailFailed] = useState(false);
  const showThumbnail = !preview && !thumbnailFailed;

  return (
    <div
      data-testid={`file-tile-${document.id}`}
      aria-current={selected ? "true" : undefined}
      className={cn(
        "group relative flex flex-col gap-2 rounded-md border p-2 text-left transition-colors",
        selected ? "border-foreground/40 bg-muted" : "hover:bg-muted/60",
      )}
    >
      <button type="button" className="block w-full text-left" onClick={onSelect} onDoubleClick={onOpen}>
        <span className="sr-only">{t.knowledge.openFile}</span>
        <span className="relative flex h-28 w-full items-center justify-center overflow-hidden rounded-sm bg-muted">
          {showThumbnail ? (
            <img
              src={document.thumbnail_url}
              alt=""
              loading="lazy"
              className="h-full w-full object-cover object-top"
              onError={() => setThumbnailFailed(true)}
            />
          ) : (
            <FileTextIcon className="size-8 text-muted-foreground" />
          )}
          {document.status === "uploading" ? (
            <span className="absolute inset-0 bg-background/60" />
          ) : null}
          {document.status === "uploaded" || document.status === "processing" ? (
            <span className="absolute inset-0 animate-pulse bg-background/50" />
          ) : null}
        </span>
        <span className="mt-2 line-clamp-2 block break-words text-[13px] font-medium leading-snug">
          {document.title}
        </span>
      </button>
      <span className="flex h-6 items-center gap-1">
        <StatusBadge status={document.status} />
        <span className="ml-auto">
          <TileActions
            label={t.knowledge.moreActions}
            moveLabel={t.knowledge.moveFile}
            deleteLabel={t.knowledge.deleteFile}
            canDelete={canDelete}
            onMove={onMove}
            onDelete={onDelete}
          />
        </span>
      </span>
    </div>
  );
}

/** One folder: same tile box as a file so the two rows stay visually balanced. */
export function FolderTile({
  folder,
  canDelete,
  onOpen,
  onMove,
  onDelete,
}: {
  folder: KnowledgeFolder;
  canDelete: boolean;
  onOpen: () => void;
  onMove: () => void;
  onDelete: () => void;
}) {
  const t = useT();
  return (
    <div className="group relative flex flex-col gap-2 rounded-md border p-2">
      <button type="button" className="block w-full text-left" onClick={onOpen} onDoubleClick={onOpen}>
        <span className="sr-only">{t.knowledge.openFolder}</span>
        <span className="flex h-28 w-full items-center justify-center rounded-sm bg-muted">
          <FolderIcon className="size-10 text-muted-foreground" />
        </span>
        <span className="mt-2 line-clamp-2 block break-words text-[13px] font-medium leading-snug">
          {folder.name}
        </span>
      </button>
      <span className="flex h-6 items-center text-xs text-muted-foreground">
        {t.knowledge.total.replace("{{count}}", String(folder.file_count))}
        <span className="ml-auto">
          <TileActions
            label={t.knowledge.folderActions}
            moveLabel={t.knowledge.moveFolder}
            deleteLabel={t.knowledge.deleteFolder}
            canDelete={canDelete}
            onMove={onMove}
            onDelete={onDelete}
          />
        </span>
      </span>
    </div>
  );
}
