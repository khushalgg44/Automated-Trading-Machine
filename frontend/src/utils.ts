/**
 * Format a number as Indian Rupee currency.
 * Display only — no arithmetic on these values in the frontend.
 */
export function formatCurrency(value: number): string {
  return `₹${value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}
