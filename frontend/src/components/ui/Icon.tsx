import React from 'react';
import type { LucideProps } from 'lucide-react';

type IconComponent = React.ForwardRefExoticComponent<LucideProps & React.RefAttributes<SVGSVGElement>>;

interface IconProps {
  icon: IconComponent;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
}

export function Icon({ icon: IconComponent, size = 'md', className = '' }: IconProps) {
  const sizes = {
    xs: 12,
    sm: 16,
    md: 20,
    lg: 24,
  };

  return (
    <IconComponent
      size={sizes[size]}
      className={`shrink-0 ${className}`}
      strokeWidth={1.5}
    />
  );
}
