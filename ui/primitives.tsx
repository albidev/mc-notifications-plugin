import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react';

type CardProps = HTMLAttributes<HTMLDivElement> & { padding?: 'sm' | 'md' | 'lg' | 'none' };

export function Card({ padding = 'md', className = '', children, ...props }: CardProps) {
  const paddingClass = padding === 'none' ? '' : padding === 'sm' ? 'p-3' : padding === 'lg' ? 'p-6' : 'p-4';
  return <div className={`rounded-lg border border-border bg-surface-raised ${paddingClass} ${className}`} {...props}>{children}</div>;
}

type BadgeProps = HTMLAttributes<HTMLSpanElement> & { variant?: 'default' | 'positive' | 'warning' | 'negative' | 'accent' };

export function Badge({ variant = 'default', className = '', children, ...props }: BadgeProps) {
  const colors = {
    default: 'border-border bg-surface text-text-muted',
    positive: 'border-positive/20 bg-positive-subtle text-positive',
    warning: 'border-warning/20 bg-warning-subtle text-warning',
    negative: 'border-negative/20 bg-negative-subtle text-negative',
    accent: 'border-accent/20 bg-accent-subtle text-accent',
  }[variant];
  return <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${colors} ${className}`} {...props}>{children}</span>;
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost'; icon?: ReactNode };

export function Button({ variant = 'secondary', icon, className = '', children, ...props }: ButtonProps) {
  const colors = {
    primary: 'border-accent/30 bg-accent text-white hover:bg-accent/85',
    secondary: 'border-border bg-surface text-text hover:bg-surface-sunken',
    ghost: 'border-transparent bg-transparent text-text-muted hover:bg-surface-sunken hover:text-text',
  }[variant];
  return <button type="button" className={`inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border px-3 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${colors} ${className}`} {...props}>{icon}{children}</button>;
}
