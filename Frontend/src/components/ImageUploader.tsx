import React, { useState, useRef } from "react";
import { UploadCloud, Image as ImageIcon, X, Loader2 } from "lucide-react";
import { env } from "@/config/env";

interface ImageUploaderProps {
  onUploadSuccess: (url: string) => void;
  currentUrl?: string;
  label?: string;
}

// Reliable pure JS SHA-1 implementation
function sha1(str: string): string {
  const buffer = new TextEncoder().encode(str);
  const len = buffer.length;
  const words = new Uint32Array(((len + 8) >> 6) + 1 << 4);
  for (let i = 0; i < len; i++) words[i >> 2] |= buffer[i] << (24 - (i % 4) * 8);
  words[len >> 2] |= 0x80 << (24 - (len % 4) * 8);
  words[words.length - 1] = len * 8;

  let h = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0];
  const rotateLeft = (n: number, s: number) => (n << s) | (n >>> (32 - s));

  for (let i = 0; i < words.length; i += 16) {
    const w = new Uint32Array(80);
    for (let j = 0; j < 16; j++) w[j] = words[i + j];
    for (let j = 16; j < 80; j++) w[j] = rotateLeft(w[j - 3] ^ w[j - 8] ^ w[j - 14] ^ w[j - 16], 1);

    let [a, b, c, d, e] = h;
    for (let j = 0; j < 80; j++) {
      let f, k;
      if (j < 20) { f = (b & c) | (~b & d); k = 0x5A827999; }
      else if (j < 40) { f = b ^ c ^ d; k = 0x6ED9EBA1; }
      else if (j < 60) { f = (b & c) | (b & d) | (c & d); k = 0x8F1BBCDC; }
      else { f = b ^ c ^ d; k = 0xCA62C1D6; }
      const temp = (rotateLeft(a, 5) + f + e + k + w[j]) | 0;
      e = d; d = c; c = rotateLeft(b, 30); b = a; a = temp;
    }
    h[0] = (h[0] + a) | 0; h[1] = (h[1] + b) | 0; h[2] = (h[2] + c) | 0; h[3] = (h[3] + d) | 0; h[4] = (h[4] + e) | 0;
  }
  return h.map(x => (x >>> 0).toString(16).padStart(8, '0')).join('');
}

async function generateSignature(timestamp: number): Promise<string> {
  const msg = `timestamp=${timestamp}${env.cloudinaryApiSecret}`;
  return sha1(msg);
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
      formData.append("api_key", env.cloudinaryApiKey);
      formData.append("timestamp", timestamp.toString());
      formData.append("signature", signature);
      // Optional: you can add folder name if needed
      // formData.append("folder", "roadsentinel/uploads");

      const response = await fetch(`https://api.cloudinary.com/v1_1/${env.cloudinaryCloudName}/image/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (response.ok && data.secure_url) {
        setPreviewUrl(data.secure_url);
        onUploadSuccess(data.secure_url);
      } else {
        console.error("Cloudinary Error Response:", data);
        throw new Error(data.error?.message || "Upload failed");
      }
    } catch (error) {
      console.error("Cloudinary upload catch error:", error);
      alert(error instanceof Error ? error.message : "Failed to upload image.");
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
