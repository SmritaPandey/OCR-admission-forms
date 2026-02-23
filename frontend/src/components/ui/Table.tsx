import React from 'react';
import { cn } from '../../utils/cn';

interface TableProps {
  children: React.ReactNode;
  className?: string;
}

export function Table({ children, className }: TableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-soft">
      <table className={cn('w-full border-collapse', className)}>
        {children}
      </table>
    </div>
  );
}

export function TableHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <thead className={cn('bg-gradient-to-r from-gray-50 to-gray-100', className)}>
      {children}
    </thead>
  );
}

export function TableHeaderCell({ children, className, ...props }: any) {
  return (
    <th className={cn(
      'px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200',
      className
    )} {...props}>
      {children}
    </th>
  );
}

export function TableBody({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <tbody className={cn('divide-y divide-gray-100', className)}>
      {children}
    </tbody>
  );
}

export function TableRow({ children, className, ...props }: any) {
  return (
    <tr className={cn(
      'hover:bg-gray-50 transition-colors duration-150',
      className
    )} {...props}>
      {children}
    </tr>
  );
}

export function TableCell({ children, className, ...props }: any) {
  return (
    <td className={cn(
      'px-6 py-4 text-sm text-gray-900',
      className
    )} {...props}>
      {children}
    </td>
  );
}

