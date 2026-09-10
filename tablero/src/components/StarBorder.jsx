import './StarBorder.css';

const StarBorder = ({
  as: Component = 'button',
  className = '',
  color = '#7cc79c',
  speed = '6s',
  thickness = 1,
  backgroundColor = '#0d2f1c',
  textColor = '#ffffff',
  borderColor = '#1f6b42',
  children,
  ...rest
}) => (
  <Component className={`star-border-container ${className}`} style={{ padding: `${thickness}px 0`, ...rest.style }} {...rest}>
    <div className="border-gradient-bottom" style={{ background: `radial-gradient(circle, ${color}, transparent 10%)`, animationDuration: speed }} />
    <div className="border-gradient-top" style={{ background: `radial-gradient(circle, ${color}, transparent 10%)`, animationDuration: speed }} />
    <div className="inner-content" style={{ background: backgroundColor, color: textColor, borderColor }}>{children}</div>
  </Component>
);

export default StarBorder;
