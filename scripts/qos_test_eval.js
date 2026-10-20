import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

const appRequests = new Counter('app_requests');
const appReqFailed = new Rate('app_req_failed');
const appReqDuration = new Trend('app_req_duration', true);
const collectorRequests = new Counter('collector_requests');

const TARGET = __ENV.TARGET || 'http://172.18.0.2:32232';
const COLLECTOR = __ENV.COLLECTOR || 'http://127.0.0.1:18080';
const LOOPS = __ENV.LOOPS || '120000';

export const options = {
  vus: Number(__ENV.VUS || 20),
  duration: __ENV.DURATION || '120s',
  thresholds: {
    app_req_failed: ['rate<0.05'],
    app_req_duration: ['p(95)<2000'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

export default function () {
  const res = http.get(`${TARGET}/?loops=${LOOPS}`, {
    timeout: '10s',
    tags: { endpoint: 'app', name: 'app_get' },
  });

  appRequests.add(1);
  appReqDuration.add(res.timings.duration);
  const ok = check(res, {
    'status is 2xx or 3xx': (r) => r.status >= 200 && r.status < 400,
  });
  appReqFailed.add(!ok);

  const payload = JSON.stringify({
    duration_ms: res.timings.duration,
    failed: ok ? 0 : 1,
    status: res.status,
  });
  const col = http.post(`${COLLECTOR}/record`, payload, {
    headers: { 'Content-Type': 'application/json' },
    timeout: '2s',
    tags: { endpoint: 'collector', name: 'collector_post' },
  });
  collectorRequests.add(1);

  sleep(0.2);
}
