import { useMemo, useState } from "react";

import { CitationRow } from "@/components/chat/citation-row";
import { EvidencePanel } from "@/components/chat/evidence-panel";
import { PageEmpty, PageError, PageHeader, PageLoading } from "@/components/layout/page-states";
import { TestResults } from "@/components/practice/test-results";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { CodeBlock, CodeBlockContent } from "@/components/ui/code-block";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { format, useT } from "@/lib/i18n";
import { usePreview } from "@/lib/preview/context";
import {
  PREVIEW_GRADING,
  PREVIEW_GRADING_PARTIAL,
  PREVIEW_QUESTIONS,
} from "@/lib/preview/fixtures";
import type { Citation, QuestionType } from "@/lib/types";

const QUESTION_TYPES: QuestionType[] = [
  "single-choice",
  "multiple-choice",
  "true-false",
  "short-answer",
  "code",
];

export function PracticePage() {
  const t = useT();
  const { pageState } = usePreview();
  const [type, setType] = useState<QuestionType>("single-choice");
  const [difficulty, setDifficulty] = useState("medium");
  const [topic, setTopic] = useState("");
  const [choice, setChoice] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [answer, setAnswer] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [graded, setGraded] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

  const question = useMemo(
    () => PREVIEW_QUESTIONS.find((item) => item.type === type) ?? PREVIEW_QUESTIONS[0],
    [type],
  );
  const result = type === "code" ? PREVIEW_GRADING : PREVIEW_GRADING_PARTIAL;
  const activeIndex =
    activeCitation === null
      ? null
      : Math.max(result.citations.indexOf(activeCitation), 0);

  function submit() {
    if (type === "code") {
      setConfirmOpen(true);
      return;
    }
    setGraded(true);
  }

  function confirmRun() {
    setConfirmOpen(false);
    setGraded(true);
  }

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-4xl space-y-4 p-6">
        <PageHeader title={t.practice.title} description={t.practice.subtitle} />

        <Alert>
          <AlertTitle>{t.practice.unavailableTitle}</AlertTitle>
          <AlertDescription>{t.practice.unavailableBody}</AlertDescription>
        </Alert>

        <Tabs defaultValue="questions">
          <TabsList>
            <TabsTrigger value="questions">{t.practice.questionsTab}</TabsTrigger>
            <TabsTrigger value="solution">{t.practice.solutionTab}</TabsTrigger>
          </TabsList>

          <TabsContent value="questions" className="space-y-4 pt-3">
            <Card>
              <CardHeader>
                <CardTitle>
                  <h2 className="text-sm font-semibold">
                    {t.practice.settingsTitle}
                  </h2>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <FieldGroup className="md:grid md:grid-cols-2">
                  <Field>
                    <FieldLabel htmlFor="practice-topic">
                      {t.practice.topic}
                    </FieldLabel>
                    <Input
                      id="practice-topic"
                      placeholder={t.practice.topicPlaceholder}
                      value={topic}
                      onChange={(event) => setTopic(event.target.value)}
                    />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="practice-type">
                      {t.practice.type}
                    </FieldLabel>
                    <Select
                      value={type}
                      onValueChange={(value) => {
                        setType(value as QuestionType);
                        setGraded(false);
                        setChoice("");
                        setSelected([]);
                      }}
                    >
                      <SelectTrigger id="practice-type">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {QUESTION_TYPES.map((item) => (
                          <SelectItem key={item} value={item}>
                            {t.practice.types[item]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="practice-difficulty">
                      {t.practice.difficulty}
                    </FieldLabel>
                    <Select value={difficulty} onValueChange={setDifficulty}>
                      <SelectTrigger id="practice-difficulty">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="easy">
                          {t.practice.difficulties.easy}
                        </SelectItem>
                        <SelectItem value="medium">
                          {t.practice.difficulties.medium}
                        </SelectItem>
                        <SelectItem value="hard">
                          {t.practice.difficulties.hard}
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </Field>
                  <div className="flex items-end">
                    <Button
                      type="button"
                      disabled
                      title={t.common.unavailable}
                    >
                      {t.practice.generate}
                    </Button>
                  </div>
                </FieldGroup>
              </CardContent>
            </Card>

            {pageState === "loading" ? (
              <PageLoading />
            ) : pageState === "error" ? (
              <PageError
                title={t.common.errorTitle}
                description={t.common.errorBody}
              />
            ) : pageState === "empty" ? (
              <PageEmpty
                title={t.common.emptyTitle}
                description={t.common.emptyBody}
              />
            ) : (
              <Card>
                <CardHeader>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{t.practice.types[question.type]}</Badge>
                    <Badge variant="outline">
                      {format(t.practice.points, { count: question.points })}
                    </Badge>
                    {question.citations.map((citation) => (
                      <Badge key={citation.doc_id + citation.page_no} variant="outline">
                        {citation.doc_id} p.{citation.page_no}
                      </Badge>
                    ))}
                  </div>
                  <CardTitle>
                    <h2 className="text-base font-semibold">{question.prompt}</h2>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {question.type === "single-choice" ? (
                    <RadioGroup value={choice} onValueChange={setChoice}>
                      {question.choices.map((option) => (
                        <label
                          key={option.value}
                          className="flex items-center gap-2 text-sm"
                        >
                          <RadioGroupItem value={option.value} />
                          {option.label}
                        </label>
                      ))}
                    </RadioGroup>
                  ) : null}

                  {question.type === "multiple-choice" ? (
                    <div className="space-y-2">
                      {question.choices.map((option) => (
                        <label
                          key={option.value}
                          className="flex items-center gap-2 text-sm"
                        >
                          <Checkbox
                            checked={selected.includes(option.value)}
                            onCheckedChange={(checked) =>
                              setSelected((current) =>
                                checked
                                  ? [...current, option.value]
                                  : current.filter((value) => value !== option.value),
                              )
                            }
                          />
                          {option.label}
                        </label>
                      ))}
                    </div>
                  ) : null}

                  {question.type === "true-false" ? (
                    <RadioGroup value={choice} onValueChange={setChoice}>
                      {question.choices.map((option) => (
                        <label
                          key={option.value}
                          className="flex items-center gap-2 text-sm"
                        >
                          <RadioGroupItem value={option.value} />
                          {option.label}
                        </label>
                      ))}
                    </RadioGroup>
                  ) : null}

                  {question.type === "short-answer" ? (
                    <Field>
                      <FieldLabel htmlFor="practice-answer">
                        {t.practice.answer}
                      </FieldLabel>
                      <Textarea
                        id="practice-answer"
                        placeholder={t.practice.answerPlaceholder}
                        value={answer}
                        onChange={(event) => setAnswer(event.target.value)}
                      />
                    </Field>
                  ) : null}

                  {question.type === "code" ? (
                    <div className="space-y-2">
                      <CodeBlock size="sm">
                        <CodeBlockContent>
                          {question.code_template ?? ""}
                        </CodeBlockContent>
                      </CodeBlock>
                      <Field>
                        <FieldLabel htmlFor="practice-code">
                          {t.practice.answer}
                        </FieldLabel>
                        <Textarea
                          id="practice-code"
                          className="min-h-32 font-mono text-xs"
                          placeholder={t.practice.codePlaceholder}
                          value={answer}
                          onChange={(event) => setAnswer(event.target.value)}
                        />
                      </Field>
                    </div>
                  ) : null}

                  <Button type="button" onClick={submit}>
                    {t.practice.submit}
                  </Button>

                  {graded ? (
                    <div className="space-y-3 rounded-lg border p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-sm font-semibold">
                          {t.practice.gradingTitle}
                        </h3>
                        <Badge
                          variant={
                            result.verdict === "correct" ? "secondary" : "outline"
                          }
                        >
                          {t.practice.verdicts[result.verdict]}
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                          {format(t.practice.score, {
                            score: result.score,
                            max: result.max_score,
                          })}
                        </span>
                      </div>
                      <p className="text-sm">{result.explanation}</p>
                      <CitationRow
                        citations={result.citations}
                        onOpen={setActiveCitation}
                      />
                      {result.test_suites ? (
                        <TestResults suites={result.test_suites} />
                      ) : null}
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            )}

            <p className="text-xs text-muted-foreground">{t.practice.previewNotice}</p>
          </TabsContent>

          <TabsContent value="solution" className="space-y-3 pt-3">
            <Card>
              <CardHeader>
                <CardTitle>
                  <h2 className="text-sm font-semibold">{t.practice.solutionTitle}</h2>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  {t.practice.solutionBody}
                </p>
                <Textarea
                  className="min-h-40 font-mono text-xs"
                  aria-label={t.practice.solutionTitle}
                  placeholder={t.practice.solutionPlaceholder}
                />
                <Button type="button" disabled title={t.common.unavailable}>
                  {t.practice.solutionSubmit}
                </Button>
                <p className="text-xs text-muted-foreground">
                  {t.practice.solutionDisabled}
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.practice.confirmationTitle}</DialogTitle>
            <DialogDescription>{t.practice.confirmationBody}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmOpen(false)}
            >
              {t.practice.cancelRun}
            </Button>
            <Button type="button" onClick={confirmRun}>
              {t.practice.confirmRun}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Sheet
        open={activeCitation !== null}
        onOpenChange={(open) => {
          if (!open) {
            setActiveCitation(null);
          }
        }}
      >
        <SheetContent side="right" className="w-full p-0 sm:max-w-lg">
          <SheetHeader className="border-b">
            <SheetTitle>{t.chat.evidenceTitle}</SheetTitle>
          </SheetHeader>
          <EvidencePanel
            citations={result.citations}
            activeIndex={activeIndex}
            onSelect={(index) => setActiveCitation(result.citations[index] ?? null)}
            className="min-h-0 flex-1"
          />
        </SheetContent>
      </Sheet>
    </div>
  );
}
