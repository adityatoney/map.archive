"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { FileUp, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useUploadReport, useAnalyzeReport } from "@/lib/hooks/use-api";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const upload = useUploadReport();
  const analyze = useAnalyzeReport();

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) setFile(droppedFile);
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    try {
      const result = await upload.mutateAsync(file);
      // Auto-trigger analysis
      await analyze.mutateAsync(result.session_id);
      router.push(`/dashboard/report/${result.session_id}`);
    } catch {
      // Error handled by mutation state
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Upload Scan Report</h1>
        <p className="text-gray-500">
          Upload a Tesla Med Bed scan report for analysis
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Select Report File</CardTitle>
          <CardDescription>
            Supported formats: PDF, CSV, JSON, PNG, JPG
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Drop zone */}
          <div
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
              dragOver
                ? "border-blue-500 bg-blue-50 dark:bg-blue-950/20"
                : "border-gray-300 dark:border-gray-700"
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            <FileUp className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Drag and drop your report file here, or
            </p>
            <label htmlFor="file-input">
              <Button variant="outline" asChild>
                <span>Browse Files</span>
              </Button>
              <input
                id="file-input"
                type="file"
                className="hidden"
                accept=".pdf,.csv,.json,.png,.jpg,.jpeg"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>
          </div>

          {/* Selected file */}
          {file && (
            <div className="mt-4 flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
              <div>
                <p className="font-medium text-sm">{file.name}</p>
                <p className="text-xs text-gray-500">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
              <Button
                onClick={handleUpload}
                disabled={upload.isPending || analyze.isPending}
              >
                {upload.isPending || analyze.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    {upload.isPending ? "Uploading..." : "Analyzing..."}
                  </>
                ) : (
                  <>
                    <FileUp className="h-4 w-4 mr-2" />
                    Upload & Analyze
                  </>
                )}
              </Button>
            </div>
          )}

          {/* Success */}
          {upload.isSuccess && (
            <Alert className="mt-4" variant="default">
              <CheckCircle className="h-4 w-4" />
              <AlertTitle>Upload Successful</AlertTitle>
              <AlertDescription>
                {upload.data.message}. Redirecting to report view...
              </AlertDescription>
            </Alert>
          )}

          {/* Error */}
          {(upload.isError || analyze.isError) && (
            <Alert className="mt-4" variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>
                {(upload.error || analyze.error)?.message ||
                  "An error occurred"}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
