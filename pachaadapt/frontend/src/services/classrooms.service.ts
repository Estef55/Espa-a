import {request} from "./http.ts";

export type Classroom={id:string;name:string;teacher_id:string;is_demo?:boolean|number;created_at?:string};

/** Lee únicamente las aulas autorizadas para el perfil actual; no crea ni inscribe usuarios. */
export const fetchClassrooms=()=>request<Classroom[]>("/api/v1/classrooms");
