import type {Submission} from "./types.ts";

/** Alineado con backend/app/api/v1/submissions.py: no hay endpoint de reapertura. */
export function isSubmissionLocked(submission?:Pick<Submission,"status"|"validation_status">):boolean{
  return !!submission&&(submission.status==="reviewed"||submission.status==="returned"||submission.validation_status==="validated");
}
