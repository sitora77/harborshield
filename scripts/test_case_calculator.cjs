'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {compare, fundingLedger} = require('../web/case-calculator.js');
const report = JSON.parse(fs.readFileSync(path.join(__dirname, '../reports/case_study.json'), 'utf8'));
const fixture = report.inputs;
const clone = value => JSON.parse(JSON.stringify(value));
const close = (a, b) => assert.ok(Math.abs(a - b) <= 1e-7 * Math.max(1, Math.abs(b)), `${a} != ${b}`);
const actual = compare(fixture), expected = report.selected_comparison;
const numeric = ['availability_day', 'collection_day', 'stockout_days', 'unmet_units', 'purchase_value',
  'sales_receipt', 'planned_contribution', 'logistics_cost', 'stockout_opportunity_cost', 'economic_burden',
  'net_economic_contribution', 'funding_dollar_days', 'funding_cost', 'peak_funding_need',
  'closing_cash_before_interest', 'residual_funding_need'];
for (let i = 0; i < expected.length; i++) {
  assert.equal(actual[i].option_id, expected[i].option_id);
  for (const key of numeric) close(actual[i][key], expected[i][key]);
  assert.deepEqual(actual[i].events, expected[i].events);
}
for (const setting of report.sensitivity) {
  const variant = clone(fixture);
  variant.order.annual_funding_rate = setting.annual_funding_rate;
  variant.order.stock_cover_days = setting.stock_cover_days;
  const best = compare(variant, setting.port_delay_days)[0];
  assert.equal(best.option_id, setting.lowest_burden_option);
  close(best.economic_burden, setting.minimum_economic_burden);
}
const cash = clone(fixture); cash.order.initial_cash = 1000000;
assert.ok(compare(cash).every(row => row.funding_cost === 0));
const zeroRate = clone(fixture); zeroRate.order.annual_funding_rate = 0;
assert.ok(compare(zeroRate).every(row => row.funding_cost === 0));
const zeroDemand = clone(fixture); zeroDemand.order.daily_demand = 0;
assert.ok(compare(zeroDemand).every(row => row.stockout_opportunity_cost === 0));
assert.equal(compare(fixture, 0)[0].option_id, 'standard_sea');
const invalid = clone(fixture); invalid.order.initial_cash = NaN;
assert.throws(() => compare(invalid));
invalid.order.initial_cash = -1; assert.throws(() => compare(invalid));
close(fundingLedger([{day: 0, amount: -100}, {day: 0, amount: 100}, {day: 10, amount: 0}], 0, .1).funding_cost, 0);
console.log('Browser/Python agreement: default metrics, 27 sensitivity cases, boundaries and input rejection passed.');
