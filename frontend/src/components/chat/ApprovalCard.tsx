import { useState } from 'react';
import { ShieldAlert, Check, X } from 'lucide-react';
import type { ApprovalItem } from '../../types';
import { useApp } from '../../contexts/AppContext';

interface ApprovalCardProps {
  approval: ApprovalItem;
}

export function ApprovalCard({ approval }: ApprovalCardProps) {
  const { resolveApproval } = useApp();
  const options = approval.options?.length ? approval.options : ['Approve', 'Reject'];
  const [selectedOption, setSelectedOption] = useState<string>(
    approval.selected_option || options[0]
  );
  const [submitting, setSubmitting] = useState(false);

  const isPending = approval.status === 'pending';

  const handleDecision = async (decision: 'approved' | 'rejected', optionOverride?: string) => {
    if (!isPending || submitting) return;
    setSubmitting(true);
    try {
      await resolveApproval(
        approval.approval_id,
        decision,
        optionOverride ?? selectedOption
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-xl border border-warning/40 bg-background p-3 text-xs space-y-2 shadow-xs">
      <div className="flex items-start gap-2">
        <div className="w-6 h-6 rounded-md bg-warning/15 flex items-center justify-center shrink-0 mt-0.5">
          <ShieldAlert size={14} className="text-warning" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-foreground">{approval.title}</span>
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded font-medium uppercase ${
                approval.status === 'approved'
                  ? 'bg-success/15 text-success'
                  : approval.status === 'rejected'
                  ? 'bg-error/15 text-error'
                  : 'bg-warning/15 text-warning'
              }`}
            >
              {approval.status}
            </span>
          </div>
          <p className="text-muted mt-1 leading-relaxed whitespace-pre-wrap">
            {approval.summary}
          </p>
        </div>
      </div>

      {options.length > 0 && isPending && (
        <div className="flex flex-wrap gap-1.5 pt-0.5">
          {options.map((opt) => {
            const active = selectedOption === opt;
            return (
              <button
                key={opt}
                type="button"
                onClick={() => setSelectedOption(opt)}
                className={`px-2 py-1 rounded-md border text-[11px] transition-colors ${
                  active
                    ? 'border-primary bg-primary/10 text-primary font-medium'
                    : 'border-border bg-surface text-muted hover:text-foreground'
                }`}
              >
                {opt}
              </button>
            );
          })}
        </div>
      )}

      {isPending ? (
        <div className="flex items-center justify-end gap-2 pt-1 border-t border-border">
          <button
            type="button"
            disabled={submitting}
            onClick={() => handleDecision('rejected', 'Reject')}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-border bg-surface text-muted hover:text-error hover:border-error/40 transition-colors disabled:opacity-50"
          >
            <X size={12} />
            <span>Reject</span>
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={() => handleDecision('approved', selectedOption)}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-primary text-white hover:bg-primary-hover transition-colors disabled:opacity-50"
          >
            <Check size={12} />
            <span>Confirm</span>
          </button>
        </div>
      ) : (
        approval.selected_option && (
          <div className="text-[11px] text-muted pt-1 border-t border-border">
            PI Decision: <span className="font-medium text-foreground">{approval.selected_option}</span>
          </div>
        )
      )}
    </div>
  );
}
