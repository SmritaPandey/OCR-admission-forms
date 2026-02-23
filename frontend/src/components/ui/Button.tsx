import React from 'react';
import { Button as AriaButton, ButtonProps as AriaButtonProps } from 'react-aria-components';
import { cn } from '../../utils/cn';

interface ButtonProps extends AriaButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  children,
  className,
  ...props
}: ButtonProps) {
  const baseStyles = 'inline-flex items-center justify-center gap-2 font-semibold rounded-full transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';
  
  const variants = {
    primary: 'bg-primary-500 text-white hover:bg-primary-600 focus:ring-primary-500 shadow-medium hover:shadow-large hover:-translate-y-0.5',
    secondary: 'bg-white text-gray-700 hover:bg-gray-50 focus:ring-primary-500 border border-gray-200 shadow-sm hover:shadow-medium',
    ghost: 'text-gray-700 hover:bg-gray-100 focus:ring-primary-500',
    danger: 'bg-red-500 text-white hover:bg-red-600 focus:ring-red-500 shadow-medium hover:shadow-large hover:-translate-y-0.5',
  };

  const sizes = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg',
  };

  return (
    <AriaButton
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      isDisabled={isLoading || props.isDisabled}
      {...props}
    >
      {isLoading ? (
        <>
          <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A10.734 10.734 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Loading...
        </>
      ) : (
        children
      )}
    </AriaButton>
  );
}

