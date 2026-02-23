import React from 'react';
import { Dialog, Modal, ModalOverlay } from 'react-aria-components';
import { cn } from '../../utils/cn';

interface ModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  title?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export function ModalDialog({
  isOpen,
  onOpenChange,
  title,
  children,
  size = 'md',
  className,
}: ModalProps) {
  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  };

  return (
    <ModalOverlay
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
    >
      <Modal className={cn(
        'bg-white rounded-2xl shadow-xl border border-gray-200 outline-none',
        sizes[size],
        className
      )}>
        <Dialog className="outline-none">
          {({ close }) => (
            <>
              {title && (
                <div className="flex items-center justify-between px-6 py-5 border-b border-gray-200">
                  <h2 className="text-xl font-bold text-gray-900">{title}</h2>
                  <button
                    onClick={() => close()}
                    className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              )}
              <div className="p-6">
                {children}
              </div>
            </>
          )}
        </Dialog>
      </Modal>
    </ModalOverlay>
  );
}

