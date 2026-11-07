# NeuroScope — EEG Research Dashboard

React + TypeScript + Vite frontend for the EEG seizure-detection research project.

## Current milestone

This is the UI foundation only. The dashboard intentionally uses clearly labelled illustrative mock data. It does not run inference, diagnose seizures, or claim validated model performance.

## Requirements

- Node.js 20.19+ or 22.12+
- npm 10+

## Setup (PowerShell)

From this directory:

```powershell
npm install
npm run dev
```

Open http://127.0.0.1:5173.

## Production build

```powershell
npm run build
npm run preview
```

## Structure

```text
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── src/
    ├── App.tsx
    ├── main.tsx
    └── styles.css
```

## Current screens

- Overview: audited cohort context, protocol summary and recent-recording preview.
- EEG Analysis: illustrative multichannel waveform display.
- Recordings: searchable sample recording table.
- Model Performance: intentionally shows a not-yet-available state.
- Patients: placeholder for patient-level summaries.

## Data and safety

- No real patient-level data is bundled in this frontend.
- Sample recording identifiers are illustrative UI content, not live backend records.
- EEG signal preview is synthetic and must not be interpreted as a clinical trace.
- The application is an academic research prototype, not a medical device.
- Backend integration will be added only after API contracts and model outputs are validated.

## Planned integration

The frontend will consume a FastAPI backend through a typed API client. Planned capabilities include dataset status, recording metadata, EEG window retrieval, inference jobs, and evaluation summaries. Model metrics must come from held-out patient-wise evaluation; never populate performance charts with fabricated results.
