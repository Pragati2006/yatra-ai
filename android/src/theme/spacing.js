export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  huge: 32,

  // Border Radii
  radiusSm: 8,
  radiusMd: 12,
  radiusLg: 16,
  radiusFull: 9999,

  // Shadows / Elevations
  shadowSm: {
    shadowColor: '#71152C',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
  },
  shadowMd: {
    shadowColor: '#71152C',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 3,
  },
  shadowLg: {
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.12,
    shadowRadius: 12,
    elevation: 6,
  },
};

export const radius = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  full: 9999,
};

export const shadows = {
  subtle: spacing.shadowSm,
  card: spacing.shadowMd,
  modal: spacing.shadowLg,
};

export default { spacing, radius, shadows };
