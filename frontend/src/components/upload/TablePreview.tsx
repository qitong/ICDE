import React from 'react';
import { Hash, Type, Calendar, List } from 'lucide-react';
import type { ColumnInfo } from '../../types';

interface TablePreviewProps {
  fileName: string;
  rowCount: number;
  columnCount: number;
  columns: ColumnInfo[];
}

const typeIcons: Record<string, React.ReactNode> = {
  numeric: <Hash size={14} className="text-blue-500" />,
  text: <Type size={14} className="text-green-500" />,
  date: <Calendar size={14} className="text-purple-500" />,
  categorical: <List size={14} className="text-orange-500" />,
};

const typeLabels: Record<string, string> = {
  numeric: 'Numeric',
  text: 'Text',
  date: 'Date',
  categorical: 'Categorical',
};

export function TablePreview({ fileName, rowCount, columnCount, columns }: TablePreviewProps) {
  return (
    <div className="border border-border rounded-lg overflow-hidden bg-surface">
      {/* Header */}
      <div className="px-4 py-3 bg-background border-b border-border">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-foreground">{fileName}</h4>
          <div className="flex items-center gap-4 text-xs text-muted">
            <span>{rowCount.toLocaleString()} rows</span>
            <span>{columnCount} columns</span>
          </div>
        </div>
      </div>

      {/* Columns table */}
      <div className="max-h-64 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="bg-background sticky top-0">
            <tr className="border-b border-border">
              <th className="px-4 py-2 text-left font-medium text-muted">Column</th>
              <th className="px-4 py-2 text-left font-medium text-muted">Type</th>
              <th className="px-4 py-2 text-left font-medium text-muted">Non-Null</th>
              <th className="px-4 py-2 text-left font-medium text-muted">Unique</th>
              <th className="px-4 py-2 text-left font-medium text-muted">Sample</th>
            </tr>
          </thead>
          <tbody>
            {columns.map((col, idx) => (
              <tr key={idx} className="border-b border-border/50 hover:bg-background/50">
                <td className="px-4 py-2 font-mono text-foreground">{col.name}</td>
                <td className="px-4 py-2">
                  <div className="flex items-center gap-1.5">
                    {typeIcons[col.data_type]}
                    <span className="text-muted">{typeLabels[col.data_type]}</span>
                  </div>
                </td>
                <td className="px-4 py-2 text-muted">
                  {col.non_null_count.toLocaleString()}
                </td>
                <td className="px-4 py-2 text-muted">
                  {col.unique_count.toLocaleString()}
                </td>
                <td className="px-4 py-2">
                  <div className="flex gap-1 flex-wrap">
                    {col.sample_values.slice(0, 3).map((val, i) => (
                      <span
                        key={i}
                        className="px-1.5 py-0.5 bg-background rounded text-xs text-muted truncate max-w-24"
                        title={val}
                      >
                        {val}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
