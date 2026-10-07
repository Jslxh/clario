let nextPidCounter = 1000 + Math.floor(Math.random() * 8000);

export const generateProcessId = (prefix = 'PID') => {
  nextPidCounter += 1;
  return `${prefix}-${nextPidCounter}`;
};

