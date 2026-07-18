export const MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024;

export function validateQuery(question: string): string | null {
  const value = question.trim();
  if (!value) return "Enter a question.";
  if (value.length > 2000) return "Questions must be 2,000 characters or fewer.";
  return null;
}

export function validateFile(file: File, extensions: readonly string[]): string | null {
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (!extension || !extensions.includes(extension)) return "This file type is not supported.";
  if (file.size > MAX_UPLOAD_SIZE_BYTES) return "Files must be 25 MB or smaller.";
  return null;
}

export function validateSlackChannel(channelId: string): string | null {
  return /^[A-Za-z0-9_-]{1,100}$/.test(channelId.trim()) ? null : "Enter a valid Slack channel ID.";
}
