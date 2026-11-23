import type { GeneratedQuestion, PracticeGradingResponse } from "@/lib/api/practice";

export interface SummaryLabels {
  title: string;
  total: string;
  yourAnswer: string;
  referenceAnswer: string;
  score: string;
  explanation: string;
  unanswered: string;
}

function fill(template: string, values: Record<string, string>): string {
  return Object.entries(values).reduce(
    (text, [key, value]) => text.replaceAll(`{{${key}}}`, () => value),
    template,
  );
}

/**
 * Build the conversation content saved for a finished practice run.
 *
 * Labels come from the active locale, so an English session never stores the
 * hard-coded Chinese headings the page used before.
 */
export function buildPracticeSummary(input: {
  topic: string;
  questions: GeneratedQuestion[];
  answers: string[];
  results: Record<number, PracticeGradingResponse | undefined>;
  labels: SummaryLabels;
}): string {
  const { topic, questions, answers, results, labels } = input;
  const totalMax = questions.reduce((sum, question) => sum + question.max_score, 0);
  const totalScore = questions.reduce(
    (sum, _question, index) => sum + (results[index]?.score ?? 0),
    0,
  );
  const lines = [
    `# ${fill(labels.title, { topic })}`,
    "",
    fill(labels.total, {
      score: String(Math.round(totalScore)),
      max: String(Math.round(totalMax)),
    }),
    "",
  ];
  questions.forEach((question, index) => {
    const result = results[index];
    lines.push(`### ${index + 1}. ${question.question}`);
    lines.push(
      `- ${fill(labels.yourAnswer, {
        answer: answers[index]?.trim() || labels.unanswered,
      })}`,
    );
    lines.push(
      `- ${fill(labels.referenceAnswer, { answer: question.reference_answer })}`,
    );
    if (result) {
      lines.push(
        `- ${fill(labels.score, {
          score: String(result.score),
          max: String(result.max_score),
        })}`,
      );
      lines.push(`- ${fill(labels.explanation, { text: result.explanation })}`);
    }
    lines.push("");
  });
  return lines.join("\n");
}
