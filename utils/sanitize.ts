/**
 * Security utilities for input sanitization and XSS prevention.
 *
 * This module provides functions to sanitize user inputs and prevent
 * cross-site scripting (XSS) and other injection attacks.
 */

import DOMPurify from 'dompurify';

/**
 * Sanitize HTML content to prevent XSS attacks.
 *
 * Uses DOMPurify to strip dangerous HTML tags and attributes while
 * preserving safe formatting elements.
 *
 * @param dirty - The potentially unsafe HTML string
 * @returns A sanitized HTML string safe for rendering
 */
export const sanitizeHTML = (dirty: string): string => {
  if (!dirty) return '';

  return DOMPurify.sanitize(dirty, {
    // Only allow safe inline formatting tags
    ALLOWED_TAGS: [
      'b',
      'i',
      'em',
      'strong',
      'a',
      'p',
      'br',
      'ul',
      'ol',
      'li',
      'span',
      'code',
      'pre',
      'blockquote',
      'h1',
      'h2',
      'h3',
      'h4',
      'h5',
      'h6',
    ],
    // Only allow safe attributes
    ALLOWED_ATTR: ['href', 'target', 'rel', 'class'],
    // Force external links to open safely
    ADD_ATTR: ['target'],
    // Ensure all links have rel="noopener noreferrer"
    FORBID_TAGS: ['script', 'style', 'iframe', 'form', 'input', 'object', 'embed'],
    FORBID_ATTR: ['onclick', 'onerror', 'onload', 'onmouseover', 'style'],
  });
};

/**
 * Validate a document ID to ensure it's safe for use in URLs.
 *
 * Document IDs should only contain alphanumeric characters, hyphens, and underscores.
 * This prevents path traversal and injection attacks.
 *
 * @param docId - The document ID to validate
 * @returns true if valid, false otherwise
 */
export const validateDocId = (docId: string): boolean => {
  if (!docId) return false;

  // Only allow alphanumeric, hyphens, underscores
  const pattern = /^[a-zA-Z0-9_-]+$/;

  // Check pattern and reasonable length
  return pattern.test(docId) && docId.length <= 255;
};

/**
 * Safely construct a document URL.
 *
 * Validates the document ID before constructing the URL to prevent
 * path traversal attacks.
 *
 * @param docId - The document ID
 * @returns The safe URL path, or null if validation fails
 */
export const safeDocumentUrl = (docId: string): string | null => {
  if (!validateDocId(docId)) {
    console.error('Invalid document ID:', docId);
    return null;
  }

  return `/documents/${encodeURIComponent(docId)}`;
};

/**
 * Sanitize a search query string.
 *
 * Trims whitespace and enforces maximum length.
 *
 * @param query - The search query
 * @param maxLength - Maximum allowed length (default: 10000)
 * @returns The sanitized query or empty string if invalid
 */
export const sanitizeQuery = (query: string, maxLength: number = 10000): string => {
  if (!query) return '';

  const trimmed = query.trim();

  if (trimmed.length > maxLength) {
    console.warn(`Query truncated from ${trimmed.length} to ${maxLength} characters`);
    return trimmed.slice(0, maxLength);
  }

  return trimmed;
};

/**
 * Escape special characters for use in regular expressions.
 *
 * @param string - The string to escape
 * @returns The escaped string safe for use in RegExp
 */
export const escapeRegExp = (string: string): string => {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
};

/**
 * Validate a file name for upload.
 *
 * Checks that the filename has an allowed extension and doesn't
 * contain path traversal patterns.
 *
 * @param filename - The filename to validate
 * @param allowedExtensions - Set of allowed extensions (with dots)
 * @returns true if valid, false otherwise
 */
export const validateFilename = (
  filename: string,
  allowedExtensions: Set<string> = new Set(['.pdf', '.txt', '.md', '.csv', '.json', '.html'])
): boolean => {
  if (!filename) return false;

  // Check for path traversal
  if (filename.includes('..') || filename.includes('/') || filename.includes('\\')) {
    console.error('Path traversal attempt detected in filename');
    return false;
  }

  // Check extension
  const ext = filename.slice(filename.lastIndexOf('.')).toLowerCase();
  if (!allowedExtensions.has(ext)) {
    console.error(`File extension not allowed: ${ext}`);
    return false;
  }

  // Check reasonable length
  if (filename.length > 255) {
    console.error('Filename too long');
    return false;
  }

  return true;
};
