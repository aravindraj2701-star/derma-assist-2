/**
 * Score and Percentage formatting utilities for DermaAssist.
 * Guarantees that any decimal fraction (0.0-1.0), percentage (0-100),
 * or legacy double-multiplied score (>100) safely normalizes to a valid 0-100% string.
 */

export function formatScore(val, decimals = 0) {
  if (val === null || val === undefined || isNaN(val) || val === '') {
    return '0%';
  }
  let num = Number(val);
  
  // Handle double-multiplication bug (e.g. 5510 -> 55.1)
  if (num > 100) {
    num = num / 100;
  } else if (num > 0 && num <= 1.0) {
    // Handle 0-1 decimal fractions (e.g. 0.551 -> 55.1)
    num = num * 100;
  }
  
  // Clamp to valid clinical percentage range [0, 100]
  num = Math.max(0, Math.min(100, num));
  
  if (decimals > 0) {
    return `${num.toFixed(decimals)}%`;
  }
  return `${Math.round(num)}%`;
}

export function formatScoreValue(val) {
  if (val === null || val === undefined || isNaN(val) || val === '') {
    return 0;
  }
  let num = Number(val);
  if (num > 100) {
    num = num / 100;
  } else if (num > 0 && num <= 1.0) {
    num = num * 100;
  }
  return Math.round(Math.max(0, Math.min(100, num)));
}

export const safePercent = formatScore;

