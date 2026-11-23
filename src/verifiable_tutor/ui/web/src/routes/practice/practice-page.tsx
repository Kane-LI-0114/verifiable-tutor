import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { Loader2Icon } from "lucide-react";

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
  generatePractice,
  gradePractice,
  savePracticeSession,
  type GeneratedQuestion,
  type PracticeGradingResponse,
} from "@/lib/api/practice";
import { format, useT } from "@/lib/i18n";
import { useConversations } from "@/lib/session/conversations";
import type { CitationSource, QuestionType } from "@/lib/types";

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

function dateStamp(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}${month}${day}`;
}

function deterministicGrade(
  question: GeneratedQuestion,
  answer: string,
  correctLabel: string,
  incorrectLabel: string,
): PracticeGradingResponse | null {
  if (
    question.type !== "single-choice" &&
    question.type !== "multiple-choice" &&
    question.type !== "true-false"
  ) {
    return null;
  }
  const normalize = (value: string) => value.trim().toLowerCase();
  const correctAnswer = question.correct_answer ?? "";
  let correct: boolean;
  if (question.type === "multiple-choice") {
    const refSet = new Set(
      correctAnswer.split(",").map(normalize).filter(Boolean),
    );
    const ansSet = new Set(answer.split(",").map(normalize).filter(Boolean));
    correct =
      refSet.size > 0 &&
      refSet.size === ansSet.size &&
      [...refSet].every((key) => ansSet.has(key));
  } else {
    correct = normalize(answer) === normalize(correctAnswer);
  }
  return {
    score: correct ? question.max_score : 0,
    max_score: question.max_score,
    explanation: correct ? correctLabel : incorrectLabel,
  };
}

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

export function PracticePage() {
  const t = useT();
  const { refresh: refreshConversations } = useConversations();
  const [topic, setTopic] = useState("");
  const [customTopic, setCustomTopic] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [questions, setQuestions] = useState<GeneratedQuestion[]>([]);
  const [sources, setSources] = useState<CitationSource[]>([]);
  const [phase, setPhase] = useState<"answer" | "result">("answer");
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [selected, setSelected] = useState<Record<number, string[]>>({});
  const [results, setResults] = useState<Record<number, PracticeGradingResponse>>({});
  const [generating, setGenerating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const effectiveTopic = topic === "others" ? customTopic.trim() : topic.trim();

  useEffect(() => {
    const topicParam = searchParams.get("topic");
    if (!topicParam) return;
    setTopic(topicParam);
    const types = (searchParams.get("types") ?? "").split(",").filter(Boolean);
    setSelectedTypes(types);
    setSearchParams({}, { replace: true });
    setGenerating(true);
    setQuestions([]);
    setResults({});
    setAnswers({});
    setSelected({});
    setPhase("answer");
    generatePractice(topicParam, types)
      .then((result) => {
        setQuestions(result.questions);
        setSources(result.sources);
        if (result.questions.length === 0) {
          setGenerateError(t.practice.emptyBody);
        }
      })
      .catch(() => setGenerateError("question generation failed"))
      .finally(() => setGenerating(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleGenerate() {
    if (!effectiveTopic || generating) return;
    setGenerating(true);
    setGenerateError(null);
    setQuestions([]);
    setResults({});
    setAnswers({});
    setSelected({});
    setPhase("answer");
    try {
      const result = await generatePractice(effectiveTopic, selectedTypes);
      setQuestions(result.questions);
      setSources(result.sources);
      if (result.questions.length === 0) {
        setGenerateError(t.practice.emptyBody);
      }
    } catch (error) {
      setGenerateError(
        error instanceof Error ? error.message : "question generation failed",
      );
    } finally {
      setGenerating(false);
    }
  }

  function answerFor(index: number, question: GeneratedQuestion): string {
    if (question.type === "multiple-choice") {
      return (selected[index] ?? []).join(", ");
    }
    return answers[index] ?? "";
  }

  async function handleSubmitAll() {
    if (submitting) return;
    setSubmitting(true);
    const next: Record<number, PracticeGradingResponse> = {};
    for (let index = 0; index < questions.length; index += 1) {
      const question = questions[index];
      const answer = answerFor(index, question);
      if (!answer.trim()) continue;
      const deterministic = deterministicGrade(
        question,
        answer,
        t.practice.verdicts.correct,
        t.practice.verdicts.incorrect,
      );
      if (deterministic) {
        next[index] = deterministic;
        continue;
      }
      try {
        next[index] = await gradePractice({
          question: question.question,
          answer,
          reference_answer: question.reference_answer,
          scoring_points: question.scoring_points,
          max_score: question.max_score,
          sources,
        });
      } catch {
        next[index] = {
          score: 0,
          max_score: question.max_score,
          explanation: t.common.errorBody,
        };
      }
    }
    setResults(next);
    const totalMax = questions.reduce((sum, q) => sum + q.max_score, 0);
    const totalScore = questions.reduce(
      (sum, _q, index) => sum + (next[index]?.score ?? 0),
      0,
    );
    const lines = [
      `# 练习：${effectiveTopic}`,
      "",
      `**总分：${Math.round(totalScore)}/${Math.round(totalMax)}**`,
      "",
    ];
    questions.forEach((q, index) => {
      const result = next[index];
      lines.push(`### ${index + 1}. ${q.question}`);
      lines.push(`- 你的答案：${answerFor(index, q) || "（未作答）"}`);
      lines.push(`- 参考答案：${q.reference_answer}`);
      if (result) {
        lines.push(`- 得分：${result.score}/${q.max_score}`);
        lines.push(`- 解析：${result.explanation}`);
      }
      lines.push("");
    });
    try {
      const title = `${effectiveTopic} ${dateStamp()}`;
      const byTopic: Record<
        string,
        { covered: Set<string>; mastered: Set<string> }
      > = {};
      questions.forEach((question, index) => {
        const topicName = question.topic || effectiveTopic;
        const entry =
          byTopic[topicName] ??
          (byTopic[topicName] = { covered: new Set(), mastered: new Set() });
        question.knowledge_points.forEach((point) => entry.covered.add(point));
        if (next[index] && next[index].score === question.max_score) {
          question.knowledge_points.forEach((point) => entry.mastered.add(point));
        }
      });
      const progress = Object.entries(byTopic).map(([topicName, entry]) => ({
        topic: topicName,
        covered_points: Array.from(entry.covered),
        mastered_points: Array.from(entry.mastered),
      }));
      await savePracticeSession(title, lines.join("\n"), sources, progress);
      refreshConversations();
    } catch {
      // Saving the session is best effort; the result stays on screen.
    }
    setSubmitting(false);
    setPhase("result");
  }

  const totalMax = questions.reduce((sum, question) => sum + question.max_score, 0);
  const totalScore = questions.reduce(
    (sum, _question, index) => sum + (results[index]?.score ?? 0),
    0,
  );

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
                  onClick={handleGenerate}
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
        ) : questions.length === 0 ? (
          <PageEmpty title={t.practice.emptyTitle} description={t.practice.emptyBody} />
        ) : phase === "result" ? (
          <>
            <Card>
              <CardContent className="flex flex-col items-center gap-3 pt-6">
                <ScoreRing score={totalScore} max={totalMax} />
                <p className="text-sm text-muted-foreground">{t.practice.gradingTitle}</p>
              </CardContent>
            </Card>
            {questions.map((question, index) => {
              const result = results[index];
              return (
                <Card key={index}>
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
                      <Markdown sources={sources} className="text-base font-semibold">
                        {question.question}
                      </Markdown>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground">
                        {t.practice.answer}
                      </p>
                      <p className="text-sm">{answerFor(index, question) || "—"}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-muted-foreground">
                        {t.practice.referenceAnswer}
                      </p>
                      <Markdown sources={sources}>{question.reference_answer}</Markdown>
                    </div>
                    {result ? (
                      <p className="text-sm">{result.explanation}</p>
                    ) : null}
                  </CardContent>
                </Card>
              );
            })}
          </>
        ) : (
          <>
            {questions.map((question, index) => (
              <Card key={index}>
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
                    <Markdown sources={sources} className="text-base font-semibold">
                      {question.question}
                    </Markdown>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {question.type === "single-choice" || question.type === "true-false" ? (
                    <RadioGroup
                      value={answers[index] ?? ""}
                      onValueChange={(value) =>
                        setAnswers((current) => ({ ...current, [index]: value }))
                      }
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
                      {question.choices.map((choice) => (
                        <label key={choice} className="flex items-center gap-2 text-sm">
                          <Checkbox
                            checked={(selected[index] ?? []).includes(choice)}
                            onCheckedChange={(checked) =>
                              setSelected((current) => ({
                                ...current,
                                [index]: checked
                                  ? [...(current[index] ?? []), choice]
                                  : (current[index] ?? []).filter(
                                      (value) => value !== choice,
                                    ),
                              }))
                            }
                          />
                          {choice}
                        </label>
                      ))}
                    </div>
                  ) : null}

                  {question.type === "short-answer" || question.type === "code" ? (
                    <Field>
                      <FieldLabel>{t.practice.answer}</FieldLabel>
                      <Textarea
                        className={
                          question.type === "code" ? "min-h-32 font-mono text-xs" : ""
                        }
                        placeholder={t.practice.answerPlaceholder}
                        value={answers[index] ?? ""}
                        onChange={(event) =>
                          setAnswers((current) => ({
                            ...current,
                            [index]: event.target.value,
                          }))
                        }
                      />
                    </Field>
                  ) : null}
                </CardContent>
              </Card>
            ))}
            <div className="flex justify-end">
              <Button type="button" disabled={submitting} onClick={handleSubmitAll}>
                {submitting ? t.practice.running : t.practice.submitAll}
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
