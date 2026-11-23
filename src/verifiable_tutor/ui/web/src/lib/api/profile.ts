import { apiFetch } from "./client";

export interface MasteryTopic {
  topic: string;
  total: number;
  covered_count: number;
  mastered_count: number;
}

export interface MasteryResponse {
  topics: MasteryTopic[];
}

export const profileApi = {
  mastery(signal?: AbortSignal): Promise<MasteryResponse> {
    return apiFetch<MasteryResponse>("/api/profile/mastery", { signal });
  },
};
