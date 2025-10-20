/**
 * Central export for all types
 */

// Re-export file types
export * from '../components/shared/types/file';

// Additional shared types can be added here
export interface FileItem {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'folder';
  size?: number;
  modified?: Date;
  children?: FileItem[];
}
