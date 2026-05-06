import React, { useState, useRef } from "react";
import { UploadCloud, Image as ImageIcon, X, Loader2 } from "lucide-react";

interface ImageUploaderProps {
  onUploadSuccess: (url: string) => void;
  currentUrl?: string;
  label?: string;
}

const CLOUDINARY_CLOUD_NAME = "dks1edqey";
const CLOUDINARY_API_KEY = "326677388198311";
const CLOUDINARY_API_SECRET = "sfp-8J3NqwkijI7m1JD54Sq5GzU";

async function generateSignature(timestamp: number): Promise<string> {
  const msg = `timestamp=${timestamp}${CLOUDINARY_API_SECRET}`;
  const msgBuffer = new TextEncoder().encode(msg);
  const hashBuffer = await crypto.subtle.digest('SHA-1', msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

export function ImageUploader({ onUploadSuccess, currentUrl, label = "Upload Image" }: ImageUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string>(currentUrl || "");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (file: File) => {
    if (!file.type.startsWith("image/")) {
      alert("Please upload an image file.");
      return;
    }

    setIsUploading(true);
    try {
      const timestamp = Math.round(new Date().getTime() / 1000);
      const signature = await generateSignature(timestamp);

      const formData = new FormData();
      formData.append("file", file);
      formData.append("api_key", CLOUDINARY_API_KEY);
      formData.append("timestamp", timestamp.toString());
      formData.append("signature", signature);
      // Optional: you can add folder name if needed
      // formData.append("folder", "roadsentinel/uploads");

      const response = await fetch(`https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD_NAME}/image/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (response.ok && data.secure_url) {
        setPreviewUrl(data.secure_url);
        onUploadSuccess(data.secure_url);
      } else {
        throw new Error(data.error?.message || "Upload failed");
      }
    } catch (error) {
      console.error("Cloudinary upload error:", error);
      alert("Failed to upload image.");
    } finally {
      setIsUploading(false);
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleUpload(e.dataTransfer.files[0]);
    }
  };

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleUpload(e.target.files[0]);
    }
  };

  const clearImage = () => {
    setPreviewUrl("");
    onUploadSuccess("");
  };

  return (
    <div className="flex flex-col gap-2 w-full">
      <label className="text-sm font-bold text-secondary">{label}</label>
      
      {previewUrl ? (
        <div className="relative group rounded-xl overflow-hidden border border-surface-container-highest bg-surface-container w-full aspect-square flex items-center justify-center">
          <img src={previewUrl} alt="Preview" className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <button 
              type="button"
              onClick={clearImage}
              className="bg-error text-white p-2 rounded-full hover:bg-error/90 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      ) : (
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`
            border-2 border-dashed rounded-xl w-full aspect-square flex flex-col items-center justify-center cursor-pointer transition-colors p-4 text-center
            ${isDragging ? "border-primary bg-primary/5" : "border-surface-container-highest bg-surface-container hover:bg-surface-container-low"}
          `}
        >
          {isUploading ? (
            <div className="flex flex-col items-center gap-2 text-primary">
              <Loader2 className="w-8 h-8 animate-spin" />
              <span className="text-sm font-medium">Uploading...</span>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 text-secondary">
              <UploadCloud className="w-8 h-8 opacity-70" />
              <span className="text-sm font-medium">Click or drag image</span>
            </div>
          )}
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={onChange} 
            accept="image/*" 
            className="hidden" 
          />
        </div>
      )}
    </div>
  );
}
