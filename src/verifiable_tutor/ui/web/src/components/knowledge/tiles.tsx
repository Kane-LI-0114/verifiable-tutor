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
          className="flex size-6 items-center justify-center rounded-md bg-background/80 text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
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

/**
 * One file: the real first page fills the whole card face, with the file name
 * on a bottom scrim and the status chip over the face.
 */
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
        // Locked 4:3 so pane resizes scale the whole card, never just its width.
        "group relative aspect-[4/3] overflow-hidden rounded-md border text-left transition-colors",
        selected ? "border-foreground/50 ring-1 ring-foreground/25" : "hover:border-foreground/30",
      )}
    >
      <span className="absolute inset-0 flex items-center justify-center overflow-hidden bg-muted">
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
      <button
        type="button"
        className="absolute inset-0 flex flex-col justify-end text-left"
        onClick={onSelect}
        onDoubleClick={onOpen}
      >
        <span className="sr-only">{t.knowledge.openFile}</span>
        <span className="pointer-events-none absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-background/95 to-transparent" />
        <span className="relative line-clamp-2 break-words px-2 pb-2 text-[13px] font-medium leading-snug">
          {document.title}
        </span>
      </button>
      <span className="pointer-events-none absolute left-2 top-2">
        <StatusBadge status={document.status} />
      </span>
      <span className="absolute right-2 top-2">
        <TileActions
          label={t.knowledge.moreActions}
          moveLabel={t.knowledge.moveFile}
          deleteLabel={t.knowledge.deleteFile}
          canDelete={canDelete}
          onMove={onMove}
          onDelete={onDelete}
        />
      </span>
    </div>
  );
}

/** One folder: same 4:3 card face as a file so the two kinds stay in step. */
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
    <div
      data-testid={`folder-tile-${folder.id}`}
      className="group relative aspect-[4/3] overflow-hidden rounded-md border text-left transition-colors hover:border-foreground/30"
    >
      <span className="absolute inset-0 flex items-center justify-center bg-muted/60 pb-8">
        <FolderIcon className="size-10 text-muted-foreground" />
      </span>
      <button
        type="button"
        className="absolute inset-0 flex flex-col justify-end text-left"
        onClick={onOpen}
        onDoubleClick={onOpen}
      >
        <span className="sr-only">{t.knowledge.openFolder}</span>
        <span className="pointer-events-none absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-background/95 to-transparent" />
        <span className="relative line-clamp-2 break-words px-2 pb-2 text-[13px] font-medium leading-snug">
          {folder.name}
        </span>
      </button>
      <span className="pointer-events-none absolute left-2 top-2">
        <Badge variant="secondary">
          {t.knowledge.total.replace("{{count}}", String(folder.file_count))}
        </Badge>
      </span>
      <span className="absolute right-2 top-2">
        <TileActions
          label={t.knowledge.folderActions}
          moveLabel={t.knowledge.moveFolder}
          deleteLabel={t.knowledge.deleteFolder}
          canDelete={canDelete}
          onMove={onMove}
          onDelete={onDelete}
        />
      </span>
    </div>
  );
}
