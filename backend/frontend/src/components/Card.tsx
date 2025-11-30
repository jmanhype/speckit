/**
 * Card component.
 *
 * A simple container with shadow and border.
 */

import { HTMLAttributes, ReactNode } from 'react';
import { cn } from '../lib/utils';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  hover?: boolean;
  padding?: boolean;
}

export function Card({
  children,
  hover = false,
  padding = false,
  className,
  ...props
}: CardProps) {
  const baseStyles =
    'bg-white rounded-lg shadow-sm border border-gray-200';

  const hoverStyles = hover
    ? 'hover:shadow-md transition-shadow cursor-pointer'
    : '';

  const paddingStyles = padding ? 'p-6' : '';

  return (
    <div
      className={cn(baseStyles, hoverStyles, paddingStyles, className)}
      {...props}
    >
      {children}
    </div>
  );
}
