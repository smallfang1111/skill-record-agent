import type { ReactNode } from 'react';
import './Modal.css';

interface ModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  width?: number;
  closeOnOverlay?: boolean;
  className?: string;
}

function Modal({ open, title, onClose, children, width = 520, closeOnOverlay = true, className }: ModalProps) {
  if (!open) return null;
  return (
    <div className="modal-overlay" onClick={closeOnOverlay ? onClose : undefined}>
      <div className={"modal-box" + (className ? " " + className : "")} style={{ width }} onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">{title}</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

export default Modal;
