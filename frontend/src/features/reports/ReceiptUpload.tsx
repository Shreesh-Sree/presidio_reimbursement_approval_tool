import { useState } from 'react';

interface ReceiptUploadProps {
  itemId: string;
  onUploadComplete?: (receiptUrl: string) => void;
}

export function ReceiptUpload({ itemId, onUploadComplete }: ReceiptUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [receipt, setReceipt] = useState<{ url: string; name: string } | null>(null);
  const [error, setError] = useState('');

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`/api/items/${itemId}/receipt`, {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) throw new Error('Upload failed');

      const data = await response.json();
      setReceipt({ url: data.receipt_url, name: file.name });
      onUploadComplete?.(data.receipt_url);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="receipt-upload">
      <label>
        <input
          type="file"
          accept="image/*,application/pdf"
          onChange={handleFileChange}
          disabled={uploading}
        />
        {uploading ? 'Uploading...' : 'Upload Receipt'}
      </label>
      {receipt && (
        <div className="receipt-preview">
          <a href={receipt.url} target="_blank" rel="noreferrer">
            {receipt.name}
          </a>
        </div>
      )}
      {error && <div className="error">{error}</div>}
    </div>
  );
}
