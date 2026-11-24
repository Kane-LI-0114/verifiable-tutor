import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  Loader2Icon,
  Trash2Icon,
} from "lucide-react";

import { Markdown } from "@/components/ai/markdown";
import { PageEmpty, PageHeader } from "@/components/layout/page-states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  createPracticeSession,
  deletePracticeAttempt,
  getPracticeSession,
  gradePractice,
  savePracticeAnswers,
  startPracticeAttempt,
  submitPracticeAttempt,
  type GeneratedQuestion,
  type PracticeAttempt,
  type PracticeGradingResponse,
  type PracticeSession,
} from "@/lib/api/practice";
import { format, useT } from "@/lib/i18n";
import { gradeDeterministic } from "@/lib/practice/grading";
import { useConversations } from "@/lib/session/conversations";
import type { QuestionType } from "@/lib/types";

const TOPICS = [
  "all topics",
  "memory hierarchy",
  "FlashAttention",
  "MPI",
  "GEMM",
  "CUDA",
  "others",
];

const QUESTION_TYPES: QuestionType[] = [
  "single-choice",
  "multiple-choice",
  "true-false",
  "short-answer",
  "code",
];

function scoreColor(ratio: number): string {
  if (ratio >= 0.85) return "#22c55e";
  if (ratio >= 0.6) return "#eab308";
  if (ratio >= 0.4) return "#f97316";
  return "#b91c1c";
}

