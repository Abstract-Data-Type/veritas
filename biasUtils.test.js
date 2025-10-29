import { getBiasClass, getBiasText } from '../src/utils/biasUtils';

describe('Bias Utils', () => {
  test('getBiasClass returns correct class for left bias', () => {
    expect(getBiasClass(-0.7)).toBe('bias-left');
    expect(getBiasClass(-0.5)).toBe('bias-left');
  });

  test('getBiasClass returns correct class for right bias', () => {
    expect(getBiasClass(0.7)).toBe('bias-right');
    expect(getBiasClass(0.5)).toBe('bias-right');
  });

  test('getBiasClass returns correct class for center bias', () => {
    expect(getBiasClass(0.3)).toBe('bias-center');
    expect(getBiasClass(-0.3)).toBe('bias-center');
    expect(getBiasClass(0)).toBe('bias-center');
  });

  test('getBiasText returns correct label for bias scores', () => {
    expect(getBiasText(-0.7)).toBe('Strong Left');
    expect(getBiasText(-0.4)).toBe('Lean Left');
    expect(getBiasText(0)).toBe('Center');
    expect(getBiasText(0.4)).toBe('Lean Right');
    expect(getBiasText(0.7)).toBe('Strong Right');
  });
});