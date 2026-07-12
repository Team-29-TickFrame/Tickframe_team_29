# Sprint Review Summary

## Sprint 4 Goal

The goal of Sprint 4 was to improve the TickFrame MVP by enhancing pattern detection functionality, improving chart visualization, refining deployment and infrastructure configuration, and preparing the product for customer transition and independent use.

---

## Work Demonstrated

During the Sprint Review, the team demonstrated the current state of the product, including:

* Interactive dashboard with customizable widgets and layout management.
* Pattern detection functionality integrated into the chart interface.
* Support for multiple chart patterns, including:

  * Double Top
  * Double Bottom
  * Triangle
  * Head and Shoulders
  * Flag (experimental)
* Pattern visualization directly on charts.
* Machine learning pipeline based on historical market data.
* Deployment of the current product version on the university VM.
* Docker-based deployment and infrastructure setup.

---

## Documentation Review

The customer reviewed the current deployment and project documentation.

The team confirmed that:

* Deployment instructions are available in the repository.
* The product can be deployed using Docker containers.
* Database configuration and infrastructure documentation are available.
* Customer handover documentation is being prepared for the final transition stage.

### Customer Feedback

The customer recommended:

* Providing a detailed contribution table describing which team member implemented each feature.
* Moving additional service ports and configuration values into environment variables.
* Improving documentation clarity for future handover.

---

## Machine Learning and Pattern Detection Review

The team presented the current machine learning approach for pattern detection.

Current implementation:

1. Historical Binance market data is used for training.
2. A rule-based detector generates pattern labels.
3. A LightGBM model is trained using those labels.
4. Model predictions are validated by the rule-based detector before visualization.

### Customer Feedback

The customer raised several concerns:

* Pattern labels were generated automatically rather than manually annotated.
* The detector has not been extensively validated independently.
* Current pattern visualization sometimes behaves inconsistently.

### Follow-Up Recommendations

The customer recommended:

* Performing manual validation of detected patterns.
* Investigating opportunities to improve pattern detection accuracy.
* Keeping the current implementation as a fallback solution while experimenting with improvements.
* Exploring alternative approaches if time permits.

---

## Trial Release Review

The current deployed version was reviewed.

The customer confirmed that:

* The application is deployed and accessible.
* The deployment process is documented.
* Infrastructure configuration is understandable.
* Docker-based deployment is appropriate for the project.

---

## Transition Readiness Review

The customer discussed the expected handover process.

Key outcomes:

* The repository and documentation will be sufficient for handover.
* No repository ownership transfer is required.
* The customer plans to clone and use the repository independently.
* Product support after delivery is not expected as part of the course project.

Current transition status:

**Ready for independent use with minor follow-up improvements.**

---

## Customer Trial and UAT Results

The customer successfully reviewed:

* Dashboard functionality.
* Chart visualization.
* Pattern detection workflow.
* Deployment approach.
* Documentation and infrastructure setup.

### Identified Follow-Up Items

* Improve pattern visualization clarity.
* Improve ML pattern detection reliability.
* Move additional configuration parameters into ENV variables.
* Prepare a detailed contribution summary for the final report.

---

## Sprint 5 Follow-Up Work

The following items were carried over to Sprint 5:

1. Improve pattern detection accuracy.
2. Validate detected patterns manually.
3. Improve visualization of detected patterns.
4. Move service ports and additional configuration into environment variables.
5. Finalize customer handover documentation.
6. Prepare final MVP v3 delivery and transition evidence.
