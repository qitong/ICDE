import { useState, useEffect } from 'react';
import { X, Check, AlertCircle, Eye, EyeOff, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import type { LLMSettings, LLMSettingUpdate, ProviderConfig } from '../../types';

interface LLMSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function LLMSettingsModal({ isOpen, onClose }: LLMSettingsModalProps) {
  const [settings, setSettings] = useState<LLMSettings | null>(null);
  const [initialSettings, setInitialSettings] = useState<LLMSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validatingProvider, setValidatingProvider] = useState<string | null>(null);
  const [validationResults, setValidationResults] = useState<Record<string, boolean>>({});
  const [validationMessages, setValidationMessages] = useState<Record<string, string>>({});

  // Track which API keys are being edited
  const [editingKeys, setEditingKeys] = useState<Record<string, string>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});

  // Load settings on mount
  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);

  const loadSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getLLMSettings();
      setSettings(data);
      setInitialSettings({
        default_provider: data.default_provider,
        providers: data.providers.map((p) => ({ ...p })),
      });
    } catch (err) {
      setError('Failed to load LLM settings');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!settings) return;

    setSaving(true);
    setError(null);

    try {
      // Build update payload for any provider with key edits OR non-key field changes
      const updates: Record<string, LLMSettingUpdate> = {};
      const baselineMap = new Map(
        (initialSettings?.providers ?? []).map((p) => [p.provider, p])
      );

      for (const provider of settings.providers) {
        const editedKey = editingKeys[provider.provider];
        const baseline = baselineMap.get(provider.provider);
        const hasFieldChanges =
          !baseline ||
          baseline.model !== provider.model ||
          baseline.enabled !== provider.enabled ||
          baseline.is_default !== provider.is_default ||
          (baseline.api_base_url ?? '') !== (provider.api_base_url ?? '');

        if (editedKey !== undefined || hasFieldChanges) {
          const providerUpdate: LLMSettingUpdate = {
            model: provider.model,
            enabled: provider.enabled,
            is_default: provider.is_default,
          };

          if (provider.api_base_url !== undefined) {
            providerUpdate.api_base_url = provider.api_base_url;
          }

          if (editedKey !== undefined) {
            providerUpdate.api_key = editedKey;
          }

          updates[provider.provider] = providerUpdate;
        }
      }

      await api.updateLLMSettings({
        default_provider: settings.default_provider,
        providers: updates,
      });

      // Reload settings
      await loadSettings();
      setEditingKeys({});
      onClose();
    } catch (err) {
      setError('Failed to save settings');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleValidateKey = async (provider: string) => {
    setValidatingProvider(provider);
    try {
      const result = await api.validateLLMApiKey(provider);
      setValidationResults((prev) => ({ ...prev, [provider]: result.valid }));

      const baseUrl = result.base_url ?? result.debug?.base_url;
      const modelName = result.model ?? result.debug?.model;
      const maskedKey = result.debug?.masked_key;
      const contextParts = [
        maskedKey ? `key: ${maskedKey}` : null,
        baseUrl ? `url: ${baseUrl}` : null,
        modelName ? `model: ${modelName}` : null,
      ].filter((part): part is string => Boolean(part));

      const errorHeader =
        !result.valid && result.error_type ? `[${result.error_type}] ` : '';
      const detailSuffix =
        !result.valid &&
        result.error_detail &&
        !result.message.includes(result.error_detail)
          ? ` — ${result.error_detail}`
          : '';
      const contextSuffix =
        contextParts.length > 0 ? ` (${contextParts.join(', ')})` : '';

      setValidationMessages((prev) => ({
        ...prev,
        [provider]: `${errorHeader}${result.message}${detailSuffix}${contextSuffix}`,
      }));
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Validation failed';
      setValidationResults((prev) => ({ ...prev, [provider]: false }));
      setValidationMessages((prev) => ({
        ...prev,
        [provider]: errMsg,
      }));
    } finally {
      setValidatingProvider(null);
    }
  };

  const handleProviderChange = <K extends keyof ProviderConfig>(
    providerName: string,
    field: K,
    value: ProviderConfig[K]
  ) => {
    if (!settings) return;

    setSettings({
      ...settings,
      providers: settings.providers.map((p) =>
        p.provider === providerName ? { ...p, [field]: value } : p
      ),
    });
  };

  const handleSetDefault = (providerName: string) => {
    if (!settings) return;

    setSettings({
      ...settings,
      default_provider: providerName,
      providers: settings.providers.map((p) => ({
        ...p,
        is_default: p.provider === providerName,
      })),
    });
  };

  const handleApiKeyChange = (provider: string, value: string) => {
    setEditingKeys((prev) => ({ ...prev, [provider]: value }));
    // Clear validation result and message when key changes
    setValidationResults((prev) => {
      const newResults = { ...prev };
      delete newResults[provider];
      return newResults;
    });
    setValidationMessages((prev) => {
      const newMessages = { ...prev };
      delete newMessages[provider];
      return newMessages;
    });
  };

  const toggleShowKey = (provider: string) => {
    setShowKeys((prev) => ({ ...prev, [provider]: !prev[provider] }));
  };

  if (!isOpen) return null;

  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case 'openai':
        return '🤖';
      case 'claude':
        return '🧠';
      case 'gemini':
        return '✨';
      case 'kimi':
        return '🌙';
      default:
        return '💬';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-background border border-border rounded-xl shadow-xl w-full max-w-lg max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold text-foreground">LLM Settings</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-surface rounded-lg text-muted hover:text-foreground transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto max-h-[calc(80vh-140px)]">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="animate-spin text-primary" size={24} />
            </div>
          ) : error && !settings ? (
            <div className="text-center py-8 text-error">{error}</div>
          ) : settings ? (
            <div className="space-y-4">
              {/* Default provider selector */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-2">
                  Default Provider
                </label>
                <select
                  value={settings.default_provider || ''}
                  onChange={(e) => handleSetDefault(e.target.value)}
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-foreground focus:outline-none focus:border-primary"
                >
                  {settings.providers
                    .filter((p) => p.api_key_set || editingKeys[p.provider])
                    .map((p) => (
                      <option key={p.provider} value={p.provider}>
                        {getProviderIcon(p.provider)} {p.display_name}
                      </option>
                    ))}
                </select>
              </div>

              {/* Provider cards */}
              {settings.providers.map((provider) => (
                <div
                  key={provider.provider}
                  className={`
                    border rounded-lg p-4 transition-all
                    ${
                      provider.is_default
                        ? 'border-primary bg-primary/5'
                        : 'border-border'
                    }
                  `}
                >
                  {/* Provider header */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">
                        {getProviderIcon(provider.provider)}
                      </span>
                      <span className="font-medium text-foreground">
                        {provider.display_name}
                      </span>
                      {provider.is_default && (
                        <span className="px-2 py-0.5 text-xs bg-primary/20 text-primary rounded-full">
                          Default
                        </span>
                      )}
                    </div>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={provider.enabled}
                        onChange={(e) =>
                          handleProviderChange(
                            provider.provider,
                            'enabled',
                            e.target.checked
                          )
                        }
                        className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
                      />
                      <span className="text-sm text-muted">Enabled</span>
                    </label>
                  </div>

                  {/* API Key input */}
                  <div className="mb-3">
                    <label className="block text-xs text-muted mb-1">
                      API Key
                    </label>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <input
                          type={showKeys[provider.provider] ? 'text' : 'password'}
                          value={
                            editingKeys[provider.provider] !== undefined
                              ? editingKeys[provider.provider]
                              : provider.api_key_set
                              ? '••••••••••••••••'
                              : ''
                          }
                          onChange={(e) =>
                            handleApiKeyChange(provider.provider, e.target.value)
                          }
                          placeholder={
                            provider.api_key_set ? 'Enter new key to update' : 'Enter API key'
                          }
                          className="w-full px-3 py-2 pr-10 bg-surface border border-border rounded-lg text-sm text-foreground focus:outline-none focus:border-primary"
                        />
                        <button
                          type="button"
                          onClick={() => toggleShowKey(provider.provider)}
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-foreground"
                        >
                          {showKeys[provider.provider] ? (
                            <EyeOff size={16} />
                          ) : (
                            <Eye size={16} />
                          )}
                        </button>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleValidateKey(provider.provider)}
                        disabled={
                          validatingProvider === provider.provider ||
                          (!provider.api_key_set && !editingKeys[provider.provider])
                        }
                        className={`
                          px-3 py-2 rounded-lg text-sm font-medium transition-colors
                          ${
                            validationResults[provider.provider] === true
                              ? 'bg-success/20 text-success'
                              : validationResults[provider.provider] === false
                              ? 'bg-error/20 text-error'
                              : 'bg-surface border border-border text-foreground hover:bg-border'
                          }
                          disabled:opacity-50 disabled:cursor-not-allowed
                        `}
                      >
                        {validatingProvider === provider.provider ? (
                          <Loader2 className="animate-spin" size={16} />
                        ) : validationResults[provider.provider] === true ? (
                          <Check size={16} />
                        ) : validationResults[provider.provider] === false ? (
                          <AlertCircle size={16} />
                        ) : (
                          'Test'
                        )}
                      </button>
                    </div>
                    {provider.api_key_set && editingKeys[provider.provider] === undefined && (
                      <p className="mt-1 text-xs text-success flex items-center gap-1">
                        <Check size={12} /> API key configured
                      </p>
                    )}
                    {validationMessages[provider.provider] && (
                      <p
                        className={`mt-1 text-xs ${
                          validationResults[provider.provider] ? 'text-success' : 'text-error'
                        } break-all`}
                      >
                        {validationMessages[provider.provider]}
                      </p>
                    )}
                  </div>

                  {/* Model selector */}
                  <div className="mb-3">
                    <label className="block text-xs text-muted mb-1">Model</label>
                    <select
                      value={provider.model}
                      onChange={(e) =>
                        handleProviderChange(provider.provider, 'model', e.target.value)
                      }
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-foreground focus:outline-none focus:border-primary"
                    >
                      {provider.available_models.map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Optional API Base URL */}
                  <div>
                    <label className="block text-xs text-muted mb-1">
                      API Base URL (Optional)
                    </label>
                    <input
                      type="text"
                      value={provider.api_base_url || ''}
                      onChange={(e) =>
                        handleProviderChange(
                          provider.provider,
                          'api_base_url',
                          e.target.value
                        )
                      }
                      placeholder="Default provider endpoint"
                      className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-foreground focus:outline-none focus:border-primary"
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-surface/50">
          {error && (
            <span className="flex-1 text-sm text-error flex items-center gap-1">
              <AlertCircle size={14} />
              {error}
            </span>
          )}
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-foreground hover:bg-surface rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="animate-spin" size={14} />}
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
