/**
 * Validates if a string is a safe URL for image sources.
 * Prevents XSS vectors like javascript: protocols.
 */
export const isValidImageUrl = (url: string | undefined | null): boolean => {
  if (!url) return false;

  try {
    const parsed = new URL(url);
    return ["http:", "https:"].includes(parsed.protocol);
  } catch {
    // If URL parsing fails, it might be a relative path which is usually safe in React apps
    // but strict validation prefers full URLs with valid protocols for external content.
    // For local assets (starting with /), we can allow them if needed,
    // but ArtistProfile mostly deals with external CDN links.
    return url.startsWith("/");
  }
};
