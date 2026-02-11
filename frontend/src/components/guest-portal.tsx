"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { searchFaces, SearchMatch } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Camera, Loader2, Upload, RefreshCw, X, ChevronLeft, Image as ImageIcon } from "lucide-react";
import { Gallery } from "./gallery";

type Mode = "menu" | "camera" | "upload" | "preview" | "searching" | "results";

export function GuestPortal({ projectId }: { projectId: string }) {
  const [mode, setMode] = useState<Mode>("menu");
  const [matches, setMatches] = useState<SearchMatch[] | null>(null);
  const [error, setError] = useState("");
  
  // Camera state
  const videoRef = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [currentDeviceId, setCurrentDeviceId] = useState<string>("");
  
  // File / Preview state
  const [capturedFile, setCapturedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Stop camera stream
  const stopCamera = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
  }, [stream]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  // Attach stream to video element when it mounts
  useEffect(() => {
    if (mode === "camera" && videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [mode, stream]);

  const startCamera = async (deviceId?: string) => {
    stopCamera();
    setError("");
    try {
      const constraints: MediaStreamConstraints = {
        video: deviceId ? { deviceId: { exact: deviceId } } : { facingMode: "user" },
        audio: false,
      };
      
      const newStream = await navigator.mediaDevices.getUserMedia(constraints);
      setStream(newStream);
      
      // Get available cameras for switching (if multiple exist)
      const allDevices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = allDevices.filter((d) => d.kind === "videoinput");
      setDevices(videoDevices);
      
      if (videoDevices.length > 0 && !deviceId) {
        // Find the active device id from the stream
        const activeTrack = newStream.getVideoTracks()[0];
        const activeDevice = videoDevices.find(d => d.label === activeTrack.label);
        if (activeDevice) setCurrentDeviceId(activeDevice.deviceId);
        else setCurrentDeviceId(videoDevices[0].deviceId);
      } else if (deviceId) {
        setCurrentDeviceId(deviceId);
      }
      
      setMode("camera");
    } catch (err: any) {
      console.error("Camera error:", err);
      setError("Unable to access camera. Please allow permissions or use file upload.");
      setMode("upload"); // fallback
    }
  };

  const switchCamera = () => {
    if (devices.length < 2) return;
    const currentIndex = devices.findIndex((d) => d.deviceId === currentDeviceId);
    const nextIndex = (currentIndex + 1) % devices.length;
    startCamera(devices[nextIndex].deviceId);
  };

  const capturePhoto = () => {
    if (videoRef.current) {
      const video = videoRef.current;
      const canvas = document.createElement("canvas");
      // Use the actual video dimensions for high quality
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        canvas.toBlob((blob) => {
          if (blob) {
            const file = new File([blob], "selfie.jpg", { type: "image/jpeg" });
            const url = URL.createObjectURL(blob);
            setCapturedFile(file);
            setPreviewUrl(url);
            stopCamera();
            setMode("preview");
          }
        }, "image/jpeg", 0.95);
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const url = URL.createObjectURL(file);
    setCapturedFile(file);
    setPreviewUrl(url);
    setMode("preview");
    
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSearch = async () => {
    if (!capturedFile) return;
    setMode("searching");
    setError("");
    setMatches(null);

    try {
      const results = await searchFaces(projectId, capturedFile);
      setMatches(results);
      setMode("results");
      // Revoke the object URL now that we have results — no longer needed for display
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
        setPreviewUrl(null);
      }
    } catch (err: any) {
      setError(err.message || "Failed to search faces");
      setMode("preview");
    }
  };

  const resetToMenu = () => {
    stopCamera();
    setCapturedFile(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setMatches(null);
    setError("");
    setMode("menu");
  };

  // ---------------------------------------------------------------------------
  // Render Helpers
  // ---------------------------------------------------------------------------

  const renderMenu = () => (
    <div className="grid gap-6 sm:grid-cols-2 max-w-2xl mx-auto w-full animate-in fade-in zoom-in-95 duration-300">
      <Card
        className="group flex flex-col items-center justify-center p-8 transition-all cursor-pointer hover:border-primary hover:shadow-lg hover:shadow-primary/10 border-2"
        onClick={() => startCamera()}
      >
        <div className="rounded-full bg-primary/10 p-4 mb-6 group-hover:scale-110 transition-transform duration-300">
          <Camera className="h-10 w-10 text-primary" />
        </div>
        <h3 className="text-xl font-bold mb-2">Live Selfie</h3>
        <p className="text-sm text-muted-foreground text-center">
          Take a photo right now to find your pictures instantly.
        </p>
      </Card>

      <Card
        className="group flex flex-col items-center justify-center p-8 transition-all cursor-pointer hover:border-primary hover:shadow-lg hover:shadow-primary/10 border-2"
        onClick={() => {
          setMode("upload");
          fileInputRef.current?.click();
        }}
      >
        <div className="rounded-full bg-secondary p-4 mb-6 group-hover:scale-110 transition-transform duration-300">
          <Upload className="h-10 w-10 text-foreground" />
        </div>
        <h3 className="text-xl font-bold mb-2">Upload Photo</h3>
        <p className="text-sm text-muted-foreground text-center">
          Choose an existing photo from your device.
        </p>
      </Card>
      
    </div>
  );

  const renderCamera = () => (
    <div className="max-w-md mx-auto w-full animate-in slide-in-from-bottom-4 duration-300">
      <Card className="relative overflow-hidden bg-black aspect-[3/4] sm:aspect-video rounded-xl border-2 flex items-center justify-center shadow-2xl">
        {!stream && <Loader2 className="h-8 w-8 text-white animate-spin absolute" />}
        
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover transition-opacity duration-500 scale-x-[-1]"
        />

        {/* Face Guide Overlay */}
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
          <div className="w-48 h-64 sm:w-56 sm:h-72 border-2 border-white/30 rounded-[40%] animate-pulse" />
        </div>

        {/* Top Controls */}
        <div className="absolute top-4 left-4 right-4 flex justify-between">
          <Button variant="secondary" size="icon" className="rounded-full bg-black/40 hover:bg-black/60 text-white backdrop-blur-md border-0" onClick={resetToMenu}>
            <X className="h-5 w-5" />
          </Button>
          {devices.length > 1 && (
            <Button variant="secondary" size="icon" className="rounded-full bg-black/40 hover:bg-black/60 text-white backdrop-blur-md border-0" onClick={switchCamera}>
              <RefreshCw className="h-5 w-5" />
            </Button>
          )}
        </div>

        {/* Bottom Controls */}
        <div className="absolute bottom-6 left-0 right-0 flex justify-center">
          <button
            onClick={capturePhoto}
            className="w-20 h-20 rounded-full border-4 border-white/50 bg-white/20 hover:bg-white/40 backdrop-blur-sm transition-all active:scale-95 flex items-center justify-center group"
          >
            <div className="w-14 h-14 bg-white rounded-full transition-transform group-hover:scale-90" />
          </button>
        </div>
      </Card>
    </div>
  );

  const renderPreview = () => (
    <div className="max-w-md mx-auto w-full animate-in fade-in zoom-in-95 duration-300">
      <Card className="overflow-hidden bg-black/5 aspect-[3/4] sm:aspect-video rounded-xl border-2 shadow-xl relative group">
        {previewUrl && (
          <img src={previewUrl} alt="Preview" className="w-full h-full object-cover" />
        )}
      </Card>
      
      <div className="mt-6 flex flex-col sm:flex-row gap-3">
        <Button 
          variant="outline" 
          size="lg" 
          className="flex-1"
          onClick={() => {
            if (devices.length > 0) startCamera();
            else { setMode("upload"); fileInputRef.current?.click(); }
          }}
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Retake
        </Button>
        <Button 
          size="lg" 
          className="flex-1 bg-primary text-primary-foreground shadow-lg hover:shadow-primary/25"
          onClick={handleSearch}
        >
          <Camera className="mr-2 h-4 w-4" />
          Find My Photos
        </Button>
      </div>
    </div>
  );

  const renderSearching = () => (
    <div className="max-w-md mx-auto w-full flex flex-col items-center justify-center py-20 animate-in fade-in duration-500">
      <div className="relative mb-8">
        <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl animate-pulse" />
        {previewUrl && (
          <div className="relative w-32 h-32 rounded-full overflow-hidden border-4 border-primary/50">
            <img src={previewUrl} alt="Analyzing" className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/30 to-transparent animate-scan" />
          </div>
        )}
      </div>
      <h3 className="text-2xl font-bold mb-2">Analyzing Face</h3>
      <p className="text-muted-foreground text-center">
        Scanning our gallery securely to find your matches...
      </p>
    </div>
  );

  const renderUploadFallback = () => (
    <div className="max-w-md mx-auto w-full animate-in fade-in duration-300">
      <Card
        className="border-2 border-dashed flex flex-col items-center justify-center p-12 transition-colors cursor-pointer hover:border-primary/50 hover:bg-accent/50 text-center"
        onClick={() => fileInputRef.current?.click()}
      >
        <ImageIcon className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-xl font-semibold mb-2">Select a photo</h3>
        <p className="text-muted-foreground mb-6">
          Upload a clear picture of your face.
        </p>
        <Button className="w-full sm:w-auto">Browse Files</Button>
      </Card>
      <div className="mt-4 flex justify-center">
        <Button variant="ghost" onClick={resetToMenu}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back to Options
        </Button>
      </div>
    </div>
  );

  return (
    <div className="w-full">
      {/* Hidden file input — always in the DOM so the ref survives mode changes */}
      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        accept="image/*"
        onChange={handleFileChange}
      />

      <style dangerouslySetInnerHTML={{__html: `
        @keyframes scan {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100%); }
        }
        .animate-scan { animation: scan 2s ease-in-out infinite; }
      `}} />
      
      {error && (
        <div className="max-w-md mx-auto mb-6 p-4 text-sm text-destructive bg-destructive/10 rounded-lg text-center animate-in slide-in-from-top-2 flex items-center justify-center gap-2">
          {error}
        </div>
      )}

      {mode === "menu" && renderMenu()}
      {mode === "camera" && renderCamera()}
      {mode === "preview" && renderPreview()}
      {mode === "searching" && renderSearching()}
      {mode === "upload" && renderUploadFallback()}
      
      {mode === "results" && matches && (
        <div className="space-y-8 animate-in fade-in duration-500">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <h2 className="text-3xl font-bold">
              Found {matches.length} photo{matches.length !== 1 ? 's' : ''}
            </h2>
            <Button variant="outline" onClick={resetToMenu} className="shrink-0">
              <RefreshCw className="mr-2 h-4 w-4" />
              Search Again
            </Button>
          </div>
          <Gallery projectId={projectId} matches={matches} />
        </div>
      )}
    </div>
  );
}
