export function getApiBase(): string {
  return import.meta.env.VITE_CREWAI_ENDPOINT || '';
}
