import { PlusIcon, SearchIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { FileInfoPane } from "@/components/knowledge/file-info-pane";
import {
  ConfirmDeleteDialog,
  MoveDialog,
  NewFolderDialog,
} from "@/components/knowledge/dialogs";
import { SearchResults } from "@/components/knowledge/search-results";
import { FileTile, FolderTile } from "@/components/knowledge/tiles";
import { SidePane } from "@/components/layout/side-pane";
import { PageEmpty, PageError, PageLoading } from "@/components/layout/page-states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";
import { knowledgeApi, type KnowledgeDocument, type KnowledgeFolder, type SearchDocument } from "@/lib/api/knowledge";
import { useSession } from "@/lib/auth/session";
import { format, useT } from "@/lib/i18n";
import { usePreview } from "@/lib/preview/context";

const SEARCH_DEBOUNCE_MS = 200;
const PANE_WIDTH_KEY = "vt.knowledge.pane.width";
const PANE_COLLAPSED_KEY = "vt.knowledge.pane.collapsed";

type Pending =
  | { kind: "new-folder" }
  | { kind: "move"; target: "folder" | "document"; id: string; name: string }
  | { kind: "delete"; target: "folder" | "document"; id: string; name: string }
  | null;

function previewFolders(): KnowledgeFolder[] {
  return [
    {
      id: "preview-lectures",
      name: "Lectures",
      parent_id: null,
      position: 0,
      created_at: "2026-11-05T04:00:00+00:00",
      file_count: 1,
      path: [{ id: "preview-lectures", name: "Lectures" }],
    },
  ];
}

function previewDocument(
  id: string,
  folderId: string | null,
  pages: number,
): KnowledgeDocument {
  return {
    id,
    title: id,
    filename: `${id}.pdf`,
    folder_id: folderId,
    page_count: pages,
    chunk_count: pages,
    byte_size: 10470744,
    status: "ready",
    status_detail: null,
    summary: "Preview summary written by Qwen on TACC.",
    summary_model: "qwen3.8-27b",
    created_at: "2026-11-05T04:00:00+00:00",
    indexed_at: "2026-11-05T04:20:00+00:00",
    pdf_url: `/api/knowledge/documents/${id}/file`,
    thumbnail_url: `/api/corpus/${id}/pages/1.webp`,
  };
}

function previewDocuments(folderId: string | null): KnowledgeDocument[] {
  const all = [
    previewDocument("ACS_Lecture_1_2026F", "preview-lectures", 67),
    previewDocument("ACS_lecture_2_2026F", "preview-lectures", 69),
    previewDocument("Tutorial_2", null, 25),
    previewDocument("course_project", null, 8),
  ];
  return all.filter((document) => document.folder_id === folderId);
}

export function KnowledgePage() {
  const t = useT();
  const navigate = useNavigate();
  const { isPreview: preview, pageState } = usePreview();
  const { user } = useSession();
  const [params, setParams] = useSearchParams();
  const folderId = params.get("folder");
  const canDelete = user?.role === "instructor";

  const [folders, setFolders] = useState<KnowledgeFolder[]>(() =>
    preview ? previewFolders() : [],
  );
  const [documents, setDocuments] = useState<KnowledgeDocument[]>(() =>
    preview ? previewDocuments(null) : [],
  );
  const [loading, setLoading] = useState(!preview);
  const [failed, setFailed] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchDocument[] | null>(null);
  const [dragging, setDragging] = useState(false);
  const [dropNotice, setDropNotice] = useState(false);
  const [pending, setPending] = useState<Pending>(null);
  const [paneCollapsed, setPaneCollapsed] = useState(false);

  const reload = useCallback(() => setReloadToken((value) => value + 1), []);

  useEffect(() => {
    if (preview) {
      setFolders(previewFolders());
      setDocuments(previewDocuments(folderId));
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setFailed(false);
    Promise.all([
      knowledgeApi.folders(controller.signal),
      knowledgeApi.documents({ folder_id: folderId, limit: 200 }, controller.signal),
    ])
      .then(([tree, listing]) => {
        setFolders(tree.folders);
        setDocuments(listing.documents);
        setLoading(false);
      })
      .catch((error: unknown) => {
        if ((error as { name?: string }).name === "AbortError") {
          return;
        }
        setFailed(true);
        setLoading(false);
      });
    return () => controller.abort();
  }, [folderId, preview, reloadToken]);

  useEffect(() => {
    const needle = query.trim();
    if (needle.length === 0) {
      setHits(null);
      return;
    }
    if (preview) {
      setHits(
        previewDocuments(folderId).map((document) => ({
          ...document,
          matches: [
            {
              kind: "filename" as const,
              page_no: null,
              snippet: document.filename,
              highlights: [
                [
                  Math.max(document.filename.toLowerCase().indexOf(needle.toLowerCase()), 0),
                  Math.max(document.filename.toLowerCase().indexOf(needle.toLowerCase()), 0) +
                    needle.length,
                ],
              ] as [number, number][],
            },
          ],
        })),
      );
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      knowledgeApi
        .search(needle, controller.signal)
        .then((body) => setHits(body.documents))
        .catch((error: unknown) => {
          if ((error as { name?: string }).name !== "AbortError") {
            setHits([]);
          }
        });
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [folderId, preview, query]);

  const currentFolder = useMemo(
    () => folders.find((folder) => folder.id === folderId) ?? null,
    [folderId, folders],
  );
  const selected = useMemo(
    () => documents.find((document) => document.id === selectedId) ?? null,
    [documents, selectedId],
  );

  function goToFolder(next: string | null) {
    setSelectedId(null);
    if (next === null) {
      setParams({});
    } else {
      setParams({ folder: next });
    }
  }

  function openDocument(id: string) {
    const from = folderId === null ? "" : `&from=${encodeURIComponent(folderId)}`;
    navigate(`/knowledge/docs/${id}?page=1${from}`);
  }

  async function createFolder(name: string) {
    setPending(null);
    if (preview) {
      return;
    }
    await knowledgeApi.createFolder({ name, parent_id: folderId ?? null });
    reload();
  }

  async function moveTo(target: string | null) {
    if (pending?.kind !== "move") {
      return;
    }
    const action = pending;
    setPending(null);
    if (preview) {
      return;
    }
    if (action.target === "folder") {
      await knowledgeApi.updateFolder(action.id, { parent_id: target });
    } else {
      await knowledgeApi.moveDocument(action.id, target);
      setSelectedId(null);
    }
    reload();
  }

  async function confirmDelete() {
    if (pending?.kind !== "delete") {
      return;
    }
    const action = pending;
    setPending(null);
    if (preview) {
      return;
    }
    if (action.target === "folder") {
      await knowledgeApi.deleteFolder(action.id);
    } else {
      await knowledgeApi.deleteDocument(action.id);
      setSelectedId(null);
    }
    reload();
  }

  const moveExcluded = useMemo(() => {
    if (pending?.kind !== "move" || pending.target !== "folder") {
      return [];
    }
    const movingId = pending.id;
    return [
      movingId,
      ...folders
        .filter((folder) => folder.path.some((segment) => segment.id === movingId))
        .map((folder) => folder.id),
    ];
  }, [folders, pending]);

  const searching = query.trim().length > 0;
  const visibleDocuments = searching ? [] : documents;
  const showEmpty =
    !loading && !failed && !searching && folders.length === 0 && documents.length === 0;

  return (
    <div className="flex min-h-0 min-w-0 flex-1">
      <section className="flex min-w-0 flex-1 flex-col" aria-label={t.knowledge.title}>
        <h1 className="sr-only">{t.knowledge.title}</h1>
        <div className="flex flex-wrap items-center gap-2 border-b px-4 py-2">
          <nav aria-label={t.knowledge.title} className="flex min-w-0 items-center gap-1 text-sm">
            <button
              type="button"
              className="rounded-sm px-1 text-muted-foreground hover:text-foreground"
              onClick={() => goToFolder(null)}
            >
              {t.knowledge.root}
            </button>
            {(currentFolder?.path ?? []).map((segment) => (
              <span key={segment.id} className="flex items-center gap-1">
                <span aria-hidden="true" className="text-muted-foreground">
                  /
                </span>
                <button
                  type="button"
                  className="truncate rounded-sm px-1 hover:text-foreground"
                  onClick={() => goToFolder(segment.id)}
                >
                  {segment.name}
                </button>
              </span>
            ))}
          </nav>

          <InputGroup className="ml-auto w-full sm:max-w-xs">
            <InputGroupAddon>
              <SearchIcon />
            </InputGroupAddon>
            <InputGroupInput
              aria-label={t.knowledge.searchTitle}
              placeholder={t.knowledge.searchPlaceholder}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </InputGroup>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                size="icon"
                variant="outline"
                aria-label={t.knowledge.newMenu}
                title={t.knowledge.newMenu}
              >
                <PlusIcon />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem disabled title={t.knowledge.uploadDisabled}>
                {t.knowledge.uploadFile}
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => setPending({ kind: "new-folder" })}>
                {t.knowledge.newFolder}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Badge variant="secondary" className="h-8 px-3">
            {format(documents.length === 1 ? t.knowledge.totalOne : t.knowledge.total, {
              count: documents.length,
            })}
          </Badge>
        </div>

        <div
          className="relative min-h-0 flex-1 overflow-y-auto p-4"
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            setDropNotice(true);
          }}
        >
          {dragging || dropNotice ? (
            <div className="mb-3 flex items-center gap-2 rounded-md border border-dashed bg-muted/60 px-3 py-2 text-sm text-muted-foreground">
              <span>{t.knowledge.uploadDisabled}</span>
              {dropNotice ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="ml-auto"
                  onClick={() => setDropNotice(false)}
                >
                  {t.knowledge.cancel}
                </Button>
              ) : null}
            </div>
          ) : null}

          {loading ? (
            <PageLoading label={t.knowledge.loading} />
          ) : failed || pageState === "error" ? (
            <PageError title={t.common.errorTitle} description={t.common.errorBody} />
          ) : pageState === "empty" || showEmpty ? (
            <PageEmpty title={t.knowledge.emptyTitle} description={t.knowledge.emptyBody} />
          ) : searching ? (
            <SearchResults
              query={query}
              documents={hits ?? []}
              onOpen={(docId) => {
                setSelectedId(docId);
                openDocument(docId);
              }}
            />
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {folders
                .filter((folder) => folder.parent_id === folderId)
                .map((folder) => (
                  <FolderTile
                    key={folder.id}
                    folder={folder}
                    canDelete={canDelete}
                    onOpen={() => goToFolder(folder.id)}
                    onMove={() =>
                      setPending({
                        kind: "move",
                        target: "folder",
                        id: folder.id,
                        name: folder.name,
                      })
                    }
                    onDelete={() =>
                      setPending({
                        kind: "delete",
                        target: "folder",
                        id: folder.id,
                        name: folder.name,
                      })
                    }
                  />
                ))}
              {visibleDocuments.map((document) => (
                <FileTile
                  key={document.id}
                  document={document}
                  preview={preview}
                  selected={document.id === selectedId}
                  canDelete={canDelete}
                  onSelect={() => setSelectedId(document.id)}
                  onOpen={() => openDocument(document.id)}
                  onMove={() =>
                    setPending({
                      kind: "move",
                      target: "document",
                      id: document.id,
                      name: document.title,
                    })
                  }
                  onDelete={() =>
                    setPending({
                      kind: "delete",
                      target: "document",
                      id: document.id,
                      name: document.title,
                    })
                  }
                />
              ))}
            </div>
          )}
        </div>
      </section>

      <SidePane
        testId="knowledge-pane"
        label={t.knowledge.selectedTitle}
        collapsedLabel={t.knowledge.selectedTitle}
        collapseLabel={t.chat.evidenceCollapse}
        expandLabel={t.chat.evidenceExpand}
        resizeLabel={t.chat.evidenceResize}
        widthKey={PANE_WIDTH_KEY}
        collapsedKey={PANE_COLLAPSED_KEY}
        collapsed={paneCollapsed}
        onCollapsedChange={setPaneCollapsed}
        header={t.knowledge.selectedTitle}
      >
        <FileInfoPane document={selected} preview={preview} onAsk={openDocument} />
      </SidePane>

      <NewFolderDialog
        open={pending?.kind === "new-folder"}
        parentName={currentFolder?.name ?? t.knowledge.root}
        onCancel={() => setPending(null)}
        onCreate={createFolder}
      />
      <MoveDialog
        open={pending?.kind === "move"}
        title={pending?.kind === "move" ? pending.name : ""}
        folders={folders}
        excluded={moveExcluded}
        onCancel={() => setPending(null)}
        onConfirm={moveTo}
      />
      <ConfirmDeleteDialog
        open={pending?.kind === "delete"}
        title={
          pending?.kind === "delete"
            ? pending.target === "folder"
              ? t.knowledge.deleteFolder
              : t.knowledge.deleteFile
            : ""
        }
        description={
          pending?.kind === "delete"
            ? pending.target === "folder"
              ? format(t.knowledge.deleteFolderBody, {
                  count: folders.find((folder) => folder.id === pending.id)?.file_count ?? 0,
                })
              : t.knowledge.deleteFileBody
            : ""
        }
        onCancel={() => setPending(null)}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
