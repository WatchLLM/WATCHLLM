import React from 'react';
import type { CSSProperties } from 'react';

interface GlitchTextProps {
  text: string;
  speed?: number;
  enableShadows?: boolean;
  enableOnHover?: boolean;
  className?: string;
  as?: keyof React.JSX.IntrinsicElements;
}

interface CustomCSSProperties extends CSSProperties {
  '--after-duration'?: string;
  '--before-duration'?: string;
  '--after-shadow'?: string;
  '--before-shadow'?: string;
}

const GlitchText: React.FC<GlitchTextProps> = ({
  text,
  speed = 0.5,
  enableShadows = true,
  enableOnHover = false,
  className = '',
  as: Component = 'div'
}) => {
  const inlineStyles: CustomCSSProperties = {
    '--after-duration': `${speed * 3}s`,
    '--before-duration': `${speed * 2}s`,
    '--after-shadow': enableShadows ? '-5px 0 red' : 'none',
    '--before-shadow': enableShadows ? '5px 0 cyan' : 'none'
  };

  const baseClasses = 'glitch-text';
  const pseudoClasses = !enableOnHover ? 'glitch-active' : 'glitch-hover';
  const combinedClasses = `${baseClasses} ${pseudoClasses} ${className}`;

  return (
    <Component style={inlineStyles} data-text={text} className={combinedClasses}>
      {text}
    </Component>
  );
};

export default GlitchText;