function ScoreRing({ score, max }: { score: number; max: number }) {
  const ratio = max > 0 ? Math.min(Math.max(score / max, 0), 1) : 0;
  const percent = Math.round(ratio * 100);
  const color = scoreColor(ratio);
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  return (
    <div className="flex flex-col items-center gap-2">
      <svg width="120" height="120" viewBox="0 0 120 120" role="img">
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeOpacity="0.15"
          strokeWidth="10"
        />
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${circumference * ratio} ${circumference * (1 - ratio)}`}
          transform="rotate(-90 60 60)"
        />
        <text
          x="60"
          y="60"
          textAnchor="middle"
          dominantBaseline="central"
          className="fill-foreground text-xl font-semibold"
        >
          {percent}%
        </text>
      </svg>
      <p className="text-sm text-muted-foreground">
        {Math.round(score)}/{Math.round(max)}
      </p>
    </div>
  );
}

function answerText(values: string[] | undefined): string {
  return (values ?? []).join(", ");
}

export function PracticePage() {
  const { sessionId } = useParams();
  return sessionId === undefined ? (
    <PracticeGenerator />
  ) : (
    <PracticeSessionView sessionId={sessionId} />
  );
}

function PracticeGenerator() {
  const t = useT();
  const navigate = useNavigate();
  const { refresh: refreshConversations } = useConversations();
  const [searchParams, setSearchParams] = useSearchParams();
  const [topic, setTopic] = useState("");
  const [customTopic, setCustomTopic] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [created, setCreated] = useState<PracticeSession | null>(null);

  const effectiveTopic = topic === "others" ? customTopic.trim() : topic.trim();

  async function generate(chosenTopic: string, types: string[]) {
    setGenerating(true);
    setGenerateError(null);
    setCreated(null);
    try {
      const session = await createPracticeSession(chosenTopic, types);
      setCreated(session);
      refreshConversations();
    } catch (error) {
      setGenerateError(
        error instanceof Error ? error.message : "question generation failed",
      );
    } finally {
      setGenerating(false);
    }
  }

  useEffect(() => {
    const topicParam = searchParams.get("topic");
    if (!topicParam) return;
    const types = (searchParams.get("types") ?? "").split(",").filter(Boolean);
    setTopic(topicParam);
    setSelectedTypes(types);
    setSearchParams({}, { replace: true });
    void generate(topicParam, types);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-4 p-6">
        <PageHeader title={t.practice.title} description={t.practice.subtitle} />

        <Card>
          <CardContent className="pt-6">
            <FieldGroup>
              <Field>
                <FieldLabel>{t.practice.topic}</FieldLabel>
                <Select value={topic} onValueChange={setTopic}>
                  <SelectTrigger>
                    <SelectValue placeholder={t.practice.topicPlaceholder} />
                  </SelectTrigger>
                  <SelectContent>
                    {TOPICS.map((item) => (
                      <SelectItem key={item} value={item}>
                        {item === "all topics"
                          ? t.practice.allTopics
                          : item === "others"
                            ? t.practice.others
                            : item}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              {topic === "others" ? (
                <Field>
                  <FieldLabel>{t.practice.topic}</FieldLabel>
                  <Input
                    value={customTopic}
                    placeholder={t.practice.topicPlaceholder}
                    onChange={(event) => setCustomTopic(event.target.value)}
                  />
                </Field>
              ) : null}
              <Field>
                <FieldLabel>{t.practice.type}</FieldLabel>
                <div className="space-y-2">
                  {QUESTION_TYPES.map((type) => (
                    <label key={type} className="flex items-center gap-2 text-sm">
                      <Checkbox
                        checked={selectedTypes.includes(type)}
                        onCheckedChange={(checked) =>
                          setSelectedTypes((current) =>
                            checked
                              ? [...current, type]
                              : current.filter((value) => value !== type),
                          )
                        }
                      />
                      {t.practice.types[type]}
                    </label>
                  ))}
                </div>
              </Field>
              <div className="flex flex-col items-start gap-1">
                <Button
                  type="button"
                  disabled={generating || !effectiveTopic}
                  onClick={() => {
                    void generate(effectiveTopic, selectedTypes);
                  }}
                >
                  {generating ? (
                    <Loader2Icon className="size-4 animate-spin" />
                  ) : null}
                  {generating ? t.practice.generating : t.practice.generate}
                </Button>
                {generateError ? (
                  <p className="text-xs text-muted-foreground">{generateError}</p>
                ) : null}
              </div>
            </FieldGroup>
          </CardContent>
        </Card>

        {generating ? (
          <div className="flex flex-col items-center gap-3 py-12 text-muted-foreground">
            <Loader2Icon className="size-8 animate-spin" />
            <p className="text-sm">{t.practice.generating}</p>
          </div>
        ) : created ? (
          <Card>
            <CardContent className="space-y-3 pt-6">
              <p className="text-sm font-medium">{t.practice.createdTitle}</p>
              <p className="text-sm text-muted-foreground">
                {t.practice.createdBody}
              </p>
              <Button
                type="button"
                onClick={() => navigate(`/practice/${created.id}`)}
              >
                {t.practice.openPractice}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <PageEmpty title={t.practice.emptyTitle} description={t.practice.emptyBody} />
        )}
      </div>
    </div>
  );
}

function PracticeSessionView({ sessionId }: { sessionId: string }) {
  const t = useT();
  const navigate = useNavigate();
  const { refresh: refreshConversations } = useConversations();
  const [session, setSession] = useState<PracticeSession | null>(null);
  const [attemptNo, setAttemptNo] = useState<number | null>(null);
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [results, setResults] = useState<Record<string, PracticeGradingResponse>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getPracticeSession(sessionId)
      .then((loaded) => {
        if (cancelled) return;
        setSession(loaded);
        const last = loaded.attempts[loaded.attempts.length - 1];
        setAttemptNo(last?.attempt_no ?? null);
        setAnswers(last?.answers ?? {});
        setResults(last?.results ?? {});
        setError(null);
      })
      .catch(() => {
        if (!cancelled) setError(t.practice.loadError);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      if (timer.current !== null) clearTimeout(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const attempt: PracticeAttempt | null =
    session?.attempts.find((entry) => entry.attempt_no === attemptNo) ?? null;

  function selectAttempt(nextNo: number) {
    if (!session) return;
    const target = session.attempts.find((entry) => entry.attempt_no === nextNo);
    if (!target) return;
    setAttemptNo(nextNo);
    setAnswers(target.answers);
    setResults(target.results);
    setSaveState("idle");
  }

  async function persist(next: Record<string, string[]>) {
    if (!session || !attempt || attempt.status !== "in_progress") return;
    setSaveState("saving");
    try {
      const saved = await savePracticeAnswers(
        session.id,
        attempt.attempt_no,
        next,
      );
      setSaveState("saved");
      if (session.status === "not_started" && saved.status === "in_progress") {
        refreshConversations();
      }
      setSession((current) =>
        current === null ? current : { ...current, status: saved.status },
      );
    } catch {
      setSaveState("idle");
    }
  }

  function updateAnswer(question: GeneratedQuestion, values: string[]) {
    const next = { ...answers, [question.id]: values };
    setAnswers(next);
    if (question.type === "short-answer" || question.type === "code") {
      if (timer.current !== null) clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        void persist(next);
      }, 1500);
    } else {
      void persist(next);
    }
  }

  async function handleSubmit() {
    if (!session || !attempt || submitting) return;
    setSubmitting(true);
    setError(null);
    const graded: Record<string, PracticeGradingResponse> = {};
    for (const question of session.questions) {
      const values = answers[question.id] ?? [];
      const answer = answerText(values);
      if (!answer.trim()) continue;
      const deterministic = gradeDeterministic(question, values, {
        correct: t.practice.verdicts.correct,
        incorrect: t.practice.verdicts.incorrect,
      });
      if (deterministic) {
        graded[question.id] = deterministic;
        continue;
      }
      try {
        graded[question.id] = await gradePractice({
          question: question.question,
          answer,
          reference_answer: question.reference_answer,
          scoring_points: question.scoring_points,
          max_score: question.max_score,
          sources: session.sources,
        });
      } catch {
        graded[question.id] = {
          score: 0,
          max_score: question.max_score,
          explanation: t.common.errorBody,
        };
      }
    }
    try {
      const updated = await submitPracticeAttempt(
        session.id,
        attempt.attempt_no,
        answers,
        graded,
      );
      const submitted = updated.attempts.find(
        (entry) => entry.attempt_no === attempt.attempt_no,
      );
      setSession(updated);
      setResults(submitted?.results ?? graded);
      setSaveState("idle");
      refreshConversations();
    } catch {
      setError(t.common.errorBody);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRedo() {
    if (!session) return;
    try {
      const updated = await startPracticeAttempt(session.id);
      const last = updated.attempts[updated.attempts.length - 1];
      setSession(updated);
      setAttemptNo(last?.attempt_no ?? null);
      setAnswers(last?.answers ?? {});
      setResults(last?.results ?? {});
      setSaveState("idle");
      refreshConversations();
    } catch {
      setError(t.common.errorBody);
    }
  }

  async function handleDelete() {
    if (!session || !attempt) return;
    try {
      await deletePracticeAttempt(session.id, attempt.attempt_no);
      refreshConversations();
      try {
        const updated = await getPracticeSession(session.id);
        setSession(updated);
        const index = Math.min(
          attempt.attempt_no - 1,
          updated.attempts.length - 1,
        );
        const target =
          updated.attempts[index] ?? updated.attempts[updated.attempts.length - 1];
        setAttemptNo(target.attempt_no);
        setAnswers(target.answers);
        setResults(target.results);
        setSaveState("idle");
        setConfirmDelete(false);
      } catch {
        // The last attempt is gone, so the practice itself is gone too.
        navigate("/practice");
      }
    } catch {
      setError(t.common.errorBody);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center p-6 text-muted-foreground">
        <Loader2Icon className="size-6 animate-spin" />
      </div>
    );
  }

  if (session === null || attempt === null) {
    return (
      <div className="mx-auto w-full max-w-4xl p-6">
        <PageEmpty title={t.practice.emptyTitle} description={error ?? t.practice.loadError} />
      </div>
    );
  }

  const totalScore = attempt.score ?? 0;
  const lastAttemptNo = session.attempts[session.attempts.length - 1]?.attempt_no;

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-4 p-6">
        <PageHeader title={session.title ?? session.topic} description={t.practice.subtitle} />

        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm">
            <Badge variant="secondary">
              {
                {
                  not_started: t.practice.statusNotStarted,
                  in_progress: t.practice.statusInProgress,
                  completed: t.practice.statusCompleted,
                }[session.status]
              }
            </Badge>
            <span className="text-muted-foreground">
              {format(t.practice.bestScore, {
                score: Math.round(session.best_score),
                max: Math.round(session.max_score),
              })}
            </span>
            {saveState === "saving" ? (
              <span className="text-xs text-muted-foreground">{t.practice.saving}</span>
            ) : null}
            {saveState === "saved" ? (
              <span className="text-xs text-muted-foreground">{t.practice.saved}</span>
            ) : null}
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <Button
                type="button"
                variant="outline"
                size="sm"
                aria-label={t.practice.prevAttempt}
                disabled={attempt.attempt_no <= 1}
                onClick={() => selectAttempt(attempt.attempt_no - 1)}
              >
                <ChevronLeftIcon className="size-4" />
              </Button>
              <span className="min-w-24 text-center text-sm">
                {format(t.practice.attempt, {
                  current: attempt.attempt_no,
                  total: session.attempts.length,
                })}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                aria-label={t.practice.nextAttempt}
                disabled={attempt.attempt_no >= (lastAttemptNo ?? attempt.attempt_no)}
                onClick={() => selectAttempt(attempt.attempt_no + 1)}
              >
                <ChevronRightIcon className="size-4" />
              </Button>
            </div>
            {session.status === "completed" &&
            attempt.attempt_no === lastAttemptNo &&
            attempt.status === "completed" ? (
              <Button type="button" variant="outline" size="sm" onClick={handleRedo}>
                {t.practice.redo}
              </Button>
            ) : null}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-label={
                session.attempts.length === 1
                  ? t.practice.deletePractice
                  : t.practice.deleteAttempt
              }
              onClick={() => setConfirmDelete(true)}
            >
              <Trash2Icon className="size-4" />
            </Button>
          </div>
        </div>

        {confirmDelete ? (
          <Card>
            <CardContent className="space-y-3 pt-6">
              <p className="text-sm font-medium">
                {session.attempts.length === 1
                  ? t.practice.deleteTitle
                  : t.practice.deleteAttemptTitle}
              </p>
              <p className="text-sm text-muted-foreground">
                {session.attempts.length === 1
                  ? t.practice.deleteBody
                  : t.practice.deleteAttemptBody}
              </p>
              <div className="flex gap-2">
                <Button type="button" variant="destructive" onClick={handleDelete}>
                  {t.practice.deleteConfirm}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setConfirmDelete(false)}
                >
                  {t.common.cancel}
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : null}

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        {attempt.status === "completed" ? (
          <>
            <Card>
              <CardContent className="flex flex-col items-center gap-3 pt-6">
                <ScoreRing score={totalScore} max={attempt.max_score} />
                <p className="text-sm text-muted-foreground">{t.practice.gradingTitle}</p>
              </CardContent>
            </Card>
            {session.questions.map((question) => {
              const result = results[question.id];
              return (
                <Card key={question.id}>
                  <CardHeader>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="secondary">{t.practice.types[question.type]}</Badge>
                      <Badge variant="outline">
                        {format(t.practice.score, {
                          score: result ? result.score : 0,
                          max: question.max_score,
                        })}
                      </Badge>
                    </div>
                    <CardTitle>
                      <Markdown sources={session.sources} className="text-base font-semibold">
                        {question.question}
                      </Markdown>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground">
                        {t.practice.answer}
                      </p>
                      <p className="text-sm">
                        {answerText(attempt.answers[question.id]) || "—"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-muted-foreground">
                        {t.practice.referenceAnswer}
                      </p>
                      <Markdown sources={session.sources}>
                        {question.reference_answer}
                      </Markdown>
                    </div>
                    {result ? <p className="text-sm">{result.explanation}</p> : null}
                  </CardContent>
                </Card>
              );
            })}
          </>
        ) : (
          <>
            {session.questions.map((question) => (
              <Card key={question.id}>
                <CardHeader>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{t.practice.types[question.type]}</Badge>
                    <Badge variant="outline">
                      {format(
                        question.max_score === 1
                          ? t.practice.pointsOne
                          : t.practice.points,
                        { count: question.max_score },
                      )}
                    </Badge>
                  </div>
                  <CardTitle>
                    <Markdown sources={session.sources} className="text-base font-semibold">
                      {question.question}
                    </Markdown>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {question.type === "single-choice" || question.type === "true-false" ? (
                    <RadioGroup
                      value={answers[question.id]?.[0] ?? ""}
                      onValueChange={(value) => updateAnswer(question, [value])}
                    >
                      {question.choices.map((choice) => (
                        <label key={choice} className="flex items-center gap-2 text-sm">
                          <RadioGroupItem value={choice} />
                          {choice}
                        </label>
                      ))}
                    </RadioGroup>
                  ) : null}

                  {question.type === "multiple-choice" ? (
                    <div className="space-y-2">
                      {question.choices.map((choice) => {
                        const chosen = answers[question.id] ?? [];
                        return (
                          <label key={choice} className="flex items-center gap-2 text-sm">
                            <Checkbox
                              checked={chosen.includes(choice)}
                              onCheckedChange={(checked) =>
                                updateAnswer(
                                  question,
                                  checked
                                    ? [...chosen, choice]
                                    : chosen.filter((value) => value !== choice),
                                )
                              }
                            />
                            {choice}
                          </label>
                        );
                      })}
                    </div>
                  ) : null}

                  {question.type === "short-answer" || question.type === "code" ? (
                    <Field>
                      <FieldLabel htmlFor={`answer-${question.id}`}>
                        {t.practice.answer}
                      </FieldLabel>
                      <Textarea
                        id={`answer-${question.id}`}
                        className={
                          question.type === "code" ? "min-h-32 font-mono text-xs" : ""
                        }
                        placeholder={t.practice.answerPlaceholder}
                        value={answers[question.id]?.[0] ?? ""}
                        onChange={(event) =>
                          updateAnswer(question, [event.target.value])
                        }
                        onBlur={() => {
                          if (timer.current !== null) clearTimeout(timer.current);
                          void persist(answers);
                        }}
                      />
                    </Field>
                  ) : null}
                </CardContent>
              </Card>
            ))}
            <div className="flex justify-end">
              <Button type="button" disabled={submitting} onClick={handleSubmit}>
                {submitting ? t.practice.running : t.practice.submitAll}
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
