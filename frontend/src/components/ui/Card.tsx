import React from 'react';
import { cn } from '../../utils/cn';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export function Card({ children, className, padding = 'md' }: CardProps) {
  const paddingClasses = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  return (
    <div className={cn(
      'bg-white rounded-2xl shadow-soft border border-gray-100 overflow-hidden',
      paddingClasses[padding],
      className
    )}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn(
      'px-6 py-5 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white',
      className
    )}>
      {children}
    </div>
  );
}

export function CardBody({ children, className, padding = 'md' }: { children: React.ReactNode; className?: string; padding?: 'none' | 'sm' | 'md' | 'lg' }) {
  const paddingClasses = {
    none: '',
    sm: 'p-4',
    md: 'px-6 py-5',
    lg: 'p-8',
  };

  return (
    <div className={cn(paddingClasses[padding], className)}>
      {children}
    </div>
  );
}

