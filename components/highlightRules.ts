
export interface HighlightRule {
  name: string;
  pattern: RegExp;
}

// Configurable extraction rules
// We use a function to allow for dynamic rules based on future context if needed
export const getHighlightRules = (): HighlightRule[] => [
  // Match Bill Numbers (e.g., Bill C-3, C-13, S-211)
  // Looks for "Bill" followed by optional space and alphanumeric identifier
  {
    name: 'Bill Number',
    pattern: /\b(Bill\s+[A-Z]-?\d+)\b/gi
  },
  // Match formal Act titles (simple heuristic: "The ... Act")
  // Restrictive to avoid bolding every occurrence of "Act"
  {
    name: 'Legislation',
    pattern: /\b(The\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Act)\b/g
  },
  // Match specific full dates (e.g., June 5, 2025; January 27, 2020)
  {
    name: 'Key Dates',
    pattern: /\b([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})\b/g
  }
];

/**
 * Applies highlighting rules to text.
 * Wraps matches in Markdown bold syntax (**match**).
 * 
 * Robustness:
 * - Checks for existing markdown bolding to avoid **double** bolding.
 * - Simple heuristic to avoid breaking markdown links (doesn't match if inside ()).
 */
export const applyDynamicHighlighting = (text: string): string => {
  if (!text) return "";

  const rules = getHighlightRules();
  let processedText = text;

  rules.forEach(rule => {
    try {
      // We use a replacement function to check context
      processedText = processedText.replace(rule.pattern, (match, p1, offset, fullString) => {
        
        // 1. Check if already bolded (preceded by ** and followed by **)
        // This is a simple check; proper AST parsing is safer but heavier.
        const before = fullString.substring(offset - 2, offset);
        const after = fullString.substring(offset + match.length, offset + match.length + 2);
        if (before === '**' && after === '**') {
          return match; // Already bold
        }

        // 2. Check if inside a Markdown URL: [Link](...match...)
        // Heuristic: Look back for `](` without a closing `)`
        const lookback = fullString.substring(Math.max(0, offset - 100), offset);
        if (lookback.includes('](') && !lookback.includes(')')) {
           // Likely inside a URL definition, skip
           return match;
        }

        // Apply formatting
        return `**${match}**`;
      });
    } catch {
      // Continue processing other rules; don't break the app
    }
  });

  return processedText;
};
