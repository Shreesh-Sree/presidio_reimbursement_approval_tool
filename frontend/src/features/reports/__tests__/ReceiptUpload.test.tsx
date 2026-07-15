import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ReceiptUpload } from '../ReceiptUpload';

describe('ReceiptUpload', () => {
  it('renders file input', () => {
    render(<ReceiptUpload itemId="test-id" />);
    const input = screen.getByRole('button', { name: /upload receipt/i });
    expect(input).toBeInTheDocument();
  });

  it('handles file upload', async () => {
    const onUploadComplete = vi.fn();
    render(<ReceiptUpload itemId="test-id" onUploadComplete={onUploadComplete} />);

    const file = new File(['receipt'], 'receipt.pdf', { type: 'application/pdf' });
    const input = screen.getByRole('button', { name: /upload receipt/i });

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/receipt.pdf/i)).toBeInTheDocument();
    });
  });

  it('shows error on upload failure', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Upload failed'));
    render(<ReceiptUpload itemId="test-id" />);

    const file = new File(['receipt'], 'receipt.pdf', { type: 'application/pdf' });
    const input = screen.getByRole('button', { name: /upload receipt/i });

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/upload failed/i)).toBeInTheDocument();
    });
  });
});
