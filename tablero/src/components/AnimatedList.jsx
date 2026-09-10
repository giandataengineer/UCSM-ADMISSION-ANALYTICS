import { useRef, useState, useEffect, useCallback } from 'react';
import { motion, useInView } from 'motion/react';
import './AnimatedList.css';

function AnimatedItem({ children, delay = 0, index, onMouseEnter, onClick }) {
  const ref = useRef(null);
  const inView = useInView(ref, { amount: 0.4, once: true });
  return (
    <motion.div
      ref={ref}
      data-index={index}
      onMouseEnter={onMouseEnter}
      onClick={onClick}
      initial={{ scale: 0.96, opacity: 0 }}
      animate={inView ? { scale: 1, opacity: 1 } : { scale: 0.96, opacity: 0 }}
      transition={{ duration: 0.25, delay }}
      className="al-item"
    >
      {children}
    </motion.div>
  );
}

export default function AnimatedList({
  items = [],
  renderItem,
  onItemSelect,
  showGradients = true,
  enableArrowNavigation = true,
  displayScrollbar = true,
  initialSelectedIndex = -1,
  className = ''
}) {
  const listRef = useRef(null);
  const [selected, setSelected] = useState(initialSelectedIndex);
  const [keyboard, setKeyboard] = useState(false);
  const [topOpacity, setTopOpacity] = useState(0);
  const [bottomOpacity, setBottomOpacity] = useState(1);

  const handleScroll = useCallback(e => {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    setTopOpacity(Math.min(scrollTop / 40, 1));
    const rest = scrollHeight - (scrollTop + clientHeight);
    setBottomOpacity(scrollHeight <= clientHeight ? 0 : Math.min(rest / 40, 1));
  }, []);

  useEffect(() => {
    if (!enableArrowNavigation) return;
    const onKey = e => {
      if (e.key === 'ArrowDown') { e.preventDefault(); setKeyboard(true); setSelected(p => Math.min(p + 1, items.length - 1)); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setKeyboard(true); setSelected(p => Math.max(p - 1, 0)); }
      else if (e.key === 'Enter' && selected >= 0) { e.preventDefault(); onItemSelect?.(items[selected], selected); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [items, selected, onItemSelect, enableArrowNavigation]);

  useEffect(() => {
    if (!keyboard || selected < 0 || !listRef.current) return;
    const el = listRef.current.querySelector(`[data-index="${selected}"]`);
    el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    setKeyboard(false);
  }, [selected, keyboard]);

  return (
    <div className={`al-wrap ${className}`}>
      <div
        ref={listRef}
        className={`al-scroll ${displayScrollbar ? 'scroll-fino' : 'al-nobar'}`}
        onScroll={handleScroll}
      >
        {items.map((item, i) => (
          <AnimatedItem
            key={i}
            index={i}
            delay={Math.min(i, 8) * 0.03}
            onMouseEnter={() => setSelected(i)}
            onClick={() => { setSelected(i); onItemSelect?.(item, i); }}
          >
            {renderItem(item, i, i === selected)}
          </AnimatedItem>
        ))}
      </div>
      {showGradients && (
        <>
          <div className="al-fade al-fade-top" style={{ opacity: topOpacity }} />
          <div className="al-fade al-fade-bottom" style={{ opacity: bottomOpacity }} />
        </>
      )}
    </div>
  );
}
