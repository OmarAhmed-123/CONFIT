export function useStagger(count, stepMs = 70, baseDelayMs = 0) {
  return Array.from({ length: count }, (_, index) => ({
    transitionDelay: `${baseDelayMs + index * stepMs}ms`,
  }));
}

