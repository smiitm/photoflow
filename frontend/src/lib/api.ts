const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface Project {
  id: string;
  name: string;
  created_at: string;
  image_count: number;
}

export interface ImageResponse {
  id: string;
  project_id: string;
  s3_key: string;
}

export interface SearchMatch {
  s3_key: string;
  url: string;
  distance: number;
}

export async function getProjects(): Promise<Project[]> {
  const res = await fetch(`${API_BASE_URL}/projects`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch projects");
  return res.json();
}

export async function getProject(id: string): Promise<Project> {
  const res = await fetch(`${API_BASE_URL}/projects/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch project");
  return res.json();
}

export async function createProject(name: string): Promise<Project> {
  const res = await fetch(`${API_BASE_URL}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error("Failed to create project");
  return res.json();
}

export async function uploadImage(projectId: string, file: File): Promise<ImageResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/projects/${projectId}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to upload image");
  return res.json();
}

export async function searchFaces(projectId: string, file: File): Promise<SearchMatch[]> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/projects/${projectId}/search`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to search faces");
  }
  return res.json();
}

export async function downloadZip(projectId: string, s3Keys: string[]): Promise<Blob> {
  const res = await fetch(`${API_BASE_URL}/projects/${projectId}/download-zip`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ s3_keys: s3Keys }),
  });
  if (!res.ok) throw new Error("Failed to download zip");
  return res.blob();
}
