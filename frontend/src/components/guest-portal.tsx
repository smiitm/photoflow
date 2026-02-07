"use client";

import { useState, useRef } from "react";
import { searchFaces, SearchMatch } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Camera, Loader2 } from "lucide-react";
import { Gallery } from "./gallery";

export function GuestPortal({ projectId }: { projectId: string }) {
  const [matches, setMatches] = useState<SearchMatch[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError("");
    setMatches(null);

    try {
      const results = await searchFaces(projectId, file);
      setMatches(results);
    } catch (err: any) {
      setError(err.message || "Failed to search faces");
    } finally {
      setLoading(false);
      // Reset input so the same file can be selected again if needed
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  if (matches !== null) {
    return (
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">
            Found {matches.length} photo{matches.length !== 1 ? 's' : ''}
          </h2>
          <Button variant="outline" onClick={() => setMatches(null)}>
            Search Again
          </Button>
        </div>
        <Gallery projectId={projectId} matches={matches} />
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto w-full">
      <Card
        className="border-2 border-dashed flex flex-col items-center justify-center p-12 transition-colors cursor-pointer hover:border-primary/50 hover:bg-accent/50 text-center"
        onClick={() => fileInputRef.current?.click()}
      >
        {loading ? (
          <Loader2 className="h-12 w-12 text-primary animate-spin mb-4" />
        ) : (
          <Camera className="h-12 w-12 text-muted-foreground mb-4" />
        )}
        
        <h3 className="text-xl font-semibold mb-2">
          {loading ? "Analyzing face..." : "Take or upload a selfie"}
        </h3>
        
        {!loading && (
          <p className="text-muted-foreground mb-6">
            We'll use facial recognition to find your photos securely.
          </p>
        )}
        
        <Button disabled={loading} className="w-full sm:w-auto">
          {loading ? "Searching..." : "Select Selfie"}
        </Button>

        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          accept="image/*"
          capture="user"
          onChange={handleFileChange}
        />
      </Card>

      {error && (
        <div className="mt-4 p-4 text-sm text-destructive bg-destructive/10 rounded-md text-center">
          {error}
        </div>
      )}
    </div>
  );
}
