import { useState } from "react";

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
  type GeneratedQuestion,
  type PracticeGradingResponse,
} from "@/lib/api/practice";
import { format, useT } from "@/lib/i18n";
import type { CitationSource, QuestionType } from "@/lib/types";

const TOPICS = [
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

export function PracticePage() {
  const t = useT();
  const [topic, setTopic] = useState("");
  const [customTopic, setCustomTopic] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [questions, setQuestions] = useState<GeneratedQuestion[]>([]);
  const [sources, setSources] = useState<CitationSource[]>([]);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [selected, setSelected] = useState<Record<number, string[]>>({});
  const [results, setResults] = useState<Record<number, PracticeGradingResponse>>({});
  const [grading, setGrading] = useState<Record<number, boolean>>({});

  const effectiveTopic = topic === "others" ? customTopic.trim() : topic.trim();

  async function handleGenerate() {
    if (!effectiveTopic || generating) return;
    setGenerating(true);
    setGenerateError(null);
    setQuestions([]);
    setResults({});
    setAnswers({});
    setSelected({});
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

  async function handleSubmit(index: number) {
    const question = questions[index];
    const answer = answerFor(index, question);
    if (!answer.trim()) return;
    setGrading((current) => ({ ...current, [index]: true }));
    try {
      const result = await gradePractice({
        question: question.question,
        answer,
        reference_answer: question.reference_answer,
        scoring_points: question.scoring_points,
        max_score: question.max_score,
      });
      setResults((current) => ({ ...current, [index]: result }));
    } catch {
      setResults((current) => ({
        ...current,
        [index]: { score: 0, max_score: question.max_score, explanation: t.common.errorBody },
      }));
    } finally {
      setGrading((current) => ({ ...current, [index]: false }));
    }
  }

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
                        {item === "others" ? t.practice.others : item}
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
                  {t.practice.generate}
                </Button>
                {generateError ? (
                  <p className="text-xs text-muted-foreground">{generateError}</p>
                ) : null}
              </div>
            </FieldGroup>
          </CardContent>
        </Card>

        {questions.length === 0 && !generating ? (
          <PageEmpty title={t.practice.emptyTitle} description={t.practice.emptyBody} />
        ) : (
          questions.map((question, index) => {
            const result = results[index];
            const isGrading = grading[index] === true;
            return (
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
                                  : (current[index] ?? []).filter((value) => value !== choice),
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
                          setAnswers((current) => ({ ...current, [index]: event.target.value }))
                        }
                      />
                    </Field>
                  ) : null}

                  <Button
                    type="button"
                    disabled={isGrading || !answerFor(index, question).trim()}
                    onClick={() => handleSubmit(index)}
                  >
                    {isGrading ? t.practice.running : t.practice.submit}
                  </Button>

                  {result ? (
                    <div className="space-y-3 rounded-lg border p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-sm font-semibold">{t.practice.gradingTitle}</h3>
                        <span className="text-sm text-muted-foreground">
                          {format(t.practice.score, {
                            score: result.score,
                            max: result.max_score,
                          })}
                        </span>
                      </div>
                      <p className="text-sm">{result.explanation}</p>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
