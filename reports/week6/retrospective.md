# Sprint Retrospective

## What Went Well

### 1. Pattern Detection Functionality Was Successfully Integrated

The team completed the initial machine-learning pattern detection pipeline and integrated it with the charting interface. Multiple pattern types, including Double Top, Double Bottom, Triangle, Head and Shoulders, and Flag, can now be detected and displayed in the application.

### 2. Deployment and Infrastructure Are Stable

The product was successfully deployed on the university VM and remains accessible through the documented Docker-based deployment process. Infrastructure components such as PostgreSQL, TimescaleDB, Grafana, and Prometheus were successfully integrated and tested.

### 3. Customer Review Provided Useful Feedback

The Sprint Review helped identify strengths and weaknesses of the current implementation. The customer confirmed that the deployment process and documentation are understandable and provided actionable recommendations for improving pattern detection and transition readiness.

---

## What Did Not Go Well

### 1. Pattern Visualization Is Still Inconsistent

Although pattern detection is operational, pattern rendering on the chart is not always reliable. Some detected patterns are not visualized correctly, making the feature harder for users to understand.

### 2. Limited Validation of the ML Pipeline

The team relied on a rule-based detector to generate training labels. Due to time constraints, extensive validation of the generated labels and prediction quality was not completed during this sprint.

### 3. Some Documentation and Configuration Improvements Remain

The customer identified several areas for improvement, including moving additional service ports into environment variables and providing a more detailed contribution breakdown for the final project report.

---

## Action Items

### 1. Improve Pattern Detection Reliability

Review the current ML pipeline, manually validate detected patterns, and investigate opportunities to improve prediction quality while preserving the existing implementation as a fallback solution.

### 2. Improve Product Transition Readiness

Finalize customer handover materials, move remaining configuration settings into environment variables, and prepare the contribution traceability information required for the final project delivery.
