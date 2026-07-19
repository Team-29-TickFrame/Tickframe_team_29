# Sprint 5 Retrospective

## What Went Well
* The team successfully completed MVP v3 and delivered the planned Sprint Goal. The product reached a stable state with documented deployment, operational scripts, and improved project structure.
* The issue causing inconsistencies between ML pattern detection and chart visualization was resolved. The updated validation logic now ensures that only confirmed patterns are displayed to users.
* Team collaboration remained effective throughout the Sprint. Development, documentation, testing, and deployment tasks were completed on schedule, allowing the team to prepare the final product for review.

## What Did Not Go Well
* The experimental ML component still depends on the rule-based detector for validation and visualization, limiting its independence and making its behavior more difficult to explain during the Sprint Review.
* Some customer-requested improvements, such as the frontend switch between ML-based and rule-based detection and the maintenance script interface, were not fully completed before the Sprint ended.
* Explaining the machine-learning pipeline and evaluation methodology to the customer required additional discussion because the relationship between the ML model and the rule-based detector was more complex than expected.

## Changes Compared with the Previous Sprint
* The team shifted its primary focus from implementing new functionality to stabilizing the existing system, improving documentation, and preparing the project for transition.
* More attention was given to deployment, maintainability, and customer-facing documentation to ensure that the project could be easily launched and understood by future users.
* The review process became more focused on product readiness, operational status, and long-term maintainability rather than adding major new features.

## Action Items
* Complete the remaining customer-requested improvements, including the detection-method switch and the frontend interface for maintenance scripts.
* Continue improving the ML component by reducing its dependence on the rule-based detector and validating the model on larger real-world datasets to improve confidence in its predictions.
