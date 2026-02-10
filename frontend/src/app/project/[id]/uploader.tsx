"use client";

import { useState, useRef, useCallback } from "react";
import { uploadImage } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { UploadCloud, CheckCircle2, AlertCircle, FileImage, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";

type UploadStatus = "pending" | "uploading" | "success" | "error";

interface UploadItem {
  id: string;
  file: File;
  status: UploadStatus;
}

export function Uploader({ projectId }: { projectId: string }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const uploadFile = useCallback(async (item: UploadItem) => {
    setUploads(prev => prev.map(u => u.id === item.id ? { ...u, status: "uploading" } : u));
    try {
      await uploadImage(projectId, item.file);
      setUploads(prev => prev.map(u => u.id === item.id ? { ...u, status: "success" } : u));
      router.refresh();
    } catch (err) {
      setUploads(prev => prev.map(u => u.id === item.id ? { ...u, status: "error" } : u));
    }
  }, [projectId, router]);

  const processFiles = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return;
    
    const newUploads: UploadItem[] = Array.from(files)
      .filter(f => f.type.startsWith('image/'))
      .map(file => ({
        id: crypto.randomUUID(),
        file,
        status: "pending" as UploadStatus,
      }));
    
    setUploads(prev => [...newUploads, ...prev]);
    
    newUploads.forEach(item => {
      uploadFile(item);
    });
  }, [uploadFile]);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    processFiles(e.dataTransfer.files);
  };

  return (
    <div className="flex flex-col gap-8">
      <Card
        className={`border-2 border-dashed flex flex-col items-center justify-center p-12 transition-colors cursor-pointer ${
          isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50"
        }`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <UploadCloud className={`h-12 w-12 mb-4 ${isDragging ? "text-primary" : "text-muted-foreground"}`} />
        <h3 className="text-xl font-semibold mb-2">Drag and drop images here</h3>
        <p className="text-muted-foreground mb-4 text-center max-w-sm">
          Supports JPEG, PNG, WEBP. Bulk upload is supported.
        </p>
        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          multiple
          accept="image/*"
          onChange={(e) => processFiles(e.target.files)}
        />
      </Card>

      {uploads.length > 0 && (
        <div className="space-y-4">
          <h4 className="font-medium text-lg">Uploads</h4>
          <div className="grid gap-3 max-h-100 overflow-y-auto pr-2">
            {uploads.map((upload) => (
              <Card key={upload.id} className="p-3 flex items-center gap-4">
                <div className="p-2 bg-muted rounded-md">
                  <FileImage className="h-6 w-6 text-muted-foreground" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{upload.file.name}</p>
                  <p className="text-xs text-muted-foreground">{(upload.file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
                <div>
                  {upload.status === "pending" && <span className="text-xs text-muted-foreground">Waiting...</span>}
                  {upload.status === "uploading" && <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />}
                  {upload.status === "success" && <CheckCircle2 className="h-5 w-5 text-green-500" />}
                  {upload.status === "error" && <AlertCircle className="h-5 w-5 text-destructive" />}
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
