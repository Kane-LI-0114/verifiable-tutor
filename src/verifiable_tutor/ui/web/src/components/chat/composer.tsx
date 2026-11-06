import {
  ArrowUpIcon,
  AudioLinesIcon,
  ChevronDownIcon,
  MicIcon,
  PaperclipIcon,
  SquareIcon,
  XIcon,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Attachment,
  AttachmentAction,
  AttachmentActions,
  AttachmentContent,
  AttachmentDescription,
  AttachmentMedia,
  AttachmentTitle,
} from "@/components/ui/attachment";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@/components/ui/input-group";
import { useT } from "@/lib/i18n";
import {
  MODEL_OPTIONS,
  thinkingLevelsFor,
  type ModelId,
  type ThinkingLevel,
} from "@/lib/models";

const MODEL_LABEL_KEYS = {
  "deepseek-flash": "modelDeepSeekFlash",
  "mimo-flash": "modelMiMoFlash",
  "mimo-pro": "modelMiMoPro",
} as const;

const THINKING_LABEL_KEYS = {
  off: "thinkingOff",
  low: "thinkingLow",
  high: "thinkingHigh",
  max: "thinkingMax",
} as const;

export function Composer({
  value,
  onChange,
  onSubmit,
  onStop,
  streaming = false,
  model,
  onModelChange,
  thinking,
  onThinkingChange,
  audioAttached = false,
  onAttachAudio,
  onRemoveAudio,
  capabilityError,
  preview = false,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop?: () => void;
  streaming?: boolean;
  model: ModelId;
  onModelChange: (model: ModelId) => void;
  thinking: ThinkingLevel;
  onThinkingChange: (level: ThinkingLevel) => void;
  audioAttached?: boolean;
  onAttachAudio?: () => void;
  onRemoveAudio?: () => void;
  capabilityError?: string | null;
  preview?: boolean;
}) {
  const t = useT();
  const thinkingLevels = thinkingLevelsFor(model);
  const thinkingLabel = (level: ThinkingLevel) =>
    t.chat[
      model.startsWith("mimo") && level === "high"
        ? "thinkingOn"
        : THINKING_LABEL_KEYS[level]
    ];
  const canSend = value.trim().length > 0;

  return (
    <div
      role="group"
      className="shrink-0 border-t bg-background p-3"
      aria-label={t.a11y.composer}
    >
      {capabilityError ? (
        <Alert variant="destructive" className="mb-2">
          <AlertTitle>{t.chat.capabilityErrorTitle}</AlertTitle>
          <AlertDescription>{capabilityError}</AlertDescription>
        </Alert>
      ) : null}
      {audioAttached ? (
        <div className="mb-2">
          <Attachment size="sm">
            <AttachmentMedia>
              <AudioLinesIcon />
            </AttachmentMedia>
            <AttachmentContent>
              <AttachmentTitle>{t.chat.audioAttached}</AttachmentTitle>
              <AttachmentDescription>question.wav · MiMo ASR</AttachmentDescription>
            </AttachmentContent>
            <AttachmentActions>
              <AttachmentAction
                type="button"
                aria-label={t.chat.removeAudio}
                onClick={onRemoveAudio}
              >
                <XIcon />
              </AttachmentAction>
            </AttachmentActions>
          </Attachment>
        </div>
      ) : null}
      <InputGroup>
        <InputGroupTextarea
          aria-label={t.chat.composerLabel}
          placeholder={t.chat.composerPlaceholder}
          value={value}
          rows={2}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key !== "Enter" || event.shiftKey) {
              return;
            }
            // Enter also commits an IME candidate. While a composition is
            // active it must not send; keyCode 229 covers older IME engines.
            if (event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229) {
              return;
            }
            event.preventDefault();
            if (canSend && !streaming) {
              onSubmit();
            }
          }}
        />
        <InputGroupAddon align="block-end" className="gap-1">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <InputGroupButton size="sm" aria-label={t.a11y.modelSelector}>
                {t.chat[MODEL_LABEL_KEYS[model]]}
                <ChevronDownIcon />
              </InputGroupButton>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuRadioGroup
                value={model}
                onValueChange={(next) => onModelChange(next as ModelId)}
              >
                <DropdownMenuGroup>
                  <DropdownMenuLabel>{t.chat.model}</DropdownMenuLabel>
                  {MODEL_OPTIONS.map((option) => (
                    <DropdownMenuRadioItem key={option.id} value={option.id}>
                      {t.chat[MODEL_LABEL_KEYS[option.id]]}
                    </DropdownMenuRadioItem>
                  ))}
                </DropdownMenuGroup>
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <InputGroupButton size="sm">
                {thinkingLabel(thinking)}
                <ChevronDownIcon />
              </InputGroupButton>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuRadioGroup
                value={thinking}
                onValueChange={(next) => onThinkingChange(next as ThinkingLevel)}
              >
                <DropdownMenuGroup>
                  <DropdownMenuLabel>{t.chat.thinking}</DropdownMenuLabel>
                  {thinkingLevels.map((level) => (
                    <DropdownMenuRadioItem key={level} value={level}>
                      {thinkingLabel(level)}
                    </DropdownMenuRadioItem>
                  ))}
                </DropdownMenuGroup>
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            className="ml-1"
            aria-label={t.chat.attachAudio}
            title={preview ? t.chat.audioHint : t.common.unavailable}
            disabled={!preview}
            onClick={onAttachAudio}
          >
            <PaperclipIcon />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={t.chat.record}
            title={t.common.unavailable}
            disabled
          >
            <MicIcon />
          </Button>

          {streaming ? (
            <InputGroupButton
              type="button"
              size="icon-sm"
              className="ml-auto"
              aria-label={t.chat.stopStreaming}
              onClick={onStop}
            >
              <SquareIcon />
            </InputGroupButton>
          ) : (
            <InputGroupButton
              type="button"
              size="icon-sm"
              variant="default"
              className="ml-auto"
              aria-label={t.common.send}
              disabled={!canSend}
              onClick={onSubmit}
            >
              <ArrowUpIcon />
            </InputGroupButton>
          )}
        </InputGroupAddon>
      </InputGroup>
      <p className="mt-1.5 text-xs text-muted-foreground">
        {audioAttached ? t.chat.audioHint : preview ? t.common.previewNotice : null}
      </p>
    </div>
  );
}
