const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err.message || res.statusText);
  }
  return res.json();
}

export const api = {
  // System
  status: () => request('/status'),
  upload: (file) => {
    const form = new FormData();
    form.append('file', file);
    return fetch(`${BASE}/upload`, { method: 'POST', body: form }).then(r => r.json());
  },

  // Review
  review: (paperPath, template, withDeep) => request('/review', {
    method: 'POST', body: JSON.stringify({ paper_path: paperPath, template, with_deep_review: withDeep }),
  }),
  deepReview: (paperPath, withDeep) => request('/review/deep', {
    method: 'POST', body: JSON.stringify({ paper_path: paperPath, with_deep_review: withDeep }),
  }),

  // Literature
  search: (query, sources, limit) => request('/literature/search', {
    method: 'POST', body: JSON.stringify({ query, sources, limit_per_source: limit }),
  }),
  survey: (query, refs) => request('/literature/survey', {
    method: 'POST', body: JSON.stringify({ query, existing_refs: refs }),
  }),
  surveyMarkdown: (query) => fetch(`${BASE}/literature/survey/markdown?query=${encodeURIComponent(query)}`).then(r=>r.text()),

  // Submission
  submissionCheck: (paperPath, journal, stage) => request('/check/submission', {
    method: 'POST', body: JSON.stringify({ paper_path: paperPath, journal, stage }),
  }),

  // Stream
  batchStream: (paths) => {
    return fetch(`${BASE}/review/batch-stream`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(paths),
    });
  },
};
