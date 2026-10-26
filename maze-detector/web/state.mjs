export function displayState(snapshot) {
  if (!snapshot?.connected || !snapshot.reading || ![0, 1].includes(snapshot.reading.raw)) {
    return 'offline';
  }
  // Firmware confirms release only after a continuous 200ms without contact.
  if (snapshot.reading.state === 'TOUCH') return 'touch';
  if (snapshot.reading.state === 'CLEAR') return 'clear';
  return snapshot.reading.raw === 0 ? 'touch' : 'clear';
}
