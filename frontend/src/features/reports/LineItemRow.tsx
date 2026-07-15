import { ReceiptUpload } from './ReceiptUpload';

interface LineItem {
  id: string;
  description: string;
  amount: number;
  category: string;
  receiptUrl?: string;
}

interface LineItemRowProps {
  item: LineItem;
  onUpdate?: (item: LineItem) => void;
  onDelete?: (itemId: string) => void;
}

export function LineItemRow({ item, onUpdate, onDelete }: LineItemRowProps) {
  return (
    <div className="line-item-row">
      <div className="item-details">
        <input
          type="text"
          defaultValue={item.description}
          onChange={(e) => onUpdate?.({ ...item, description: e.target.value })}
          placeholder="Description"
        />
        <input
          type="number"
          defaultValue={item.amount}
          onChange={(e) => onUpdate?.({ ...item, amount: parseFloat(e.target.value) })}
          placeholder="Amount"
          step="0.01"
        />
        <select
          defaultValue={item.category}
          onChange={(e) => onUpdate?.({ ...item, category: e.target.value })}
        >
          <option>Select Category</option>
          <option>Travel</option>
          <option>Meals</option>
          <option>Supplies</option>
        </select>
      </div>
      <ReceiptUpload
        itemId={item.id}
        onUploadComplete={(url) => onUpdate?.({ ...item, receiptUrl: url })}
      />
      {item.receiptUrl && (
        <div className="receipt-link">
          <a href={item.receiptUrl} target="_blank" rel="noreferrer">
            View Receipt
          </a>
        </div>
      )}
      <button onClick={() => onDelete?.(item.id)}>Delete</button>
    </div>
  );
}
