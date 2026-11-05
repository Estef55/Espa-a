import {request} from "./http.ts";
import type {Submission} from "../lib/types.ts";

export type SubmissionReviewInput={
  status:"reviewed"|"returned";
  score?:number;
  max_score?:number;
  validation_status?:"pending"|"validated"|"rejected";
};

/** Revisa o valida un resultado usando los parámetros reales de FastAPI. */
export const reviewSubmission=(id:string,review:SubmissionReviewInput)=>
  request<Submission>(`/api/v1/submissions/${encodeURIComponent(id)}/review`,{
    method:"PATCH",
    query:{status:review.status,score:review.score,max_score:review.max_score,validation_status:review.validation_status},
  });
