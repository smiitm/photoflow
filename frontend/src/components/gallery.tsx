"use client";

import { useState } from "react";
import { SearchMatch, downloadZip } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Download, Loader2 } from "lucide-react";

export function Gallery({ projectId, matches }: { projectId: string; matches: SearchMatch[] }) {
  const [downloading, setDownloading] = useState(false);

  const handleDownloadAll = async () => {
    if (matches.length === 0) return;
    
    setDownloading(true);
    try {
      const keys = matches.map(m => m.s3_key);
      const blob = await downloadZip(projectId, keys);
      
      // Create a temporary link to trigger download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `photoflow-${projectId}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error(err);
      alert("Failed to download ZIP");
    } finally {
      setDownloading(false);
    }
  };

  if (matches.length === 0) {
    return (
      <div className="text-center py-20 bg-muted/30 rounded-lg">
        <p className="text-muted-foreground text-lg">We couldn't find any photos matching your selfie.</p>
        <p className="text-sm text-muted-foreground mt-2">Try uploading a different photo with a clear view of your face.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button onClick={handleDownloadAll} disabled={downloading}>
          {downloading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Download className="mr-2 h-4 w-4" />
          )}
          {downloading ? "Preparing ZIP..." : "Download All"}
        </Button>
      </div>

      <div className="columns-1 sm:columns-2 md:columns-3 lg:columns-4 gap-4 space-y-4">
        {matches.map((match) => (
          <div key={match.s3_key} className="break-inside-avoid relative group rounded-lg overflow-hidden border bg-muted">
            <img 
              src={match.url} 
              alt="Match" 
              className="w-full h-auto object-cover transition-transform duration-300 group-hover:scale-105"
              loading="lazy"
            />
            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
              <a 
                href={match.url} 
                download 
                target="_blank" 
                rel="noreferrer"
                className="bg-white/20 hover:bg-white/40 text-white rounded-full p-3 backdrop-blur-sm transition-colors"
              >
                <Download className="h-5 w-5" />
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
