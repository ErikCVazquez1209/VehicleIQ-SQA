import test from 'node:test';
import assert from 'node:assert/strict';
import { getComponentStatus } from '../lib/component-status.mjs';

const expected = {
  Normal: '#43e97b',
  Atención: '#ffb454',
  Crítico: '#ff0844',
  'Sin evaluación': '#a1a1aa',
};

function assertVisibleStatus(status, label) {
  assert.equal(status.label, label);
  assert.equal(status.color, expected[label]);
}

for (const [component, score, label] of [
  ['brake', 54.9, 'Crítico'],
  ['brake', 55, 'Atención'],
  ['brake', 74.9, 'Atención'],
  ['brake', 75, 'Normal'],
  ['engine', 49.9, 'Crítico'],
  ['engine', 50, 'Atención'],
  ['engine', 79.9, 'Atención'],
  ['engine', 80, 'Normal'],
  ['battery', 49.9, 'Crítico'],
  ['battery', 50, 'Atención'],
  ['battery', 79.9, 'Atención'],
  ['battery', 80, 'Normal'],
]) {
  test(`${component}: ${score}% muestra ${label} con su color`, () => {
    assertVisibleStatus(getComponentStatus(component, score), label);
  });
}

test('sin puntuación válida muestra Sin evaluación', () => {
  for (const score of [null, undefined, NaN, Infinity, -1, 101]) {
    assertVisibleStatus(getComponentStatus('engine', score), 'Sin evaluación');
  }
});

test('una alerta crítica prevalece sobre un porcentaje normal', () => {
  for (const [component, name] of [
    ['brake', 'Brakes'], ['engine', 'Engine Thermal'], ['battery', 'Battery & Alternator'],
  ]) {
    assertVisibleStatus(getComponentStatus(component, 95, [
      { component: name, severity: 'CRITICAL' },
    ]), 'Crítico');
  }
});

test('una alerta de advertencia prevalece sobre un porcentaje normal', () => {
  assertVisibleStatus(getComponentStatus('brake', 95, [
    { component: 'Brakes', severity: 'WARNING' },
  ]), 'Atención');
});

test('una alerta de batería no modifica el estado del motor', () => {
  assertVisibleStatus(getComponentStatus('engine', 95, [
    { component: 'Battery & Alternator', severity: 'CRITICAL' },
  ]), 'Normal');
});

test('una advertencia no reduce un estado ya crítico por puntuación', () => {
  assertVisibleStatus(getComponentStatus('engine', 30, [
    { component: 'Engine Thermal', severity: 'WARNING' },
  ]), 'Crítico');
});

test('una alerta informativa no convierte un estado normal en advertencia', () => {
  assertVisibleStatus(getComponentStatus('battery', 95, [
    { component: 'Battery & Alternator', severity: 'INFO' },
  ]), 'Normal');
});
