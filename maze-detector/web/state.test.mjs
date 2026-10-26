import { test } from 'node:test';
import assert from 'node:assert/strict';
import { displayState } from './state.mjs';

test('contact turns red and release immediately returns green, without a reset', () => {
  const frame = raw => ({ connected: true, reading: { raw } });
  assert.deepEqual([1, 0, 0, 1, 0, 1].map(raw => displayState(frame(raw))),
    ['clear', 'touch', 'touch', 'clear', 'touch', 'clear']);
});

test('missing or disconnected data is not presented as a live reading', () => {
  assert.equal(displayState(null), 'offline');
  assert.equal(displayState({ connected: false, reading: { raw: 1 } }), 'offline');
  assert.equal(displayState({ connected: true, reading: { raw: '0' } }), 'offline');
  assert.equal(displayState({ connected: true }), 'offline');
});

test('brief high input stays red until the firmware confirms release', () => {
  assert.equal(displayState({ connected: true, reading: { raw: 1, state: 'TOUCH' } }), 'touch');
  assert.equal(displayState({ connected: true, reading: { raw: 1, state: 'CLEAR' } }), 'clear');
});
