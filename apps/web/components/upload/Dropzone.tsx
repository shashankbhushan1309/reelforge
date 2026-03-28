"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import * as tus from "tus-js-client";
import { UploadCloud, File, AlertCircle } from "lucide-react";

export function Dropzone() {
  const [uploads, setUploads] = useState<{ [key: string]: number }>({});
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setError(null);

    for (const file of acceptedFiles) {
      try {
        // 1. Initiate upload with API
        const initRes = await fetch("/api/v1/upload/initiate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            filename: file.name,
            file_size: file.size,
            content_type: file.type,
          }),
        });

        if (!initRes.ok) {
          throw new Error("Failed to initiate upload");
        }

        const { upload_url } = await initRes.json();

        // 2. Start tus upload
        const upload = new tus.Upload(file, {
          endpoint: "/api/v1/upload",
          uploadUrl: upload_url,
          retryDelays: [0, 3000, 5000, 10000, 20000],
          metadata: {
            filename: file.name,
            filetype: file.type,
          },
          onError(err) {
            setError(`Upload failed: ${err.message}`);
          },
          onProgress(bytesUploaded, bytesTotal) {
            const percentage = ((bytesUploaded / bytesTotal) * 100).toFixed(2);
            setUploads((prev) => ({ ...prev, [file.name]: parseFloat(percentage) }));
          },
          onSuccess() {
            setUploads((prev) => ({ ...prev, [file.name]: 100 }));
          },
        });

        upload.start();
      } catch (err: any) {
        setError(err.message);
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "video/*": [".mp4", ".mov", ".webm"],
      "image/*": [".jpg", ".jpeg", ".png", ".webp", ".heic"],
    },
  });

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
          isDragActive
            ? "border-blue-500 bg-blue-500/10"
            : "border-gray-700 bg-gray-900/50 hover:bg-gray-800"
        }`}
      >
        <input {...getInputProps()} />
        <UploadCloud className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <p className="text-gray-300 font-medium text-lg">
          {isDragActive ? "Drop files here" : "Drag & drop files or click to browse"}
        </p>
        <p className="text-gray-500 text-sm mt-2">
          Supports video (MP4, MOV) and images (JPG, PNG). Max file size 1GB.
        </p>
      </div>

      {error && (
        <div className="mt-4 p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center text-red-400">
          <AlertCircle className="w-5 h-5 mr-3" />
          {error}
        </div>
      )}

      {Object.keys(uploads).length > 0 && (
        <div className="mt-6 space-y-3">
          {Object.entries(uploads).map(([filename, progress]) => (
            <div key={filename} className="bg-gray-800 rounded-lg p-4">
              <div className="flex justify-between text-sm mb-2">
                <span className="flex items-center text-gray-200 truncate">
                  <File className="w-4 h-4 mr-2 text-gray-400" />
                  {filename}
                </span>
                <span className="text-blue-400 ml-4 font-mono">{progress}%</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-blue-500 h-1.5 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
