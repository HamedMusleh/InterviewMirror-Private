import type { InterviewDetailsResponse } from "../types/interviewDetailsTypes";

const API_BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/api/interviews`;

// Response shape matches InterviewDetailsResponse exactly — no mapping needed.
export async function getInterviewDetails(
  interviewId: number
): Promise<InterviewDetailsResponse | null> {
  const response = await fetch(`${API_BASE_URL}/${interviewId}/details`);

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error("Failed to fetch interview details");
  }

  return response.json();
}