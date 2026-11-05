// Disponibilidad de recursos con y sin conexión (integrante 2). El servidor es la fuente de verdad
// (GET /api/v1/adaptations/capabilities); esta tabla es solo el respaldo cuando no se puede consultar.
export type ResourceAvailability = {
  id: string; label: string; available: boolean; requires_server: boolean; requires_internet: boolean;
  works_offline_on_device: boolean; note: string;
};
export type CapabilitiesResponse = { resources: ResourceAvailability[]; generated_at?: string };

const local = (id: string, label: string, note = ""): ResourceAvailability =>
  ({ id, label, available: true, requires_server: false, requires_internet: false, works_offline_on_device: true, note });

/** Lo que SIEMPRE funciona sin llegar al servidor, porque vive en el dispositivo. */
export const OFFLINE_ON_DEVICE: ResourceAvailability[] = [
  local("cached_materials", "Materiales ya descargados", "Solo los descargados antes con conexión."),
  local("saved_adaptations", "Adaptaciones guardadas en el dispositivo"),
  local("activity_drafts", "Borradores de actividades en curso"),
];

export const SERVER_REQUIRED_NOTE =
  "Subir, extraer, adaptar, generar audio, traducir o describir imágenes requiere conexión con el servidor; la IA, la traducción y el audio no funcionan sin conexión.";

/** Divide los recursos en los que funcionan sin conexión y los que la requieren. */
export function splitByConnection(resources: ResourceAvailability[]) {
  return {
    offline: resources.filter(r => r.works_offline_on_device),
    needsConnection: resources.filter(r => !r.works_offline_on_device),
  };
}

export function describeResource(r: ResourceAvailability, online: boolean): string {
  if (r.works_offline_on_device) return "Disponible sin conexión";
  if (!r.available) return r.note || "No disponible en este servidor";
  if (!online) return "Requiere conexión con el servidor";
  return r.requires_internet ? "Requiere Internet" : "Disponible en la red local";
}
