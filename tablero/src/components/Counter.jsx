import { motion, useSpring, useTransform } from 'motion/react';
import { useEffect } from 'react';
import './Counter.css';

function Number({ mv, number, height }) {
  const y = useTransform(mv, latest => {
    const placeValue = latest % 10;
    const offset = (10 + number - placeValue) % 10;
    let memo = offset * height;
    if (offset > 5) memo -= 10 * height;
    return memo;
  });
  return (
    <motion.span className="counter-number" style={{ y }}>
      {number}
    </motion.span>
  );
}

function normalizeNearInteger(num) {
  const nearest = Math.round(num);
  const tolerance = 1e-9 * Math.max(1, Math.abs(num));
  return Math.abs(num - nearest) < tolerance ? nearest : num;
}

function getValueRoundedToPlace(value, place) {
  return Math.floor(normalizeNearInteger(value / place));
}

function Digit({ place, value, height, digitStyle }) {
  const isDecimal = place === '.';
  const valueRoundedToPlace = isDecimal ? 0 : getValueRoundedToPlace(value, place);
  const animatedValue = useSpring(valueRoundedToPlace, { stiffness: 90, damping: 18 });

  useEffect(() => {
    if (!isDecimal) animatedValue.set(valueRoundedToPlace);
  }, [animatedValue, valueRoundedToPlace, isDecimal]);

  if (isDecimal) {
    return (
      <span className="counter-digit" style={{ height, ...digitStyle, width: 'fit-content' }}>
        .
      </span>
    );
  }

  return (
    <span className="counter-digit" style={{ height, ...digitStyle }}>
      {Array.from({ length: 10 }, (_, i) => (
        <Number key={i} mv={animatedValue} number={i} height={height} />
      ))}
    </span>
  );
}

function placesFor(value) {
  return [...value.toString()].map((ch, i, a) => {
    if (ch === '.') return '.';
    const dot = a.indexOf('.');
    const exp = dot === -1 ? a.length - i - 1 : i < dot ? dot - i - 1 : -(i - dot);
    return 10 ** exp;
  });
}

export default function Counter({
  value,
  fontSize = 40,
  padding = 0,
  places,
  gap = 1,
  borderRadius = 4,
  horizontalPadding = 0,
  textColor = 'inherit',
  fontWeight = 700,
  containerStyle,
  counterStyle,
  digitStyle,
  gradientHeight = 10,
  gradientFrom = 'transparent',
  gradientTo = 'transparent',
}) {
  const height = fontSize + padding;
  const resolvedPlaces = places ?? placesFor(value);

  return (
    <span className="counter-container" style={containerStyle}>
      <span
        className="counter-counter"
        style={{
          fontSize,
          gap,
          borderRadius,
          paddingLeft: horizontalPadding,
          paddingRight: horizontalPadding,
          color: textColor,
          fontWeight,
          direction: 'ltr',
          ...counterStyle,
        }}
      >
        {resolvedPlaces.map((place, i) => (
          <Digit key={`${place}-${i}`} place={place} value={value} height={height} digitStyle={digitStyle} />
        ))}
      </span>
      <span className="gradient-container">
        <span
          className="top-gradient"
          style={{ height: gradientHeight, background: `linear-gradient(to bottom, ${gradientFrom}, ${gradientTo})` }}
        />
        <span
          className="bottom-gradient"
          style={{ height: gradientHeight, background: `linear-gradient(to top, ${gradientFrom}, ${gradientTo})` }}
        />
      </span>
    </span>
  );
}
