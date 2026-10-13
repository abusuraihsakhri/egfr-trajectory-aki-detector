'use strict';
const assert = require('node:assert/strict');
const { assessTrajectory, parseCSV } = require('../app.js');
const row = (day, creat) => ({ timestamp: '2026-01-' + String(day).padStart(2, '0'), creatinine_mg_dl: creat });
assert.equal(assessTrajectory([row(1, 1), row(3, 1.3)]).aki_stage, 1);
assert.equal(assessTrajectory([row(1, 1), row(4, 1.3)]).aki_stage, 0);
assert.equal(assessTrajectory([row(1, 1), row(8, 2)]).aki_stage, 2);
assert.equal(assessTrajectory([row(1, 1), row(8, 3)]).aki_stage, 3);
assert.equal(assessTrajectory([row(1, 1), row(9, 3)]).aki_stage, null);
assert.equal(assessTrajectory([row(1, 4.2), row(2, 4.2)]).aki_stage, 0);
assert.equal(assessTrajectory([row(1, 3.7), row(2, 4.1)]).aki_stage, 3);
assert.equal(assessTrajectory([row(1, 1)], { urine_output_ml_kg_h: 0.4, urine_duration_hours: 12 }).aki_stage, 2);
assert.equal(assessTrajectory([row(1, 1)], { urine_output_ml_kg_h: 0, urine_duration_hours: 12 }).aki_stage, 3);
assert.equal(assessTrajectory([row(1, 1)], { renal_replacement_therapy: true }).aki_stage, 3);
assert.equal(assessTrajectory([row(1, 1)]).aki_stage, null);
assert.equal(assessTrajectory([
  {timestamp:'2024-01-01',egfr_ml_min_1_73m2:80},
  {timestamp:'2025-01-01',egfr_ml_min_1_73m2:72},
  {timestamp:'2026-01-01',egfr_ml_min_1_73m2:64}
]).rapid_egfr_decline_flag, true);
assert.equal(assessTrajectory([
  {timestamp:'2026-01-01',egfr_ml_min_1_73m2:80},
  {timestamp:'2026-01-03',egfr_ml_min_1_73m2:64}
]).rapid_egfr_decline_flag, null);
assert.throws(() => assessTrajectory([row(1, 0)]), /positive/);
assert.throws(() => assessTrajectory([row(1, 1), row(1, 1)]), /Duplicate/i);
assert.throws(() => assessTrajectory([{timestamp:'2026-02-30',creatinine_mg_dl:1}]), /date/i);
const input='timestamp,creatinine_mg_dl,egfr_ml_min_1_73m2\n2026-01-01,1,80\n2026-01-03,1.3,70\n';
assert.equal(assessTrajectory(parseCSV(input)).aki_stage, 1);
assert.throws(() => parseCSV('timestamp,creatinine_mg_dl\n2026-01-01,1,extra'), /columns/);
console.log('Browser engine tests passed');
