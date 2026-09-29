import React, { useState, useEffect } from "react";
import {
  X,
  Upload,
  FileText,
  Download,
  CheckCircle,
  Paperclip,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";
import {
  uploadEvaluationAttachment,
  fetchEvaluationDetails,
  getAuthToken,
} from "../utils/apiClient";

interface AttachmentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  evaluationId: string;
  onNotification: (msg: string) => void;
}

export const AttachmentUploadModal: React.FC<AttachmentUploadModalProps> = ({
  isOpen,
  onClose,
  evaluationId,
  onNotification,
}) => {
  const [attachments, setAttachments] = useState<any[]>([]);
  const [description, setDescription] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const loadAttachments = async () => {
    if (!evaluationId) return;
    setIsLoading(true);
    try {
      const details = await fetchEvaluationDetails(evaluationId);
      if (details && details.attachments) {
        setAttachments(details.attachments);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadAttachments();
    }
  }, [isOpen, evaluationId]);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!evaluationId) {
      alert("Please create or select an evaluation before uploading attachments.");
      return;
    }

    if (!selectedFile) {
      alert("Please select a file to upload");
      return;
    }

    if (selectedFile.size === 0) {
      alert("The selected file is empty.");
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      alert("File size exceeds maximum allowed limit of 10 MB.");
      return;
    }

    const dangerousExts = [
      ".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs", ".js", ".py", ".php",
      ".pl", ".dll", ".scr", ".msi", ".jar", ".com", ".hta", ".bin", ".iso", ".wsf"
    ];
    const dotIdx = selectedFile.name.lastIndexOf(".");
    const ext = dotIdx !== -1 ? selectedFile.name.substring(dotIdx).toLowerCase() : "";
    if (dangerousExts.includes(ext)) {
      alert(`Dangerous file type '${ext}' is forbidden for security.`);
      return;
    }

    const allowedExts = [
      ".pdf", ".png", ".jpg", ".jpeg", ".csv", ".xlsx", ".xls", ".txt", ".docx", ".doc"
    ];
    if (!allowedExts.includes(ext)) {
      alert(`Unsupported file type '${ext}'. Allowed types: PDF, PNG, JPG, JPEG, CSV, XLSX, TXT, DOCX`);
      return;
    }

    setIsUploading(true);
    try {
      const reader = new FileReader();
      reader.onload = async () => {
        const base64Data = (reader.result as string).split(",")[1];
        const res = await uploadEvaluationAttachment(
          evaluationId,
          base64Data,
          selectedFile.name,
          description || "Metrological verification evidence",
          selectedFile.type || "application/octet-stream",
        );

        if (res.success) {
          onNotification(`Uploaded ${selectedFile.name} successfully`);
          setSelectedFile(null);
          setDescription("");
          await loadAttachments();
        } else {
          alert(res.error || "Upload failed");
        }
      };
      reader.readAsDataURL(selectedFile);
    } catch (err: any) {
      alert("Error reading file: " + err.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
      <div className="bg-white border border-[#E2E8F0] rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E2E8F0] bg-slate-50/50">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
              <Paperclip className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-[#0F172A]">
                Metrological Test Evidence & Attachments
              </h2>
              <p className="text-xs text-[#64748B]">
                Evaluation ID:{" "}
                <span className="font-mono">
                  {evaluationId || "No active evaluation"}
                </span>
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={loadAttachments}
              className="p-1.5 text-slate-500 hover:text-slate-800 rounded transition-colors"
            >
              <RefreshCw
                className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`}
              />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 rounded transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-5">
          {!evaluationId && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800 flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>
                Please start or select an evaluation first to link and view
                attachments.
              </span>
            </div>
          )}

          {/* Upload Area */}
          <div className="p-4 border-2 border-dashed border-[#E2E8F0] rounded-lg bg-slate-50/50 space-y-3">
            <div className="flex flex-col items-center justify-center text-center">
              <Upload className="w-8 h-8 text-blue-500 mb-2" />
              <div className="text-xs font-semibold text-[#0F172A]">
                Upload Scale Evidence or Certificate
              </div>
              <div className="text-[11px] text-[#64748B]">
                PDF, PNG, JPG, or CSV (Max 10 MB)
              </div>
              <input
                type="file"
                disabled={!evaluationId}
                onChange={handleFileChange}
                className="mt-3 block text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
              />
            </div>

            {selectedFile && (
              <div className="space-y-2 pt-2 border-t border-slate-200">
                <input
                  type="text"
                  placeholder="Description (e.g. Standard Weights Calibration Certificate)"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full text-xs p-2 border border-[#E2E8F0] rounded focus:outline-none focus:border-blue-600 bg-white"
                />
                <button
                  onClick={handleUpload}
                  disabled={isUploading}
                  className="w-full py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded transition-colors shadow-xs"
                >
                  {isUploading ? "Uploading..." : "Confirm Upload Attachment"}
                </button>
              </div>
            )}
          </div>

          {/* Existing Attachments List */}
          <div className="space-y-2">
            <div className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">
              Uploaded Attachments ({attachments.length})
            </div>
            {attachments.length === 0 ? (
              <div className="text-xs text-slate-400 py-3 text-center border border-dashed rounded">
                No attachments uploaded yet.
              </div>
            ) : (
              <div className="divide-y divide-slate-100 border border-[#E2E8F0] rounded-lg overflow-hidden">
                {attachments.map((att) => {
                  const token = getAuthToken();
                  const downloadUrl = `/api/attachments/${att.id}/download${token ? `?token=${encodeURIComponent(token)}` : ""}`;
                  return (
                    <div
                      key={att.id}
                      className="p-3 flex items-center justify-between hover:bg-slate-50 transition-colors"
                    >
                      <div className="flex items-center space-x-3">
                        <FileText className="w-5 h-5 text-blue-600" />
                        <div>
                          <div className="text-xs font-medium text-slate-900">
                            {att.original_name}
                          </div>
                          <div className="text-[11px] text-slate-500">
                            {att.description} •{" "}
                            {(att.file_size / 1024).toFixed(1)} KB •{" "}
                            {att.uploaded_at?.slice(0, 10)}
                          </div>
                        </div>
                      </div>
                      <a
                        href={downloadUrl}
                        download={att.original_name}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1.5 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"
                        title="Download Attachment"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#E2E8F0] bg-slate-50 text-right">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-medium text-slate-700 bg-white border border-[#E2E8F0] rounded hover:bg-slate-100 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
