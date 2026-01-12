import React from 'react';
import { Select as AriaSelect, SelectValue, Button, ListBox, ListBoxItem, Popover } from 'react-aria-components';
import { cn } from '../../utils/cn';

interface SelectProps {
  label?: string;
  placeholder?: string;
  error?: string;
  children: React.ReactNode;
  className?: string;
  [key: string]: any;
}

export function Select({
  label,
  placeholder = 'Select an option',
  error,
  children,
  className,
  ...props
}: SelectProps) {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-semibold text-gray-700 mb-2">
          {label}
        </label>
      )}
      <AriaSelect
        className={cn('w-full', className)}
        {...props}
      >
        <Button className={cn(
          'w-full px-4 py-3 rounded-xl border bg-white text-left',
          'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
          'transition-all duration-200 flex items-center justify-between',
          error ? 'border-red-300 focus:ring-red-500' : 'border-gray-200'
        )}>
          <SelectValue>
            {({ selectedText }) => selectedText || placeholder}
          </SelectValue>
          <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </Button>
        <Popover className="w-[--trigger-width] rounded-xl border border-gray-200 bg-white shadow-large mt-1">
          <ListBox className="p-1 outline-none">
            {children}
          </ListBox>
        </Popover>
      </AriaSelect>
      {error && (
        <p className="mt-1 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}

export function SelectItem({ children, ...props }: any) {
  return (
    <ListBoxItem
      className="px-4 py-2 rounded-lg cursor-pointer outline-none focus:bg-primary-50 focus:text-primary-700 selected:bg-primary-100 selected:text-primary-700"
      {...props}
    >
      {children}
    </ListBoxItem>
  );
}

